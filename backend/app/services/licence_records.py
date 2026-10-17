"""Save reviewed licence fields: validate, store the record and embed it for Q&A."""

from datetime import date
from typing import Any

from app.core.errors import AppError
from app.schemas.licence import ExtractedField, LicenceFields
from app.services.embeddings import embed_texts
from app.services.vector_store import VectorStore

# Descriptive labels make each field chunk easier to match with natural questions.
FIELD_LABELS = {
    "full_name": "Full name of the licence holder",
    "licence_number": "Driving licence number",
    "date_of_birth": "Date of birth of the licence holder",
    "date_of_issue": "Licence issue date",
    "date_of_expiry": "Licence expiry date (valid until)",
    "address": "Home address of the licence holder",
    "licence_classes": "Vehicle categories / classes allowed to drive",
    "issuing_authority": "Issuing authority of the licence",
}


def validate_fields(fields: LicenceFields) -> None:
    """Business rules on top of the schema's type checks. Errors are shown to the user."""
    errors: list[str] = []
    if not fields.full_name.value:
        errors.append("Full name is required.")
    if not fields.licence_number.value:
        errors.append("Licence number is required.")
    dob, issued, expires = (
        fields.date_of_birth.value,
        fields.date_of_issue.value,
        fields.date_of_expiry.value,
    )
    if dob and dob >= date.today():
        errors.append("Date of birth must be in the past.")
    if issued and expires and expires <= issued:
        errors.append("Date of expiry must be after the date of issue.")
    if dob and issued and issued <= dob:
        errors.append("Date of issue must be after the date of birth.")
    if errors:
        raise AppError(" ".join(errors), status_code=422)


def _format_value(field: ExtractedField[Any]) -> str | None:
    value = field.value
    if value is None or value == "" or value == []:
        return None
    if isinstance(value, list):
        return ", ".join(value)
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def build_field_chunks(fields: LicenceFields) -> list[tuple[str, int]]:
    """One short "Label: value" text per filled field, with its source page (0 = unknown)."""
    chunks: list[tuple[str, int]] = []
    for name, label in FIELD_LABELS.items():
        field = getattr(fields, name)
        if (text := _format_value(field)) is not None:
            chunks.append((f"{label}: {text}", field.source_page or 0))
    for label, field in fields.other_fields.items():
        if (text := _format_value(field)) is not None:
            chunks.append((f"{label.replace('_', ' ').capitalize()}: {text}", field.source_page or 0))
    return chunks


def save_licence_fields(
    vector_store: VectorStore, document_id: str, filename: str, fields: LicenceFields
) -> None:
    """Upsert the record into Milvus and replace this document's field chunks.

    Runs synchronously (embedding is CPU-bound); call from a worker thread.
    """
    chunks = build_field_chunks(fields)
    summary = "Driving licence. " + ". ".join(text for text, _ in chunks)
    # One batch: the record summary first, then each chunk.
    vectors = embed_texts([summary, *[text for text, _ in chunks]])

    vector_store.save_licence(
        document_id, filename, fields.model_dump(mode="json"), vector=vectors[0]
    )
    vector_store.replace_chunks(
        document_id,
        source="field",
        chunks=[
            {"text": text, "page": page, "vector": vector}
            for (text, page), vector in zip(chunks, vectors[1:], strict=True)
        ],
    )
