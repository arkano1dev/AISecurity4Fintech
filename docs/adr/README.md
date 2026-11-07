# Architecture Decision Records

This directory tracks the key trade-offs of the platform.

## Index

- [ADR 0001](0001-monorepo-and-uv.md): monorepo structure and uv workspace decision
- [ADR 0002](0002-audit-log-hash-chain.md): SHA-256 hash chain with DB-layer immutability
- [ADR 0003](0003-jwt-rs256-jwks.md): RS256 JWTs with a JWKS endpoint
- [ADR 0004](0004-agentflow-uses-cached-jwks.md): AgentFlow verifies tokens with a cached JWKS
- [ADR 0005](0005-vaultrag-rag-design.md): VaultRAG retrieval design (in-memory cosine scan, HTTP trust boundaries)
- [ADR 0006](0006-agentflow-supervisor.md): AgentFlow supervisor (deterministic routing, scope enforcement)
- [ADR 0007](0007-agentflow-vaultrag-integration.md): AgentFlow delegates retrieval to VaultRAG (token forwarding, VaultRAG auth, defense in depth)
- [ADR 0008](0008-llm-driven-agent.md): LLM-driven agent loop with bounded tools (JSON allowlist, multi-step, keyword fallback)
