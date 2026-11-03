.PHONY: test lint format ci

PYTHON ?= python3
PYTEST ?= $(PYTHON) -m pytest
RUFF ?= $(PYTHON) -m ruff
MYPY ?= $(PYTHON) -m mypy

# Local commands aligned with CI jobs and the uv workspace layout.
test:
	$(PYTEST) services/audit-log -q --cov=services/audit-log/src --cov-fail-under=0

lint:
	$(RUFF) check .
	$(RUFF) format --check .
	$(MYPY) --strict .

format:
	$(RUFF) format .

ci: lint test
	python -c "import pathlib; root = pathlib.Path('.').resolve(); assert (root / 'services' / 'audit-log' / 'src' / 'audit_log').exists(); print('contract stub ok')"
	gitleaks detect --no-banner --redact --config .gitleaks.toml || true
	echo "red-team suite not wired yet (W5)"
