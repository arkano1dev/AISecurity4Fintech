from __future__ import annotations

from typing import Protocol

import httpx


class Masker(Protocol):
    def mask(self, text: str) -> str: ...


class PiiClient:
    """HTTP client for the shared pii-proxy service."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def mask(self, text: str) -> str:
        response = httpx.post(f"{self.base_url}/pii/mask", json={"text": text}, timeout=10.0)
        response.raise_for_status()
        return str(response.json()["redacted"])
