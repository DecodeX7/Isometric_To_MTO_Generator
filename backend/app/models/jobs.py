from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from app.models.mto import MTOResponse


class JobState(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class UploadResponse(BaseModel):
    job_id: str
    status: JobState


class JobResponse(BaseModel):
    job_id: str
    status: JobState
    filename: str
    result: MTOResponse | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class ErrorResponse(BaseModel):
    detail: str = Field(..., examples=["Unsupported file type"])
