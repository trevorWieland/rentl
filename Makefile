.PHONY: help validate context translate detail-scene detail-mvp clean test lint format typecheck

# Default project path for development
PROJECT ?= examples/tiny_vn

help:
	@echo "rentl Development Makefile"
	@echo ""
	@echo "Pipeline Commands:"
	@echo "  make validate       - Validate project structure and metadata"
	@echo "  make context        - Run Context Builder pipeline (enrich metadata)"
	@echo "  make translate      - Run Translator pipeline (translate scenes)"
	@echo ""
	@echo "Development Commands:"
	@echo "  make detail-scene SCENE=<id>  - Detail a specific scene"
	@echo "  make detail-mvp     - Detail all scenes (MVP command)"
	@echo ""
	@echo "Quality Commands:"
	@echo "  make test           - Run test suite"
	@echo "  make lint           - Run linter (ruff)"
	@echo "  make format         - Format code (ruff)"
	@echo "  make typecheck      - Run type checker (ty)"
	@echo "  make check          - Run all quality checks"
	@echo ""
	@echo "Options:"
	@echo "  PROJECT=<path>      - Set project path (default: examples/tiny_vn)"
	@echo "  VERBOSE=1           - Enable verbose logging"
	@echo "  OVERWRITE=1         - Allow overwriting existing data"

# Build verbose and overwrite flags
VERBOSE_FLAG := $(if $(VERBOSE),--verbose,)
OVERWRITE_FLAG := $(if $(OVERWRITE),--overwrite,)

# Core pipeline commands
validate:
	uv run python -m rentl_cli validate --project-path $(PROJECT) $(VERBOSE_FLAG)

context:
	uv run python -m rentl_cli context --project-path $(PROJECT) $(OVERWRITE_FLAG) $(VERBOSE_FLAG)

translate:
	uv run python -m rentl_cli translate --project-path $(PROJECT) $(OVERWRITE_FLAG) $(VERBOSE_FLAG)

# Development commands
detail-scene:
	@if [ -z "$(SCENE)" ]; then \
		echo "Error: SCENE parameter required. Usage: make detail-scene SCENE=scene_c_00"; \
		exit 1; \
	fi
	uv run python -m rentl_cli detail-scene $(SCENE) --project-path $(PROJECT) $(OVERWRITE_FLAG) $(VERBOSE_FLAG)

detail-mvp:
	uv run python -m rentl_cli detail-mvp --project-path $(PROJECT) $(OVERWRITE_FLAG) $(VERBOSE_FLAG)

# Quality commands
test:
	uv run pytest

lint:
	uv run ruff check --fix

lint-check:
	uv run ruff check

format:
	uv run ruff format

format-check:
	uv run ruff format --check

type:
	uv run ty check

fix: format lint

check: format-check lint-check type test
	@echo "All checks passed!"

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned up cache directories"
