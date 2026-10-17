"""Shared FastAPI dependencies. Override these in tests via `app.dependency_overrides`."""

from typing import Annotated

from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.services.storage import InMemoryDocumentStore


def get_document_store(request: Request) -> InMemoryDocumentStore:
    return request.app.state.document_store


SettingsDep = Annotated[Settings, Depends(get_settings)]
DocumentStoreDep = Annotated[InMemoryDocumentStore, Depends(get_document_store)]
