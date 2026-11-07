# US-A2: Supervisor routing with bounded, audited agents

## User story

As a support agent, I want the platform to route a customer's request to the
right specialized agent, each with bounded authority, so that no single agent
does everything and every dispatch and action is recorded.

## Depends on

- US-A1 (done): authenticated session with a scoped JWT
- US-V6 (done): append-only audit log
- V1/V2 (done): VaultRAG proves the HTTP-boundary pattern

## Acceptance criteria

### A1 — Supervisor routing

```gherkin
Given a customer message
When the supervisor processes it
Then it classifies the intent and dispatches to the correct agent
And the dispatch is recorded in the audit log
And a token without the agent's required scope is rejected with 403
```

### A2 — One scoped, audited action

```gherkin
Given a request to freeze a card
When the action agent runs
Then exactly one bounded action (freeze_card) executes
And the action is recorded in the audit log
And a token without agent:action scope is rejected with 403
```

## API contract

- `POST /chat/send` — body `{message}` → `{sub, scopes, intent, agent, result, status}`

## Scopes

- `chat:send` — entry to the endpoint (existing)
- `agent:retrieve` — required by the retrieval agent
- `agent:action` — required by the action agent

## Out of scope

- LLM in AgentFlow (no model call yet)
- pii-proxy integration (no model, so nothing to mask yet)
- SCA / TOTP for high-value actions (US-A3)
- Delegated short-lived agent tokens (a later story)
