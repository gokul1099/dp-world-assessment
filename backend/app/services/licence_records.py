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


CORRECTED_MARKER = "(corrected by the licence holder)"
_SOURCE_MAX = 32  # licence_chunks.source column length


def field_source(key: str) -> str:
    """Chunk `source` tag for one field, e.g. "field:full_name". Lets us replace one field only."""
    return f"field:{key}"[:_SOURCE_MAX]


def build_field_texts(fields: LicenceFields) -> dict[str, tuple[str, int]]:
    """{field key: ("Label: value", source page)} for every filled field (page 0 = unknown)."""
    texts: dict[str, tuple[str, int]] = {}
    for name, label in FIELD_LABELS.items():
        field = getattr(fields, name)
        if (text := _format_value(field)) is not None:
            texts[name] = (f"{label}: {text}", field.source_page or 0)
    for label, field in fields.other_fields.items():
        if (text := _format_value(field)) is not None:
            pretty = label.replace("_", " ").capitalize()
            texts[f"other.{label}"] = (f"{pretty}: {text}", field.source_page or 0)
    return texts


def index_field_chunks(
    vector_store: VectorStore,
    document_id: str,
    fields: LicenceFields,
    keys: set[str] | None = None,
    corrected: bool = False,
) -> int:
    """Embed field chunks. `keys=None` = all fields (at upload); otherwise only those keys.

    A key that is no longer filled has its chunk removed. Returns how many chunks were embedded.
    """
    texts = build_field_texts(fields)
    keys = set(texts) if keys is None else keys
    to_embed = {k: texts[k] for k in keys if k in texts}

    for key in keys - set(to_embed):  # cleared by the user → drop its chunk
        vector_store.replace_chunks(document_id, source=field_source(key), chunks=[])
    if not to_embed:
        return 0

    marker = f" {CORRECTED_MARKER}" if corrected else ""
    items = [(key, f"{text}{marker}", page) for key, (text, page) in to_embed.items()]
    vectors = embed_texts([text for _, text, _ in items])
    for (key, text, page), vector in zip(items, vectors, strict=True):
        vector_store.replace_chunks(
            document_id,
            source=field_source(key),
            chunks=[{"text": text, "page": page, "vector": vector}],
        )
    return len(items)


def changed_field_keys(old: LicenceFields | None, new: LicenceFields) -> set[str]:
    """Keys whose value differs between two versions (added, edited or cleared)."""
    old_texts = build_field_texts(old) if old else {}
    new_texts = build_field_texts(new)
    return {
        key
        for key in old_texts.keys() | new_texts.keys()
        if old_texts.get(key, ("", 0))[0] != new_texts.get(key, ("", 0))[0]
    }


def save_licence_fields(
    vector_store: VectorStore,
    document_id: str,
    filename: str,
    previous: LicenceFields | None,
    fields: LicenceFields,
    page_texts: list[str],
) -> int:
    """Write the reviewed licence to Milvus. Returns the number of chunks embedded.

    - First save (no record yet): embed the page text and every field. Fields that differ from
      what was extracted are marked as corrections, so answers prefer them over the scan.
    - Later saves: embed ONLY the fields that changed since the last save (also as corrections).
    Runs synchronously (embedding is CPU-bound); call from a worker thread.
    """
    first_save = vector_store.get_licence(document_id) is None
    changed = changed_field_keys(previous, fields)

    texts = build_field_texts(fields)
    summary = "Driving licence. " + ". ".join(text for text, _ in texts.values())
    vector_store.save_licence(
        document_id, filename, fields.model_dump(mode="json"), vector=embed_texts([summary])[0]
    )

    if not first_save:
        return index_field_chunks(vector_store, document_id, fields, keys=changed, corrected=True)

    from app.services.rag import index_page_texts  # local import: rag imports this module

    page_chunks = index_page_texts(vector_store, document_id, page_texts)
    unchanged = set(texts) - changed
    return (
        page_chunks
        + index_field_chunks(vector_store, document_id, fields, keys=unchanged)
        + index_field_chunks(vector_store, document_id, fields, keys=changed, corrected=True)
    )
