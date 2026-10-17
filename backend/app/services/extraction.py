"""Page images → page text + structured licence fields, in one vision call per page."""

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.llm.client import image_to_json
from app.llm.prompts import EXTRACTION_PROMPT, EXTRACTION_SCHEMA
from app.schemas.licence import LicenceFields

SINGLE_FIELDS = [
    "full_name",
    "licence_number",
    "date_of_birth",
    "date_of_issue",
    "date_of_expiry",
    "address",
    "licence_classes",
    "issuing_authority",
]
DATE_FIELDS = {"date_of_birth", "date_of_issue", "date_of_expiry"}
# Fallback if the model ignores the ISO instruction. Day-first, as on most licences.
_DATE_FORMATS = ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y"]


@dataclass
class ExtractionResult:
    page_texts: list[str]
    fields: LicenceFields


def extract_document(pages: list[bytes]) -> ExtractionResult:
    with ThreadPoolExecutor(max_workers=min(len(pages), 4)) as pool:
        results = list(pool.map(_read_page, pages))
    return ExtractionResult(
        page_texts=[r["page_text"] for r in results],
        fields=_merge_pages([r["fields"] for r in results]),
    )


def _read_page(png: bytes) -> dict[str, Any]:
    return image_to_json(png, EXTRACTION_PROMPT, EXTRACTION_SCHEMA, name="licence_page")


def _merge_pages(pages: list[dict[str, Any]]) -> LicenceFields:
    """Keep, per field, the most confident non-empty value across pages, with its page number."""
    merged: dict[str, Any] = {}
    for name in SINGLE_FIELDS:
        best: dict[str, Any] | None = None
        for page_number, page_fields in enumerate(pages, start=1):
            candidate = _to_field(name, page_fields[name], page_number)
            if candidate is None:
                continue
            if best is None or candidate["confidence"] > best["confidence"]:
                best = candidate
        merged[name] = best or {}

    other: dict[str, dict[str, Any]] = {}
    for page_number, page_fields in enumerate(pages, start=1):
        for item in page_fields["other_fields"]:
            label, value = item["label"].strip(), item["value"].strip()
            if label and value and label not in other:
                other[label] = {
                    "value": value,
                    "confidence": _clamp(item["confidence"]),
                    "source_page": page_number,
                }
    merged["other_fields"] = other
    return LicenceFields.model_validate(merged)


def _to_field(name: str, raw: dict[str, Any], page_number: int) -> dict[str, Any] | None:
    value = raw["value"]
    if isinstance(value, str):
        value = value.strip() or None
    if name in DATE_FIELDS and value is not None:
        value = _parse_date(value)
    if name == "licence_classes" and value is not None:
        value = [c.strip() for c in value if c.strip()] or None
    if value is None:
        return None
    return {"value": value, "confidence": _clamp(raw["confidence"]), "source_page": page_number}


def _parse_date(text: str) -> date | None:
    text = re.sub(r"\s+", " ", text.strip())
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None  # unparseable → treat as not found rather than guess


def _clamp(confidence: Any) -> float:
    if not isinstance(confidence, int | float):
        return 0.0
    return max(0.0, min(1.0, float(confidence)))
