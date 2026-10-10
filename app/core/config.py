import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    database_url: str
    echo_sql: bool


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Falta DATABASE_URL: definila en el archivo .env")
    echo_sql = os.getenv("ECHO_SQL", "false").strip().lower() in {"1", "true", "yes"}
    return Settings(database_url=database_url, echo_sql=echo_sql)
