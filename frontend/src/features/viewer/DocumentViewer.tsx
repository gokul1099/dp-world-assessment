"use client";

interface DocumentViewerProps {
  /** Object URL of the uploaded file (URL.createObjectURL) — stays in the browser. */
  fileUrl: string;
  contentType: string;
}

// Feature 6 — shows the uploaded document beside the extracted data for verification.
export function DocumentViewer(_props: DocumentViewerProps) {
  return <section aria-label="Uploaded document">Document viewer</section>;
}
