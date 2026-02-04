# Tech Stack

## Language & Runtime

- **Python 3.14** - Core language baseline
- **uv** - Dependency and project management (package manager, lockfiles, virtual environments)

## Frontend

### CLI Surface (Primary)
- **Typer** - Type-hinted CLI framework for command definitions and argument parsing
- **Rich** - Terminal output formatting (progress bars, tables, syntax highlighting)

### TUI Surface (v0.1 minimal, v0.4 complete)
- **Textual** - Modern TUI framework for terminal-based user interface
- **Textual CSS** - Styling and theming for TUI screens
- **Note:** v0.1 includes minimal read-only status viewer; v0.4 expands to complete interactive TUI

### GUI Surface (Future - v1.0+)
- **TBD** - Web or desktop GUI (decision deferred until post-MVP)

## Backend & AI Integration

### Agent Orchestration
- **PydanticAI** - Agent framework for structured, type-safe agent workflows and tool composition

### Model Integration
- **Open Responses specification** - Multi-provider LLM API specification for interoperability across model providers
  - Enables support for OpenAI, OpenRouter, Hugging Face, LM Studio, Ollama, vLLM, and more
  - Single schema maps cleanly to many providers with minimal translation work
- **OpenAI Python SDK (v2.11.0)** - Primary client implementation for OpenAI-compatible endpoints
- **BYOK (Bring Your Own Key)** - Users configure custom base URL and API key for any OpenAI-compatible endpoint
- **Pydantic** - Schema validation and type safety for all AI inputs/outputs

## Database & Storage

### Run Metadata & State
- **SQLite** - Primary database for run metadata, state indexing, and fast querying
- **JSONL** - Immutable artifact storage for per-phase logs and pipeline outputs (auditable, human-readable)

### Vector Storage
- **Chroma** - Vector database for context and translation memory (v0.1 default)
- **Pluggable interface** - Extensible vector store protocol to support alternative backends (PostgreSQL/pgvector, Pinecone, etc.)
- **Note:** Future Docker Compose support will enable hosted vector DB alternatives for collaborative/production deployments

### Configuration
- **TOML** - Configuration format for project settings, pipeline phases, and agent configurations
- **Schema versioning** - Explicit version numbers with migration paths for config schema evolution

## File Formats & Data Exchange

### Input/Output Formats
- **CSV** - Tabular data import/export
- **JSONL** - Line-delimited JSON for logs and artifacts
- **TXT** - Plain text import/export

### Logging & Events
- **JSONL logs** - Structured log lines with timestamps, event types, and metadata
- **Event schema** - Standardized event format (timestamp, level, event, run_id, phase, message, data)
- **JSON output** - CLI default output format with envelope: `{data, error, meta}`

## Testing & Quality

### Testing Framework
- **pytest** - Test framework with fixtures and parametrization
- **pytest-coverage** - Code coverage measurement

### Test Tiers
- **Unit tests** - <250ms per test, mocks only, no external services
- **Integration tests** - <5s per test, minimal mocks, real services (excluding LLMs), BDD format
- **Quality tests** - Integration-like, no mocks, real LLMs, assert quality benchmarks

### Code Quality
- **ruff** - Linter and formatter (Python-first, fast, extensible)
- **ty** - Type checking (complements pyright/mypy)

## Development Tooling

### Build & Packaging
- **uv build** - Build system for creating distribution artifacts
- **pyproject.toml** - Package configuration and metadata
- **uv.lock** - Locked dependency versions for reproducibility

### CI/CD
- **GitHub Actions** - Continuous integration and deployment
- **Matrix testing** - Cross-platform (Linux/macOS/Windows) and Python version support (3.12-3.14)

### Code Organization
- **Multi-package monorepo** - Flat package layout with clear separation of concerns
  - `rentl-core` - Core pipeline logic, adapters, schemas
  - `rentl-cli` - CLI commands and output formatting
  - `rentl-tui` - Textual UI screens and state management
  - `rentl-api` - Future API surface (placeholder for v1.0+)

## Distribution

### Primary Distribution
- **Copier template** - First-party template repo for git-native collaboration and consistent project structure
- **uv tool** - Installation method for template-based projects
- **uvx package** - Direct package execution without installation

### Secondary Distribution
- **PyPI** - Standard Python package index (planned for v1.0+)

## Infrastructure & Deployment

### Local Development
- **Local execution** - All components run locally on user machine
- **Environment variables** - API keys and secrets stored via env vars only (never logged)

### Future Production Support
- **Docker Compose** - Infrastructure-as-code for collaborative/production deployments (post-v1.0)
  - Containerized services for PostgreSQL, hosted vector DB, and other hosted alternatives
  - Easily configurable docker images for production scaling
  - Enables team collaboration with shared infrastructure

## Security & Privacy

### API Key Management
- **Environment variables only** - API keys stored in `OPENAI_API_KEY` and similar env vars
- **No key logging** - API keys never logged, exposed in outputs, or persisted in artifacts
- **Redaction policy** - Keys and tokens redacted from logs and reports

### Network Policy
- **Configured endpoints only** - Network access restricted to user-provided model endpoints
- **No telemetry** - No telemetry or data collection by default

## Performance & Scalability

### Concurrency
- **Configurable max concurrency** - User-controlled parallelism limits for API calls
- **Exponential backoff** - Automatic retry with backoff on 429 and 5xx errors
- **Rate limiting** - Respects provider rate limits via backoff strategies

### Caching
- **Opt-in disk cache** - Cache keyed by model + prompt + schema (user-enabled)
- **TTL and size cap** - Time-to-live and LRU eviction for cache management
- **Cache invalidation** - Explicit cache invalidation via versioned schemas

## Cross-Platform Support

- **Linux** - Primary development platform
- **macOS** - Supported platform
- **Windows** - Supported platform (tested in CI matrix)

## Version Management

- **Semantic versioning** - Follows semver for all releases (MAJOR.MINOR.PATCH)
- **Deprecation policy** - Breaking changes announced 1 minor version in advance (e.g., deprecated in 1.3.0 for removal in 2.0)
- **Schema migrations** - Explicit migration scripts when schemas change between versions

## Future Considerations (Out of Scope for v1.0)

- Web API framework (FastAPI planned for `rentl-api`)
- Additional vector store backends (beyond Chroma)
- Hosted service layer with team collaboration
- Enterprise authentication (SSO, OAuth)
- Advanced observability (APM, distributed tracing)
- Cloud provider integrations (AWS, GCP, Azure)
