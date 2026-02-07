"""Command help and documentation module."""

from __future__ import annotations

from operator import itemgetter

from pydantic import Field

from rentl_schemas.base import BaseSchema


class CommandInfo(BaseSchema):
    """Information about a CLI command."""

    name: str = Field(..., min_length=1, description="Command name")
    brief: str = Field(..., min_length=1, description="Brief one-line description")
    detailed_help: str = Field(..., min_length=1, description="Detailed help text")
    args: list[str] = Field(..., description="Positional arguments")
    options: list[str] = Field(..., description="Command-line options")
    examples: list[str] = Field(..., description="Usage examples")


# Command registry with complete information for all commands
_COMMAND_REGISTRY: dict[str, CommandInfo] = {
    "version": CommandInfo(
        name="version",
        brief="Display version information",
        detailed_help=(
            "Display the current version of rentl.\n\n"
            "This command outputs the version number of the installed rentl CLI."
        ),
        args=[],
        options=[],
        examples=["rentl version"],
    ),
    "init": CommandInfo(
        name="init",
        brief="Initialize a new rentl project interactively",
        detailed_help=(
            "Initialize a new rentl project in the current directory.\n\n"
            "This command creates the necessary configuration files "
            "(rentl.toml, .env), workspace directories, and optional seed data "
            "through an interactive wizard. If rentl.toml already exists, you "
            "will be prompted to confirm overwriting it."
        ),
        args=[],
        options=[],
        examples=[
            "rentl init",
            "# Follow the prompts to configure your project",
        ],
    ),
    "validate-connection": CommandInfo(
        name="validate-connection",
        brief="Validate connectivity for configured model endpoints",
        detailed_help=(
            "Test connectivity to configured LLM endpoints.\n\n"
            "This command validates that all configured model endpoints are reachable "
            "and responsive. It reads the endpoint configuration from rentl.toml "
            "and attempts to connect to each endpoint, reporting success or failure."
        ),
        args=[],
        options=[
            "--config PATH  Path to rentl.toml config file (default: ./rentl.toml)",
        ],
        examples=[
            "rentl validate-connection",
            "rentl validate-connection --config custom/path/rentl.toml",
        ],
    ),
    "export": CommandInfo(
        name="export",
        brief="Export translated lines to output files",
        detailed_help=(
            "Export translated lines from the workspace to CSV, JSONL, or TXT "
            "format.\n\n"
            "This command reads translated data from the workspace and writes "
            "it to the specified output format. You can control how untranslated "
            "lines are handled, which columns to include, and the order of "
            "columns in the output."
        ),
        args=[],
        options=[
            "--config PATH            Path to rentl.toml config file "
            "(default: ./rentl.toml)",
            "--input PATH             Input file path",
            "--output PATH            Output file path",
            "--format FORMAT          Output format: csv, jsonl, or txt "
            "(default: jsonl)",
            "--untranslated-policy    How to handle untranslated lines: "
            "error, warn, or allow",
            "--include-source-text    Include source text in output",
            "--include-scene-id       Include scene ID in output",
            "--include-speaker        Include speaker name in output",
            "--column-order           Comma-separated column order",
            "--expected-line-count    Expected number of lines (validation check)",
        ],
        examples=[
            "rentl export --output translations.jsonl",
            "rentl export --format csv --output translations.csv --include-source-text",
            "rentl export --untranslated-policy warn --output output.txt",
        ],
    ),
    "run-pipeline": CommandInfo(
        name="run-pipeline",
        brief="Run the full translation pipeline",
        detailed_help=(
            "Execute the full translation pipeline for configured target "
            "languages.\n\n"
            "This command orchestrates the entire translation workflow, "
            "running all enabled phases (ingest, context, pretranslation, "
            "translate, qa, edit, export) in sequence. Progress is displayed "
            "in real-time with a visual progress bar."
        ),
        args=[],
        options=[
            "--config PATH             Path to rentl.toml config file "
            "(default: ./rentl.toml)",
            "--run-id ID               Optional run ID for resuming or tracking",
            "--target-languages LANGS  Target language codes (comma-separated)",
        ],
        examples=[
            "rentl run-pipeline",
            "rentl run-pipeline --target-languages en,es",
            "rentl run-pipeline --run-id 01234567-89ab-cdef-0123-456789abcdef",
        ],
    ),
    "run-phase": CommandInfo(
        name="run-phase",
        brief="Run a single pipeline phase",
        detailed_help=(
            "Execute a single phase of the translation pipeline.\n\n"
            "This command runs one specific phase (with its required "
            "prerequisites) instead of the full pipeline. Useful for testing "
            "individual phases or running only part of the workflow. Available "
            "phases: ingest, context, pretranslation, translate, qa, edit, "
            "export."
        ),
        args=[],
        options=[
            "--config PATH          Path to rentl.toml config file "
            "(default: ./rentl.toml)",
            "--phase PHASE          Phase to run (required): ingest, context, "
            "pretranslation, translate, qa, edit, export",
            "--run-id ID            Optional run ID for resuming or tracking",
            "--target-language LANG Target language code",
            "--input-path PATH      Input file path (phase-specific)",
            "--output-path PATH     Output file path (phase-specific)",
        ],
        examples=[
            "rentl run-phase --phase ingest",
            "rentl run-phase --phase translate --target-language en",
            "rentl run-phase --phase export --output-path output/translations.jsonl",
        ],
    ),
    "status": CommandInfo(
        name="status",
        brief="Show run status and progress",
        detailed_help=(
            "Display the status and progress of pipeline runs.\n\n"
            "This command shows the current state of a pipeline run, including "
            "which phases have completed, which are in progress, and any errors "
            "encountered. Use --watch to monitor progress in real-time, or "
            "--json for machine-readable output."
        ),
        args=[],
        options=[
            "--config PATH   Path to rentl.toml config file (default: ./rentl.toml)",
            "--run-id ID     Run ID to show status for (default: most recent)",
            "--watch, -w     Watch progress in real-time",
            "--json          Output status as JSON",
        ],
        examples=[
            "rentl status",
            "rentl status --run-id 01234567-89ab-cdef-0123-456789abcdef",
            "rentl status --watch",
            "rentl status --json",
        ],
    ),
    "help": CommandInfo(
        name="help",
        brief="Display help information for commands",
        detailed_help=(
            "Show help information for rentl commands.\n\n"
            "When called without arguments, displays a summary of all available "
            "commands. When called with a command name, displays detailed help "
            "for that specific command including arguments, options, and usage "
            "examples."
        ),
        args=["[COMMAND]  Optional command name to get detailed help for"],
        options=[],
        examples=[
            "rentl help",
            "rentl help init",
            "rentl help run-pipeline",
        ],
    ),
    "doctor": CommandInfo(
        name="doctor",
        brief="Run diagnostic checks on your rentl setup",
        detailed_help=(
            "Perform comprehensive diagnostic checks on your rentl "
            "environment.\n\n"
            "This command validates your Python version, configuration files, "
            "workspace directory structure, API keys, and LLM endpoint "
            "connectivity. Each check reports pass/fail/warn status with "
            "actionable fix suggestions for any issues found. Exit code is 0 "
            "when all checks pass, non-zero otherwise."
        ),
        args=[],
        options=[
            "--config PATH  Path to rentl.toml config file (default: ./rentl.toml)",
        ],
        examples=[
            "rentl doctor",
            "rentl doctor --config custom/path/rentl.toml",
        ],
    ),
    "explain": CommandInfo(
        name="explain",
        brief="Explain what a pipeline phase does",
        detailed_help=(
            "Display detailed information about a pipeline phase.\n\n"
            "This command explains what a specific phase does, its inputs and "
            "outputs, prerequisites, and relevant configuration options. When "
            "called without a phase name, it lists all available phases with "
            "brief descriptions.\n\n"
            "Available phases: ingest, context, pretranslation, translate, qa, "
            "edit, export"
        ),
        args=["[PHASE]  Optional phase name to explain"],
        options=[],
        examples=[
            "rentl explain",
            "rentl explain ingest",
            "rentl explain translate",
        ],
    ),
}


def get_command_help(name: str) -> CommandInfo:
    """Get detailed help information for a command.

    Args:
        name: The name of the command

    Returns:
        CommandInfo: Detailed information about the command

    Raises:
        ValueError: If the command name is invalid
    """
    if name not in _COMMAND_REGISTRY:
        valid_commands = ", ".join(sorted(_COMMAND_REGISTRY.keys()))
        raise ValueError(
            f"Invalid command name '{name}'. Valid commands: {valid_commands}"
        )

    return _COMMAND_REGISTRY[name]


def list_commands() -> list[tuple[str, str]]:
    """List all available commands with brief descriptions.

    Returns:
        list[tuple[str, str]]: List of (command_name, brief_description) tuples,
            sorted alphabetically by command name
    """
    return sorted(
        [(name, info.brief) for name, info in _COMMAND_REGISTRY.items()],
        key=itemgetter(0),
    )
