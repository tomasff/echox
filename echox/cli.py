from pathlib import Path

import click
import logging

from echox.config import Config
from echox.credentials import Credentials
from echox.echo_client import EchoClient, Media, MediaFile
from echox.index import Index


_DEFAULT_CONFIG_PATH = Path.home() / ".echox.toml"


def _save_media_file(
    *,
    echo_client: EchoClient,
    index: Index,
    media: Media,
    file: MediaFile,
    media_path: Path,
):
    if not file.is_processed:
        logging.info(
            "Skipping file %s for media %s as it is not processed.",
            file.name,
            media.media_id,
        )
        return

    if index.has_media(media_id=media.media_id, file_name=file.name):
        logging.info(
            "Skipping file %s for media %s as it is already present in the index.",
            file.name,
            media.media_id,
        )
        return

    save_directory = media_path / media.course.id / media.lesson.id
    save_directory.mkdir(parents=True, exist_ok=True)

    logging.info(
        "Downloading file %s for media %s.",
        file.name,
        media.media_id,
    )
    echo_client.save_media_file(
        media=media,
        target_file=file.name,
        save_path=save_directory / file.name,
    )

    logging.info(
        "Creating index entry for file %s and media %s.",
        file.name,
        media.media_id,
    )
    index.create_media(
        media_id=media.media_id,
        file_name=file.name,
        for_lesson_id=media.lesson.id,
    )

    logging.info("File %s for media %s complete.", file.name, media.media_id)


def _download_media_if_not_exists(
    *,
    echo_client: EchoClient,
    index: Index,
    media_path: Path,
    media_id: str,
):
    media = echo_client.get_media(media_id=media_id)

    index.create_course_or_update(
        course_id=media.course.id,
        course_name=media.course.name,
        course_code=media.course.code,
    )

    index.create_lesson_or_update(
        lesson_id=media.lesson.id,
        lesson_name=media.lesson.name,
        for_course_id=media.course.id,
    )

    for file in media.files:
        _save_media_file(
            echo_client=echo_client,
            index=index,
            media=media,
            file=file,
            media_path=media_path,
        )


@click.command()
@click.option(
    "--config",
    "config_path",
    default=_DEFAULT_CONFIG_PATH,
    required=True,
    type=click.Path(exists=True),
)
def cli(config_path: Path):
    logging.basicConfig(level=logging.INFO)

    config = Config.from_file(config_path)
    config.media_path.mkdir(parents=True, exist_ok=True)

    credentials = Credentials.from_env()

    index = Index(config.media_path / "index.db")
    echo_client = EchoClient(
        user_agent=config.user_agent,
        chunk_size=config.chunk_size,
        email=credentials.email,
        password=credentials.password,
        app_id=credentials.app_id,
    )

    with index, echo_client:
        for section in config.sections:
            logging.info("Fetching syllabus for section %s", section)

            syllabus = echo_client.get_syllabus(section_id=section)
            media_ids = [
                media["id"]
                for lesson in syllabus
                for media in lesson["lesson"]["medias"]
            ]

            logging.info(
                "Found %d media(s) for section %s", len(media_ids), section
            )

            for media_id in media_ids:
                _download_media_if_not_exists(
                    echo_client=echo_client,
                    index=index,
                    media_id=media_id,
                    media_path=config.media_path,
                )


if __name__ == "__main__":
    cli()
