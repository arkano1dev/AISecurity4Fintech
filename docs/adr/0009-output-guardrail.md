# ADR 0009: Deterministic output guardrail + delimited untrusted context

## Status

Accepted.

## Date

2026-11-07

## Context

The model is the weakest link. A poisoned document (indirect injection) or a
jailbreak prompt (direct injection) can make it reveal its system prompt or act
outside its bounds. A prompt-only defense cannot be verified.

## Decisions

### 1. Deterministic deny-list guardrail (shared module)

`shared.guardrail.check_output` scans generated text against a deny-list of
system-prompt leaks, jailbreak canaries, and instruction-following signals.
Blocked output is replaced with a refusal and audited. It is deterministic, so it
is fully testable.

### 2. Delimited untrusted context + hardened prompts

Retrieved sources and tool results are wrapped in `<source>` delimiters, and the
system prompt declares them untrusted data — never instructions to follow.

### 3. Guardrail applied at both generation points

VaultRAG's answer and AgentFlow's final answer both pass through the guardrail.

### 4. Explicit refusal on repeated tool calls

The agent refuses a repeated tool call instead of looping to the step cap, with
a per-tool refusal ("I can only access your own account." for balance).

## Security properties (each proven by a test)

- A generated answer containing a canary or leak is blocked and audited.
- The guardrail is deterministic and independent of model behavior.
- A scripted model that would comply with an injection is still blocked by the
  system layer.

## Alternatives rejected

- LLM-judge guardrail: probabilistic, costs a second model call, not testable.
- Prompt-only defense: not verifiable.
- Separate guardrail service: stateless and fast; an in-process module is simpler.

## Follow-up

- Red-team tests against the real model (best-effort, non-deterministic).
- A deny-list curated from real attack patterns.
