import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, File, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from app.api.deps import DocumentStoreDep, SettingsDep, VectorStoreDep
from app.core.security import read_upload_limited, sanitize_filename
from app.core.errors import NotFoundError
from app.schemas.document import DocumentResponse, DocumentTextResponse, PageText
from app.services.ingestion import ingest
from app.schemas.licence import LicenceFields
from app.services.extraction import extract_document
from app.services.licence_records import save_licence_fields, validate_fields
from app.services.rag import index_page_texts
from app.services.storage import StoredDocument

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


def _to_response(document: StoredDocument) -> DocumentResponse:
    return DocumentResponse(
        document_id=document.document_id,
        filename=document.filename,
        content_type=document.content_type,
        page_count=document.page_count,
        status="ready",
        fields=document.fields,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: Annotated[UploadFile, File(description="Driving licence as PDF, JPG or PNG")],
    settings: SettingsDep,
    store: DocumentStoreDep,
    vector_store: VectorStoreDep,
) -> DocumentResponse:
    """Validate an uploaded licence, read it with the vision model and store the result."""
    data = await read_upload_limited(file, settings.max_upload_bytes)
    # PDF rendering / image decoding is CPU-bound: keep it off the event loop.
    ingested = await run_in_threadpool(ingest, data, settings.max_pdf_pages)
    # One vision call per page returns both the page text and structured fields.
    extraction = await run_in_threadpool(extract_document, ingested.pages)

    document = StoredDocument(
        document_id=str(uuid.uuid4()),
        filename=sanitize_filename(file.filename),
        content_type=ingested.content_type.value,
        pages=ingested.pages,
        page_texts=extraction.page_texts,
        fields=extraction.fields,
    )
    store.save(document)
    # Make the OCR text searchable right away so the chat can use it.
    await run_in_threadpool(
        index_page_texts, vector_store, document.document_id, document.page_texts
    )
    logger.info("Stored document %s (%d page(s))", document.document_id, document.page_count)
    return _to_response(document)


@router.get("/{document_id}")
async def get_document(
    document_id: uuid.UUID, store: DocumentStoreDep, vector_store: VectorStoreDep
) -> DocumentResponse:
    """The document with its latest fields: the saved record from Milvus if there is one."""
    document = store.get(str(document_id))
    if document is None:
        raise NotFoundError("Document not found. Please upload it again.")
    saved = await run_in_threadpool(vector_store.get_licence, document.document_id)
    response = _to_response(document)
    if saved is not None:
        response.fields = LicenceFields.model_validate(saved["fields"])
    return response


@router.get("/{document_id}/text")
async def get_document_text(document_id: str, store: DocumentStoreDep) -> DocumentTextResponse:
    """OCR text per page. Used for Q&A context and to check what the model read."""
    document = store.get(document_id)
    if document is None:
        raise NotFoundError("Document not found. Please upload it again.")
    return DocumentTextResponse(
        document_id=document.document_id,
        pages=[PageText(page=i + 1, text=t) for i, t in enumerate(document.page_texts)],
    )


@router.put("/{document_id}/fields")
async def save_document_fields(
    document_id: uuid.UUID,  # UUID-only: also keeps the id safe inside Milvus filter expressions
    fields: LicenceFields,
    store: DocumentStoreDep,
    vector_store: VectorStoreDep,
) -> DocumentResponse:
    """Save the reviewed/edited fields to Milvus and (re)embed them for Q&A."""
    document = store.get(str(document_id))
    if document is None:
        raise NotFoundError("Document not found. Please upload it again.")

    validate_fields(fields)
    await run_in_threadpool(
        save_licence_fields, vector_store, document.document_id, document.filename, fields
    )
    document.fields = fields
    logger.info("Saved fields for document %s", document.document_id)
    return _to_response(document)
