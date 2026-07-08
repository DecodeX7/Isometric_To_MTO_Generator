from fastapi import APIRouter

from app.core.config import get_settings
from app.pipeline.factory import get_pipeline

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    pipeline = get_pipeline()
    return {
        "status": "ok",
        "app": settings.app_name,
        "pipeline": pipeline.name,
        "gemini_model": settings.gemini_model,
        "max_upload_size_mb": settings.max_upload_size_mb,
        "ai_job_timeout_seconds": settings.ai_job_timeout_seconds,
    }
