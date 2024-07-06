import dataclasses
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from lxml import html

_LOGIN_HOST = "https://login.echo360.org.uk/"
_BASE_HOST = "https://echo360.org.uk/"

_ECHO_OK_STATUS = "ok"
_REQUIRED_COOKIES = {
    "ECHO_JWT",
    "PLAY_SESSION",
    "CloudFront-Key-Pair-Id",
    "CloudFront-Policy",
    "CloudFront-Signature",
    "CloudFront-Tracking2",
}


@dataclasses.dataclass
class EchoUser:
    user_id: str
    institution_id: str
    app_id: str


@dataclasses.dataclass
class Course:
    id: str
    name: str
    code: str


@dataclasses.dataclass
class MediaFile:
    name: str
    size: int
    is_processed: bool


@dataclasses.dataclass
class Lesson:
    id: str
    name: str


@dataclasses.dataclass
class Media:
    organization_id: str
    department_id: str

    section_id: str
    media_id: str

    lesson: Lesson
    course: Course
    files: list[MediaFile]


class EchoException(Exception):
    def __init__(self, error: str):
        super().__init__(error)


def _get_url_singular_query_params(url: str) -> dict[str, str]:
    query_params = parse_qs(
        urlparse(url).query,
        strict_parsing=True,
        keep_blank_values=False,
    )

    return {name: value for name, (value, *_) in query_params.items()}


class EchoClient:
    def __init__(
        self,
        user_agent: str,
        chunk_size: int,
        email: str,
        password: str,
        app_id: str,
    ):
        self._user_agent = user_agent
        self._chunk_size = chunk_size

        self._email = email
        self._password = password
        self._app_id = app_id

        self._session = None
        self._user = None

    def _make_session(self):
        session = requests.Session()

        session.headers.update(
            {
                "User-Agent": self._user_agent,
            }
        )

        return session

    def __enter__(self):
        self._session = self._make_session()
        self._user = self.login(
            email=self._email,
            password=self._password,
            app_id=self._app_id,
        )

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._session.close()

    def _begin_institution_authentication(
        self,
        *,
        email: str,
        app_id: str,
    ) -> tuple[str, EchoUser]:
        institutions_response = self._session.post(
            url=urljoin(_LOGIN_HOST, "/login/institutions"),
            data={
                "email": email,
                "appId": app_id,
                "role": "",
                "requestedResource": "",
            },
            allow_redirects=True,
        )

        if institutions_response.status_code != 200:
            raise EchoException(
                "Failed to find institution while attempting to login."
            )

        login_url = institutions_response.url
        login_url_query_params = _get_url_singular_query_params(login_url)

        if "userId" not in login_url_query_params:
            raise EchoException(
                "Failed to obtain the the user ID from authentication."
            )

        if "callbackUrl" not in login_url_query_params:
            raise EchoException(
                "Failed to obtain the callback URL for authentication."
            )

        callback_url = login_url_query_params.get("callbackUrl")
        callback_url_query_params = _get_url_singular_query_params(
            callback_url
        )

        if "institutionId" not in callback_url_query_params:
            raise EchoException(
                "Failed to obtain the institution ID for authentication."
            )

        user = EchoUser(
            user_id=login_url_query_params["userId"],
            institution_id=callback_url_query_params["institutionId"],
            app_id=app_id,
        )

        return login_url, callback_url, user

    def _extract_nonce_and_completion_url(
        self,
        login_response: str,
    ) -> tuple[str, str]:
        login_completion_form = html.fromstring(login_response).find(".//form")

        if login_completion_form is None:
            raise EchoException("Failed to find the login completion form.")

        completion_url = login_completion_form.get("action")

        if completion_url is None:
            raise EchoException("Failed to find the login completion URL.")

        nonce_input = login_completion_form.find(".//input[@name='nonce']")

        if nonce_input is None:
            raise EchoException(
                "Failed to find the authentication nonce input."
            )

        nonce = nonce_input.get("value")

        if nonce is None:
            raise EchoException("Failed to find the authentication nonce.")

        return nonce, completion_url

    def _apply_institution_credentials(
        self,
        *,
        login_url: str,
        callback_url: str,
        email: str,
        password: str,
    ) -> tuple[str, str]:
        login_response = self._session.post(
            url=login_url,
            data={
                "email": email,
                "password": password,
                "callbackUrl": callback_url,
                "readOnly": "readonly",
            },
            allow_redirects=True,
        )

        if login_response.status_code != 200:
            raise EchoException("Failed to apply credentials.")

        return self._extract_nonce_and_completion_url(login_response.text)

    def _complete_institution_login(
        self,
        *,
        completion_url: str,
        nonce: str,
    ):
        login_response = self._session.post(
            url=completion_url,
            data={
                "nonce": nonce,
            },
            allow_redirects=True,
        )

        if login_response.status_code != 200:
            raise EchoException(
                "Failed to complete authentication: response not ok."
            )

        if not _REQUIRED_COOKIES.issubset(self._session.cookies.keys()):
            raise EchoException(
                "Failed to complete authentication: missing required cookies."
            )

    def login(
        self,
        *,
        email: str,
        password: str,
        app_id: str,
    ) -> EchoUser:
        login_url, callback_url, user = self._begin_institution_authentication(
            email=email,
            app_id=app_id,
        )

        nonce, completion_url = self._apply_institution_credentials(
            login_url=login_url,
            callback_url=callback_url,
            email=email,
            password=password,
        )

        self._complete_institution_login(
            nonce=nonce,
            completion_url=completion_url,
        )

        return user

    def get_syllabus(
        self,
        *,
        section_id: str,
    ) -> dict[str, str]:
        response = self._session.get(
            urljoin(_BASE_HOST, f"/section/{section_id}/syllabus")
        )

        if response.status_code != 200:
            raise EchoException(
                f"Failed to get the syllabus for section {section_id}."
            )

        syllabus = response.json()

        if syllabus["status"] != _ECHO_OK_STATUS:
            raise EchoException(f"Status not ok for section {section_id}.")

        return syllabus["data"]

    def get_media_details(
        self,
        *,
        media_id: str,
    ) -> dict[str, Any]:
        response = self._session.get(
            urljoin(_BASE_HOST, f"/media/{media_id}/details")
        )

        if response.status_code != 200:
            raise EchoException(f"Failed to get media {media_id} details.")

        media_details = response.json()

        if media_details["status"] != _ECHO_OK_STATUS:
            raise EchoException(f"Status not ok for media {media_id}.")

        media_details, *_ = media_details["data"]

        return media_details

    def get_media(
        self,
        *,
        media_id: str,
    ) -> Media:
        media_details = self.get_media_details(media_id=media_id)

        course_id, *_ = media_details["media"]["publishedCourseIds"]
        section_id, *_ = media_details["media"]["publishedSectionIds"]
        lesson_id, *_ = media_details["media"]["publishedLessonIds"]
        organization_id, *_ = media_details["details"][
            "publishedOrgsByCourseId"
        ][course_id]["id"]
        department_id, *_ = media_details["details"][
            "publishedDeptsByCourseId"
        ][course_id]["id"]

        course = Course(
            id=course_id,
            name=media_details["coursesById"][course_id]["name"],
            code=media_details["coursesById"][course_id]["identifier"],
        )

        lesson = Lesson(
            id=lesson_id, name=media_details["lessonsById"][lesson_id]["name"]
        )

        files = [
            MediaFile(
                name=file["name"],
                size=file["fileSize"],
                is_processed=file["isProcessedFile"],
            )
            for file in media_details["details"]["files"]
        ]

        return Media(
            media_id=media_id,
            course=course,
            lesson=lesson,
            files=files,
            organization_id=organization_id,
            department_id=department_id,
            section_id=section_id,
        )

    def save_media_file(
        self,
        *,
        media: Media,
        target_file: str,
        save_path: Path,
    ):
        response = self._session.get(
            urljoin(
                _BASE_HOST,
                f"/media/download/{media.media_id}/{target_file}",
            ),
            stream=True,
        )

        if response.status_code != 200:
            raise EchoException(f"Failed to download media {media}.")

        with response, open(save_path, "wb") as file:
            for chunk in response.iter_content(
                chunk_size=self._chunk_size,
                decode_unicode=False,
            ):
                file.write(chunk)
