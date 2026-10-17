# SPEC: AI Driving Licence Reader

The single source of truth for scope. Tick a box only when it works **end-to-end on both sample
licences** (frontend → backend → AI → frontend), not when one side is done.

- **Goal:** upload a driving licence → extract its data with OCR/LLM → auto-fill an editable form -> let the user to review the form -> submit the form → ask questions about the document → verify everything side by side with source pages.

---

## Feature 1: Upload document

**Frontend** (`features/upload/`)
- [ ] Client-side checks: PDF/JPG/PNG only, ≤ 10 MB, not empty (`validation.ts`)
- [ ] Upload progress / processing state; the upload button is disabled while busy
- [ ] Clear error message on rejection or failure; the user can retry or pick another file

**Backend** (`api/documents.py`, `services/ingestion.py`, `core/security.py`)
- [ ] `POST /documents` accepts multipart `file`
- [ ] Server-side validation: MIME type checked from file content (magic bytes), size ≤ `MAX_UPLOAD_MB`
- [ ] Generates a random `document_id` (UUID). The client filename is never used as a path
- [ ] PDF → page images; images treated as 1 page; `page_count` returned
- [ ] Errors: 413 too large, 422 unsupported/corrupt file

**Done when**
- [ ] licences upload successfully
---

## Feature 2: Document reading & extraction

**Frontend**
- [ ] Shows a "Reading document…" state while OCR and extraction run
- [ ] Handles extraction failure (502) with a friendly message and a retry option

**Backend** (`services/ocr.py`, `services/extraction.py`, `llm/`)
- [ ] OCR / vision step produces text per page (keeps page numbers)
- [ ] LLM extraction returns JSON that is validated into `LicenceFields` (Pydantic)
- [ ] Each field has `value`, `confidence` (0–1) and `source_page`
- [ ] Dates normalised to ISO `YYYY-MM-DD`; a field that is missing → `value: null`, never guessed
- [ ] Invalid/unparseable LLM output → one retry, then `ExtractionError` (502)
- [ ] Prompts kept in `llm/prompts.py`; document text treated as data (prompt-injection safe)
- [ ] Never logs document text or extracted values

**Done when**
- [ ] uploaded document produce correct values for every field that is present on the card
- [ ] Unit tests cover schema validation and the invalid-LLM-output path (LLM mocked)

---

## Feature 3: Auto-populate form

**Frontend** (`features/extraction-form/`)
- [ ] Form fields: Full name, Licence number, Date of birth, Date of issue, Date of expiry,
      Address, Vehicle classes, Issuing authority
- [ ] "Other information" section rendered dynamically from `other_fields`
- [ ] Populated automatically from the upload response; no extra click needed
- [ ] Empty fields shown as empty (with a "Not found in document" hint), not hidden

**Backend**
- [ ] `POST /documents` response includes `fields` (`DocumentResponse` schema)
- [ ] `GET /documents/{id}` returns the same data (for refresh/reload)

**Done when**
- [ ] Uploading a sample fills every form field the document contains, with no manual steps

---

## Feature 4: Review & edit

**Frontend** (`features/extraction-form/`)
- [ ] Every field is editable; vehicle classes editable as a list/tags
- [ ] Low-confidence fields (< 0.7) are visually flagged for review
- [ ] Validation: required name & licence number; valid dates; expiry after issue;
      DOB in the past; inline error messages
- [ ] Edited fields are marked as "edited by user"
- [ ] Save button disabled until the form is valid; success/failure feedback on save

**Backend**
- [ ] `PUT /documents/{id}/fields` accepts corrected `LicenceFields`, validates and stores them
- [ ] Same validation rules enforced server-side (the client is never trusted)

**Done when**
- [ ] User can fix a wrong value, save it, reload the page, and still see the corrected value
- [ ] Invalid input (e.g. expiry before issue) is blocked on both client and server

---

## Feature 5: Ask the document (RAG Q&A)

**Frontend** (`features/chat/`)
- [ ] Chat panel: question input, message history, loading indicator
- [ ] Suggested questions: "What is the licence expiry date?", "What vehicles is this person
      authorised to drive?", "What is the licence number?"
- [ ] Each answer shows `SourceBadge` page citation(s); hover shows the source snippet
- [ ] "Not in document" answers are styled distinctly (not as an error)

**Backend** (`api/chat.py`, `services/rag.py`)
- [ ] On ingestion: chunk OCR text per page, embed, and index under `document_id`
- [ ] `POST /documents/{id}/ask` → retrieve top-k chunks → grounded prompt → `AskResponse`
- [ ] Answers only from retrieved context; if the answer is absent, return `found: false` with
      "This information is not available in the document."
- [ ] `sources` lists page + snippet actually used
- [ ] Question length capped (500 chars); empty questions rejected (422)
- [ ] Extracted structured fields also available as context (licence classes, dates)

**Done when**
- [ ] The 3 example questions answer correctly with the right page cited, on both samples
- [ ] "What is the holder's blood group?" / "What is their salary?" → `found: false`, no invention
- [ ] Test asserts the not-found behaviour (LLM mocked)

---

## Feature 6: Document & data view

**Frontend** (`features/viewer/`, `app/page.tsx`)
- [ ] Side-by-side layout: document preview (left) and form + chat (right); stacks on mobile
- [ ] Preview renders images and PDFs (multi-page with page switcher)
- [ ] Each field shows its source page; clicking it jumps the viewer to that page
- [ ] Preview uses a local object URL (revoked on unmount); nothing stored in localStorage

**Backend**
- [ ] `source_page` populated on fields and answers
- [ ] (Stretch) bounding boxes for highlighting the field's location on the page

**Done when**
- [ ] A reviewer can verify every field against the document without leaving the screen

---

## Cross-cutting requirements

### Error handling
- [ ] All API errors are `{"detail": "..."}`; the frontend shows `ApiError.message`
- [ ] No stack traces or provider errors reach the client
- [ ] Network failure / timeout / server down each show a clear message in the UI

### Security (basic)
- [ ] LLM API key only in the backend (Secret Manager on Cloud Run; `.env` locally, gitignored)
- [ ] CORS limited to the Vercel domain + localhost
- [ ] Upload type/size validated server-side; random IDs; no path traversal
- [ ] Document text treated as untrusted in prompts (prompt-injection guard)
- [ ] No personal data in logs; docs (`/docs`) disabled in production
- [ ] Sample licences not committed (`samples/` gitignored)

### Code quality & testing
- [ ] Backend: ruff clean, pytest passing; LLM always mocked in tests
- [ ] Frontend: ESLint clean, `tsc --noEmit` passing, `npm run build` passing
- [ ] Schemas and TS types in sync (`backend/app/schemas/` ↔ `frontend/src/types/licence.ts`)

### Deployment
- [ ] Backend deployed to Cloud Run (`--max-instances 1` while state is in memory)
- [ ] Frontend deployed to Vercel with `NEXT_PUBLIC_API_URL` pointing at Cloud Run
- [ ] Full flow works on the deployed URLs
- [ ] (Later) CI/CD: path-filtered GitHub Actions for frontend and backend

---

## API contract

| Method | Path | Request | Response | Errors |
|---|---|---|---|---|
| GET | `/health` | – | `HealthResponse` | – |
| POST | `/documents` | multipart `file` | `DocumentResponse` | 413, 422, 502 |
| GET | `/documents/{id}` | – | `DocumentResponse` | 404 |
| PUT | `/documents/{id}/fields` | `LicenceFields` | `DocumentResponse` | 404, 422 |
| POST | `/documents/{id}/ask` | `AskRequest` | `AskResponse` | 404, 422, 502 |

Schemas: `backend/app/schemas/` (source of truth), mirrored in `frontend/src/types/licence.ts`.

---

## Open decisions

Record each choice and its reason in `README.md → Key technical decisions`.

- [ ] LLM provider/model for extraction (vision) and Q&A
- [ ] OCR approach: LLM vision only vs. dedicated OCR (e.g. Tesseract / Document AI) + LLM
- [ ] Embeddings model and vector store (in-memory for demo vs. pgvector/Firestore)
- [ ] Storage for uploads and state (memory + max-instances=1 vs. GCS + Firestore)

## Out of scope

User accounts/auth, multi-tenant data, document history across sessions, production-grade
retention/compliance, languages other than English, documents other than driving licences.

## Submission checklist

- [ ] README: tech stack, architecture (+ diagram), setup/run, AI/LLM approach,
      key technical decisions, known limitations, AI development tools used
- [ ] `docs/AI_USAGE.md` up to date
- [ ] Deployed URLs in the README
- [ ] Demo video (5–10 min): architecture → live flow on both samples incl. a
      "not in document" question → decisions & limitations
- [ ] Fresh-clone setup tested from the README
