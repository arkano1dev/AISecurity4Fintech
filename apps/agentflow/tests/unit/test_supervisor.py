from __future__ import annotations

import pytest

from agentflow.agents import ActionAgent, RetrievalAgent
from agentflow.supervisor import InsufficientScopeError, Intent, Supervisor, classify
from agentflow.tools import AccountService


class _FakeMasker:
    def mask(self, text: str) -> str:
        return text


class _FakeVaultrag:
    def query(self, question: str, token: str) -> dict[str, object]:
        return {"answer": "ok", "citations": []}


def _supervisor() -> Supervisor:
    return Supervisor(
        RetrievalAgent(_FakeMasker(), _FakeVaultrag()),
        ActionAgent(AccountService(balances={"alice": 100.0})),
    )


def test_classify_action_keywords() -> None:
    assert classify("please freeze my card") is Intent.ACTION
    assert classify("check my balance") is Intent.ACTION
    assert classify("I want to dispute a charge") is Intent.ACTION


def test_classify_defaults_to_retrieval() -> None:
    assert classify("what is the wire transfer threshold?") is Intent.RETRIEVAL


def test_dispatch_retrieval() -> None:
    outcome = _supervisor().dispatch(
        "what is the wire transfer threshold?",
        actor_sub="alice",
        scopes=["agent:retrieve"],
        token="t",
    )
    assert outcome["intent"] == "retrieval"
    assert outcome["agent"] == "retrieval"
    assert outcome["result"]["answer"] == "ok"


def test_dispatch_check_balance() -> None:
    outcome = _supervisor().dispatch(
        "check my balance",
        actor_sub="alice",
        scopes=["agent:action"],
        token="t",
    )
    assert outcome["intent"] == "action"
    assert outcome["result"]["tool"] == "check_balance"
    assert outcome["result"]["account"] == "alice"


def test_dispatch_freeze() -> None:
    outcome = _supervisor().dispatch(
        "freeze my card",
        actor_sub="alice",
        scopes=["agent:action"],
        token="t",
    )
    assert outcome["intent"] == "action"
    assert outcome["result"]["tool"] == "freeze_card"
    assert outcome["result"]["status"] == "frozen"


def test_dispatch_missing_scope_raises() -> None:
    with pytest.raises(InsufficientScopeError):
        _supervisor().dispatch(
            "freeze my card",
            actor_sub="alice",
            scopes=["chat:send"],
            token="t",
        )
