# AUTH-1: RS256 JWT issuer with JWKS and scope enforcement

## User story

As any service in the platform, I want to issue and verify short-lived, scoped, RS256-signed JWTs, so that callers can trust identity claims without sharing private keys.

## Why shared

Both VaultRAG and AgentFlow need a common, verifiable identity layer. The auth service acts as the issuer for platform-scoped user tokens, while dependent services verify them locally against a JWKS cache.

## API contract

### POST /auth/token

Request:

```json
{ "username": "alice", "password": "correct-horse" }
```

Response:

```json
{
  "access_token": "<jwt>",
  "token_type": "Bearer",
  "expires_in": 900,
  "scope": "chat:send account:read"
}
```

### GET /auth/.well-known/jwks.json

Response:

```json
{ "keys": [ { "kty": "RSA", "alg": "RS256", "use": "sig", "kid": "active", "n": "...", "e": "AQAB" } ] }
```

### POST /auth/verify

Request:

```json
{ "token": "<jwt>" }
```

Success response:

```json
{
  "valid": true,
  "sub": "alice",
  "tenant": null,
  "scopes": ["chat:send", "account:read"],
  "exp": 173...
}
```

Failure response:

```json
{ "valid": false, "reason": "token_expired" }
```

## Notes

- Synthetic users are defined in config/users.yaml for the story.
- Password hashing and refresh tokens are explicitly out of scope.
- `iss`, `aud`, `exp`, and `jti` are required claims.
- The library uses an RSA 2048 key pair generated on first startup and stored under `.keys/`.
