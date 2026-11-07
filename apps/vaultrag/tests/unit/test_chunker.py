from __future__ import annotations

import pytest
from vaultrag.chunker import chunk_text


def test_chunk_text_preserves_overlap() -> None:
    chunks = chunk_text("a" * 1000, chunk_size=400, overlap=50)
    assert len(chunks) >= 3
    assert chunks[0][-50:] == chunks[1][:50]


def test_chunk_text_empty_input() -> None:
    assert chunk_text("   ") == []


def test_chunk_text_rejects_bad_overlap() -> None:
    with pytest.raises(ValueError):
        chunk_text("text", chunk_size=10, overlap=10)


def test_chunk_text_short_input_single_chunk() -> None:
    chunks = chunk_text("hello", chunk_size=400, overlap=50)
    assert chunks == ["hello"]
