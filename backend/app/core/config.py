import json

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Ensight API"
    api_prefix: str = "/api"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("["):
                return json.loads(s)
            parts = [x.strip() for x in s.split(",") if x.strip()]
            return parts if parts else ["http://localhost:5173"]
        return v
    db_host: str = Field(default="127.0.0.1", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="postgres", alias="DB_NAME")
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_password: str = Field(default="postgres", alias="DB_PASSWORD")
    db_schema: str = Field(default="capstone", alias="DB_SCHEMA")
    db_sslmode: str = Field(default="require", alias="DB_SSLMODE")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", env_prefix="")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?sslmode={self.db_sslmode}"
        )


settings = Settings()
