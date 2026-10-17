import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import documents, health
from app.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.security import MULTIPART_OVERHEAD_BYTES, MaxBodySizeMiddleware
from app.services.storage import InMemoryDocumentStore


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
    return app


app = create_app()
