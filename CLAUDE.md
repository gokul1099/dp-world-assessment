# DL Intelligence: AI Driving Licence Reader

Take-home assessment (48 h). Upload a driving licence → OCR/LLM extraction → auto-filled editable
form → ask-the-document chat (RAG) with page citations → document and data shown side by side.

**Scope and acceptance criteria: `docs/SPEC.md` (source of truth).** Check it before starting a
feature and tick its boxes only when the feature works end-to-end on both sample licences.

## Repo layout (monorepo)
```
frontend/   Next.js 16 + TypeScript + Tailwind → Vercel        (see frontend/CLAUDE.md)
backend/    FastAPI + Pydantic, Python 3.12, uv → Cloud Run    (see backend/CLAUDE.md)
docs/       SPEC.md, AI_USAGE.md, architecture diagram
samples/    sample licences: gitignored, contains personal data
```
Each app has its own `CLAUDE.md` with commands and conventions; follow the one for the folder
you are working in.

## How the pieces connect
- Browser → frontend (Vercel) → `NEXT_PUBLIC_API_URL` → backend (Cloud Run) → LLM provider.
- The API contract is `backend/app/schemas/` (source of truth), mirrored in
  `frontend/src/types/licence.ts`. Change both in the same commit.
- Endpoints are listed in `docs/SPEC.md → API contract`.

## Quick start
```
cd backend && uv sync && cp .env.example .env && uv run uvicorn app.main:app --reload --port 8080
cd frontend && npm install && cp .env.example .env.local && npm run dev   # http://localhost:3000
```

## Working rules
- **Plan first** for anything larger than a small fix: propose the approach, wait for approval.
- **Vertical slices:** build one feature end-to-end (UI → API → service → AI) before polishing.
- **Verify before claiming done:** run the relevant checks and report actual output.
  - backend: `uv run ruff check . && uv run pytest`
  - frontend: `npm run lint && npx tsc --noEmit && npm run build`
- **Ask before** adding a dependency, changing the API contract, or changing deployment config.
- Keep changes focused; no drive-by refactors or unrelated formatting.
- Don't commit unless asked. Commit messages use Conventional Commits (`feat:`, `fix:`,
  `docs:`, `test:`, `chore:`), scoped where useful (e.g. `feat(backend): …`).

## Non-negotiables
- **No secrets in code, logs or the frontend.** The LLM key lives only in the backend env
  (Secret Manager on Cloud Run). Never read or print `.env` files.
- **No invented answers.** Extraction leaves missing fields `null`; Q&A returns `found: false`
  when the document doesn't contain the answer. Always carry source pages through.
- **Licences are personal data:** don't log document contents, don't commit samples,
  don't persist data in browser storage.
- **Validate on the server**; client-side validation is UX only.
- **LLM output is untrusted:** always parse it into Pydantic models; document text is data,
  never instructions.

## Deployment (manual for now; CI/CD later)
- Frontend: Vercel, Root Directory `frontend`, env `NEXT_PUBLIC_API_URL`.
- Backend: `gcloud run deploy dl-backend --source backend …` (full command in backend/CLAUDE.md).
  Cloud Run is stateless; state stays in memory with `--max-instances 1` until storage moves to GCS.

## Documentation duties
- Record notable AI-assisted work and corrections in `docs/AI_USAGE.md`.
- When a technical decision from `docs/SPEC.md → Open decisions` is made, note it and the reason
  for the README's "Key technical decisions" section.
