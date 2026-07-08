from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    The env file list supports running the backend either from the repository
    root or directly from the backend/ directory.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Isometric MTO Generator"
    api_prefix: str = "/api"

    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    use_mock_pipeline: bool = Field(default=False, alias="USE_MOCK_PIPELINE")
    fallback_to_mock_on_llm_error: bool = Field(
        default=True, alias="FALLBACK_TO_MOCK_ON_LLM_ERROR"
    )
    ai_job_timeout_seconds: int = Field(
        default=420, alias="AI_JOB_TIMEOUT_SECONDS"
    )

    max_upload_size_mb: int = Field(default=20, alias="MAX_UPLOAD_SIZE_MB")
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="CORS_ORIGINS",
    )
    upload_dir: Path = Path(".uploads")

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
