#!/usr/bin/env bash
# CI publish script for rentl packages
# Builds and publishes all packages to PyPI in dependency order

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default to dry run for safety
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      echo "Usage: $0 [--dry-run]"
      exit 1
      ;;
  esac
done

# Helper functions
log_info() {
  echo -e "${GREEN}▶${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
  echo -e "${RED}✗${NC} $1"
}

# Verify we're in the workspace root
if [[ ! -f "pyproject.toml" ]] || [[ ! -d "packages" ]]; then
  log_error "Must be run from workspace root"
  exit 1
fi

# Clean dist directory
log_info "Cleaning dist/ directory..."
rm -rf dist/
mkdir -p dist/

# Package list in dependency order
declare -a PACKAGES=(
  "rentl-schemas"
  "rentl-core"
  "rentl-llm"
  "rentl-io"
  "rentl-agents"
  "rentl"
)

# Build all packages
log_info "Building all packages..."
for pkg in "${PACKAGES[@]}"; do
  log_info "Building $pkg..."
  if ! uv build --package "$pkg" --no-sources; then
    log_error "Failed to build $pkg"
    exit 1
  fi
done

log_info "All packages built successfully"

# Verify all packages were built
log_info "Verifying build artifacts..."
for pkg in "${PACKAGES[@]}"; do
  # Convert package name to wheel pattern (rentl-core -> rentl_core)
  wheel_name="${pkg//-/_}"
  if ! ls dist/"${wheel_name}"-*.whl &>/dev/null; then
    log_error "Missing wheel for $pkg"
    exit 1
  fi
  # sdist files also use underscores
  if ! ls dist/"${wheel_name}"-*.tar.gz &>/dev/null; then
    log_error "Missing sdist for $pkg"
    exit 1
  fi
done

log_info "All build artifacts present"

# Publish packages
if [[ "$DRY_RUN" == "true" ]]; then
  log_warn "Running in DRY RUN mode - no packages will be published"

  for pkg in "${PACKAGES[@]}"; do
    log_info "Would publish $pkg..."
    wheel_name="${pkg//-/_}"
    wheel_file=$(ls dist/"${wheel_name}"-*.whl | head -1)
    sdist_file=$(ls dist/"${wheel_name}"-*.tar.gz | head -1)

    # Source .env to load PYPI_TOKEN
    source .env
    if ! UV_PUBLISH_TOKEN="${PYPI_TOKEN}" uv publish --dry-run "$wheel_file" "$sdist_file"; then
      log_error "Dry run failed for $pkg"
      exit 1
    fi
  done

  log_info "Dry run completed successfully"
else
  log_info "Publishing packages to PyPI..."

  # Verify PYPI_TOKEN is available
  if [[ -f .env ]]; then
    source .env
  fi

  if [[ -z "${PYPI_TOKEN:-}" ]]; then
    log_error "PYPI_TOKEN not set. Please set it in .env or environment"
    exit 1
  fi

  for pkg in "${PACKAGES[@]}"; do
    log_info "Publishing $pkg..."
    wheel_name="${pkg//-/_}"
    wheel_file=$(ls dist/"${wheel_name}"-*.whl | head -1)
    sdist_file=$(ls dist/"${wheel_name}"-*.tar.gz | head -1)

    if ! UV_PUBLISH_TOKEN="${PYPI_TOKEN}" uv publish "$wheel_file" "$sdist_file"; then
      log_error "Failed to publish $pkg"
      exit 1
    fi

    # Verify package is available on PyPI
    pkg_name="${pkg}"
    log_info "Verifying $pkg_name on PyPI..."
    sleep 2  # Give PyPI time to index

    if ! curl -s -f "https://pypi.org/pypi/${pkg_name}/json" >/dev/null; then
      log_warn "$pkg_name not yet visible on PyPI (this may be normal for new packages)"
    else
      log_info "$pkg_name verified on PyPI"
    fi
  done

  log_info "All packages published successfully"
fi

# Summary
echo ""
log_info "Publish script completed"
if [[ "$DRY_RUN" == "true" ]]; then
  log_warn "DRY RUN mode - no packages were actually published"
  log_info "To publish for real, run: $0"
else
  log_info "All 6 packages published to PyPI in dependency order"
fi
