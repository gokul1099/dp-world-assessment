"""Turn an uploaded file into normalised page images.

The file type is detected from its content (magic bytes), never from the client's filename or
Content-Type header. Every page, from a PDF or an image, ends up as a PNG so later stages
(OCR / LLM vision) handle a single format. Re-encoding also strips image metadata such as EXIF.

This module is CPU-bound and synchronous; call it from a worker thread.
"""

import io
import logging
from dataclasses import dataclass
from enum import StrEnum

import pypdfium2 as pdfium
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.errors import InvalidFileError

logger = logging.getLogger(__name__)

RENDER_DPI = 200  # good OCR quality for card-sized text
MAX_PAGE_SIDE_PX = 2400  # caps memory for oversized pages / photos
MAX_IMAGE_PIXELS = 40_000_000  # reject decompression bombs before decoding


class FileType(StrEnum):
    PDF = "application/pdf"
    JPEG = "image/jpeg"
    PNG = "image/png"


_SIGNATURES: tuple[tuple[bytes, FileType], ...] = (
    (b"%PDF-", FileType.PDF),
    (b"\xff\xd8\xff", FileType.JPEG),
    (b"\x89PNG\r\n\x1a\n", FileType.PNG),
)

UNSUPPORTED_MESSAGE = "Unsupported file type. Please upload a PDF, JPG or PNG."


@dataclass(frozen=True, slots=True)
class IngestedDocument:
    content_type: FileType
    pages: list[bytes]  # PNG bytes, one per page, in order

    @property
    def page_count(self) -> int:
        return len(self.pages)


def detect_file_type(data: bytes) -> FileType | None:
    for signature, file_type in _SIGNATURES:
        if data.startswith(signature):
            return file_type
    # Some PDF writers put junk bytes before the header; the PDF spec tolerates up to 1 KB.
    if b"%PDF-" in data[:1024]:
        return FileType.PDF
    return None


def ingest(data: bytes, max_pages: int) -> IngestedDocument:
    file_type = detect_file_type(data)
    if file_type is None:
        raise InvalidFileError(UNSUPPORTED_MESSAGE)

    pages = _pdf_to_pages(data, max_pages) if file_type is FileType.PDF else [_image_to_png(data)]
    logger.info("Ingested %s with %d page(s)", file_type.value, len(pages))
    return IngestedDocument(content_type=file_type, pages=pages)


def _pdf_to_pages(data: bytes, max_pages: int) -> list[bytes]:
    try:
        pdf = pdfium.PdfDocument(data)
    except pdfium.PdfiumError as exc:
        # Covers corrupt files and password-protected PDFs.
        raise InvalidFileError(
            "This PDF could not be opened. It may be corrupted or password-protected."
        ) from exc

    try:
        page_count = len(pdf)
        if page_count == 0:
            raise InvalidFileError("This PDF has no pages.")
        if page_count > max_pages:
            raise InvalidFileError(f"This PDF has {page_count} pages. The maximum is {max_pages}.")

        pages: list[bytes] = []
        for index in range(page_count):
            page = pdf[index]
            try:
                width_pt, height_pt = page.get_size()
                scale = min(RENDER_DPI / 72, MAX_PAGE_SIDE_PX / max(width_pt, height_pt, 1))
                image = page.render(scale=scale).to_pil()
            finally:
                page.close()
            pages.append(_encode_png(image))
        return pages
    except pdfium.PdfiumError as exc:
        raise InvalidFileError("This PDF could not be read. It may be corrupted.") from exc
    finally:
        pdf.close()


def _image_to_png(data: bytes) -> bytes:
    try:
        with Image.open(io.BytesIO(data)) as image:
            # Header-only check: refuse huge images before decoding pixels.
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise InvalidFileError("This image is too large to process.")
            image.load()
            # Respect camera orientation, then drop all metadata via re-encoding.
            normalised = ImageOps.exif_transpose(image)
            normalised.thumbnail((MAX_PAGE_SIDE_PX, MAX_PAGE_SIDE_PX))
            return _encode_png(normalised)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise InvalidFileError("This image could not be read. It may be corrupted.") from exc


def _encode_png(image: Image.Image) -> bytes:
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        # Flatten transparency onto white so transparent areas don't turn black.
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        image = background
    elif image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
