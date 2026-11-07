from __future__ import annotations

from typing import Any

from agentflow.tools import FreezeCardTool

# A small, bounded knowledge base for the retrieval agent. Deterministic, no LLM.
KNOWLEDGE: dict[str, str] = {
    "wire transfer": (
        "A wire transfer of ten thousand euro or more requires approval by a manager."
    ),
    "retention": "Customer records are retained for ten years.",
    "subject access": "A subject access request must be answered within thirty days.",
}


class RetrievalAgent:
    """Answers information questions from a fixed knowledge base. No tools."""

    name = "retrieval"
    required_scopes = ["agent:retrieve"]

    def run(self, message: str) -> dict[str, Any]:
        lowered = message.lower()
        for key, answer in KNOWLEDGE.items():
            if key in lowered:
                return {"answer": answer, "source": key}
        return {"answer": "No matching entry in the internal knowledge base.", "source": None}


class ActionAgent:
    """Performs exactly one bounded, audited action: freeze_card."""

    name = "action"
    required_scopes = ["agent:action"]

    def __init__(self, tool: FreezeCardTool | None = None) -> None:
        self._tool = tool or FreezeCardTool()

    def run(self, message: str) -> dict[str, Any]:
        # MVP: freeze applies to the caller's primary card.
        return self._tool.run("primary")
