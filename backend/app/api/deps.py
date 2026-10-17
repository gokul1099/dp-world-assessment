"""Shared FastAPI dependencies. Override these in tests via `app.dependency_overrides`."""

from typing import Annotated

from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.services.storage import InMemoryDocumentStore
from app.services.vector_store import VectorStore


def get_document_store(request: Request) -> InMemoryDocumentStore:
    return request.app.state.document_store


def get_vector_store(request: Request) -> VectorStore:
    return request.app.state.vector_store


SettingsDep = Annotated[Settings, Depends(get_settings)]
DocumentStoreDep = Annotated[InMemoryDocumentStore, Depends(get_document_store)]
VectorStoreDep = Annotated[VectorStore, Depends(get_vector_store)]
