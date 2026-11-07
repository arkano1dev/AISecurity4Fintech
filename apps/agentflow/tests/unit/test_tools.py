from __future__ import annotations

from agentflow.tools import FreezeCardTool


def test_freeze_card_marks_frozen() -> None:
    tool = FreezeCardTool()
    result = tool.run("primary")
    assert result["status"] == "frozen"
    assert result["tool"] == "freeze_card"
    assert tool.is_frozen("primary")


def test_freeze_card_is_idempotent() -> None:
    tool = FreezeCardTool()
    tool.run("primary")
    tool.run("primary")
    assert tool.is_frozen("primary")
