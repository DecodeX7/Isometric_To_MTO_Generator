from __future__ import annotations

import json
import re
import time
from typing import Any

from app.core.config import Settings
from app.models.mto import MTOResponse
from app.pipeline.base import PipelineError
from app.pipeline.mock_pipeline import MockPipeline
from app.pipeline.postprocess import normalize_and_enrich_mto
from app.pipeline.preprocess import VisionImage, preprocess_to_vision_images
from app.pipeline.prompt import EXTRACTION_PROMPT, FAST_EXTRACTION_PROMPT, MTO_JSON_SCHEMA


class GeminiPipeline:
    name = "gemini"

    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key:
            raise PipelineError("GEMINI_API_KEY is not configured.")
        self.settings = settings

    def extract(self, file_bytes: bytes, content_type: str, filename: str) -> MTOResponse:
        try:
            return self._extract_with_gemini(file_bytes, content_type, filename)
        except Exception as exc:
            if self.settings.fallback_to_mock_on_llm_error:
                fallback = MockPipeline().extract(file_bytes, content_type, filename)
                fallback.extraction_info.provider = "mock"
                fallback.extraction_info.model = "mock"
                fallback.extraction_info.mode = "mock_fallback_after_llm_error"
                fallback.extraction_info.warnings.append(
                    "Gemini extraction failed; returned mock fallback so the app remains runnable. "
                    f"Technical detail: {exc.__class__.__name__}: {str(exc)[:500]}"
                )
                return fallback
            if isinstance(exc, PipelineError):
                raise
            raise PipelineError(f"Gemini extraction failed: {exc.__class__.__name__}: {exc}") from exc

    def _extract_with_gemini(self, file_bytes: bytes, content_type: str, filename: str) -> MTOResponse:
        try:
            from google import genai
            from google.genai import types
        except Exception as exc:  # pragma: no cover - import depends on installed package
            raise PipelineError("google-genai package is not installed correctly.") from exc

        images = preprocess_to_vision_images(file_bytes, content_type)
        client = genai.Client(api_key=self.settings.gemini_api_key)

        # Fast path first: JSON MIME mode without a strict response_schema. This
        # is much more reliable for dense scanned drawings and older google-genai
        # SDK versions. The prompt still contains the exact schema and the
        # backend still validates with Pydantic.
        attempts = [
            {
                "mode": "vision_llm_json_optimized_multi_view",
                "prompt": f"{FAST_EXTRACTION_PROMPT}\n\n{EXTRACTION_PROMPT}",
                "use_schema": False,
                "temperature": 0.05,
            },
            {
                "mode": "vision_llm_schema_retry",
                "prompt": EXTRACTION_PROMPT,
                "use_schema": True,
                "temperature": 0.1,
            },
        ]

        errors: list[str] = []
        for attempt in attempts:
            started = time.perf_counter()
            try:
                response = self._generate(types, client, images, attempt)
                raw = _response_to_data(response)
                raw.setdefault("extraction_info", {})
                raw["extraction_info"].update(
                    {
                        "provider": "google_ai_studio",
                        "model": self.settings.gemini_model,
                        "mode": attempt["mode"],
                    }
                )
                result = normalize_and_enrich_mto(raw)
                elapsed = round(time.perf_counter() - started, 2)
                result.extraction_info.warnings.append(
                    f"Live Gemini extraction completed in {elapsed}s using {len(images)} optimized image views for {filename}."
                )
                return result
            except Exception as exc:
                errors.append(f"{attempt['mode']}: {exc.__class__.__name__}: {str(exc)[:400]}")
                continue

        raise PipelineError("All Gemini extraction attempts failed. " + " | ".join(errors))

    def _generate(self, types: Any, client: Any, images: list[VisionImage], attempt: dict[str, Any]) -> Any:
        contents: list[Any] = [attempt["prompt"]]
        for image in images:
            contents.append(
                f"\nImage view: {image.label}. Size: {image.width}x{image.height}. "
                "Use this view together with the other views; it is not a different drawing."
            )
            contents.append(types.Part.from_bytes(data=image.data, mime_type=image.mime_type))

        config_kwargs: dict[str, Any] = {
            "temperature": attempt["temperature"],
            "response_mime_type": "application/json",
        }
        # Newer google-genai versions support max_output_tokens. If an older
        # version rejects it, the TypeError handler below retries without it.
        config_kwargs["max_output_tokens"] = 8192
        if attempt["use_schema"]:
            config_kwargs["response_schema"] = MTO_JSON_SCHEMA

        try:
            config = types.GenerateContentConfig(**config_kwargs)
        except TypeError:
            config_kwargs.pop("max_output_tokens", None)
            config = types.GenerateContentConfig(**config_kwargs)

        return client.models.generate_content(
            model=self.settings.gemini_model,
            contents=contents,
            config=config,
        )


def _response_to_data(response: Any) -> dict:
    """Convert a Gemini response into a JSON object."""

    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, dict):
        return parsed

    text = getattr(response, "text", None)
    if not text:
        # Some SDK versions expose candidates rather than response.text.
        candidates = getattr(response, "candidates", None)
        if candidates:
            text_parts: list[str] = []
            for candidate in candidates:
                content = getattr(candidate, "content", None)
                for part in getattr(content, "parts", []) or []:
                    part_text = getattr(part, "text", None)
                    if part_text:
                        text_parts.append(part_text)
            text = "\n".join(text_parts).strip()

    if not text:
        raise PipelineError("Gemini returned an empty response.")

    return _parse_json_text(text)


def _parse_json_text(text: str) -> dict:
    """Parse model JSON, tolerating accidental fences or leading prose."""

    cleaned = text.strip()
    if cleaned.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.DOTALL)
        if match:
            cleaned = match.group(1).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise PipelineError("Gemini returned invalid JSON.")
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise PipelineError("Gemini returned invalid JSON.") from exc

    if not isinstance(data, dict):
        raise PipelineError("Gemini JSON root must be an object.")
    return data
