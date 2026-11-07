from __future__ import annotations

import httpx

from vaultrag.settings import settings


def embed_texts(
    texts: list[str],
    *,
    ollama_url: str | None = None,
    model: str | None = None,
) -> list[list[float]]:
    """Embed a list of texts with the configured embedding model (Ollama)."""
    base = ollama_url or settings.ollama_url
    name = model or settings.embed_model
    embeddings: list[list[float]] = []
    for text in texts:
        response = httpx.post(
            f"{base}/api/embeddings",
            json={"model": name, "prompt": text},
            timeout=60.0,
        )
        response.raise_for_status()
        embeddings.append([float(x) for x in response.json()["embedding"]])
    return embeddings
