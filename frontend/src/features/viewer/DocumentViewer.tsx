"use client";

import { useState } from "react";

import { pageImageUrl } from "@/api/documents";

interface DocumentViewerProps {
  documentId: string;
  pageCount: number;
  /** 1-based page currently shown; controlled so field/answer badges can jump to a page. */
  page: number;
  onPageChange: (page: number) => void;
}

// Feature 6 — shows the uploaded document beside the extracted data for verification.
// Pages are the PNGs the backend rendered at upload, so PDFs and images look the same.
export function DocumentViewer({ documentId, pageCount, page, onPageChange }: DocumentViewerProps) {
  const [failed, setFailed] = useState<Record<number, boolean>>({});
  const [zoomed, setZoomed] = useState(false);

  return (
    <section
      aria-labelledby="viewer-title"
      className="flex w-full flex-col rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-950"
    >
      <header className="flex items-center justify-between gap-3 border-b border-zinc-200 px-5 py-3 dark:border-zinc-800">
        <h2 id="viewer-title" className="text-sm font-semibold">
          Uploaded document
        </h2>
        {pageCount > 1 && (
          <div className="flex items-center gap-2 text-sm">
            <button
              type="button"
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              aria-label="Previous page"
              className={pagerButton}
            >
              ‹
            </button>
            <span aria-live="polite">
              Page {page} of {pageCount}
            </span>
            <button
              type="button"
              onClick={() => onPageChange(page + 1)}
              disabled={page >= pageCount}
              aria-label="Next page"
              className={pagerButton}
            >
              ›
            </button>
          </div>
        )}
      </header>

      <div className="flex min-h-64 items-center justify-center bg-zinc-100 p-4 dark:bg-zinc-900">
        {failed[page] ? (
          <p className="text-center text-sm text-zinc-600 dark:text-zinc-400">
            This page can&apos;t be shown. The document may have expired on the server — try
            uploading it again.
          </p>
        ) : (
          <button
            type="button"
            onClick={() => setZoomed((z) => !z)}
            className={`block focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 ${zoomed ? "cursor-zoom-out overflow-auto" : "cursor-zoom-in"}`}
            aria-label={zoomed ? "Zoom out" : "Zoom in"}
          >
            {/* Backend-rendered page image; next/image adds nothing for a private, dynamic URL. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              key={page}
              src={pageImageUrl(documentId, page)}
              alt={`Page ${page} of the uploaded driving licence`}
              onError={() => setFailed((prev) => ({ ...prev, [page]: true }))}
              className={`rounded-md shadow-md ${zoomed ? "max-w-none" : "max-h-[32rem] w-full object-contain"}`}
            />
          </button>
        )}
      </div>
    </section>
  );
}

const pagerButton =
  "inline-flex h-8 w-8 items-center justify-center rounded-md border border-zinc-300 text-base transition-colors hover:bg-zinc-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-40 dark:border-zinc-700 dark:hover:bg-zinc-800";
