from __future__ import annotations

import pytest
from agentflow.llm import LlmError, _parse


def test_parse_valid_tool_call() -> None:
    decision = _parse('{"action": "tool_call", "tool": "freeze_card"}')
    assert decision.action == "tool_call"
    assert decision.tool == "freeze_card"


def test_parse_valid_final() -> None:
    decision = _parse('{"action": "final", "answer": "Your card is frozen."}')
    assert decision.action == "final"
    assert decision.answer == "Your card is frozen."


def test_parse_strips_markdown_fence() -> None:
    decision = _parse('```json\n{"action": "final", "answer": "hi"}\n```')
    assert decision.action == "final"
    assert decision.answer == "hi"


def test_parse_rejects_unknown_tool() -> None:
    with pytest.raises(LlmError):
        _parse('{"action": "tool_call", "tool": "transfer_money"}')


def test_parse_rejects_unknown_action() -> None:
    with pytest.raises(LlmError):
        _parse('{"action": "do_stuff"}')


def test_parse_rejects_malformed() -> None:
    with pytest.raises(LlmError):
        _parse("not json at all")
