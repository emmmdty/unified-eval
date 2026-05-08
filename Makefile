.PHONY: test lint format check

UV ?= uv

test:
	$(UV) run pytest

lint:
	$(UV) run ruff check .

format:
	$(UV) run ruff format .

check:
	$(UV) run ruff format --check .
	$(UV) run ruff check .
	$(UV) run pytest
