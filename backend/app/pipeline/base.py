from typing import Protocol

from app.models.mto import MTOResponse


class PipelineError(RuntimeError):
    """Raised when extraction fails in a controlled way."""


class ExtractionPipeline(Protocol):
    name: str

    def extract(self, file_bytes: bytes, content_type: str, filename: str) -> MTOResponse:
        """Convert an uploaded drawing into a validated MTO response."""
