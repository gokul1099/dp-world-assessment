"use client";

import { useEffect, useId, useRef, useState } from "react";

import { ApiError } from "@/api/client";
import { uploadDocument } from "@/api/documents";
import type { DocumentResponse } from "@/types/licence";

import { ACCEPT_ATTRIBUTE, formatFileSize, validateLicenceFile } from "./validation";

interface UploadPanelProps {
  onUploaded: (document: DocumentResponse, file: File) => void;
}

type UploadState =
  | { status: "idle"; file: File | null; error: string | null }
  | { status: "uploading"; file: File }
  | { status: "failed"; file: File; error: string };

const INITIAL_STATE: UploadState = { status: "idle", file: null, error: null };

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Upload failed. Please try again.";
}

// Feature 1 — upload a driving licence (PDF/JPG/PNG).
export function UploadPanel({ onUploaded }: UploadPanelProps) {
  const [state, setState] = useState<UploadState>(INITIAL_STATE);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const inputId = useId();
  const hintId = useId();

  // Cancel an in-flight upload if the panel unmounts.
  useEffect(() => () => abortRef.current?.abort(), []);

  const isUploading = state.status === "uploading";

  // The request covers upload + OCR/extraction; after a moment, say we're reading the document.
  const [isReading, setIsReading] = useState(false);
  useEffect(() => {
    if (!isUploading) return;
    const timer = setTimeout(() => setIsReading(true), 1200);
    return () => {
      clearTimeout(timer);
      setIsReading(false);
    };
  }, [isUploading]);
  const error = state.status === "uploading" ? null : state.error;

  function openPicker() {
    inputRef.current?.click();
  }

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    // Reset so choosing the same file again still fires a change event.
    event.target.value = "";
    if (!file) return;

    const result = validateLicenceFile(file);
    setState({ status: "idle", file: result.ok ? file : null, error: result.ok ? null : result.error });
  }

  async function upload(file: File) {
    const controller = new AbortController();
    abortRef.current = controller;
    setState({ status: "uploading", file });

    try {
      const document = await uploadDocument(file, controller.signal);
      setState(INITIAL_STATE);
      onUploaded(document, file);
    } catch (err) {
      if (controller.signal.aborted) {
        setState({ status: "idle", file, error: null });
        return;
      }
      setState({ status: "failed", file, error: errorMessage(err) });
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
    }
  }

  function cancelUpload() {
    abortRef.current?.abort();
  }

  return (
    <section
      aria-labelledby={`${inputId}-title`}
      className="w-full max-w-xl rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950 sm:p-8"
    >
      <h2 id={`${inputId}-title`} className="text-lg font-semibold">
        Upload driving licence
      </h2>
      <p id={hintId} className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
        PDF, JPG or PNG, up to 10 MB.
      </p>

      <input
        ref={inputRef}
        id={inputId}
        type="file"
        accept={ACCEPT_ATTRIBUTE}
        onChange={handleFileChange}
        disabled={isUploading}
        aria-describedby={hintId}
        className="sr-only"
        tabIndex={-1}
      />

      <div className="mt-6 flex flex-col gap-4">
        {state.file ? (
          <SelectedFile file={state.file} />
        ) : (
          <button
            type="button"
            onClick={openPicker}
            className="flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-zinc-300 px-6 py-10 text-center transition-colors hover:border-zinc-400 hover:bg-zinc-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:border-zinc-700 dark:hover:border-zinc-600 dark:hover:bg-zinc-900"
          >
            <UploadIcon />
            <span className="font-medium">Choose a file</span>
            <span className="text-sm text-zinc-500">Click to browse your device</span>
          </button>
        )}

        <div role="status" aria-live="polite" className="min-h-0">
          {isUploading && (
            <p className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300">
              <Spinner />
              {isReading
                ? "Reading document and extracting details…"
                : "Uploading document…"}
            </p>
          )}
        </div>

        {error && (
          <p
            role="alert"
            className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200"
          >
            {error}
          </p>
        )}

        {state.file && (
          <div className="flex flex-wrap gap-3">
            {isUploading ? (
              <button type="button" onClick={cancelUpload} className={secondaryButton}>
                Cancel
              </button>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => state.file && upload(state.file)}
                  className={primaryButton}
                >
                  {state.status === "failed" ? "Try again" : "Upload"}
                </button>
                <button type="button" onClick={openPicker} className={secondaryButton}>
                  Choose another file
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

const buttonBase =
  "inline-flex h-10 items-center justify-center rounded-lg px-4 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-50";
const primaryButton = `${buttonBase} bg-zinc-900 text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300`;
const secondaryButton = `${buttonBase} border border-zinc-300 hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-900`;

function SelectedFile({ file }: { file: File }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-zinc-200 px-4 py-3 dark:border-zinc-800">
      <FileIcon />
      <div className="min-w-0">
        <p className="truncate font-medium" title={file.name}>
          {file.name}
        </p>
        <p className="text-sm text-zinc-500">{formatFileSize(file.size)}</p>
      </div>
    </div>
  );
}

function Spinner() {
  return (
    <span
      aria-hidden="true"
      className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-100"
    />
  );
}

function UploadIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-8 w-8 text-zinc-400" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
    </svg>
  );
}

function FileIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-8 w-8 shrink-0 text-zinc-400" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
    </svg>
  );
}
