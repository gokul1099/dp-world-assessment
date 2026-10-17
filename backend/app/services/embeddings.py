"""Text embeddings with fastembed (local ONNX model, no API key needed)."""

from functools import lru_cache
from pathlib import Path

from fastembed import TextEmbedding

from app.config import get_settings

EMBEDDING_DIM = 384  # BAAI/bge-small-en-v1.5


@lru_cache
def get_embedding_model() -> TextEmbedding:
    """Loaded once per process. The first run downloads the model (~70 MB) into data/models."""
    settings = get_settings()
    cache_dir = Path(settings.data_dir) / "models"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return TextEmbedding(settings.embedding_model, cache_dir=str(cache_dir))


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed document text (chunks, summaries)."""
    return [vector.tolist() for vector in get_embedding_model().embed(texts)]


def embed_query(text: str) -> list[float]:
    """Embed a user question (bge uses a query-specific prefix)."""
    return next(get_embedding_model().query_embed(text)).tolist()
