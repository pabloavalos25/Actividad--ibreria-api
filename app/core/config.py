from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8', extra='ignore',
        hide_input_in_errors=True,
    )

    postgres_user: str = Field(min_length=1)
    postgres_password: SecretStr = Field(min_length=1)
    postgres_db: str = Field(min_length=1)
    postgres_host: str = Field(min_length=1)
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    jwt_secret: SecretStr = Field(min_length=1)
    echo_sql: bool = Field(
        default=False, validation_alias=AliasChoices('SQL_ECHO', 'ECHO_SQL'),
    )
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    bcrypt_rounds: int = Field(default=12, ge=4, le=31)
    bcrypt_concurrency: int = Field(default=4, ge=1)
    jwt_ttl_seconds: int = Field(default=1800, ge=1)
    cookie_secure: bool = False

    @computed_field(repr=False)
    @property
    def database_url(self) -> str:
        return URL.create(
            'postgresql+asyncpg',
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        ).render_as_string(hide_password=False)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
