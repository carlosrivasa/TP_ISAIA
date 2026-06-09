from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    llm_provider: str = "mock"
    storage: str = "local"
    data_dir: Path = Path("./backend/data")
    cors_allow_origins: list[str] = ["http://localhost:5500"]
    rate_limit_per_minute: int = 10


settings = Settings()
