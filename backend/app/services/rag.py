"""Document Q&A (RAG): index page text, retrieve chunks for one document, answer from them."""

from app.llm.client import chat_json
from app.llm.prompts import ANSWER_SCHEMA, ANSWER_SYSTEM_PROMPT
from app.schemas.chat import AskResponse, SourceRef
from app.services.embeddings import embed_query, embed_texts
from app.services.vector_store import VectorStore

LINES_PER_CHUNK = 4
LINE_OVERLAP = 1
TOP_K = 10  # a licence has ~15 chunks; still filtered to this document only
NOT_FOUND_ANSWER = "This information is not available in the document."


def chunk_page_text(text: str) -> list[str]:
    """Small overlapping groups of lines: licence text is short and line-oriented."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    step = LINES_PER_CHUNK - LINE_OVERLAP
    chunks = []
    for start in range(0, len(lines), step):
        chunks.append("\n".join(lines[start : start + LINES_PER_CHUNK]))
        if start + LINES_PER_CHUNK >= len(lines):
            break
    return chunks


def index_page_texts(vector_store: VectorStore, document_id: str, page_texts: list[str]) -> None:
    """Embed OCR text per page into Milvus (source="page_text"). Runs in a worker thread."""
    chunks = [
        (chunk, page_number)
        for page_number, text in enumerate(page_texts, start=1)
        for chunk in chunk_page_text(text)
    ]
    vectors = embed_texts([text for text, _ in chunks]) if chunks else []
    vector_store.replace_chunks(
        document_id,
        source="page_text",
        chunks=[
            {"text": text[:4000], "page": page, "vector": vector}
            for (text, page), vector in zip(chunks, vectors, strict=True)
        ],
    )


def answer_question(vector_store: VectorStore, document_id: str, question: str) -> AskResponse:
    """Retrieve this document's most relevant chunks and answer only from them."""
    # Hybrid retrieval: dense embedding + BM25 keywords, fused with RRF.
    hits = vector_store.search_chunks(document_id, question, embed_query(question), limit=TOP_K)
    if not hits:
        return AskResponse(answer=NOT_FOUND_ANSWER, found=False)

    excerpts = "\n\n".join(
        f"[{i}] (page {hit['page'] or 'unknown'}, {hit['source']})\n{hit['text']}"
        for i, hit in enumerate(hits, start=1)
    )
    reply = chat_json(
        system=ANSWER_SYSTEM_PROMPT,
        user=f"<excerpts>\n{excerpts}\n</excerpts>\n\nQuestion: {question}",
        schema=ANSWER_SCHEMA,
        name="licence_answer",
    )

    if not reply["found"]:
        return AskResponse(answer=reply["answer"] or NOT_FOUND_ANSWER, found=False)

    # Cite the pages of the excerpts the model says it used (one badge per page).
    sources: dict[int, SourceRef] = {}
    for index in reply["used_excerpts"]:
        if 1 <= index <= len(hits):
            hit = hits[index - 1]
            if hit["page"] >= 1 and hit["page"] not in sources:
                sources[hit["page"]] = SourceRef(page=hit["page"], snippet=hit["text"])
    return AskResponse(answer=reply["answer"], found=True, sources=list(sources.values()))
