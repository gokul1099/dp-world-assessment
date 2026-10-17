"use client";

import { useState } from "react";

import { UploadPanel } from "@/features/upload/UploadPanel";
import { formatFileSize } from "@/features/upload/validation";
import type { DocumentResponse } from "@/types/licence";

interface UploadedDocument {
  document: DocumentResponse;
  file: File;
}

// Client-side state for the current document. Each feature panel plugs in here.
export function LicenceWorkspace() {
  const [uploaded, setUploaded] = useState<UploadedDocument | null>(null);

  if (!uploaded) {
    return <UploadPanel onUploaded={(document, file) => setUploaded({ document, file })} />;
  }

  const { document, file } = uploaded;
  return (
    <section
      aria-label="Uploaded document"
      className="w-full max-w-xl rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950 sm:p-8"
    >
      <p className="text-sm font-medium text-green-700 dark:text-green-400" role="status">
        Document uploaded
      </p>
      <h2 className="mt-1 truncate text-lg font-semibold" title={document.filename}>
        {document.filename}
      </h2>
      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        <dt className="text-zinc-500">Size</dt>
        <dd>{formatFileSize(file.size)}</dd>
        <dt className="text-zinc-500">Pages</dt>
        <dd>{document.page_count}</dd>
        <dt className="text-zinc-500">Status</dt>
        <dd className="capitalize">{document.status}</dd>
      </dl>
      <button
        type="button"
        onClick={() => setUploaded(null)}
        className="mt-6 inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium transition-colors hover:bg-zinc-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:border-zinc-700 dark:hover:bg-zinc-900"
      >
        Upload another document
      </button>
    </section>
  );
}
