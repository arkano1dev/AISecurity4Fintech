# ADR 0008: LLM-driven agent loop with bounded tools

## Status

Accepted.

## Date

2026-11-07

## Context

AgentFlow's supervisor was a deterministic keyword classifier and the action
agent a lookup table; only the retrieval path (via VaultRAG) used the model. To
make AgentFlow a genuine multi-agent AI, the model must drive dispatch while
staying bounded.

## Decisions

### 1. One model is the brain (full dispatch)

A single LLM call returns a structured decision (`tool_call` or `final`),
replacing the keyword classifier and the action agent's keyword matching.

### 2. JSON mode + Pydantic allowlist validation

The model returns JSON, validated against an `AgentDecision` schema whose
`tool` field is a `Literal` allowlist (`retrieve` / `freeze_card` /
`check_balance`). Anything outside the allowlist is rejected as `LlmError`.

### 3. Deterministic keyword fallback

If the model is unavailable or its output is malformed at the first step, the
existing keyword classifier takes over. The system degrades gracefully instead
of failing.

### 4. Multi-step loop

The model sees each tool result and can re-reason, up to a hard cap (3 steps),
which prevents runaway loops.

### 5. Tool selection only — args bound to identity

The model selects the tool, never its arguments. Every tool is keyed by the JWT
`sub`, so the model cannot inject a target account or bypass isolation.

## Security properties (each proven by a test)

- The model never sees raw PII (the message is masked before the call).
- The model's output is validated against a fixed allowlist.
- Tool arguments come from the authenticated identity, never the model.
- Every LLM decision and tool call is audited.
- Scope is re-checked at tool execution.

## Alternatives rejected

- Function-calling (`tools` param): depends on model support; JSON + Pydantic is
  simpler and fully testable.
- No fallback: a model outage would take the whole support path down.
- Model-supplied arguments: violates bounded authority.

## Follow-up

- Output guardrails / prompt-injection defenses.
- SCA / TOTP for high-value actions.
