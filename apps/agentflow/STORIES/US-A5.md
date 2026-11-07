# US-A5: LLM-driven agent with bounded tools (multi-step)

## User story

As a support agent, I want the platform to reason over the customer's message
with the model, choose a tool from a fixed allowlist, and execute it — so the
assistant is genuinely AI-driven while every model choice is bounded, masked,
and audited.

## Decisions (locked)

- Full dispatch: one LLM call returns intent + tool (supervisor and action agent
  both LLM-driven).
- JSON mode + Pydantic validation against an allowlist schema.
- On LLM failure/malformed output: fall back to the deterministic keyword
  classifier (graceful).
- Multi-step loop: the LLM sees the tool result and can re-reason.
- Tool selection only: tool arguments are bound to the JWT `sub`, never the
  model's output.

## Tools (the allowlist)

| Tool | Scope | Behavior |
| --- | --- | --- |
| `retrieve` | `agent:retrieve` | delegate to VaultRAG (cited answer) |
| `freeze_card` | `agent:action` | sub-keyed |
| `check_balance` | `agent:action` | sub-keyed |

## Acceptance criteria

```gherkin
Given a customer message
When the agent runs
Then the message is masked before the model sees it
And the model returns a structured decision (tool_call or final)
And the decision is validated against the tool allowlist
And a tool call executes sub-keyed, scope-checked, and audited
And the loop continues until a final answer (max 3 steps)
And a token without the tool's scope is rejected with 403
And an LLM failure at the first step falls back to the keyword classifier
```

## Out of scope

- Output guardrails / prompt-injection defenses
- Persistence (Postgres)
- SCA / TOTP
