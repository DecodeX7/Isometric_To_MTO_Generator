from dataclasses import dataclass
from pathlib import Path
import mimetypes

from fastapi import HTTPException, UploadFile, status

from app.core.config import Settings


ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "application/pdf"}
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}


@dataclass(frozen=True)
class UploadedPayload:
    filename: str
    content_type: str
    data: bytes


async def read_and_validate_upload(file: UploadFile, settings: Settings) -> UploadedPayload:
    """Read an uploaded file safely while enforcing type and size limits.

    The frontend also validates files, but server-side validation is the source
    of truth because clients cannot be trusted.
    """

    original_name = file.filename or "uploaded_drawing"
    extension = Path(original_name).suffix.lower()
    guessed_mime = mimetypes.guess_type(original_name)[0]
    content_type = file.content_type or guessed_mime or "application/octet-stream"

    if content_type == "application/octet-stream" and guessed_mime:
        content_type = guessed_mime

    if content_type not in ALLOWED_MIME_TYPES or extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Unsupported file type. Upload one PNG, JPG/JPEG, or PDF piping "
                "isometric drawing."
            ),
        )

    chunks: list[bytes] = []
    total_size = 0
    chunk_size = 1024 * 1024

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum allowed size is {settings.max_upload_size_mb} MB.",
            )
        chunks.append(chunk)

    if total_size == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    return UploadedPayload(filename=original_name, content_type=content_type, data=b"".join(chunks))
