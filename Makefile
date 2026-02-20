.PHONY: install format lint lint-check lint-fix type unit integration quality test check ci all clean

# output styling
ECHO_CHECK = @echo "  Checking... "
ECHO_PASS = echo "✅ $@ Passed"
ECHO_FAIL = echo "❌ $@ Failed"

# Helper to run command cleanly
# Usage: $(call run_clean, command, log_file)
define run_clean
	$(ECHO_CHECK)
	@if $1 > $2 2>&1; then \
		$(ECHO_PASS); \
		rm -f $2; \
	else \
		$(ECHO_FAIL); \
		cat $2; \
		rm -f $2; \
		exit 1; \
	fi
endef

# Helper to run tests cleanly and extract summary
# Usage: $(call run_test, command, log_file, label)
define run_test
	$(ECHO_CHECK)
	@if $1 > $2 2>&1; then \
		SUMMARY=$$(grep -o '[0-9]\+ passed' $2 | tail -n 1); \
		if [ -z "$$SUMMARY" ]; then SUMMARY="Passed"; fi; \
		echo "✅ $3 $$SUMMARY"; \
		rm -f $2; \
	else \
		echo "❌ $3 Failed"; \
		cat $2; \
		rm -f $2; \
		exit 1; \
	fi
endef

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	@uv sync --upgrade > /dev/null
	@echo "✅ Install Complete"

# Format code with ruff
format:
	@echo "🎨 Formatting code..."
	$(call run_clean, uv run ruff format ., .format.log)

# Check linting rule compliance (strict, no autofix)
lint-check:
	@echo "🔍 checking lints (strict)..."
	$(call run_clean, uv run ruff check ., .lint.log)

# Fix auto-fixable lint issues
lint:
	@echo "🛠️  Fixing lints..."
	$(call run_clean, uv run ruff check --fix ., .lint-fix.log)

# Type check with ty
type:
	@echo "types checking types..."
	$(call run_clean, uv run ty check, .type.log)

# Run unit tests with coverage enforcement
unit:
	@echo "🧪 Running unit tests with coverage..."
	$(call run_test, uv run pytest tests/unit -q --tb=short --timeout=1 -W error::DeprecationWarning --cov=packages --cov=services --cov-fail-under=80 --cov-precision=2, .unit.log, Unit Tests)

# Run integration tests
integration:
	@echo "🔌 Running integration tests..."
	$(call run_test, uv run pytest tests/integration -q --tb=short --timeout=5 -W error::DeprecationWarning --cov=packages/rentl-core --cov=packages/rentl-schemas --cov=packages/rentl-io --cov-fail-under=75 --cov-precision=2, .integration.log, Integration Tests)

# Run quality tests (requires RENTL_OPENROUTER_API_KEY in .env or environment)
quality:
	@echo "💎 Running quality tests..."
	$(call run_test, bash -c 'set -a && [ -f .env ] && source .env && set +a && uv run pytest tests/quality -q --tb=short --timeout=30 -W error::DeprecationWarning', .quality.log, Quality Tests)

# Run all tests with coverage
test:
	@uv run pytest --cov=packages --cov=services --cov-report=term-missing

# Quick verification gate (format, lint, type, unit) — used per-task
check:
	@echo "⚡ Running Quick Verification..."
	@$(MAKE) format --no-print-directory
	@$(MAKE) lint --no-print-directory
	@$(MAKE) type --no-print-directory
	@$(MAKE) unit --no-print-directory
	@echo "⚡ Quick Verification Passed!"

# CI verification gate (format, lint, type, unit, integration) — no quality (requires API keys)
ci:
	@echo "🤖 Starting CI Verification..."
	@$(MAKE) format --no-print-directory
	@$(MAKE) lint --no-print-directory
	@$(MAKE) type --no-print-directory
	@$(MAKE) unit --no-print-directory
	@$(MAKE) integration --no-print-directory
	@echo "🤖 CI Verification Passed!"

# Full verification gate (format, lint, type, unit, integration, quality)
all:
	@echo "🚀 Starting Full Verification..."
	@$(MAKE) format --no-print-directory
	@$(MAKE) lint --no-print-directory
	@$(MAKE) type --no-print-directory
	@$(MAKE) unit --no-print-directory
	@$(MAKE) integration --no-print-directory
	@$(MAKE) quality --no-print-directory
	@echo "🎉 All Checks Passed!"

# Clean build artifacts
clean:
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -f .*.log
