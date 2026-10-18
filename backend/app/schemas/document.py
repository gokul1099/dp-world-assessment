from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.licence import LicenceFields

DocumentStatus = Literal["processing", "ready", "failed"]


class DocumentResponse(BaseModel):
    document_id: str
    filename: str
    content_type: str
    page_count: int
    status: DocumentStatus
    fields: LicenceFields | None = None
    # OCR text per page (index 0 = page 1). Returned to the frontend at upload and sent back
    # with the save request; nothing is written to the database until the user saves.
    page_texts: list[str] = Field(default_factory=list)


class SaveFieldsRequest(BaseModel):
    fields: LicenceFields
    page_texts: list[str] = Field(default_factory=list, max_length=20)


class PageText(BaseModel):
    page: int  # 1-based
    text: str


class DocumentTextResponse(BaseModel):
    document_id: str
    pages: list[PageText]
