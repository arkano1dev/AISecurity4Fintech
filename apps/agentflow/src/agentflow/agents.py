from __future__ import annotations

from typing import Any

from agentflow.pii_client import Masker
from agentflow.tools import AccountService
from agentflow.vaultrag_client import VaultragQuerier


class RetrievalAgent:
    """Answers questions by delegating to VaultRAG, masking the question first."""

    name = "retrieval"
    required_scopes = ["agent:retrieve"]

    def __init__(self, masker: Masker, vaultrag: VaultragQuerier) -> None:
        self._masker = masker
        self._vaultrag = vaultrag

    def run(self, message: str, actor_sub: str, token: str) -> dict[str, Any]:
        masked = self._masker.mask(message)  # defense in depth
        return self._vaultrag.query(masked, token)


class ActionAgent:
    """Performs bounded, sub-keyed actions: freeze_card and check_balance."""

    name = "action"
    required_scopes = ["agent:action"]

    def __init__(self, account: AccountService) -> None:
        self._account = account

    def run(self, message: str, actor_sub: str, token: str) -> dict[str, Any]:
        lowered = message.lower()
        if "balance" in lowered or "funds" in lowered:
            return self._account.check_balance(actor_sub)
        return self._account.freeze_card(actor_sub)
