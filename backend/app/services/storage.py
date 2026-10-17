"""Document storage.

In-memory for the demo: data lives only in this process, so Cloud Run must run with
`--max-instances 1` and documents disappear on restart or scale-down. Swapping this for
GCS (page images) + Firestore (metadata/fields) only requires a new class with the same methods.
"""

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.schemas.licence import LicenceFields


@dataclass(slots=True)
class StoredDocument:
    document_id: str
    filename: str  # sanitised, for display only
    content_type: str
    pages: list[bytes]  # PNG bytes, one per page
    page_texts: list[str] = field(default_factory=list)  # OCR text, one per page
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    fields: LicenceFields | None = None

    @property
    def page_count(self) -> int:
        return len(self.pages)


class InMemoryDocumentStore:
    """Thread-safe store that evicts the oldest documents beyond `max_documents`."""

    def __init__(self, max_documents: int = 50) -> None:
        self._max_documents = max_documents
        self._documents: OrderedDict[str, StoredDocument] = OrderedDict()
        self._lock = threading.Lock()

    def save(self, document: StoredDocument) -> None:
        with self._lock:
            self._documents[document.document_id] = document
            self._documents.move_to_end(document.document_id)
            while len(self._documents) > self._max_documents:
                self._documents.popitem(last=False)

    def get(self, document_id: str) -> StoredDocument | None:
        with self._lock:
            return self._documents.get(document_id)

    def __len__(self) -> int:
        with self._lock:
            return len(self._documents)
