"use client";

import { useState } from "react";

import { ChatPanel } from "@/features/chat/ChatPanel";
import { LicenceForm } from "@/features/extraction-form/LicenceForm";
import { UploadPanel } from "@/features/upload/UploadPanel";
import { formatFileSize } from "@/features/upload/validation";
import { DocumentViewer } from "@/features/viewer/DocumentViewer";
import type { DocumentResponse, LicenceFields } from "@/types/licence";

interface UploadedDocument {
  document: DocumentResponse;
  file: File;
}

type Step = "review" | "chat";

// Client-side state for the current document: upload → review & save → chat,
// with the document shown beside the form/chat so the user can verify everything.
export function LicenceWorkspace() {
  const [uploaded, setUploaded] = useState<UploadedDocument | null>(null);
  const [step, setStep] = useState<Step>("review");
  const [page, setPage] = useState(1);

  if (!uploaded) {
    return (
      <UploadPanel
        onUploaded={(document, file) => {
          setUploaded({ document, file });
          setStep("review");
          setPage(1);
        }}
      />
    );
  }

  const { document, file } = uploaded;

  function handleSaved(fields: LicenceFields) {
    // Keep the saved values so "Edit details" reopens the form with them.
    setUploaded((prev) => prev && { ...prev, document: { ...prev.document, fields } });
    setStep("chat");
  }

  function showPage(target: number) {
    setPage(Math.min(Math.max(target, 1), document.page_count));
    // On narrow screens the viewer is above the form: bring it into view.
    if (window.matchMedia("(max-width: 1023px)").matches) {
      window.document.getElementById("viewer-title")?.scrollIntoView({ behavior: "smooth" });
    }
  }

  return (
    <div className="flex w-full max-w-6xl flex-col gap-6">
      <section
        aria-label="Uploaded file"
        className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-zinc-200 bg-white px-6 py-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-950"
      >
        <div className="min-w-0">
          <h2 className="truncate font-semibold" title={document.filename}>
            {document.filename}
          </h2>
          <p className="text-sm text-zinc-500">
            {formatFileSize(file.size)} · {document.page_count}{" "}
            {document.page_count === 1 ? "page" : "pages"}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setUploaded(null)}
          className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium transition-colors hover:bg-zinc-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:border-zinc-700 dark:hover:bg-zinc-900"
        >
          Upload another document
        </button>
      </section>

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
        {/* Sticky on desktop so the document stays visible while scrolling the form. */}
        <div className="lg:sticky lg:top-6">
          <DocumentViewer
            documentId={document.document_id}
            pageCount={document.page_count}
            page={page}
            onPageChange={showPage}
          />
        </div>

        {!document.fields ? (
          <p role="alert" className="text-sm text-red-700 dark:text-red-400">
            No details could be extracted from this document.
          </p>
        ) : step === "review" ? (
          // key resets the form's state when a new document is uploaded
          <LicenceForm
            key={document.document_id}
            documentId={document.document_id}
            fields={document.fields}
            onSaved={handleSaved}
            onShowPage={showPage}
          />
        ) : (
          <ChatPanel
            key={document.document_id}
            documentId={document.document_id}
            holderName={document.fields.full_name.value}
            onEditDetails={() => setStep("review")}
            onShowPage={showPage}
          />
        )}
      </div>
    </div>
  );
}
