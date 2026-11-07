from __future__ import annotations


class FreezeCardTool:
    """The single bounded action: freeze a card.

    In-memory for now; the PRD defers persistence. The ``run`` interface is what a
    real ledger-backed action will also implement.
    """

    def __init__(self) -> None:
        self._frozen: set[str] = set()

    def run(self, card_ref: str) -> dict[str, str]:
        self._frozen.add(card_ref)
        return {"tool": "freeze_card", "card_ref": card_ref, "status": "frozen"}

    def is_frozen(self, card_ref: str) -> bool:
        return card_ref in self._frozen
