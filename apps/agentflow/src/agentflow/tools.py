from __future__ import annotations

from typing import Any


class AccountService:
    """Sub-keyed in-memory account state: balances and frozen cards.

    Every operation is keyed by the authenticated ``sub`` from the JWT, so a
    caller can only touch their own account — never an attacker-chosen id.
    """

    def __init__(self, balances: dict[str, float] | None = None) -> None:
        self._balances: dict[str, float] = dict(balances or {})
        self._frozen: set[str] = set()

    def check_balance(self, actor_sub: str) -> dict[str, Any]:
        return {
            "tool": "check_balance",
            "account": actor_sub,
            "balance": self._balances.get(actor_sub, 0.0),
        }

    def freeze_card(self, actor_sub: str) -> dict[str, Any]:
        self._frozen.add(actor_sub)
        return {"tool": "freeze_card", "account": actor_sub, "status": "frozen"}

    def is_frozen(self, actor_sub: str) -> bool:
        return actor_sub in self._frozen
