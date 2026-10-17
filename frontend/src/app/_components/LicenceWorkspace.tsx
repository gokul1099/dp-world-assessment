"use client";

import { useState } from "react";

import { ChatPanel } from "@/features/chat/ChatPanel";
import { LicenceForm } from "@/features/extraction-form/LicenceForm";
import { UploadPanel } from "@/features/upload/UploadPanel";
import { formatFileSize } from "@/features/upload/validation";
import type { DocumentResponse, LicenceFields } from "@/types/licence";

interface UploadedDocument {
  document: DocumentResponse;
  file: File;
}

type Step = "review" | "chat";

// Client-side state for the current document: upload → review & save → chat.
export function LicenceWorkspace() {
  const [uploaded, setUploaded] = useState<UploadedDocument | null>(null);
  const [step, setStep] = useState<Step>("review");

  if (!uploaded) {
    return (
      <UploadPanel
        onUploaded={(document, file) => {
          setUploaded({ document, file });
          setStep("review");
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

  return (
    <div className="flex w-full max-w-3xl flex-col gap-6">
      <section
        aria-label="Uploaded document"
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
        />
      ) : (
        <ChatPanel
          key={document.document_id}
          documentId={document.document_id}
          holderName={document.fields.full_name.value}
          onEditDetails={() => setStep("review")}
        />
      )}
    </div>
  );
}
