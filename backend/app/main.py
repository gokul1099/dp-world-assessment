import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, documents, health
from app.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.security import MULTIPART_OVERHEAD_BYTES, MaxBodySizeMiddleware
from app.services.embeddings import get_embedding_model
from app.services.storage import InMemoryDocumentStore
from app.services.vector_store import VectorStore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    # Embedded Milvus Lite: a local file, no separate server or port.
    app.state.vector_store = VectorStore(settings.data_dir)
    # Load the embedding model now so the first save isn't slow (downloads once, ~70 MB).
    await run_in_threadpool(get_embedding_model)
    yield
    app.state.vector_store.client.close()


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        # Interactive docs are handy locally but needless attack surface in production.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
        lifespan=lifespan,
    )

    app.state.document_store = InMemoryDocumentStore(settings.max_stored_documents)

    # Middleware added last runs first: CORS must wrap the size limit so a 413 is
    # still readable by the browser.
    app.add_middleware(
        MaxBodySizeMiddleware,
        max_bytes=settings.max_upload_bytes + MULTIPART_OVERHEAD_BYTES,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type", "Accept"],
    )

    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(documents.router)
    app.include_router(chat.router)
    return app


app = create_app()
