"use client";

import type { DocumentResponse } from "@/types/licence";

interface UploadPanelProps {
  onUploaded: (document: DocumentResponse) => void;
}

// Feature 1 — upload a driving licence (PDF/JPG/PNG). Uses validateLicenceFile + uploadDocument.
export function UploadPanel(_props: UploadPanelProps) {
  return <section aria-label="Upload licence">Upload panel</section>;
}
