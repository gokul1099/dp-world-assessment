// Fake backend for frontend-first development (NEXT_PUBLIC_API_MOCK=true).
// Returns obviously fake data so it can never be mistaken for a real extraction.
// Tip: a filename containing "fail" simulates a server error.

import { ApiError } from "@/api/client";
import type { DocumentResponse, LicenceFields } from "@/types/licence";

const MOCK_LATENCY_MS = 1500;

function delay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(new DOMException("Aborted", "AbortError"));
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    });
  });
}

const field = <T,>(value: T, confidence = 0.95) => ({ value, confidence, source_page: 1 });

const MOCK_FIELDS: LicenceFields = {
  full_name: field("JANE SAMPLE"),
  licence_number: field("MOCK-0000-1234"),
  date_of_birth: field("1990-01-15"),
  date_of_issue: field("2020-03-01"),
  date_of_expiry: field("2030-02-28", 0.62),
  address: field("1 Example Street, Sample City"),
  licence_classes: field(["B", "C1"]),
  issuing_authority: field("Mock Licensing Authority"),
  other_fields: {},
};

export async function mockUploadDocument(
  file: File,
  signal?: AbortSignal,
): Promise<DocumentResponse> {
  await delay(MOCK_LATENCY_MS, signal);
  if (/fail/i.test(file.name)) {
    throw new ApiError("We couldn't process this document. Please try again.", 502);
  }
  return {
    document_id: crypto.randomUUID(),
    filename: file.name,
    content_type: file.type,
    page_count: 1,
    status: "ready",
    fields: MOCK_FIELDS,
  };
}
