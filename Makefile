.PHONY: help install install-dev lint format typecheck test test-cov clean run-panel docs

PYTHON ?= python3.12
UV ?= uv

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install runtime dependencies with uv
	$(UV) sync

install-dev: ## Install with development dependencies and pre-commit hooks
	$(UV) sync --all-extras
	$(UV) run pre-commit install

lint: ## Run ruff linter
	$(UV) run ruff check src tests scripts

format: ## Auto-format code with ruff
	$(UV) run ruff format src tests scripts
	$(UV) run ruff check --fix src tests scripts

typecheck: ## Run mypy static type checker
	$(UV) run mypy

test: ## Run pytest test suite
	$(UV) run pytest

test-cov: ## Run tests with coverage report
	$(UV) run pytest --cov=oaa_observatory --cov-report=term-missing

clean: ## Remove build artifacts and caches
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	rm -rf dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

run-panel: ## Build firm-year panel from configured feature tables
	$(UV) run oaa panel build --config configs/pipeline/panel_builder.toml

docs: ## Print documentation index
	@echo "Documentation:"
	@echo "  README.md"
	@echo "  docs/architecture.md"
	@echo "  docs/data_pipeline.md"
	@echo "  docs/entity_resolution.md"
	@echo "  docs/contributing.md"
