import anyio
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.core.config import Settings, get_settings
from app.models.jobs import JobResponse, JobState, UploadResponse
from app.pipeline.base import PipelineError
from app.pipeline.factory import get_pipeline
from app.pipeline.mock_pipeline import MockPipeline
from app.services.csv_service import mto_to_csv
from app.services.file_service import read_and_validate_upload
from app.services.job_store import job_store

router = APIRouter(tags=["mto"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload one isometric drawing for MTO extraction",
)
async def upload_drawing(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    settings: Settings = Depends(get_settings),
) -> UploadResponse:
    payload = await read_and_validate_upload(file, settings)
    job = job_store.create(payload.filename)
    background_tasks.add_task(
        process_job,
        job.job_id,
        payload.data,
        payload.content_type,
        payload.filename,
    )
    return UploadResponse(job_id=job.job_id, status=job.status)


@router.get("/mto/{job_id}", response_model=JobResponse, summary="Get MTO extraction job status")
def get_mto(job_id: str) -> JobResponse:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return job.to_response()


@router.get("/mto/{job_id}/csv", summary="Download completed MTO as CSV")
def download_mto_csv(job_id: str) -> Response:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    if job.status != JobState.COMPLETED or job.result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="MTO is not ready yet. Wait until the job status is completed.",
        )

    csv_data = mto_to_csv(job.result)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{job_id}_mto.csv"'},
    )


async def process_job(job_id: str, file_bytes: bytes, content_type: str, filename: str) -> None:
    """Run the extraction job with a hard timeout.

    Real vision LLM calls can occasionally take longer than the frontend polling
    window, especially for dense scanned PDFs. The timeout below is intentionally generous
    for live Gemini extraction. If Gemini still does not finish in time and
    fallback is enabled, the job completes with a clearly labelled mock result
    instead of staying stuck in `processing` forever.
    """

    settings = get_settings()
    job_store.mark_processing(job_id)
    try:
        pipeline = get_pipeline()
        with anyio.fail_after(settings.ai_job_timeout_seconds):
            result = await anyio.to_thread.run_sync(
                pipeline.extract,
                file_bytes,
                content_type,
                filename,
                abandon_on_cancel=True,
            )
        job_store.mark_completed(job_id, result)
    except TimeoutError:
        if settings.fallback_to_mock_on_llm_error:
            result = MockPipeline().extract(file_bytes, content_type, filename)
            result.extraction_info.provider = "mock"
            result.extraction_info.model = "mock"
            result.extraction_info.mode = "mock_fallback_after_timeout"
            result.extraction_info.warnings.append(
                f"Live Gemini extraction exceeded {settings.ai_job_timeout_seconds} seconds; returned mock fallback so the app remains runnable."
            )
            job_store.mark_completed(job_id, result)
        else:
            job_store.mark_failed(
                job_id,
                f"AI extraction timed out after {settings.ai_job_timeout_seconds} seconds.",
            )
    except PipelineError as exc:
        job_store.mark_failed(job_id, str(exc))
    except Exception as exc:  # pragma: no cover - defensive server boundary
        job_store.mark_failed(job_id, f"Unexpected processing error: {exc.__class__.__name__}")
