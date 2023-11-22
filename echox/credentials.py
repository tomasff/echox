import os
import dataclasses


@dataclasses.dataclass
class Credentials:
    email: str
    password: str
    app_id: str

    @staticmethod
    def from_env():
        """Loads credentials from the environment."""
        return Credentials(
            email=os.getenv("ECHO360_EMAIL"),
            password=os.getenv("ECHO360_PASSWORD"),
            app_id=os.getenv("ECHO360_APP_ID"),
        )
