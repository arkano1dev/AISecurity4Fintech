from __future__ import annotations

import pytest
from agentflow.supervisor import InsufficientScopeError, Intent, Supervisor, classify


def test_classify_action_keywords() -> None:
    assert classify("please freeze my card") is Intent.ACTION
    assert classify("I want to dispute a charge") is Intent.ACTION


def test_classify_defaults_to_retrieval() -> None:
    assert classify("what is the wire transfer threshold?") is Intent.RETRIEVAL


def test_dispatch_retrieval() -> None:
    outcome = Supervisor().dispatch("what is the wire transfer threshold?", ["agent:retrieve"])
    assert outcome["intent"] == "retrieval"
    assert outcome["agent"] == "retrieval"
    assert outcome["result"]["answer"]


def test_dispatch_action() -> None:
    outcome = Supervisor().dispatch("freeze my card", ["agent:action"])
    assert outcome["intent"] == "action"
    assert outcome["agent"] == "action"
    assert outcome["result"]["status"] == "frozen"


def test_dispatch_missing_scope_raises() -> None:
    with pytest.raises(InsufficientScopeError):
        Supervisor().dispatch("freeze my card", ["chat:send"])
