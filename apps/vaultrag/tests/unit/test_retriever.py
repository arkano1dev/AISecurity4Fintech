from __future__ import annotations

import pytest

from vaultrag.retriever import cosine_similarity, retrieve
from vaultrag.store import Chunk


def test_cosine_identical_vectors() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)


def test_cosine_orthogonal_vectors() -> None:
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_mismatched_length_raises() -> None:
    with pytest.raises(ValueError):
        cosine_similarity([1.0], [1.0, 2.0])


def test_retrieve_returns_top_k_ordered() -> None:
    chunks = [
        Chunk(chunk_id="a", doc_id="d", text="a", embedding=[1.0, 0.0]),
        Chunk(chunk_id="b", doc_id="d", text="b", embedding=[0.9, 0.4]),
        Chunk(chunk_id="c", doc_id="d", text="c", embedding=[0.0, 1.0]),
    ]
    hits = retrieve(chunks, [1.0, 0.0], top_k=2)
    assert [chunk.chunk_id for _, chunk in hits] == ["a", "b"]
