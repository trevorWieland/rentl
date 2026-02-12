# rentl

An open-source, BYOK agentic localization pipeline that makes professional-grade game translation feel as easy and fast as simple MTL.

rentl delivers a coherent, playable v1 translation in hours through a phase-based workflow (ingest → context → pretranslation → translate → QA → edit → export), targeting both fan translators seeking accessibility and professional localization teams demanding reliability and quality.

## Key Features

- **Phase-based pipeline orchestration** — Run a complete localization pipeline with deterministic completion and clear phase boundaries
- **BYOK model integration** — Configure any OpenAI-compatible endpoint (OpenRouter, OpenAI, Ollama, LM Studio) and switch models per phase
- **Context-aware translation** — Automatically associate scene, route, and line context with source text for coherent translations
- **Multi-format support** — Ingest from CSV, JSONL, or TXT formats and export localized outputs suitable for patching

## Installation

### Option 1: uvx (Recommended)

The fastest way to get started with rentl is using `uvx`, which runs the latest version without requiring installation:

```bash
uvx rentl --version
```

If you don't have `uvx` installed, install it first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Option 2: From Source

For development or to run the latest unreleased changes:

```bash
git clone https://github.com/trevorWieland/rentl.git
cd rentl
uv sync
```

rentl requires Python 3.14+ and uses [uv](https://github.com/astral-sh/uv) for dependency management.

## Quick Start

Get started with a new rentl project in four steps:

### 1. Initialize a new project

```bash
uvx rentl init
```

This interactive command will:
- Guide you through provider selection (OpenRouter, OpenAI, Local/Ollama, or custom)
- Pre-fill configuration with sensible defaults
- Generate a valid `rentl.toml` configuration file
- Create required directory structure (`input/`, `out/`, `logs/`)
- Generate a `.env` file for API key configuration

### 2. Add your API key

Edit the `.env` file in your project directory with your API key:

```bash
# For OpenRouter
OPENROUTER_API_KEY=your_key_here

# For OpenAI
OPENAI_API_KEY=your_key_here

# For local endpoints (Ollama, LM Studio)
RENTL_LOCAL_API_KEY=placeholder
```

### 3. Verify your setup

```bash
uvx rentl doctor
```

Doctor runs diagnostic checks on your configuration and environment, including:
- Configuration file validation
- API key presence (loads from `.env` files)
- Model endpoint connectivity
- Required directory structure

### 4. Run the pipeline

```bash
uvx rentl run-pipeline
```

Executes the full localization pipeline:
- Ingests source text from your configured input
- Builds context and analyzes source text
- Translates with your configured model
- Runs QA checks on the output
- Tracks progress and status throughout

Once the pipeline completes, export the translated lines to your preferred format. First, capture the pipeline output to extract the edit phase artifact:

```bash
# Get the run status with JSON output
RUN_STATUS=$(uvx rentl status --json)

# Extract the edit phase artifact path for target language (e.g., "en")
EDIT_ARTIFACT=$(echo "$RUN_STATUS" | jq -r '.data.run_state.artifacts[] | select(.phase == "edit") | .artifacts[0].path')

# Extract the edited_lines array from the EditPhaseOutput and write as JSONL
jq -c '.edited_lines[]' "$EDIT_ARTIFACT" > translated_lines.jsonl

# Export to CSV (or use --format jsonl/txt)
uvx rentl export \
  --input translated_lines.jsonl \
  --output translations.csv \
  --format csv
```

The export command supports multiple formats (csv, jsonl, txt) and writes to the specified output path.

**Note:** If you installed from source, replace `uvx rentl` with `uv run rentl` in all commands above.

## Available Commands

| Command | Description |
|---------|-------------|
| `rentl version` | Display version information. |
| `rentl help` | Display help for commands. |
| `rentl doctor` | Run diagnostic checks on rentl configuration and environment. |
| `rentl explain` | Explain pipeline phases. |
| `rentl init` | Initialize a new rentl project interactively. |
| `rentl validate-connection` | Validate connectivity for configured model endpoints. |
| `rentl export` | Export translated lines to CSV/JSONL/TXT. |
| `rentl run-pipeline` | Run the full pipeline plan. |
| `rentl run-phase` | Run a single phase (with required prerequisites). |
| `rentl status` | Show run status and progress. |
| `rentl check-secrets` | Scan configuration files for hardcoded secrets. |
| `rentl migrate` | Migrate rentl.toml config file to the current schema version. |
| `rentl benchmark` | Download and compare benchmark evaluation datasets. |

For detailed help on any command, run:

```bash
uvx rentl <command> --help
```

**Note:** If you installed from source, replace `uvx rentl` with `uv run rentl`.

## Configuration

After running `rentl init`, your configuration lives in `rentl.toml`. This file controls all aspects of your localization pipeline.

### Configuration File Structure

#### `[project]` — Project metadata and paths

```toml
[project]
schema_version = { major = 0, minor = 1, patch = 0 }
project_name = "my-translation-project"

[project.paths]
workspace_dir = "."
input_path = "input.txt"
output_dir = "out"
logs_dir = "logs"

[project.formats]
input_format = "txt"
output_format = "txt"

[project.languages]
source_language = "en"
target_languages = ["ja"]
```

- **schema_version** — Config file schema version (managed automatically by `rentl migrate`)
- **project_name** — Name for this translation project
- **paths.workspace_dir** — Root directory for all rentl operations
- **paths.input_path** — Path to your source text file
- **paths.output_dir** — Where to write pipeline outputs
- **paths.logs_dir** — Where to write log files
- **formats.input_format** — Input file format (`txt`, `csv`, or `jsonl`)
- **formats.output_format** — Export file format (`txt`, `csv`, or `jsonl`)
- **languages.source_language** — Source language code (e.g., `en`)
- **languages.target_languages** — List of target language codes (e.g., `["ja", "es"]`)

#### `[endpoint]` — Model provider configuration

```toml
[endpoint]
provider_name = "openrouter"
base_url = "https://openrouter.ai/api/v1"
api_key_env = "OPENROUTER_API_KEY"
```

- **provider_name** — Provider identifier (for display and logging)
- **base_url** — OpenAI-compatible API endpoint URL
- **api_key_env** — Name of the environment variable containing your API key

#### `[pipeline]` — Pipeline model and phase configuration

```toml
[pipeline.default_model]
model_id = "anthropic/claude-3.5-sonnet"

[[pipeline.phases]]
phase = "ingest"

[[pipeline.phases]]
phase = "context"
agents = ["scene_summarizer"]

[[pipeline.phases]]
phase = "pretranslation"
agents = ["idiom_labeler"]

[[pipeline.phases]]
phase = "translate"
agents = ["direct_translator"]

[[pipeline.phases]]
phase = "qa"
agents = ["style_guide_critic"]

[[pipeline.phases]]
phase = "edit"
agents = ["basic_editor"]

[[pipeline.phases]]
phase = "export"
```

- **default_model.model_id** — Model identifier to use for all phases (unless overridden)
- **phases** — Ordered list of pipeline phases to execute
- **phases[].phase** — Phase name (`ingest`, `context`, `pretranslation`, `translate`, `qa`, `edit`, `export`)
- **phases[].agents** — Which agents to run during this phase

#### `[agents]` — Agent configuration paths

```toml
[agents]
prompts_dir = "packages/rentl-agents/prompts"
agents_dir = "packages/rentl-agents/agents"
```

- **prompts_dir** — Directory containing agent prompt templates
- **agents_dir** — Directory containing agent configuration files

#### `[logging]` — Logging configuration

```toml
[logging]
[[logging.sinks]]
type = "file"

[[logging.sinks]]
type = "console"
```

- **sinks** — Where to write logs (`file` writes to logs_dir, `console` writes to stdout)

#### `[concurrency]` — Parallel execution settings

```toml
[concurrency]
max_parallel_requests = 1
max_parallel_scenes = 1
```

- **max_parallel_requests** — Maximum concurrent API requests per scene
- **max_parallel_scenes** — Maximum scenes to process in parallel

#### `[retry]` — Retry and backoff configuration

```toml
[retry]
max_retries = 3
backoff_s = 1.0
max_backoff_s = 60.0
```

- **max_retries** — Maximum number of retry attempts on API failures
- **backoff_s** — Initial backoff delay in seconds
- **max_backoff_s** — Maximum backoff delay in seconds

#### `[cache]` — Response caching

```toml
[cache]
enabled = false
```

- **enabled** — Whether to cache API responses (useful for development/testing)

### Environment Variables

Store API keys and sensitive configuration in `.env` or `.env.local` files in your project directory. **Never commit these files to version control.**

#### Pipeline API keys

```bash
# OpenRouter
OPENROUTER_API_KEY=your_key_here

# OpenAI
OPENAI_API_KEY=your_key_here

# Local endpoints (Ollama, LM Studio)
RENTL_LOCAL_API_KEY=placeholder
```

#### Quality evaluation API keys (optional)

```bash
# Quality evals: API key for the model provider
RENTL_QUALITY_API_KEY=your_key_here

# Quality evals: base URL for the model provider
RENTL_QUALITY_BASE_URL=https://api.openai.com/v1

# Quality evals: model ID used for agent evaluation runs
RENTL_QUALITY_MODEL=gpt-4

# Quality evals: judge model ID used for LLM-as-judge evaluations
RENTL_QUALITY_JUDGE_MODEL=gpt-4

# Quality evals: base URL for the judge model provider
RENTL_QUALITY_JUDGE_BASE_URL=https://api.openai.com/v1
```

These environment variables are loaded automatically from `.env` files in your workspace directory.

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

## Contributing

This project is in active development. Contributions, issues, and feature requests are welcome.

See our [contribution guidelines](./CONTRIBUTING.md) for details on how to contribute.

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

## Links

- **Repository:** https://github.com/trevorWieland/rentl
- **Issues:** https://github.com/trevorWieland/rentl/issues
