.PHONY: lint typecheck security complexity test test-unit test-e2e coverage quality precommit setup

SRC := domain adapters application infrastructure
UV  := uv run --frozen

setup:
	uv sync --group dev
	git config core.hooksPath .githooks

lint:
	$(UV) ruff check .

typecheck:
	$(UV) mypy .

security:
	$(UV) bandit -r $(SRC) -ll

complexity:
	@output=$$($(UV) radon cc $(SRC) --min C -s); \
	if [ -n "$$output" ]; then echo "$$output"; exit 1; fi

test:
	$(UV) pytest -v

test-unit:
	$(UV) pytest -v -m "not e2e"

test-e2e:
	$(UV) pytest -v -m "e2e"

coverage:
	$(UV) pytest --cov --cov-report=term-missing --cov-report=html

quality: lint security complexity coverage
	@echo "--- typecheck (info only) ---"
	-$(UV) mypy .

precommit: lint typecheck security

