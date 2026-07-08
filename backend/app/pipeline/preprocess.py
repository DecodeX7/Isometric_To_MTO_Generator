from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps

from app.pipeline.base import PipelineError


MAX_PRIMARY_SIDE = 1600
MAX_SECONDARY_SIDE = 1300
JPEG_QUALITY = 84


@dataclass(frozen=True)
class VisionImage:
    """One optimized view of the uploaded drawing for the vision model."""

    label: str
    data: bytes
    mime_type: str
    width: int
    height: int


def _open_image(file_bytes: bytes) -> Image.Image:
    try:
        image = Image.open(BytesIO(file_bytes))
        return ImageOps.exif_transpose(image).convert("RGB")
    except Exception as exc:  # pragma: no cover - exact Pillow exceptions vary
        raise PipelineError("Could not read uploaded image file.") from exc


def _render_pdf_first_page(file_bytes: bytes) -> Image.Image:
    try:
        import fitz  # PyMuPDF

        document = fitz.open(stream=file_bytes, filetype="pdf")
        if document.page_count == 0:
            raise PipelineError("PDF has no pages.")
        page = document.load_page(0)

        # 3x keeps small handwritten dimensions readable. The image is resized
        # later, so this does not create a huge API payload.
        matrix = fitz.Matrix(3, 3)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        return Image.open(BytesIO(pixmap.tobytes("png"))).convert("RGB")
    except PipelineError:
        raise
    except Exception as exc:  # pragma: no cover - depends on external PDF content
        raise PipelineError("Could not render the first page of the PDF.") from exc


def _load_original(file_bytes: bytes, content_type: str) -> Image.Image:
    if content_type == "application/pdf":
        return _render_pdf_first_page(file_bytes)
    return _open_image(file_bytes)


def _crop_white_margin(image: Image.Image) -> Image.Image:
    """Remove large scanner margins without assuming a fixed page layout."""

    background = Image.new(image.mode, image.size, (255, 255, 255))
    diff = ImageChops.difference(image, background).convert("L")
    # Keep faint grey/blue lines and handwriting as content.
    bbox = diff.point(lambda pixel: 255 if pixel > 18 else 0).getbbox()
    if bbox is None:
        return image

    left, top, right, bottom = bbox
    pad_x = max(8, int(image.width * 0.015))
    pad_y = max(8, int(image.height * 0.015))
    return image.crop(
        (
            max(0, left - pad_x),
            max(0, top - pad_y),
            min(image.width, right + pad_x),
            min(image.height, bottom + pad_y),
        )
    )


def _resize_copy(image: Image.Image, max_side: int) -> Image.Image:
    resized = image.copy()
    resized.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return resized


def _enhance_for_vision(image: Image.Image) -> Image.Image:
    """General enhancement for scanned engineering drawings."""

    image = ImageOps.autocontrast(image, cutoff=0.5)
    image = ImageEnhance.Contrast(image).enhance(1.18)
    image = ImageEnhance.Sharpness(image).enhance(1.25)
    return image.filter(ImageFilter.UnsharpMask(radius=1.1, percent=115, threshold=3))


def _suppress_blue_grid(image: Image.Image) -> Image.Image:
    """Create a second view with blue isometric graph paper reduced.

    The company sample is a scanned marked isometric drawn on blue grid paper.
    Sending only the raw page makes the vision model spend tokens on thousands
    of irrelevant blue grid intersections. This variant removes most cyan/blue
    grid pixels while preserving black route geometry, text and most handwriting.
    The raw view is still sent alongside it, so blue item balloons are not lost.
    """

    pixels = image.convert("RGB").load()
    cleaned = image.convert("RGB")
    out = cleaned.load()
    width, height = cleaned.size

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            # Blue/cyan grid lines: high blue, moderate/high green, lower red.
            blue_grid = b > 115 and g > 80 and r < 150 and (b - r) > 30
            very_light_blue = b > 145 and g > 120 and r < 190 and (b - r) > 20
            if blue_grid or very_light_blue:
                out[x, y] = (255, 255, 255)

    cleaned = ImageOps.grayscale(cleaned)
    cleaned = ImageOps.autocontrast(cleaned, cutoff=1)
    cleaned = ImageEnhance.Contrast(cleaned).enhance(1.35)
    cleaned = ImageEnhance.Sharpness(cleaned).enhance(1.35)
    return cleaned.convert("RGB")


def _encode_jpeg(image: Image.Image, label: str) -> VisionImage:
    output = BytesIO()
    image.save(output, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    return VisionImage(
        label=label,
        data=output.getvalue(),
        mime_type="image/jpeg",
        width=image.width,
        height=image.height,
    )


def preprocess_to_vision_images(file_bytes: bytes, content_type: str) -> list[VisionImage]:
    """Return multiple lightweight views optimized for Gemini.

    A single full-page scanned isometric can be dense and slow for a vision LLM.
    The pipeline therefore sends a small packet of complementary views:
    1. Full page, enhanced and resized.
    2. Grid-suppressed drawing view.
    3. Top/title-band crop for metadata.
    4. A compact packet size so the live Gemini call is less likely to time out.
    """

    original = _crop_white_margin(_load_original(file_bytes, content_type))
    width, height = original.size

    full = _enhance_for_vision(_resize_copy(original, MAX_PRIMARY_SIDE))
    no_grid = _enhance_for_vision(
        _resize_copy(_suppress_blue_grid(original), MAX_PRIMARY_SIDE)
    )

    title_crop = original.crop((0, 0, width, max(1, int(height * 0.26))))
    title_crop = _enhance_for_vision(_resize_copy(title_crop, MAX_SECONDARY_SIDE))

    return [
        _encode_jpeg(no_grid, "blue_grid_suppressed_view"),
        _encode_jpeg(full, "full_enhanced_page"),
        _encode_jpeg(title_crop, "title_and_metadata_band"),
    ]


def preprocess_to_png(file_bytes: bytes, content_type: str) -> tuple[bytes, str]:
    """Backward-compatible helper used by tests/legacy code."""

    first = preprocess_to_vision_images(file_bytes, content_type)[0]
    return first.data, first.mime_type
