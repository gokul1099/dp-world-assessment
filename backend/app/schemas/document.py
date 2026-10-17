from typing import Literal

from pydantic import BaseModel

from app.schemas.licence import LicenceFields

DocumentStatus = Literal["processing", "ready", "failed"]


class DocumentResponse(BaseModel):
    document_id: str
    filename: str
    content_type: str
    page_count: int
    status: DocumentStatus
    fields: LicenceFields | None = None


class PageText(BaseModel):
    page: int  # 1-based
    text: str


class DocumentTextResponse(BaseModel):
    document_id: str
    pages: list[PageText]
