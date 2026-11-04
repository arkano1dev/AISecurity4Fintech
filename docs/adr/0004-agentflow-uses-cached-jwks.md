# ADR 0004: AgentFlow verifies tokens with a cached JWKS

- Status: Accepted
- Date: 2026-11-04

## Decision

AgentFlow verifies JWTs locally using a cached JWKS obtained from the auth-service instead of calling `/auth/verify` on every request.

## Context

The platform uses a shared JWT issuer with RS256 keys and a JWKS endpoint. AgentFlow is a customer-facing orchestration service that must validate many requests per second while keeping the trust boundary with the auth-service intact.

A per-request verification call adds latency, couples verifier health to auth-service health, and creates a needless bottleneck at the trust boundary. The shared auth-service can still remain the issuer of record even as each verifier caches the public key set for a bounded period.

## Rationale

The design balances reliability and latency:

- local verification keeps the hot path fast and removes a synchronous dependency on the issuer for every request
- JWKS caching reduces load on the auth-service and makes the verifier resilient to short issuer outages
- a TTL of 5 minutes gives a bounded staleness window that is acceptable for a platform that is not yet supporting full immediate revocation semantics

This is intentionally a trade-off, not a replacement for proper revocation. The risk is that a newly rotated key is not visible immediately to every verifier; the mitigation is a short TTL, key rotation with overlapping `kid` values, and a future revocation capability in W7.

## Consequences

### Positive

- lower latency for request validation
- auth-service remains a trust anchor without becoming a per-request SPOF
- easier horizontal scaling for downstream services

### Negative

- stale cached keys can temporarily allow a token signed by a recently rotated key to be rejected until the cache refreshes
- a compromised verifier may continue trusting a stale key for up to the TTL window

## Alternatives considered

- verify via `/auth/verify` on every request: safer but slower and more coupled
- self-signed tokens in AgentFlow: rejected because it would recreate the trust problem the shared auth-service is meant to solve
- opaque session tokens: rejected because scope-bearing JWTs are required for service-to-service authorization and tool scoping

## Follow-up

- W7: add explicit key revocation, subscriber synchronization, and a hardened KMS-backed key lifecycle
- US-A3: add replay detection and SCA enforcement based on `jti` and session state
