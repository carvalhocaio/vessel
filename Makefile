.PHONY: help sync install hooks hooks-run test lint lint-fix format format-check typecheck audit ci check clean rename

help: ## Lists all available Makefile commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

sync: ## Installs runtime and dev dependencies using uv
	uv sync

install: sync ## Alias for sync

hooks: ## Installs the pre-commit hooks into .git/hooks
	uv run pre-commit install

hooks-run: ## Runs all pre-commit hooks against all files
	uv run pre-commit run --all-files

test: ## Runs the test suite with pytest
	uv run pytest

lint: ## Checks code with ruff
	uv run ruff check .

lint-fix: ## Automatically fixes ruff lint issues
	uv run ruff check --fix .

format: ## Formats code with ruff
	uv run ruff format .

format-check: ## Verifies formatting with ruff without modifying files
	uv run ruff format --check .

typecheck: ## Runs static type checking with pyright
	uv run pyright

audit: ## Audits dependencies for known security vulnerabilities
	uv run pip-audit

ci: lint format-check typecheck audit test ## Runs full verification pipeline locally

check: ci ## Alias for ci

clean: ## Cleans build artifacts and caches
	rm -rf .ruff_cache .pytest_cache dist build *.egg-info .coverage htmlcov
	find . -type d -name '__pycache__' -not -path './.venv*' -exec rm -rf {} +

rename: ## Renames the project package: make rename NAME=my_new_project
	@if [ -z "$(NAME)" ]; then \
		echo "Error: NAME is required. Example: make rename NAME=my-project"; \
		exit 1; \
	fi
	uv run python scripts/rename.py "$(NAME)"
