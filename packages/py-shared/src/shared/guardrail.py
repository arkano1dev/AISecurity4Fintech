from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailVerdict:
    """The result of checking generated text against the deny-list."""

    blocked: bool
    reason: str | None = None


# A deterministic deny-list. Any output containing one of these is blocked.
DENY_PATTERNS: tuple[str, ...] = (
    # system-prompt leakage
    "you are a customer support agent",
    "you are a compliance analyst",
    # jailbreak canaries
    "i have been pwned",
    "dan mode",
    "developer mode",
    "jailbreak",
    # instruction-following signals
    "reveal your system prompt",
    "ignore previous instructions",
    "ignore all previous instructions",
)

REFUSAL = "I can't answer that request."


def check_output(text: str) -> GuardrailVerdict:
    """Return a verdict for generated text.

    The check is deterministic: it lowercases the text and scans the deny-list.
    """
    lowered = text.lower()
    for pattern in DENY_PATTERNS:
        if pattern in lowered:
            return GuardrailVerdict(blocked=True, reason=pattern)
    return GuardrailVerdict(blocked=False)
