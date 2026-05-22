from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Look for .env in the repo root (two levels up from this file: pipeline/pipeline/config.py)
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/recording_pipeline"
    redis_url: str = "redis://localhost:6379"
    storage_base_path: str = "./storage"
    anthropic_api_key: str = ""
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    max_input_duration_s: int = 1800
    worker_max_jobs: int = 1
    job_timeout_s: int = 3600
    music_track_path: str = ""  # Optional: path to background music MP3/WAV


@lru_cache()
def get_settings() -> Settings:
    return Settings()
