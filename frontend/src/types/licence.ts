// Mirrors the backend Pydantic schemas (backend/app/schemas/). Field names stay
// snake_case to match the JSON on the wire; keep both sides in sync when changing.

/** A single extracted value plus where it came from in the document. */
export interface ExtractedField<T = string> {
  value: T | null;
  /** 0–1 model confidence; null when the backend could not estimate it. */
  confidence: number | null;
  /** 1-based page number the value was read from; null if unknown. */
  source_page: number | null;
}

export interface LicenceFields {
  full_name: ExtractedField;
  licence_number: ExtractedField;
  /** ISO 8601 date (YYYY-MM-DD) */
  date_of_birth: ExtractedField;
  date_of_issue: ExtractedField;
  date_of_expiry: ExtractedField;
  address: ExtractedField;
  /** Vehicle categories / classes, e.g. ["B", "C1"] */
  licence_classes: ExtractedField<string[]>;
  issuing_authority: ExtractedField;
  /** Anything else relevant found on the document, keyed by label. */
  other_fields: Record<string, ExtractedField>;
}

export type DocumentStatus = "processing" | "ready" | "failed";

export interface DocumentResponse {
  document_id: string;
  filename: string;
  content_type: string;
  page_count: number;
  status: DocumentStatus;
  fields: LicenceFields | null;
}

export interface SourceRef {
  page: number;
  /** Short excerpt of the document text the answer was grounded on. */
  snippet: string | null;
}

export interface AskRequest {
  question: string;
}

export interface AskResponse {
  answer: string;
  /** False when the document does not contain the requested information. */
  found: boolean;
  sources: SourceRef[];
}

export interface HealthResponse {
  status: "ok";
}
