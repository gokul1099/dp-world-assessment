// The only module that knows the backend URL. Feature code calls the typed
// functions in src/api/*.ts, never fetch() directly.

// Must be referenced literally so Next.js can inline it at build time.
const API_URL = process.env.NEXT_PUBLIC_API_URL;

const DEFAULT_TIMEOUT_MS = 30_000;

export class ApiError extends Error {
  constructor(
    message: string,
    /** HTTP status, or 0 for network errors / timeouts. */
    public readonly status: number,
    public readonly detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  /** Plain objects are sent as JSON; FormData is sent as multipart. */
  body?: unknown;
  timeoutMs?: number;
}

export function baseUrl(): string {
  if (!API_URL) {
    throw new ApiError(
      "NEXT_PUBLIC_API_URL is not set. Copy .env.example to .env.local.",
      0,
    );
  }
  return API_URL.replace(/\/+$/, "");
}

/** FastAPI returns `{ detail: string }` or `{ detail: [{ msg, ... }] }` for validation errors. */
function messageFromBody(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const { detail } = body as { detail: unknown };
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: unknown };
      if (typeof first?.msg === "string") return first.msg;
    }
  }
  return fallback;
}

export async function apiRequest<T>(
  path: string,
  { body, timeoutMs = DEFAULT_TIMEOUT_MS, headers, signal, ...init }: RequestOptions = {},
): Promise<T> {
  const timeoutSignal = AbortSignal.timeout(timeoutMs);
  const finalHeaders = new Headers(headers);
  let payload: BodyInit | undefined;

  if (body instanceof FormData) {
    // Let the browser set the multipart boundary.
    payload = body;
  } else if (body !== undefined) {
    finalHeaders.set("Content-Type", "application/json");
    payload = JSON.stringify(body);
  }
  finalHeaders.set("Accept", "application/json");

  let response: Response;
  try {
    response = await fetch(`${baseUrl()}${path}`, {
      ...init,
      headers: finalHeaders,
      body: payload,
      signal: signal ? AbortSignal.any([signal, timeoutSignal]) : timeoutSignal,
    });
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (timeoutSignal.aborted) {
      throw new ApiError("The server took too long to respond.", 0);
    }
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error; // caller cancelled; let them handle it
    }
    throw new ApiError("Could not reach the server. Check your connection.", 0);
  }

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const data: unknown = isJson ? await response.json().catch(() => null) : null;

  if (!response.ok) {
    throw new ApiError(
      messageFromBody(data, `Request failed (${response.status}).`),
      response.status,
      data,
    );
  }

  return data as T;
}
