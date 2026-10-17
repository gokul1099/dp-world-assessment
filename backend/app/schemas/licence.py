"""Structured licence data. Mirrored in frontend/src/types/licence.ts; keep both in sync."""

from datetime import date

from pydantic import BaseModel, Field


class ExtractedField[T](BaseModel):
    """One extracted value plus where it came from in the document."""

    value: T | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_page: int | None = Field(default=None, ge=1, description="1-based page number")


class LicenceFields(BaseModel):
    full_name: ExtractedField[str] = ExtractedField[str]()
    licence_number: ExtractedField[str] = ExtractedField[str]()
    date_of_birth: ExtractedField[date] = ExtractedField[date]()
    date_of_issue: ExtractedField[date] = ExtractedField[date]()
    date_of_expiry: ExtractedField[date] = ExtractedField[date]()
    address: ExtractedField[str] = ExtractedField[str]()
    licence_classes: ExtractedField[list[str]] = ExtractedField[list[str]]()
    issuing_authority: ExtractedField[str] = ExtractedField[str]()
    other_fields: dict[str, ExtractedField[str]] = Field(default_factory=dict)
