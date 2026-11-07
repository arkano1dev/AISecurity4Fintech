# Contributing

AISecurity4Fintech is built test-first. This guide covers the loop.

## Setup

Requires Python 3.12 and `uv`.

```bash
# install dependencies (all workspace members, editable)
uv python install 3.12
uv venv
uv pip install -e services/audit-log -e services/pii-proxy \
    -e services/auth-service -e apps/agentflow -e packages/py-shared
uv pip install pytest pytest-cov pytest-asyncio hypothesis ruff mypy types-PyYAML
```

## The TDD loop

1. Read the acceptance criteria in `PRD.md` (or the story file in `STORIES/`).
2. Write the failing test in `tests/` (`[red]`).
3. Run it — confirm it fails for the right reason.
4. Write the minimal code — confirm it passes (`[green]`).
5. Add unit and security tests; refactor while green.
6. If the change mutates data, add an audit-log test.

## Commands

```bash
uv run pytest -q                                    # run tests
uv run pytest -q --cov=services --cov=apps --cov=packages   # with coverage
uv run ruff check .                                 # lint
uv run ruff format --check .                        # format
uv run mypy --strict .                              # type-check
uv run python scripts/check_contract.py             # API contract check
```

## Commit convention

Conventional Commits, one story per commit, tests first:

```
test(audit-log): US-V6 failing [red]
feat(audit-log): US-V6 append-only hash chain [green]
```

## Pull requests

One PR per unit of work. The PR body must answer:

- **What** changed and **why**
- **Decisions** made and their trade-offs
- **How to run and use it**
- **What is next** (including what was deliberately left out)

CI must be green. A reviewer (or the author, re-reading) approves before merge.
