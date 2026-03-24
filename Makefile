.PHONY: lint typecheck security complexity test test-unit test-e2e coverage quality precommit setup

SRC := domain adapters application infrastructure
UV  := uv run --frozen

setup:
	git config core.hooksPath .githooks

lint:
	$(UV) ruff check $(SRC)

typecheck:
	$(UV) mypy .

security:
	$(UV) bandit -r $(SRC) -ll

complexity:
	@output=$$($(UV) radon cc . --min C -s); \
	if [ -n "$$output" ]; then echo "$$output"; exit 1; fi

test:
	$(UV) pytest -v

test-unit:
	$(UV) pytest -v -m "not e2e"

test-e2e:
	$(UV) pytest -v -m "e2e"

coverage:
	$(UV) pytest \
		--cov=domain --cov=adapters --cov=application --cov=infrastructure \
		--cov-report=term-missing --cov-report=html --cov-branch \
		--cov-fail-under=80

quality: lint security complexity typecheck coverage

precommit: lint typecheck security

