.PHONY: install test triage baseline lint

install:
	python3 -m venv .venv
	.venv/bin/python -m pip install -U pip
	.venv/bin/python -m pip install -e ".[dev]"

test:
	.venv/bin/python -m pytest --cov=misra_triage --cov-report=term-missing

baseline:
	.venv/bin/misra-triage update-baseline --config config/default.yaml --report-dir samples/

triage:
	.venv/bin/misra-triage triage --config config/default.yaml --report-dir samples/

lint:
	.venv/bin/ruff check src tests
