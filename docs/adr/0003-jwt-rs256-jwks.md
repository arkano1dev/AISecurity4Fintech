# ADR 0003: Use RS256 JWTs with a JWKS endpoint

## Status

Accepted.

## Context

The platform needs a shared identity primitive for service-to-service and app-to-service authorization. The main requirement is that verifiers can trust identity claims without sharing the signing key.

## Decision

We use RS256-signed JWTs issued by the shared auth service, with a JWKS endpoint exposing the active public key. Tokens are short-lived and include `iss`, `aud`, `exp`, and `jti` claims. The issuer rotates keys by updating the JWK set while retaining the old key during a short grace period.

## Why not HS256

HS256 requires every verifier to hold the same symmetric secret. In a platform with many verifiers, that creates a broad blast radius where a compromised downstream service can become a signing authority. RS256 keeps the private key in the issuer and distributes only public keys.

## Why not opaque tokens

Opaque tokens do not carry the claims needed to enforce tool- and route-level authorization. This platform needs scoped JWTs to pass identity and permission assertions across boundaries without needing a central database lookup on every request.

## Trade-offs

- Benefits: strong issuer separation, less key-sharing risk, centralized rotation, auditable token semantics.
- Costs: the verifier needs a JWKS cache and a bounded staleness window; a cached key can lag behind rotation by a few minutes.
- Mitigation: use a short cache TTL and document rotation as a platform operational procedure.

## Consequences

- Token verification is local and fast.
- Key rotation is manageable through `kid` headers and a JWKS set.
- The auth service is the root of trust for identity assertions in the platform.
