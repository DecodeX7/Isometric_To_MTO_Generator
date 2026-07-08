from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from app.models.jobs import JobResponse, JobState
from app.models.mto import MTOResponse


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class JobRecord:
    job_id: str
    filename: str
    status: JobState = JobState.QUEUED
    result: MTOResponse | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_response(self) -> JobResponse:
        return JobResponse(
            job_id=self.job_id,
            status=self.status,
            filename=self.filename,
            result=self.result,
            error=self.error,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class InMemoryJobStore:
    """Small in-memory job store suitable for the assessment.

    A production system would replace this with Redis, a database, and a worker
    queue. A lock is used so background processing and request threads do not
    mutate job state at the same time.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = RLock()

    def create(self, filename: str) -> JobRecord:
        with self._lock:
            job = JobRecord(job_id=str(uuid4()), filename=filename)
            self._jobs[job.job_id] = job
            return job

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def mark_processing(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = JobState.PROCESSING
            job.updated_at = utc_now()

    def mark_completed(self, job_id: str, result: MTOResponse) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = JobState.COMPLETED
            job.result = result
            job.error = None
            job.updated_at = utc_now()

    def mark_failed(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = JobState.FAILED
            job.error = error
            job.updated_at = utc_now()


job_store = InMemoryJobStore()
