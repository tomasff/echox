"""An index to keep track of the media that has already been downloaded."""
import sqlite3
from pathlib import Path

_COURSE_SCHEMA = """
    CREATE TABLE IF NOT EXISTS course (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        code TEXT NOT NULL
    )
"""

_LESSON_SCHEMA = """
    CREATE TABLE IF NOT EXISTS lesson (
        id TEXT PRIMARY KEY,
        name TEXT,
        for_course TEXT NOT NULL,
        FOREIGN KEY (for_course) REFERENCES course(id)
    )
"""

_MEDIA_SCHEMA = """
    CREATE TABLE IF NOT EXISTS media (
        id TEXT NOT NULL,
        file_name TEXT NOT NULL,
        for_lesson TEXT NOT NULL,
        PRIMARY KEY (id, file_name),
        FOREIGN KEY (for_lesson) REFERENCES lesson(id)
    )
"""


class Index:
    _connection: sqlite3.Connection

    def __init__(self, path: Path):
        self._path = path
        self._connection = None

    def _initialize_index(self):
        with self._connection:
            self._connection.execute(_COURSE_SCHEMA)
            self._connection.execute(_LESSON_SCHEMA)
            self._connection.execute(_MEDIA_SCHEMA)

    def __enter__(self):
        self._connection = sqlite3.connect(self._path)
        self._initialize_index()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._connection.close()

    def create_course_or_update(
        self,
        course_id: str,
        course_name: str,
        course_code: str,
    ):
        with self._connection:
            self._connection.execute(
                (
                    "INSERT INTO course(id, name, code) "
                    "VALUES (?, ?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET "
                    "name = excluded.name,"
                    "code = excluded.code"
                ),
                (course_id, course_name, course_code),
            )

    def create_lesson_or_update(
        self,
        *,
        lesson_id: str,
        lesson_name: str,
        for_course_id: str,
    ):
        with self._connection:
            self._connection.execute(
                (
                    "INSERT INTO lesson(id, name, for_course) "
                    "VALUES (?, ?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET "
                    "name = excluded.name,"
                    "for_course = excluded.for_course"
                ),
                (lesson_id, lesson_name, for_course_id),
            )

    def has_media(self, *, media_id: str, file_name: str) -> bool:
        with self._connection:
            cursor = self._connection.cursor()
            result = cursor.execute(
                "SELECT EXISTS (SELECT 1 FROM media WHERE id=? AND file_name=?)",
                (media_id, file_name),
            )

            exists, *_ = result.fetchone()

            return exists == 1

    def create_media(
        self,
        *,
        media_id: str,
        file_name: str,
        for_lesson_id: str,
    ):
        with self._connection:
            self._connection.execute(
                (
                    "INSERT INTO media"
                    "(id, file_name, for_lesson) "
                    "VALUES (?, ?, ?)"
                ),
                (media_id, file_name, for_lesson_id),
            )
