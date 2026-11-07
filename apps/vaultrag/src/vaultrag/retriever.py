from __future__ import annotations

import math

from vaultrag.store import Chunk


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors; 0.0 when either is a zero vector."""
    if len(a) != len(b):
        raise ValueError("vectors must have the same length")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def retrieve(
    chunks: list[Chunk], query_embedding: list[float], top_k: int
) -> list[tuple[float, Chunk]]:
    """Return the top_k most similar chunks, sorted by descending similarity."""
    scored = [(cosine_similarity(query_embedding, chunk.embedding), chunk) for chunk in chunks]
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[:top_k]
