# US-A6: Prompt-injection protection + graceful agent errors

## User story

As a security engineer, I want the platform to resist prompt injection — both
from a poisoned document and from the user's message — and to fail gracefully,
so the model can never leak its instructions or act outside its bounds.

## Decisions (locked)

- Defend both vectors: direct (user message) + indirect (retrieved documents) +
  a deterministic output guardrail.
- Defense in depth: hardened prompts with delimited untrusted context, plus a
  deterministic deny-list guardrail on the output.
- Guardrail is a deterministic deny-list (patterns, system-prompt leak, canaries).
- The guardrail lives as a shared module in `py-shared`.
- On a loop / can't-complete, return an explicit refusal, never "could not
  complete".

## Acceptance criteria

```gherkin
Given a generated answer containing a jailbreak canary or system-prompt leak
When the guardrail checks it
Then it is blocked and replaced with a refusal
And the block is audited

Given a poisoned document instructing the model to reveal its prompt
When the retrieval pipeline runs
Then retrieved content is delimited as untrusted data
And the hardened prompt refuses to follow instructions inside sources

Given a model that calls the same tool twice
When the agent loop runs
Then it returns an explicit refusal (e.g. "I can only access your own account.")
```

## Out of scope

- An LLM-judge guardrail (probabilistic)
- A separate guardrail service
- Persistence
