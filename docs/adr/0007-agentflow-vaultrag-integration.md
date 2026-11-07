# ADR 0007: AgentFlow delegates retrieval to VaultRAG (auth + defense in depth)

## Status

Accepted.

## Date

2026-11-07

## Context

AgentFlow's retrieval agent must answer support questions from the actual
ingested documents, not hardcoded strings. VaultRAG already owns retrieval
(chunk → redact → embed → retrieve → generate). Two questions: how AgentFlow
reaches VaultRAG, and how the two trust each other.

## Decisions

### 1. Retrieval agent delegates to VaultRAG over HTTP

The retrieval agent is a thin client: mask the question, call VaultRAG's
`/vaultrag/query`, return the answer + citations.

**Why:** reuses the retrieval + redaction + embedding + audit already proven in
VaultRAG; the two apps genuinely talk instead of duplicating the pipeline.

### 2. Token forwarding (the caller's own JWT)

AgentFlow forwards the customer's bearer token to VaultRAG. VaultRAG verifies it
against the shared JWKS and requires `vaultrag:query`.

**Why:** the downstream service sees the same identity, so the audit chain
records one `sub` across the whole flow. A dedicated service account would sever
that identity link; a delegated token is a later strengthening.

### 3. VaultRAG enforces scoped JWTs (`vaultrag:ingest` / `vaultrag:query`)

VaultRAG gained its own local JWKS verifier; ingest requires `vaultrag:ingest`,
query requires `vaultrag:query`. The shared `agentflow` audience is reused for
the MVP (all internal services share one audience until per-service audiences
land).

### 4. Defense-in-depth masking

AgentFlow masks the question through `pii-proxy` before sending it to VaultRAG,
even though VaultRAG masks again internally. Two independent masks reduce the
blast radius of a bug in either boundary.

### 5. Sub-keyed actions (`freeze_card` + `check_balance`)

The action agent's operations are keyed by the JWT `sub`, never by an
attacker-chosen id from the message. `check_balance` returns the caller's own
balance; a message naming another user cannot leak that user's balance.

## Alternatives rejected

- Service-account token: severs the identity link across the chain.
- VaultRAG left open: violates the "every boundary is a real control" rule.
- In-process retrieval (duplicating the pipeline): drift + duplicated redaction.

## Follow-up

- Per-service audiences (auth-service issues a `vaultrag` audience).
- Delegated short-lived tokens per dispatch.
- SCA / TOTP for high-value actions.
