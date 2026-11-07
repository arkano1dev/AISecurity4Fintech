from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest
from agentflow.agent import Agent
from agentflow.agents import ActionAgent, RetrievalAgent
from agentflow.llm import AgentDecision, LlmError
from agentflow.supervisor import InsufficientScopeError, Supervisor
from agentflow.tools import AccountService


class FakeMasker:
    def mask(self, text: str) -> str:
        return text.replace("DE89370400440532013000", "[IBAN]")


class FakeVaultrag:
    def __init__(self) -> None:
        self.questions: list[str] = []
        self.tokens: list[str] = []

    def query(self, question: str, token: str) -> dict[str, Any]:
        self.questions.append(question)
        self.tokens.append(token)
        return {
            "answer": "cited answer",
            "citations": [{"doc_id": "d", "chunk_id": "d:0", "text": "ctx"}],
        }


class FakeAuditor:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def append(self, *, actor_sub: str, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.records.append({"actor_sub": actor_sub, "action": action, "payload": payload})
        return {"id": "a", "seq": len(self.records)}


class FakeLlm:
    def __init__(self, decisions: Sequence[AgentDecision | Exception]) -> None:
        self._decisions = list(decisions)
        self.questions: list[str] = []
        self.histories: list[list[dict[str, Any]]] = []

    def decide(self, question: str, history: list[dict[str, Any]]) -> AgentDecision:
        self.questions.append(question)
        self.histories.append(list(history))
        if not self._decisions:
            raise LlmError("no more decisions")
        item = self._decisions.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _make_agent(
    llm: FakeLlm,
    *,
    account: AccountService | None = None,
    auditor: FakeAuditor | None = None,
    vaultrag: FakeVaultrag | None = None,
    masker: FakeMasker | None = None,
) -> Agent:
    masker = masker or FakeMasker()
    vaultrag = vaultrag or FakeVaultrag()
    account = account or AccountService(balances={"alice": 1000.0, "bob": 250.0})
    auditor = auditor or FakeAuditor()
    fallback = Supervisor(RetrievalAgent(masker, vaultrag), ActionAgent(account))
    return Agent(llm, masker, vaultrag, account, fallback, auditor)


def test_agent_multi_step_freezes_card() -> None:
    llm = FakeLlm(
        [
            AgentDecision(action="tool_call", tool="freeze_card"),
            AgentDecision(action="final", answer="Your card is frozen."),
        ]
    )
    account = AccountService(balances={"alice": 1000.0})
    auditor = FakeAuditor()
    agent = _make_agent(llm, account=account, auditor=auditor)

    outcome = agent.run(
        "please freeze my card", actor_sub="alice", scopes=["agent:action"], token="t"
    )

    assert outcome["intent"] == "final"
    assert outcome["answer"] == "Your card is frozen."
    assert outcome["steps"] == 2
    assert account.is_frozen("alice")
    actions = [r for r in auditor.records if r["action"] == "agentflow.action"]
    assert actions and actions[0]["payload"]["tool"] == "freeze_card"


def test_agent_retrieve_delegates_to_vaultrag() -> None:
    llm = FakeLlm(
        [
            AgentDecision(action="tool_call", tool="retrieve"),
            AgentDecision(action="final", answer="The answer is cited."),
        ]
    )
    vaultrag = FakeVaultrag()
    agent = _make_agent(llm, vaultrag=vaultrag)

    outcome = agent.run(
        "wire transfer threshold?", actor_sub="alice", scopes=["agent:retrieve"], token="tok"
    )

    assert outcome["intent"] == "final"
    assert vaultrag.questions == ["wire transfer threshold?"]
    assert vaultrag.tokens == ["tok"]


def test_agent_masks_before_model() -> None:
    llm = FakeLlm([AgentDecision(action="final", answer="ok")])
    agent = _make_agent(llm)

    agent.run(
        "account DE89370400440532013000", actor_sub="alice", scopes=["agent:retrieve"], token="t"
    )

    assert "DE89370400440532013000" not in llm.questions[0]
    assert "[IBAN]" in llm.questions[0]


def test_agent_enforces_scope() -> None:
    llm = FakeLlm([AgentDecision(action="tool_call", tool="freeze_card")])
    agent = _make_agent(llm)

    with pytest.raises(InsufficientScopeError):
        agent.run("freeze my card", actor_sub="alice", scopes=["chat:send"], token="t")


def test_agent_falls_back_on_llm_error() -> None:
    llm = FakeLlm([LlmError("model unavailable")])
    agent = _make_agent(llm)

    outcome = agent.run(
        "what is the wire transfer threshold?",
        actor_sub="alice",
        scopes=["agent:retrieve"],
        token="t",
    )

    assert outcome["fallback"] is True
    assert outcome["intent"] == "retrieval"
    assert outcome["agent"] == "retrieval"


def test_agent_terminates_after_max_steps() -> None:
    decisions = [AgentDecision(action="tool_call", tool="freeze_card") for _ in range(5)]
    llm = FakeLlm(decisions)
    account = AccountService()
    agent = _make_agent(llm, account=account)

    outcome = agent.run("freeze", actor_sub="alice", scopes=["agent:action"], token="t")

    assert outcome["intent"] == "final"
    assert outcome["steps"] == 3
    assert "could not complete" in outcome["answer"]


def test_agent_sees_tool_result_in_next_step() -> None:
    # The model re-reasons with the tool result in the history (multi-step).
    llm = FakeLlm(
        [
            AgentDecision(action="tool_call", tool="check_balance"),
            AgentDecision(action="final", answer="Your balance is 1000.0."),
        ]
    )
    agent = _make_agent(llm)

    agent.run("check my balance", actor_sub="alice", scopes=["agent:action"], token="t")

    assert len(llm.histories) == 2
    assert llm.histories[1][0]["tool"] == "check_balance"
    assert llm.histories[1][0]["result"]["balance"] == 1000.0
