// Client-side checks for fast feedback only — the backend re-validates everything.

export const ALLOWED_MIME_TYPES = ["application/pdf", "image/jpeg", "image/png"] as const;
export const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB, keep in sync with backend

export type FileValidationResult = { ok: true } | { ok: false; error: string };

export function validateLicenceFile(file: File): FileValidationResult {
  if (!(ALLOWED_MIME_TYPES as readonly string[]).includes(file.type)) {
    return { ok: false, error: "Please upload a PDF, JPG or PNG file." };
  }
  if (file.size === 0) {
    return { ok: false, error: "The selected file is empty." };
  }
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return { ok: false, error: "File is too large. The maximum size is 10 MB." };
  }
  return { ok: true };
}
