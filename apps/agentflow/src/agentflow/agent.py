from __future__ import annotations

import hashlib
from typing import Any

from agentflow.audit_client import Auditor
from agentflow.llm import AgentDecision, Decider, LlmError
from agentflow.pii_client import Masker
from agentflow.supervisor import InsufficientScopeError, Supervisor
from agentflow.tools import AccountService
from agentflow.vaultrag_client import VaultragQuerier
from shared.guardrail import REFUSAL, check_output

MAX_STEPS = 3

TOOL_SCOPES: dict[str, str] = {
    "retrieve": "agent:retrieve",
    "freeze_card": "agent:action",
    "check_balance": "agent:action",
}

# Explicit refusal when the model repeats a tool (isolation / loop guard).
REFUSALS: dict[str, str] = {
    "check_balance": "I can only access your own account.",
    "freeze_card": "I can only manage your own card.",
    "retrieve": "I can only search your own documents.",
}
GENERIC_REFUSAL = "I couldn't complete that request safely."


class Agent:
    """An LLM-driven agent loop over a bounded, sub-keyed tool allowlist.

    The model selects a tool from the allowlist; the tool then executes with
    arguments bound to the authenticated identity, never to the model's output.
    Every LLM decision and every tool call is audited. If the model fails at the
    first step, the deterministic keyword classifier takes over. A repeated tool
    call is refused explicitly rather than allowed to loop, and the final answer
    passes through a deterministic output guardrail.
    """

    def __init__(
        self,
        llm: Decider,
        masker: Masker,
        vaultrag: VaultragQuerier,
        account: AccountService,
        fallback: Supervisor,
        audit: Auditor,
        *,
        max_steps: int = MAX_STEPS,
    ) -> None:
        self._llm = llm
        self._masker = masker
        self._vaultrag = vaultrag
        self._account = account
        self._fallback = fallback
        self._audit = audit
        self._max_steps = max_steps

    def run(self, message: str, *, actor_sub: str, scopes: list[str], token: str) -> dict[str, Any]:
        masked = self._masker.mask(message)
        self._audit.append(
            actor_sub=actor_sub,
            action="agentflow.dispatch",
            payload={"agent": "llm", "message_hash": _sha256(masked)},
        )
        history: list[dict[str, Any]] = []
        called: set[str] = set()
        for step in range(self._max_steps):
            try:
                decision = self._llm.decide(masked, history)
            except LlmError:
                if step == 0:
                    return self._fallback_result(masked, actor_sub, scopes, token)
                break
            if decision.action == "final":
                return self._final(decision, step, actor_sub)
            tool = decision.tool
            assert tool is not None
            if tool in called:
                return self._refusal(tool, step, actor_sub)
            self._enforce_scope(scopes, TOOL_SCOPES[tool])
            called.add(tool)
            result = self._execute_tool(tool, masked, actor_sub, token)
            self._audit.append(
                actor_sub=actor_sub,
                action="agentflow.action",
                payload={
                    "tool": tool,
                    "account": result.get("account"),
                    "status": result.get("status"),
                },
            )
            history.append({"tool": tool, "result": result})
        return self._refusal(None, self._max_steps - 1, actor_sub)

    def _execute_tool(self, tool: str, masked: str, actor_sub: str, token: str) -> dict[str, Any]:
        if tool == "retrieve":
            return self._vaultrag.query(masked, token)
        if tool == "freeze_card":
            return self._account.freeze_card(actor_sub)
        return self._account.check_balance(actor_sub)

    def _fallback_result(
        self, masked: str, actor_sub: str, scopes: list[str], token: str
    ) -> dict[str, Any]:
        outcome = self._fallback.dispatch(masked, actor_sub=actor_sub, scopes=scopes, token=token)
        result = outcome["result"]
        if outcome["intent"] == "action":
            self._audit.append(
                actor_sub=actor_sub,
                action="agentflow.action",
                payload={
                    "tool": result.get("tool"),
                    "account": result.get("account"),
                    "status": result.get("status"),
                },
            )
        return {
            "intent": outcome["intent"],
            "agent": outcome["agent"],
            "answer": result.get("answer", ""),
            "result": result,
            "steps": 1,
            "fallback": True,
        }

    def _final(self, decision: AgentDecision, step: int, actor_sub: str) -> dict[str, Any]:
        answer = decision.answer or ""
        verdict = check_output(answer)
        if verdict.blocked:
            answer = REFUSAL
            self._audit.append(
                actor_sub=actor_sub,
                action="agentflow.guardrail_block",
                payload={"reason": verdict.reason},
            )
        return {
            "intent": "final",
            "agent": "llm",
            "answer": answer,
            "result": {"answer": answer},
            "steps": step + 1,
            "fallback": False,
        }

    def _refusal(self, tool: str | None, step: int, actor_sub: str) -> dict[str, Any]:
        answer = REFUSALS.get(tool, GENERIC_REFUSAL) if tool else GENERIC_REFUSAL
        self._audit.append(
            actor_sub=actor_sub,
            action="agentflow.refusal",
            payload={"tool": tool},
        )
        return {
            "intent": "final",
            "agent": "llm",
            "answer": answer,
            "result": {"answer": answer},
            "steps": step + 1,
            "fallback": False,
        }

    @staticmethod
    def _enforce_scope(scopes: list[str], required: str) -> None:
        if required not in scopes:
            raise InsufficientScopeError([required])


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
