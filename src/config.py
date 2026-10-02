import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    token: str
    voicevox_url: str
    db_path: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            token = os.environ["API_TOKEN"],
            voicevox_url = os.environ["VOICEVOX_URL"].rstrip("/"),
            db_path = os.environ.get("DB_PATH", "./data.db"),
        )
