
import logging
import time
from pathlib import Path
from typing import Any

from pymilvus import AnnSearchRequest, DataType, Function, FunctionType, MilvusClient, RRFRanker

from app.services.embeddings import EMBEDDING_DIM

logger = logging.getLogger(__name__)

LICENCES = "licences"
CHUNKS = "licence_chunks"
RRF_K = 60  # standard Reciprocal Rank Fusion constant


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

        if self.client.has_collection(CHUNKS) and not self._chunks_have_sparse():
            # Older schema without the BM25 field: chunks are derived data, so rebuild.
            logger.warning("Recreating %s with hybrid (BM25) schema", CHUNKS)
            self.client.drop_collection(CHUNKS)

        if not self.client.has_collection(CHUNKS):
            schema = self.client.create_schema(auto_id=True, enable_dynamic_field=False)
            schema.add_field("id", DataType.INT64, is_primary=True)
            schema.add_field("document_id", DataType.VARCHAR, max_length=64)
            schema.add_field("page", DataType.INT64)  # 0 = unknown page
            schema.add_field("source", DataType.VARCHAR, max_length=32)  # "field" | "page_text"
            # enable_analyzer: Milvus tokenises the text for BM25 keyword search.
            schema.add_field("text", DataType.VARCHAR, max_length=4096, enable_analyzer=True)
            schema.add_field("vector", DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM)
            schema.add_field("sparse", DataType.SPARSE_FLOAT_VECTOR)
            # Milvus fills `sparse` from `text` on insert, and from the query text on search.
            schema.add_function(
                Function(
                    name="text_bm25",
                    function_type=FunctionType.BM25,
                    input_field_names=["text"],
                    output_field_names=["sparse"],
                )
            )
            index = self.client.prepare_index_params()
            index.add_index("vector", index_type="FLAT", metric_type="COSINE")
            index.add_index("sparse", index_type="SPARSE_INVERTED_INDEX", metric_type="BM25")
            self.client.create_collection(CHUNKS, schema=schema, index_params=index)

        # Collections reopened from disk start "released"; load them before reads/searches.
        for name in (LICENCES, CHUNKS):
            self.client.load_collection(name)

    def _chunks_have_sparse(self) -> bool:
        fields = self.client.describe_collection(CHUNKS)["fields"]
        return any(field["name"] == "sparse" for field in fields)

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
        self, document_id: str, query_text: str, query_vector: list[float], limit: int = 10
    ) -> list[dict[str, Any]]:
        """Hybrid search restricted to ONE document.

        - dense: embedding similarity, good for meaning ("when does it run out?" → expiry date)
        - BM25:  exact keyword match, good for codes/numbers ("TESTE901150JM9AB", "code 01")
        Results are merged with Reciprocal Rank Fusion. The document_id filter is applied inside
        both searches, so other documents' chunks are never candidates.
        """
        doc_filter = f'document_id == "{document_id}"'
        requests = [
            AnnSearchRequest(
                data=[query_vector], anns_field="vector", param={}, limit=limit, expr=doc_filter
            ),
            AnnSearchRequest(
                data=[query_text], anns_field="sparse", param={}, limit=limit, expr=doc_filter
            ),
        ]
        results = self.client.hybrid_search(
            CHUNKS,
            requests,
            ranker=RRFRanker(RRF_K),
            limit=limit,
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
