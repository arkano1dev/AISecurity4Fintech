.PHONY: test lint format contract ci up down demo demo-vaultrag demo-agentflow

# Local commands aligned with the CI jobs (.github/workflows/ci.yml).
# Dependencies are installed with uv — see CONTRIBUTING.md.

test:
	uv run pytest -q --cov=services --cov=apps --cov=packages --cov-fail-under=80

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy --strict .

format:
	uv run ruff format .

contract:
	uv run python scripts/check_contract.py

ci: test lint contract

up:
	docker compose -f infra/docker-compose/docker-compose.dev.yml up -d

down:
	docker compose -f infra/docker-compose/docker-compose.dev.yml down

demo:
	uv run python scripts/demo_vaultrag.py
	uv run python scripts/demo_agentflow.py

demo-vaultrag:
	uv run python scripts/demo_vaultrag.py

demo-agentflow:
	uv run python scripts/demo_agentflow.py
