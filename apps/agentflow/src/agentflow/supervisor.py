from __future__ import annotations

from enum import StrEnum
from typing import Any

from agentflow.agents import ActionAgent, RetrievalAgent


class Intent(StrEnum):
    RETRIEVAL = "retrieval"
    ACTION = "action"


ACTION_KEYWORDS = ("freeze", "block", "dispute", "fraud", "unauthorized", "stolen", "suspend")


def classify(message: str) -> Intent:
    """Classify a message into an intent with a deterministic keyword map.

    No model is called to route: routing is a security decision, not a language
    task, so it must have no injection surface and be fully testable.
    """
    lowered = message.lower()
    if any(keyword in lowered for keyword in ACTION_KEYWORDS):
        return Intent.ACTION
    return Intent.RETRIEVAL


class InsufficientScopeError(Exception):
    def __init__(self, required: list[str]) -> None:
        self.required = required
        super().__init__(f"missing required scopes: {required}")


class Supervisor:
    """Classifies a message and dispatches it to the agent with bounded authority.

    Each agent declares ``required_scopes``; a dispatch is rejected if the
    caller's token does not carry them.
    """

    def __init__(
        self,
        retrieval_agent: RetrievalAgent | None = None,
        action_agent: ActionAgent | None = None,
    ) -> None:
        self._retrieval = retrieval_agent or RetrievalAgent()
        self._action = action_agent or ActionAgent()

    def dispatch(self, message: str, scopes: list[str]) -> dict[str, Any]:
        intent = classify(message)
        agent = self._action if intent is Intent.ACTION else self._retrieval
        self._enforce_scope(scopes, agent.required_scopes)
        result = agent.run(message)
        return {"intent": intent.value, "agent": agent.name, "result": result}

    @staticmethod
    def _enforce_scope(scopes: list[str], required: list[str]) -> None:
        if set(required) - set(scopes):
            raise InsufficientScopeError(required)
