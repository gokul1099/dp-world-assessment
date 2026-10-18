# Backend: FastAPI (deployed to Google Cloud Run)

API for the driving-licence reader: upload → OCR → LLM structured extraction → document Q&A (RAG)
with page citations. Project-wide rules are in `../CLAUDE.md`.

## Stack
- Python 3.12, FastAPI, Pydantic v2, pydantic-settings, uvicorn
- uv for dependencies (`pyproject.toml` + `uv.lock`), ruff for lint/format, pytest for tests

## Commands (run from `backend/`)
- `uv sync`: install deps (incl. dev group)
- `uv run uvicorn app.main:app --reload --port 8080`: dev server (docs at /docs)
- `uv run pytest`: tests
- `uv run ruff check . && uv run ruff format --check .`: lint + format check
- `uv add <pkg>` / `uv add --dev <pkg>`: add deps (ask first)
- `docker build -t dl-backend . && docker run -p 8080:8080 --env-file .env dl-backend`

## Structure / layering
```
app/
  main.py        create_app(): CORS, exception handlers, routers
  config.py      Settings from env vars (get_settings() is cached)
  api/           HTTP layer only: parse request → call service → return schema. No logic here.
  schemas/       Pydantic models = the API contract (mirrored in frontend/src/types/licence.ts)
  services/      business logic, one stage per module: ingestion, ocr, extraction, rag, storage
  llm/           the only code that calls the LLM provider; prompts live in llm/prompts.py
  core/          cross-cutting: errors.py (AppError → JSON), security.py (upload checks)
tests/           pytest; mock the LLM, never call a real API in tests
```
Dependency direction: `api → services → llm`. Services never import from `api`.

## Rules
- Route handlers declare a return type that is a schema from `app/schemas/`.
- Every LLM response is parsed into a Pydantic model; invalid output raises `ExtractionError`.
- Q&A answers come only from retrieved document text. If it isn't there, return
  `found=false` and say so; never guess. Always include source page(s).
- Raise `AppError` subclasses for expected failures; their message is shown to the user.
  Never return stack traces or raw provider errors.
- Error responses are always `{"detail": "..."}`.
- Validate uploads server-side: MIME allowlist (pdf/jpeg/png) checked by content, not just the
  extension; size ≤ `MAX_UPLOAD_MB`; never use the client filename as a filesystem path.
- Never log document text, extracted fields or API keys (licences are personal data).
- Read config only via `get_settings()`; secrets are `SecretStr`.
- Cloud Run is stateless: don't rely on local disk or in-memory state across requests unless
  max-instances=1 (current demo setting). Keep persistence behind `services/storage.py`.
- If you change a schema, update `frontend/src/types/licence.ts` in the same change.
- Every new endpoint or service gets tests.

## Deployment
```
gcloud run deploy dl-backend --source . --region <region> --allow-unauthenticated \
  --memory 1Gi --max-instances 1 \
  --set-env-vars ENVIRONMENT=production,ALLOWED_ORIGINS=https://dl-frontend-xxxx.run.app \
  --set-secrets GROQ_API_KEY=groq-api-key:latest
```
The container listens on `$PORT` (Cloud Run sets it; defaults to 8080).
