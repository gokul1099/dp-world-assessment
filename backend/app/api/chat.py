import logging
import uuid

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from app.api.deps import DocumentStoreDep, VectorStoreDep
from app.core.errors import NotFoundError
from app.schemas.chat import AskRequest, AskResponse
from app.services.rag import answer_question

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["chat"])


@router.post("/{document_id}/ask")
async def ask_document(
    document_id: uuid.UUID,  # UUID-only: safe to use inside the Milvus filter expression
    body: AskRequest,
    store: DocumentStoreDep,
    vector_store: VectorStoreDep,
) -> AskResponse:
    """Answer a question using only this document's chunks (retrieval filtered by document_id)."""
    doc_id = str(document_id)
    known = store.get(doc_id) is not None or (
        await run_in_threadpool(vector_store.get_licence, doc_id)
    ) is not None
    if not known:
        raise NotFoundError("Document not found. Please upload it again.")

    response = await run_in_threadpool(answer_question, vector_store, doc_id, body.question)
    logger.info("Answered question for document %s (found=%s)", doc_id, response.found)
    return response
