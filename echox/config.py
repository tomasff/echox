import tomllib
import dataclasses
from pathlib import Path


@dataclasses.dataclass
class Config:
    user_agent: str
    chunk_size: int

    media_path: Path
    sections: list[str]

    @staticmethod
    def from_file(path: Path):
        """Loads the configuration from a file."""
        with open(path, "rb") as config_file:
            config_file_data = tomllib.load(config_file)

        return Config(
            chunk_size=config_file_data["chunk_size"],
            user_agent=config_file_data["user_agent"],
            media_path=Path(config_file_data["media_path"]),
            sections=config_file_data["sections"],
        )
