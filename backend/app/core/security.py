"""Upload safety helpers: size limits and filename sanitising."""

import re
import unicodedata
from pathlib import PurePosixPath, PureWindowsPath

from fastapi import UploadFile
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.errors import FileTooLargeError, InvalidFileError

_READ_CHUNK_BYTES = 1024 * 1024
_MAX_FILENAME_LENGTH = 255
# Allowance for multipart boundaries and headers on top of the file itself.
MULTIPART_OVERHEAD_BYTES = 64 * 1024


async def read_upload_limited(upload: UploadFile, max_bytes: int) -> bytes:
    """Read an upload fully, failing as soon as it exceeds `max_bytes`."""
    chunks: list[bytes] = []
    total = 0
    while chunk := await upload.read(_READ_CHUNK_BYTES):
        total += len(chunk)
        if total > max_bytes:
            raise FileTooLargeError(
                f"File is too large. The maximum size is {max_bytes // 2**20} MB."
            )
        chunks.append(chunk)
    if total == 0:
        raise InvalidFileError("The uploaded file is empty.")
    return b"".join(chunks)


def sanitize_filename(raw: str | None) -> str:
    """Return a display-safe filename. Never use it (or the raw name) as a filesystem path."""
    if not raw:
        return "document"
    # Drop any directory part, whether the client sent / or \ separators.
    name = PureWindowsPath(PurePosixPath(raw).name).name
    name = unicodedata.normalize("NFC", name)
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip().strip(".")
    if not name:
        return "document"
    return name[:_MAX_FILENAME_LENGTH]


class MaxBodySizeMiddleware:
    """Reject requests whose declared Content-Length is over the limit, before the body is read.

    Browsers always send Content-Length for uploads. Chunked bodies without it are still caught
    by `read_upload_limited` (and Cloud Run caps HTTP/1 requests at 32 MB).
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            declared = dict(scope["headers"]).get(b"content-length", b"")
            if declared.isdigit() and int(declared) > self.max_bytes:
                limit_mb = (self.max_bytes - MULTIPART_OVERHEAD_BYTES) // 2**20
                response = JSONResponse(
                    status_code=413,
                    content={"detail": f"File is too large. The maximum size is {limit_mb} MB."},
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
