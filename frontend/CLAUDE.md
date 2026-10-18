@AGENTS.md

# Frontend — Next.js (deployed to Google Cloud Run)

UI for the driving-licence reader: upload → auto-filled editable form → ask-the-document chat,
with the document shown beside the extracted data. Project-wide rules live in `../CLAUDE.md`.

## Stack
- Next.js 16 (App Router, `src/` dir), React 19, TypeScript (strict), Tailwind CSS v4, ESLint 9
- `next.config.ts` enables `cacheComponents` — check `node_modules/next/dist/docs/` before using
  caching, data-fetching or routing APIs; this version differs from older Next.js.

## Commands (run from `frontend/`)
- `npm run dev` — dev server on http://localhost:3000
- `npm run lint` — ESLint
- `npx tsc --noEmit` — type-check
- `npm run build` — production build (must pass before committing)

## Environment
- `NEXT_PUBLIC_API_URL` — backend base URL. Local: copy `.env.example` → `.env.local`.
  Cloud Run: set in `.env.production` (inlined at build time by `next build`).
- `NEXT_PUBLIC_*` values are inlined into the browser bundle at build time: never put secrets
  or API keys in the frontend. The LLM key lives only in the backend.

## Structure
```
src/
  app/                 routes & layouts only — compose features, no business logic
  api/client.ts        the ONLY place that calls fetch(); base URL, timeouts, ApiError
  api/documents.ts     typed endpoint functions: getHealth, uploadDocument, getDocument, askDocument
  types/licence.ts     mirrors backend Pydantic schemas (snake_case, same as the JSON)
  features/
    upload/            Feature 1 — upload + client-side file validation
    extraction-form/   Features 3–4 — auto-populated, editable, validated form
    chat/              Feature 5 — ask the document, answers with page citations
    viewer/            Feature 6 — document preview beside extracted data
  components/          shared UI used by 2+ features
  hooks/               shared hooks used by 2+ features
```

## Conventions
- Components: named exports, PascalCase files. Add `"use client"` only to interactive components.
- Feature code calls `@/api/*` functions; never call `fetch` or read `NEXT_PUBLIC_API_URL` elsewhere.
- Catch `ApiError` and show `error.message` to the user; no raw stack traces or JSON in the UI.
- If the API contract changes, update `src/types/licence.ts` in the same change as the backend.
- Client-side validation is for UX only; the backend is the source of truth.
- Show the uploaded file with `URL.createObjectURL` (revoke on unmount); don't store licence
  data in localStorage, it's personal data.
- Every extracted field and chat answer shows its source page when the backend provides one.
- Accessible by default: labelled inputs, buttons not divs, visible focus states.
- Ask before adding a dependency (e.g. a form/validation library).
