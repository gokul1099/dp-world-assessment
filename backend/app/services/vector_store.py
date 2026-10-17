"""Milvus Lite storage: embedded in this process, persisted to data/milvus.db (no server/port).

Two collections:
- `licences`:       one row per document — the saved form (JSON) + an embedding of its summary.
- `licence_chunks`: many rows per document — short texts with page metadata, used for Q&A.

Pointing MilvusClient at a Zilliz Cloud URI instead of a file moves this to managed Milvus.
"""

import time
from pathlib import Path
from typing import Any

from pymilvus import DataType, MilvusClient

from app.services.embeddings import EMBEDDING_DIM

LICENCES = "licences"
CHUNKS = "licence_chunks"


class VectorStore:
    def __init__(self, data_dir: str) -> None:
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        self.client = MilvusClient(str(Path(data_dir) / "milvus.db"))
        self._ensure_collections()

    def _ensure_collections(self) -> None:
        if not self.client.has_collection(LICENCES):
            schema = self.client.create_schema(auto_id=False, enable_dynamic_field=False)
            schema.add_field("document_id", DataType.VARCHAR, is_primary=True, max_length=64)
            schema.add_field("filename", DataType.VARCHAR, max_length=255)
            schema.add_field("fields", DataType.JSON)
            schema.add_field("updated_at", DataType.INT64)
            schema.add_field("vector", DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM)
            index = self.client.prepare_index_params()
            index.add_index("vector", index_type="FLAT", metric_type="COSINE")
            self.client.create_collection(LICENCES, schema=schema, index_params=index)

        if not self.client.has_collection(CHUNKS):
            schema = self.client.create_schema(auto_id=True, enable_dynamic_field=False)
            schema.add_field("id", DataType.INT64, is_primary=True)
            schema.add_field("document_id", DataType.VARCHAR, max_length=64)
            schema.add_field("page", DataType.INT64)  # 0 = unknown page
            schema.add_field("source", DataType.VARCHAR, max_length=32)  # "field" | "page_text"
            schema.add_field("text", DataType.VARCHAR, max_length=4096)
            schema.add_field("vector", DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM)
            index = self.client.prepare_index_params()
            index.add_index("vector", index_type="FLAT", metric_type="COSINE")
            self.client.create_collection(CHUNKS, schema=schema, index_params=index)

        # Collections reopened from disk start "released"; load them before reads/searches.
        for name in (LICENCES, CHUNKS):
            self.client.load_collection(name)

    # --- saved licence record -------------------------------------------------

    def save_licence(
        self, document_id: str, filename: str, fields: dict[str, Any], vector: list[float]
    ) -> None:
        """Insert or replace the saved form for this document."""
        self.client.upsert(
            LICENCES,
            [
                {
                    "document_id": document_id,
                    "filename": filename,
                    "fields": fields,
                    "updated_at": int(time.time()),
                    "vector": vector,
                }
            ],
        )

    def get_licence(self, document_id: str) -> dict[str, Any] | None:
        rows = self.client.get(
            LICENCES, ids=[document_id], output_fields=["filename", "fields", "updated_at"]
        )
        return rows[0] if rows else None

    # --- chunks for Q&A -------------------------------------------------------

    def search_chunks(
        self, document_id: str, vector: list[float], limit: int = 6
    ) -> list[dict[str, Any]]:
        """Vector search restricted to ONE document. The filter is applied inside the search,
        so other documents' chunks are never candidates."""
        results = self.client.search(
            CHUNKS,
            data=[vector],
            limit=limit,
            filter=f'document_id == "{document_id}"',
            output_fields=["page", "source", "text"],
        )
        return [{**hit["entity"], "score": hit["distance"]} for hit in results[0]]

    def replace_chunks(
        self, document_id: str, source: str, chunks: list[dict[str, Any]]
    ) -> None:
        """Swap all chunks of one source type for a document (e.g. after the user edits fields).

        Each chunk: {"text": str, "page": int, "vector": list[float]}.
        """
        self.client.delete(
            CHUNKS, filter=f'document_id == "{document_id}" and source == "{source}"'
        )
        if chunks:
            self.client.insert(
                CHUNKS,
                [{**chunk, "document_id": document_id, "source": source} for chunk in chunks],
            )
