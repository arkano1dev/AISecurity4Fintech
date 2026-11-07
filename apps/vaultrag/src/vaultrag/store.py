from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    """A single embedded chunk of a document, stored redacted."""

    chunk_id: str
    doc_id: str
    text: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorStore:
    """In-memory store of embedded chunks with a linear scan.

    Deliberately simple: the PRD defers a real vector database (pgvector) until
    the platform is proven end to end. The interface (add_chunk, chunks) is what
    a future pgvector-backed store will also implement.
    """

    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._documents: dict[str, str] = {}

    def add_document(self, doc_id: str, title: str) -> None:
        self._documents[doc_id] = title

    def add_chunk(self, chunk: Chunk) -> None:
        self._chunks.append(chunk)

    def chunks(self) -> list[Chunk]:
        return list(self._chunks)

    def document_title(self, doc_id: str) -> str:
        return self._documents.get(doc_id, doc_id)
