from __future__ import annotations


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into fixed-size windows with a character overlap.

    The overlap keeps context that would otherwise fall across a window boundary
    retrievable, so a fact split between two chunks is still found.
    """
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    cleaned = text.strip()
    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0
    length = len(cleaned)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = end - overlap
    return chunks
