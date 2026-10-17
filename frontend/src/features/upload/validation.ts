// Client-side checks for fast feedback only — the backend re-validates everything.

export const ALLOWED_MIME_TYPES = ["application/pdf", "image/jpeg", "image/png"] as const;
const ALLOWED_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png"];
export const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB, keep in sync with backend

/** Value for <input accept>: lets the OS file picker filter to supported types. */
export const ACCEPT_ATTRIBUTE = [...ALLOWED_MIME_TYPES, ...ALLOWED_EXTENSIONS].join(",");

export type FileValidationResult = { ok: true } | { ok: false; error: string };

function hasAllowedType(file: File): boolean {
  if (file.type) return (ALLOWED_MIME_TYPES as readonly string[]).includes(file.type);
  // Some browsers/OSes report an empty type; fall back to the extension.
  const name = file.name.toLowerCase();
  return ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext));
}

export function validateLicenceFile(file: File): FileValidationResult {
  if (!hasAllowedType(file)) {
    return { ok: false, error: "Unsupported file type. Please upload a PDF, JPG or PNG." };
  }
  if (file.size === 0) {
    return { ok: false, error: "The selected file is empty." };
  }
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return { ok: false, error: "File is too large. The maximum size is 10 MB." };
  }
  return { ok: true };
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
