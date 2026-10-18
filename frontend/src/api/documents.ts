import { apiRequest, baseUrl } from "@/api/client";
import { mockUploadDocument } from "@/api/mock";
import type {
  AskResponse,
  DocumentResponse,
  HealthResponse,
  LicenceFields,
} from "@/types/licence";

// OCR + LLM extraction can be slow, so uploads get a longer timeout.
const UPLOAD_TIMEOUT_MS = 120_000;

// Referenced literally so Next.js inlines it; see src/api/mock.ts.
const USE_MOCK = process.env.NEXT_PUBLIC_API_MOCK === "true";

export function getHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/health", { timeoutMs: 10_000 });
}

export function uploadDocument(file: File, signal?: AbortSignal): Promise<DocumentResponse> {
  if (USE_MOCK) return mockUploadDocument(file, signal);
  const form = new FormData();
  form.append("file", file);
  return apiRequest<DocumentResponse>("/documents", {
    method: "POST",
    body: form,
    signal,
    timeoutMs: UPLOAD_TIMEOUT_MS,
  });
}

export function getDocument(documentId: string): Promise<DocumentResponse> {
  return apiRequest<DocumentResponse>(`/documents/${encodeURIComponent(documentId)}`);
}

/** Save the reviewed licence: the backend stores it (and its page text) in the vector DB. */
export function updateDocumentFields(
  documentId: string,
  fields: LicenceFields,
  pageTexts: string[],
): Promise<DocumentResponse> {
  return apiRequest<DocumentResponse>(`/documents/${encodeURIComponent(documentId)}/fields`, {
    method: "PUT",
    body: { fields, page_texts: pageTexts },
    timeoutMs: 60_000,
  });
}

export function askDocument(
  documentId: string,
  question: string,
  signal?: AbortSignal,
): Promise<AskResponse> {
  return apiRequest<AskResponse>(`/documents/${encodeURIComponent(documentId)}/ask`, {
    method: "POST",
    body: { question },
    signal,
    timeoutMs: 60_000,
  });
}

/** URL of one rendered page image (1-based), for <img src>. */
export function pageImageUrl(documentId: string, page: number): string {
  return `${baseUrl()}/documents/${encodeURIComponent(documentId)}/pages/${page}`;
}
