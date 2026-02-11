# rentl

An open-source, BYOK agentic localization pipeline that makes professional-grade game translation feel as easy and fast as simple MTL.

rentl delivers a coherent, playable v1 translation in hours through a phase-based workflow (ingest → context → pretranslation → translate → QA → edit → export), targeting both fan translators seeking accessibility and professional localization teams demanding reliability and quality.

## Key Features

- **Phase-based pipeline orchestration** — Run a complete localization pipeline with deterministic completion and clear phase boundaries
- **BYOK model integration** — Configure any OpenAI-compatible endpoint (OpenRouter, OpenAI, Ollama, LM Studio) and switch models per phase
- **Context-aware translation** — Automatically associate scene, route, and line context with source text for coherent translations
- **Multi-format support** — Ingest from CSV, JSONL, or TXT formats and export localized outputs suitable for patching

## Installation

rentl requires Python 3.14+ and uses [uv](https://github.com/astral-sh/uv) for dependency management.

### Install uv

If you don't have uv installed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install rentl

Clone the repository and install dependencies:

```bash
git clone https://github.com/trevorWieland/rentl.git
cd rentl
uv sync
```

Or run directly with uvx (no installation required):

```bash
uvx --from git+https://github.com/trevorWieland/rentl.git rentl --help
```

## Quick Start

Get started with a new rentl project in four steps:

### 1. Initialize a new project

```bash
uv run rentl init
```

This interactive command will:
- Guide you through provider selection (OpenRouter, OpenAI, Local/Ollama, or custom)
- Pre-fill configuration with sensible defaults
- Generate a valid `rentl.toml` configuration file

### 2. Verify your setup

```bash
uv run rentl doctor
```

Doctor runs diagnostic checks on your configuration and environment, including:
- Configuration file validation
- API key presence (loads from `.env` files)
- Model endpoint connectivity
- Required directory structure

### 3. Run the pipeline

```bash
uv run rentl run-pipeline
```

Executes the full localization pipeline:
- Ingests source text from your configured input
- Builds context and analyzes source text
- Translates with your configured model
- Runs QA checks on the output
- Tracks progress and status throughout

### 4. Export translated files

```bash
uv run rentl export --input run-001/edited_lines.jsonl --output translations.csv --format csv
```

Exports translated lines to your specified output file in CSV, JSONL, or TXT format, ready for patching.

## Available Commands

| Command | Description |
|---------|-------------|
| `rentl init` | Initialize a new rentl project interactively |
| `rentl doctor` | Run diagnostic checks on configuration and environment |
| `rentl run-pipeline` | Run the full localization pipeline |
| `rentl run-phase` | Run a single phase (with required prerequisites) |
| `rentl export` | Export translated lines to CSV/JSONL/TXT |
| `rentl status` | Show run status and progress |
| `rentl explain` | Explain pipeline phases |
| `rentl validate-connection` | Validate connectivity for configured model endpoints |
| `rentl check-secrets` | Scan configuration files for hardcoded secrets |
| `rentl migrate` | Migrate rentl.toml config to the current schema version |
| `rentl benchmark` | Benchmark evaluation commands |
| `rentl version` | Display version information |
| `rentl help` | Display help for commands |

For detailed help on any command, run:

```bash
uv run rentl <command> --help
```

## Project Structure

```
rentl/
├── packages/          # Core packages
│   ├── rentl-core/    # Core pipeline logic
│   ├── rentl-schemas/ # Pydantic schemas
│   ├── rentl-io/      # I/O operations
│   ├── rentl-llm/     # LLM integration
│   ├── rentl-agents/  # Agent implementations
│   └── rentl-tui/     # Terminal UI
├── services/          # Service applications
│   ├── rentl-cli/     # CLI application
│   └── rentl-api/     # API service (future)
└── tests/             # Test suite
```

## Configuration

After running `rentl init`, your configuration lives in `rentl.toml`. Key settings include:

- **Model configuration** — Base URL, API key reference, and model ID per phase
- **Input/output paths** — Source data location and export directory
- **Target languages** — Which languages to translate to
- **Pipeline phases** — Which phases to run and in what order

Store your API keys in `.env` or `.env.local` files in your config directory (never commit these files):

```bash
# .env
OPENROUTER_API_KEY=your_key_here
```

## Development

Run tests:

```bash
make test         # All tests with coverage
make unit         # Unit tests only
make integration  # Integration tests
make quality      # Quality tests
```

Run verification gates:

```bash
make check       # Format, lint, type, unit tests
make all         # Full gate (format, lint, type, unit, integration, quality)
```

Format code:

```bash
make format
```

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

## Contributing

This project is in active development. Contributions, issues, and feature requests are welcome.

## Links

- **Repository:** https://github.com/trevorWieland/rentl
- **Issues:** https://github.com/trevorWieland/rentl/issues
