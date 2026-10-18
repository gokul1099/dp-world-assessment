# Walkthrough notes: AI Document Intelligence assessment

A first-person explanation to talk through while demonstrating the application. The notes in
*italics* say what to have on screen.

---

## Overview

This is my submission for the AI Document Intelligence assessment. The application reads a
driving licence, extracts its details into a structured form, lets the user review and correct
them, and then lets them ask questions about the licence. Answers come only from the document,
with the page they came from.

The frontend is built with Next.js and TypeScript; the backend is a Python FastAPI service.
Both are deployed on Google Cloud Run. I'll walk through the application first, then explain
the architecture, the AI approach and the main decisions I made.

---

## Application walkthrough

*Open the live application and upload one of the sample licences.*

**Upload.** The application accepts PDF, JPG and PNG files up to 10 MB. Files are checked in the
browser for immediate feedback and validated again on the server. The server detects the real
file type from the file's content rather than trusting the file name, and limits size and page
count.

**Extraction.** On the server, the document is converted into page images. Each page is sent to
a vision language model, which returns both the full text of the page and the structured licence
fields in a single call. While this runs, the user sees a "Reading document" status.

*The review screen appears.*

**Auto-populated form.** The extracted details fill the form: full name, licence number, date of
birth, issue and expiry dates, address, vehicle classes and issuing authority. Any additional
information the model finds, such as restriction codes or place of birth, appears under "Other
information". If a field is not present on the document, it is left empty and marked "Not found
in document" rather than guessed.

**Verification.** The uploaded document stays visible beside the extracted data, so each value
can be checked against the original. Every field shows which page it was read from. Selecting
that page reference switches the document viewer to that page, and the image can be enlarged to
read small text.

*Make a deliberate error, for example clear the name, then correct a field and save.*

**Review and edit.** All fields are editable. Validation runs in the browser and again on the
server: name and licence number are required, the date of birth must be in the past, and the
expiry date must come after the issue date. When the user saves, the reviewed record is stored,
along with searchable versions of each field, so later answers reflect the user's corrections.

*The chat screen opens with a personalised greeting.*

**Ask the document.** After saving, the user is greeted by name and can ask questions about
their licence. For example:
- *"What is the licence expiry date?"*: the answer shows the date and its source page.
- *"What vehicles am I authorised to drive?"*: it lists the categories and explains the codes.
- *"What is the licence number?"*: an exact match from the document.
- *"What is my blood group?"*: the answer is "This information is not available in the
  document." The system does not invent information that isn't there.

---

## Architecture

*Show the architecture diagram in the README.*

The solution has two services on Google Cloud Run: the Next.js frontend and the FastAPI backend.

The backend has a thin API layer over four services:
- **Ingestion** validates the file and converts it to page images.
- **Extraction** calls the vision model and returns page text plus structured fields.
- **Records** validates and saves the reviewed fields.
- **Retrieval and answering** handles document question-answering.

For language models I use Groq: a Qwen vision model reads the documents, and the gpt-oss-120b
model answers questions. Text embeddings are generated locally with the fastembed library, so no
additional external service is needed. Data is stored in Milvus Lite, a vector database that runs
embedded inside the backend, so there is no separate database server to operate.

---

## AI approach

*Optionally show `backend/app/llm/prompts.py` and `backend/app/services/rag.py`.*

**Structured extraction.** Each page is sent to the vision model with a strict JSON schema using
Groq's structured outputs, so the response always has the expected shape. The output is then
validated with Pydantic, which ensures, for example, that dates are real dates. If a call fails,
it is retried once, and the user then sees a clear error with an option to try again. For
multi-page documents, the most confident value for each field is kept along with its page
number, which is what drives the page references in the interface.

**Question answering with retrieval (RAG).** The page text is split into small sections when the
document is uploaded, and each saved field is stored as its own short entry. All of these are
embedded and stored in Milvus with the document ID and page number as metadata.

When a question is asked, the system runs a **hybrid search** that combines two methods:
- semantic vector search, which matches meaning;
- keyword search (BM25), which is better at exact values such as licence numbers and category
  codes.

The two result lists are merged using Reciprocal Rank Fusion. Both searches are restricted to the
current document's ID within the search itself, so a question can never retrieve another
document's data.

The retrieved sections are passed to the answering model with clear rules: answer only from the
provided content, state when the information is not available, prefer the user's corrected
values, and ignore any instructions that might appear inside the document itself. That last rule
guards against prompt injection.

---

## Key decisions

- **Vision model instead of traditional OCR.** Driving licences have small fonts, coloured
  backgrounds and varied layouts. A vision model handles these well and produces the text and
  the structured fields in one step.
- **A single data store.** Milvus holds both the saved licence record and the searchable content,
  which keeps the system simpler. A relational database would be added if the application needed
  transactions or reporting.
- **No user accounts.** Each upload receives a random, unguessable identifier that scopes all
  storage and retrieval for that session.
- **Hybrid search, but no reranking or query expansion.** A licence produces only around fifteen
  searchable sections, so retrieval already covers nearly everything. Reranking or query expansion
  would add latency without a measurable benefit here, though they would be appropriate for large
  document collections.
- **Security basics.** The API key is held only on the server in Google Secret Manager, access
  from other websites is restricted to the application's own address, uploads are validated, and
  document contents are never written to logs.

---

## Limitations and next steps

- Uploaded documents are held in the backend's memory and the vector database is stored inside
  the container, so the backend runs as a single instance. For production, I would move documents
  to Cloud Storage and the vector database to a managed service such as Zilliz Cloud.
- The Groq free tier limits how many tokens can be processed per minute, which can briefly slow
  or delay processing during heavy use.
- There is no authentication; a production version would add user accounts and filter data by
  user as well as by document.
- Automated tests were deprioritised to deliver the complete feature set within the timeframe.

---

## Development tools

As permitted in the brief, I used Claude Code during development, for planning, scaffolding,
implementation support, debugging and documentation. I made the design decisions, and I reviewed
and tested each feature as it was built.

The source code, README with setup instructions, and the live application link are included in
my submission.
