# US-A1: Authenticated customer session with scoped JWT

## User story

As a customer, I want to log in and receive a scoped session token, so that I can chat with support agents without re-authenticating and without ever exposing my password to an agent.

## Depends on

- AUTH-1 (done): shared RS256 JWT issuer with JWKS and scope enforcement

## API contract

### POST /chat/session

Request:

```json
{ "username": "alice", "password": "correct-horse" }
```

Response:

```json
{
  "access_token": "<jwt>",
  "expires_in": 900,
  "token_type": "Bearer"
}
```

### GET /chat/whoami

Requires a valid bearer token. Response:

```json
{
  "sub": "alice",
  "scopes": ["chat:send", "account:read"]
}
```

### GET /chat/account

Requires `account:read` scope.

## Security notes

- Customer credentials are exchanged only with the auth-service.
- AgentFlow verifies tokens locally against cached JWKS and does not trust self-signed tokens.
- Tokens are short-lived and audience-bound to the `agentflow` service.

## Out of scope

- SCA enforcement (US-A3)
- refresh tokens
- MFA
- rate limiting on login
