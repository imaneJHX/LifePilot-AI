from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    database_url: str = f"sqlite:///{(ROOT / 'lifepilot.db').as_posix()}"
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://localhost",  # Packaged Capacitor Android WebView.
    ]
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:latest"
    ollama_timeout_seconds: float = Field(default=60, gt=0, le=300)
    dataset_path: Path = ROOT / "data" / "sample" / "universities.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
