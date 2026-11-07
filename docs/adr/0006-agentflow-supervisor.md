# ADR 0006: AgentFlow supervisor — deterministic routing and scope enforcement

## Status

Accepted.

## Date

2026-11-07

## Context

AgentFlow must route a customer message to a specialized agent with bounded
authority. Two non-trivial choices shape the code: how routing decides, and how
agent authority is enforced.

## Decisions

### 1. Deterministic keyword routing (no LLM in the routing path)

The supervisor classifies a message with a keyword map into `retrieval` or
`action`. No model is called to route.

**Why:** routing is a security decision, not a language task. A deterministic
classifier has no injection surface, is fully testable, and cannot be steered by
prompt injection inside the message. The LLM enters later, inside the agent that
generates a response, behind the pii-proxy.

### 2. Scope enforcement on the caller's token (no delegated token exchange yet)

Each agent declares `required_scopes`; the supervisor rejects a dispatch with
403 if the caller's token does not carry them.

**Why:** it makes bounded authority real and testable without expanding the
auth-service. A short-lived, scope-narrowed delegated token per dispatch is the
later strengthening (US-A3/W2).

### 3. Exactly one bounded action in this iteration (freeze_card)

The action agent runs one operation, `freeze_card`, on the caller's primary
card. No multi-step tool sequences yet.

**Why:** proves the audited, scoped action loop with the smallest surface. This
is the action SCA (TOTP) will later guard.

## Alternatives rejected

- LLM classification: adds an injection surface and non-deterministic tests
  before any model call is needed.
- Delegated token exchange now: auth-service expansion before the orchestration
  loop is proven.
- Multiple tools in the action agent: more surface than A2 requires.

## Follow-up

- LLM answer generation behind the pii-proxy.
- Delegated short-lived agent tokens (least privilege per dispatch).
- SCA / TOTP for `freeze_card` and other high-value actions.
