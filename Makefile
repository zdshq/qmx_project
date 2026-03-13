PYTHON ?= python

.PHONY: install install-dev init-db run run-once report doctor test lint format check clean

install:
	$(PYTHON) -m pip install -e .

install-dev:
	$(PYTHON) -m pip install -r requirements-dev.txt

init-db:
	PYTHONPATH=src $(PYTHON) -m study_agent.main init-db

run:
	PYTHONPATH=src $(PYTHON) -m study_agent.main run

run-once:
	PYTHONPATH=src $(PYTHON) -m study_agent.main run-once

report:
	PYTHONPATH=src $(PYTHON) -m study_agent.main report

doctor:
	PYTHONPATH=src $(PYTHON) -m study_agent.main doctor

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check src tests

format:
	$(PYTHON) -m ruff format src tests

check: lint test

clean:
	rm -rf .pytest_cache .ruff_cache build dist htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
