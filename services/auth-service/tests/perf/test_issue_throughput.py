from __future__ import annotations

from time import perf_counter

from auth.jwt import issue_token


def test_issue_1000_tokens_in_under_two_seconds() -> None:
    started = perf_counter()
    for _ in range(1000):
        issue_token({"username": "alice"}, ["agentflow"], ["chat:send"])
    assert perf_counter() - started < 2.0