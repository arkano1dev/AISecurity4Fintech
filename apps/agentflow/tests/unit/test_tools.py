from __future__ import annotations

from agentflow.tools import AccountService


def test_check_balance_returns_seeded_balance() -> None:
    account = AccountService(balances={"alice": 1000.0})
    result = account.check_balance("alice")
    assert result["balance"] == 1000.0
    assert result["account"] == "alice"
    assert result["tool"] == "check_balance"


def test_check_balance_defaults_to_zero() -> None:
    account = AccountService()
    assert account.check_balance("unknown")["balance"] == 0.0


def test_check_balance_is_sub_keyed() -> None:
    # The tool only ever looks up the actor's own sub; a name in a message is
    # irrelevant to the lookup.
    account = AccountService(balances={"alice": 1000.0, "bob": 250.0})
    assert account.check_balance("alice")["balance"] == 1000.0


def test_freeze_card_marks_sub_frozen() -> None:
    account = AccountService()
    result = account.freeze_card("alice")
    assert result["status"] == "frozen"
    assert result["account"] == "alice"
    assert account.is_frozen("alice")
    assert not account.is_frozen("bob")
