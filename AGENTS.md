# AGENTS.md — how to work in this repository

Rules for any AI agent (and human) contributing to AISecurity4Fintech. The goal
is a system that is simple, correct, and defensible — not clever.

## Read first

- `PRD.md` — the product source of truth (private, gitignored).
- `README.md` — what the platform is and how to run it.
- `docs/threat-model/v1.md` — the security model every change must respect.

## Non-negotiables

1. **Tests before code.** Never write production code before a failing test
   (`[red]` then `[green]`). No exceptions for features, fixes, or refactors.
2. **No secrets or real PII in the repo.** Synthetic data only. `gitleaks` runs
   in CI and fails the build on any secret.
3. **No compliance claim without a test.** If a claim cannot point to a
   `test_*`, it does not go in the docs.
4. **One story at a time.** Conventional commits; the red commit precedes the
   green commit.

## The delivery contract

- Every unit of work lands as **one pull request** that documents:
  - what changed and why
  - decisions made and their trade-offs
  - how to run and use it
  - what was deliberately left out and what comes next
- CI must be green before merge. Lint, format, type-check (`mypy --strict`),
  tests, coverage, secrets scan, dependency audit, and the API contract check
  all run on every push and PR.

## The security model

- PII is masked by `pii-proxy` before any model call. Nothing crosses the LLM
  boundary unmasked.
- Every sensitive action is recorded in the append-only `audit-log`.
- Identity is RS256-signed, scoped JWTs from `auth-service`; verifiers reject
  `HS256`/`none` (algorithm confusion).

## Decisions

Surface only the genuinely technical forks, with options + trade-offs + one
recommendation. Low-stakes decisions are made and reported, not asked. Record
non-trivial decisions in `docs/adr/`.

## Environment

- Python 3.12, managed with `uv` (see `CONTRIBUTING.md` for exact commands).
- Workspace members live in `services/`, `apps/`, and `packages/`.
