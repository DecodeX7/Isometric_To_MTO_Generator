from functools import lru_cache

from app.core.config import get_settings
from app.pipeline.base import ExtractionPipeline
from app.pipeline.gemini_pipeline import GeminiPipeline
from app.pipeline.mock_pipeline import MockPipeline


@lru_cache
def get_pipeline() -> ExtractionPipeline:
    settings = get_settings()
    if settings.use_mock_pipeline or not settings.gemini_api_key:
        return MockPipeline()
    return GeminiPipeline(settings)
