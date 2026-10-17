"""Groq client. The only module that calls the LLM API."""

import base64
import io
import json
from functools import lru_cache
from typing import Any

from groq import Groq, GroqError
from PIL import Image

from app.config import get_settings
from app.core.errors import ExtractionError

# Groq rejects base64 images over 4 MB, so pages are sent as JPEG.
_MAX_IMAGE_SIDE_PX = 2000


@lru_cache
def get_groq_client() -> Groq:
    key = get_settings().groq_api_key
    if key is None:
        raise ExtractionError("GROQ_API_KEY is not configured on the server.", status_code=500)
    return Groq(api_key=key.get_secret_value(), timeout=60, max_retries=2)


def _png_to_data_url(png: bytes) -> str:
    with Image.open(io.BytesIO(png)) as image:
        image = image.convert("RGB")
        image.thumbnail((_MAX_IMAGE_SIDE_PX, _MAX_IMAGE_SIDE_PX))
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def image_to_json(png: bytes, prompt: str, schema: dict[str, Any], name: str) -> dict[str, Any]:
    """Send one page image to the vision model and get JSON back that matches `schema`.

    Uses Groq structured output (strict json_schema), so the reply is guaranteed to follow
    the schema's shape. Retries once if the call or parsing fails.
    """
    settings = get_settings()
    last_error: Exception | None = None
    for _attempt in range(2):
        try:
            response = get_groq_client().chat.completions.create(
                model=settings.groq_vision_model,
                temperature=0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": name, "strict": True, "schema": schema},
                },
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": _png_to_data_url(png)}},
                        ],
                    }
                ],
            )
            return json.loads(response.choices[0].message.content or "")
        except (GroqError, json.JSONDecodeError) as exc:
            last_error = exc
    raise ExtractionError("The document could not be read. Please try again.") from last_error
