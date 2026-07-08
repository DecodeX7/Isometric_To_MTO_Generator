import io
import os
import time

os.environ.setdefault("USE_MOCK_PIPELINE", "true")

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.main import app  # noqa: E402


def _tiny_png() -> bytes:
    image = Image.new("RGB", (50, 50), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_upload_and_get_mock_mto() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/upload",
        files={"file": ("sample.png", _tiny_png(), "image/png")},
    )

    assert response.status_code == 202
    job_id = response.json()["job_id"]

    result_response = None
    for _ in range(10):
        result_response = client.get(f"/api/mto/{job_id}")
        if result_response.json()["status"] == "completed":
            break
        time.sleep(0.1)

    assert result_response is not None
    assert result_response.status_code == 200
    body = result_response.json()
    assert body["status"] == "completed"
    assert body["result"]["summary"]["total_pipe_length_m"] > 0

    csv_response = client.get(f"/api/mto/{job_id}/csv")
    assert csv_response.status_code == 200
    assert "item_no,category,description" in csv_response.text
