# Getting Started with rentl

This tutorial walks you through translating a visual novel script from Japanese to English using rentl. By the end, you'll have a complete, playable-quality translation ready for patching.

**Who this is for:** Fan translators who want professional-grade results without professional-grade effort.

**What you'll need:**
- A computer running Linux, macOS, or Windows (WSL)
- Python 3.14+
- An API key from an LLM provider (OpenRouter, OpenAI, or a local endpoint)

**Time:** About 10 minutes of setup, then pipeline runtime depends on script length and model speed.

---

## Step 1: Install rentl

The fastest way to get started is with `uvx`, which runs the latest published version without a permanent install:

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify rentl runs
uvx rentl --version
```

You should see output like `rentl v0.1.8`.

> **From source?** If you cloned the repo, use `uv run rentl` instead of `uvx rentl` for all commands below.

---

## Step 2: Create a project

Create a directory for your translation project and initialize it:

```bash
mkdir my-translation && cd my-translation
uvx rentl init
```

The `init` command walks you through an interactive setup:

1. **Provider** — Choose your LLM provider (OpenRouter, OpenAI, Local, or custom)
2. **Model** — Pick a model for translation (the default works well for most scripts)
3. **Languages** — Set source and target languages (e.g., Japanese → English)
4. **Input format** — Choose your script format (TXT, CSV, or JSONL)

When it finishes, your project directory looks like this:

```
my-translation/
├── rentl.toml    # Pipeline configuration
├── .env          # API key placeholder
├── input/        # Put your source script here
├── out/          # Pipeline output appears here
└── logs/         # Run logs
```

---

## Step 3: Add your API key

The `init` command generates a `.env` file with a `RENTL_LOCAL_API_KEY` variable. Open it in any text editor and paste your API key:

```env
# Set your API key for the LLM endpoint
RENTL_LOCAL_API_KEY=sk-or-your-key-here
```

> **Which provider?** [OpenRouter](https://openrouter.ai/) is the easiest option — it gives you access to many models through a single API key. For local models, use [Ollama](https://ollama.ai/) or [LM Studio](https://lmstudio.ai/) and set the API key to `placeholder`.

---

## Step 4: Verify your setup

Run the doctor command to check that everything is configured correctly:

```bash
uvx rentl doctor
```

Doctor checks:
- Python version meets requirements
- `rentl.toml` is valid
- API key is present and loaded
- Model endpoint is reachable
- Required directories exist

Fix any reported issues before continuing. See the [Troubleshooting Guide](./troubleshooting.md) if you get stuck.

---

## Step 5: Prepare your source script

Place your source script in the `input/` directory. rentl accepts three formats:

### Plain text (TXT)

One line of dialogue per line. The simplest format:

```
春の朝、桜の花びらが風に舞う学園の門。
「あの、すみません！」
振り向くと、見知らぬ少女が息を切らせて立っていた。
```

Save as `input/script.txt` and set `input_format = "txt"` in `rentl.toml`.

### JSONL (recommended)

One JSON object per line with structured metadata. This format gives rentl the most context for higher-quality translations:

```json
{"line_id":"scene_001_0001","route_id":"common_0","scene_id":"scene_001","text":"春の朝、桜の花びらが風に舞う学園の門。","metadata":{"is_choice":false,"is_dialogue":false}}
{"line_id":"scene_001_0002","route_id":"common_0","scene_id":"scene_001","speaker":"???","text":"「あの、すみません！」","metadata":{"is_choice":false,"is_dialogue":true}}
```

Save as `input/script.jsonl` and set `input_format = "jsonl"` in `rentl.toml`.

### CSV

Standard CSV with headers. Useful if your script is already in a spreadsheet:

```csv
line_id,scene_id,speaker,text
scene_001_0001,scene_001,,春の朝、桜の花びらが風に舞う学園の門。
scene_001_0002,scene_001,???,「あの、すみません！」
```

Save as `input/script.csv` and set `input_format = "csv"` in `rentl.toml`.

Then update `rentl.toml` to point at your file:

```toml
[project.paths]
input_path = "input/script.jsonl"   # adjust filename and format to match
```

---

## Step 6: Understand the pipeline

Before running, it helps to know what rentl does with your script. You can explore the phases interactively:

```bash
uvx rentl explain
```

The pipeline runs 7 phases in order:

| Phase | What it does |
|-------|-------------|
| **ingest** | Reads your source script and normalizes it into internal format |
| **context** | Summarizes scenes, identifies characters, and builds context |
| **pretranslation** | Labels idioms, cultural references, and tricky expressions |
| **translate** | Translates each line using scene context and annotations |
| **qa** | Reviews translations against a style guide and flags issues |
| **edit** | Applies corrections based on QA findings |
| **export** | Writes final translated output |

Each phase builds on the previous one. Context helps translation, translation feeds QA, and QA drives editing.

---

## Step 7: Run the pipeline

Start the full pipeline:

```bash
uvx rentl run-pipeline
```

This runs all 7 phases in sequence. You'll see progress output as each phase starts and completes.

To monitor a running pipeline in another terminal:

```bash
uvx rentl status --watch
```

> **Targeting specific languages:** If your config lists multiple target languages, you can run one at a time with `uvx rentl run-pipeline -t en`.

---

## Step 8: Check your output

When the pipeline finishes, your translations are in the `out/` directory. Each run gets a unique UUID-based directory:

```bash
ls out/
```

The pipeline summary printed at the end includes the run ID and output file paths. You can also check with:

```bash
uvx rentl status
```

Inside the run directory you'll find the final translated output as JSONL along with phase artifacts.

To export the translation into a different format:

```bash
# Replace <run-id> with the actual run ID from the pipeline output
uvx rentl export -i out/run-<run-id>/en.jsonl -o translation.csv -f csv
```

The `export` command supports CSV, JSONL, and TXT output formats. Use `--include-source-text` to add the original text alongside translations in CSV exports.

---

## What's next?

- **Tune your config** — Adjust `rentl.toml` to change models, concurrency, or retry settings. See the [README](../README.md) for full configuration reference.
- **Run individual phases** — Use `uvx rentl run-phase --phase <phase>` to re-run a specific phase without starting over.
- **Add a style guide** — Place a `style-guide.md` in your project root to guide the QA and editing phases.
- **Check quality** — Review QA artifacts in the run output to see what the style critic flagged.
- **Read troubleshooting** — See the [Troubleshooting Guide](./troubleshooting.md) for common issues and fixes.
