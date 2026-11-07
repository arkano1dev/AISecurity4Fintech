from __future__ import annotations

from typing import Any, Protocol

import httpx


class VaultragUnavailableError(Exception):
    """Raised when VaultRAG cannot serve a retrieval request."""


class VaultragQuerier(Protocol):
    def query(self, question: str, token: str) -> dict[str, Any]: ...


class VaultragClient:
    """HTTP client for the VaultRAG service; forwards the caller's bearer token."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def query(self, question: str, token: str) -> dict[str, Any]:
        try:
            response = httpx.post(
                f"{self.base_url}/vaultrag/query",
                json={"question": question},
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0,
            )
            response.raise_for_status()
            return dict(response.json())
        except httpx.HTTPError as exc:
            raise VaultragUnavailableError() from exc
