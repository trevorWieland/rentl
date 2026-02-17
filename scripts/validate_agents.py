#!/usr/bin/env python3
"""Manual validation script for rentl phase agents.

This script validates the pipeline agents by running them in sequence:
1. Scene Summarizer (context phase) - produces scene summaries
2. Idiom Labeler (pretranslation phase) - identifies idioms using summaries
3. Direct Translator (translate phase) - produces translated lines

Usage:
    uv run python scripts/validate_agents.py [--config FILE] [--input FILE]
        [--model MODEL]

Examples:
    # Validate with mock data (no LLM call)
    uv run python scripts/validate_agents.py --mock

    # Validate with real LLM (requires API key)
    uv run python scripts/validate_agents.py --model gpt-5-nano

    # Validate with JSONL input file (full pipeline)
    uv run python scripts/validate_agents.py --config rentl.toml \
        --input samples/golden/script.jsonl

    # Run only scene summarizer
    uv run python scripts/validate_agents.py --phase context

    # Run only idiom labeler
    uv run python scripts/validate_agents.py --phase pretranslation

    # Run only translator
    uv run python scripts/validate_agents.py --phase translate
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tomllib
import traceback
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid7

from dotenv import load_dotenv

from rentl_agents import (
    chunk_lines,
    format_lines_for_prompt,
    get_default_agents_dir,
    get_default_prompts_dir,
    load_agent_profile,
)
from rentl_agents.context import group_lines_by_scene, validate_scene_input
from rentl_agents.runtime import ProfileAgentConfig
from rentl_agents.wiring import (
    create_context_agent_from_profile,
    create_edit_agent_from_profile,
    create_pretranslation_agent_from_profile,
    create_qa_agent_from_profile,
    create_translate_agent_from_profile,
)
from rentl_core.qa import DeterministicQaRunner, get_default_registry
from rentl_schemas.config import (
    ModelEndpointConfig,
    ModelSettings,
    PhaseConfig,
    RunConfig,
)
from rentl_schemas.io import SourceLine, TranslatedLine
from rentl_schemas.phases import (
    ContextPhaseInput,
    ContextPhaseOutput,
    EditPhaseInput,
    PretranslationAnnotation,
    PretranslationPhaseInput,
    QaPhaseInput,
    SceneSummary,
    TermCandidate,
    TranslatePhaseInput,
)
from rentl_schemas.primitives import JsonValue, PhaseName, QaSeverity
from rentl_schemas.qa import QaIssue
from rentl_schemas.validation import validate_run_config


def normalize_id(value: str) -> str:
    """Normalize ID to match HumanReadableId pattern.

    Args:
        value: The ID string to normalize.

    Returns:
        Normalized ID matching pattern ^[a-z]+_[0-9]+$.
    """
    if not value:
        return "unknown_0"
    # Extract only lowercase letters and numbers
    letters = "".join(c for c in value if c.isalpha()).lower()
    numbers = "".join(c for c in value if c.isdigit())
    if not letters:
        letters = "id"
    if not numbers:
        numbers = "0"
    return f"{letters}_{numbers}"


class ConfigError(Exception):
    """Error loading configuration."""

    pass


@dataclass(frozen=True, slots=True)
class _ResolvedConfig:
    config: RunConfig
    config_path: Path
    workspace_dir: Path
    agents_dir: Path
    prompts_dir: Path


@dataclass(frozen=True, slots=True)
class _AgentProfileSpec:
    name: str
    phase: PhaseName
    version: str
    path: Path


def load_config(config_path: Path) -> _ResolvedConfig:
    """Load and resolve configuration from rentl.toml.

    Args:
        config_path: Path to rentl TOML config.

    Returns:
        Resolved configuration bundle.

    Raises:
        ConfigError: If rentl.toml is missing or cannot be parsed.
    """
    if not config_path.exists():
        raise ConfigError(
            "rentl.toml not found in current directory.\n"
            "Either create rentl.toml or provide --model and --base-url CLI arguments."
        )

    try:
        with config_path.open("rb") as handle:
            payload: dict[str, JsonValue] = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Failed to parse rentl.toml: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"Failed to read rentl.toml: {exc}") from exc

    if not isinstance(payload, dict):
        raise ConfigError("Config root must be a TOML table")

    config = validate_run_config(payload)
    config = _resolve_project_paths(config, config_path)
    config = _resolve_agent_paths(config)

    workspace_dir = Path(config.project.paths.workspace_dir)
    return _ResolvedConfig(
        config=config,
        config_path=config_path,
        workspace_dir=workspace_dir,
        agents_dir=Path(config.agents.agents_dir),
        prompts_dir=Path(config.agents.prompts_dir),
    )


def _resolve_project_paths(config: RunConfig, config_path: Path) -> RunConfig:
    config_dir = config_path.parent
    workspace_dir = Path(config.project.paths.workspace_dir)
    if not workspace_dir.is_absolute():
        workspace_dir = (config_dir / workspace_dir).resolve()
    input_path = _resolve_path(Path(config.project.paths.input_path), workspace_dir)
    output_dir = _resolve_path(Path(config.project.paths.output_dir), workspace_dir)
    logs_dir = _resolve_path(Path(config.project.paths.logs_dir), workspace_dir)
    updated_paths = config.project.paths.model_copy(
        update={
            "workspace_dir": str(workspace_dir),
            "input_path": str(input_path),
            "output_dir": str(output_dir),
            "logs_dir": str(logs_dir),
        }
    )
    updated_project = config.project.model_copy(update={"paths": updated_paths})
    return config.model_copy(update={"project": updated_project})


def _resolve_agent_paths(config: RunConfig) -> RunConfig:
    workspace_dir = Path(config.project.paths.workspace_dir)
    agents_config = config.agents
    updated_agents = agents_config.model_copy(
        update={
            "prompts_dir": str(
                _resolve_path(Path(agents_config.prompts_dir), workspace_dir)
            ),
            "agents_dir": str(
                _resolve_path(Path(agents_config.agents_dir), workspace_dir)
            ),
        }
    )
    return config.model_copy(update={"agents": updated_agents})


def _resolve_path(path: Path, base_dir: Path) -> Path:
    base_dir = base_dir.resolve()
    resolved = path if path.is_absolute() else base_dir / path
    resolved = resolved.resolve()
    try:
        resolved.relative_to(base_dir)
    except ValueError as exc:
        raise ConfigError(f"Path must stay within workspace: {resolved}") from exc
    return resolved


def _discover_agent_profile_specs(
    agents_dir: Path,
) -> dict[str, _AgentProfileSpec]:
    specs: dict[str, _AgentProfileSpec] = {}
    if not agents_dir.exists():
        return specs
    for phase in PhaseName:
        if phase in {PhaseName.INGEST, PhaseName.EXPORT}:
            continue
        phase_dir = agents_dir / phase.value
        if not phase_dir.exists():
            continue
        for toml_path in phase_dir.glob("*.toml"):
            profile = load_agent_profile(toml_path)
            if profile.meta.phase != phase:
                raise ConfigError(
                    f"Agent {profile.meta.name} declares phase "
                    f"{profile.meta.phase.value} but is in {phase.value}/"
                )
            name = profile.meta.name
            if name in specs:
                raise ConfigError(f"Duplicate agent name: {name}")
            specs[name] = _AgentProfileSpec(
                name=name,
                phase=phase,
                version=str(profile.meta.version),
                path=toml_path,
            )
    return specs


def _resolve_phase_config(config: RunConfig, phase: PhaseName) -> PhaseConfig:
    for entry in config.pipeline.phases:
        if entry.phase == phase:
            return entry
    raise ConfigError(f"Phase {phase.value} is not configured")


def _resolve_phase_agents(config: RunConfig, phase: PhaseName) -> list[str]:
    phase_config = _resolve_phase_config(config, phase)
    if not phase_config.enabled:
        return []
    if not phase_config.agents:
        raise ConfigError(f"agents must be configured for {phase.value} phase")
    return list(phase_config.agents)


def _resolve_phase_model(config: RunConfig, phase: PhaseName) -> ModelSettings:
    phase_config = _resolve_phase_config(config, phase)
    if phase_config.model is not None:
        return phase_config.model
    if config.pipeline.default_model is None:
        raise ConfigError("default_model is required for agent phases")
    return config.pipeline.default_model


def _resolve_endpoint_config(
    config: RunConfig, model_settings: ModelSettings
) -> ModelEndpointConfig:
    if config.endpoints is None:
        endpoint = config.endpoint
        if endpoint is None:
            raise ConfigError("Endpoint configuration is required")
        return endpoint
    endpoint_ref = config.resolve_endpoint_ref(model=model_settings)
    if endpoint_ref is None:
        raise ConfigError("Endpoint reference could not be resolved")
    for endpoint in config.endpoints.endpoints:
        if endpoint.provider_name == endpoint_ref:
            return endpoint
    raise ConfigError(f"Unknown endpoint reference: {endpoint_ref}")


def _build_profile_agent_config(
    config: RunConfig,
    phase: PhaseName,
    *,
    api_key: str,
    base_url_override: str | None,
    model_override: str | None,
) -> ProfileAgentConfig:
    model_settings = _resolve_phase_model(config, phase)
    endpoint = _resolve_endpoint_config(config, model_settings)
    return ProfileAgentConfig(
        api_key=api_key,
        base_url=base_url_override or endpoint.base_url,
        model_id=model_override or model_settings.model_id,
        temperature=model_settings.temperature,
        top_p=model_settings.top_p,
        timeout_s=endpoint.timeout_s,
        openrouter_provider=endpoint.openrouter_provider,
        max_retries=config.retry.max_retries,
        retry_base_delay=config.retry.backoff_s,
    )


def _resolve_api_key(
    config: RunConfig,
    phase: PhaseName,
    api_key_override: str | None,
) -> str:
    if api_key_override:
        return api_key_override
    endpoint = _resolve_endpoint_config(config, _resolve_phase_model(config, phase))
    api_key = os.environ.get(endpoint.api_key_env)
    if not api_key:
        raise ConfigError(
            "Missing API key environment variable: "
            f"{endpoint.api_key_env} (phase: {phase.value})"
        )
    return api_key


def main() -> int:
    """Run the validation script.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = argparse.ArgumentParser(
        description="Validate rentl phase agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Input JSONL file with source lines (optional)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("rentl.toml"),
        help="Path to rentl TOML config (default: rentl.toml)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model ID to use (default: from rentl.toml)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock data only (no LLM call)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="API key (or set env var, default: RENTL_LOCAL_API_KEY)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="API base URL (default: from rentl.toml)",
    )
    parser.add_argument(
        "--phase",
        type=str,
        choices=["all", "context", "pretranslation", "translate", "qa", "edit"],
        default="all",
        help="Which phase(s) to run (default: all)",
    )
    parser.add_argument(
        "--style-guide",
        type=Path,
        default=Path("samples/style-guide.md"),
        help="Path to style guide markdown file (default: samples/style-guide.md)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=10,
        help="Lines per chunk for translation/pretranslation (default: 10)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Max concurrent LLM requests (default: 1)",
    )
    args = parser.parse_args()

    # Load .env file if present
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path, override=False)

    print("=" * 70)
    print("rentl Agent Validation")
    print("=" * 70)

    # Load configuration
    resolved_config: _ResolvedConfig | None = None
    source_lang = "ja"
    target_lang = "en"
    agents_dir = get_default_agents_dir()
    prompts_dir = get_default_prompts_dir()

    try:
        resolved_config = load_config(args.config)
        source_lang = resolved_config.config.project.languages.source_language
        target_lang = resolved_config.config.project.languages.target_languages[0]
        agents_dir = resolved_config.agents_dir
        prompts_dir = resolved_config.prompts_dir
        print(f"\n  ✓ Loaded config from {args.config}")
    except ConfigError as exc:
        if not args.model or not args.base_url:
            print(f"\n  ✗ Configuration error: {exc}")
            print("\n  Either fix rentl.toml or provide both --model and --base-url")
            return 1
        print("\n  ⚠ rentl.toml not loaded, using CLI arguments")

    # Step 1: Load input data
    print("\n[1/8] Loading input data...")
    input_path = args.input
    if input_path is None and resolved_config is not None:
        input_path = Path(resolved_config.config.project.paths.input_path)

    if input_path is not None:
        if not input_path.exists():
            print(f"  ✗ Input file not found: {input_path}")
            return 1
        print(f"  Loading from: {input_path}")
        source_lines: list[SourceLine] = []
        line_counter = 0
        with input_path.open() as f:
            for line in f:
                data: dict[str, JsonValue] = json.loads(line)
                # Normalize IDs to match HumanReadableId pattern
                data["line_id"] = f"line_{line_counter:04d}"
                if data.get("scene_id"):
                    data["scene_id"] = normalize_id(data.get("scene_id", "scene_0"))
                if data.get("route_id"):
                    data["route_id"] = normalize_id(data.get("route_id", "route_0"))
                source_lines.append(SourceLine.model_validate(data))
                line_counter += 1
        print(f"  ✓ Loaded {len(source_lines)} lines")
    else:
        print("  Using sample data...")
        source_lines = [
            SourceLine(
                line_id="line_001",
                text="猫の手も借りたいほど忙しいんだ。",
                speaker="田中",
                route_id="main_001",
                scene_id="scene_001",
            ),
            SourceLine(
                line_id="line_002",
                text="まあまあ、落ち着いて。石の上にも三年だよ。",
                speaker="佐藤",
                route_id="main_001",
                scene_id="scene_001",
            ),
            SourceLine(
                line_id="line_003",
                text="先輩、今日の天気は本当に暑いですね。",
                speaker="山田",
                route_id="main_001",
                scene_id="scene_001",
            ),
            SourceLine(
                line_id="line_004",
                text="It's raining cats and dogs outside!",
                speaker="John",
                route_id="main_001",
                scene_id="scene_002",
            ),
            SourceLine(
                line_id="line_005",
                text="Well, every cloud has a silver lining, right?",
                speaker="Mary",
                route_id="main_001",
                scene_id="scene_002",
            ),
        ]
        print(f"  ✓ Created {len(source_lines)} sample lines")

    # Step 2: Load profiles
    print("\n[2/8] Loading agent profiles...")
    agent_specs = _discover_agent_profile_specs(agents_dir)
    if not agent_specs:
        print(f"  ✗ No agent profiles found in {agents_dir}")
        return 1

    default_agent_names: dict[PhaseName, list[str]] = {
        PhaseName.CONTEXT: ["scene_summarizer"],
        PhaseName.PRETRANSLATION: ["idiom_labeler"],
        PhaseName.TRANSLATE: ["direct_translator"],
        PhaseName.QA: ["style_guide_critic"],
        PhaseName.EDIT: ["basic_editor"],
    }

    if resolved_config is not None:
        config = resolved_config.config
        try:
            context_agents = _resolve_phase_agents(config, PhaseName.CONTEXT)
            pretranslation_agents = _resolve_phase_agents(
                config, PhaseName.PRETRANSLATION
            )
            translate_agents = _resolve_phase_agents(config, PhaseName.TRANSLATE)
            qa_agents = _resolve_phase_agents(config, PhaseName.QA)
            edit_agents = _resolve_phase_agents(config, PhaseName.EDIT)
        except ConfigError as exc:
            print(f"  ✗ {exc}")
            return 1
    else:
        context_agents = default_agent_names[PhaseName.CONTEXT]
        pretranslation_agents = default_agent_names[PhaseName.PRETRANSLATION]
        translate_agents = default_agent_names[PhaseName.TRANSLATE]
        qa_agents = default_agent_names[PhaseName.QA]
        edit_agents = default_agent_names[PhaseName.EDIT]

    def resolve_specs(phase: PhaseName, names: list[str]) -> list[_AgentProfileSpec]:
        specs: list[_AgentProfileSpec] = []
        for name in names:
            spec = agent_specs.get(name)
            if spec is None:
                available = ", ".join(sorted(agent_specs.keys())) or "none"
                raise ConfigError(
                    f"Unknown agent '{name}' for phase {phase.value}. "
                    f"Available: {available}"
                )
            if spec.phase != phase:
                raise ConfigError(
                    f"Agent {name} is for phase {spec.phase.value} "
                    f"but was configured for {phase.value}"
                )
            specs.append(spec)
        return specs

    try:
        context_specs = resolve_specs(PhaseName.CONTEXT, context_agents)
        pretranslation_specs = resolve_specs(
            PhaseName.PRETRANSLATION, pretranslation_agents
        )
        translate_specs = resolve_specs(PhaseName.TRANSLATE, translate_agents)
        qa_specs = resolve_specs(PhaseName.QA, qa_agents)
        edit_specs = resolve_specs(PhaseName.EDIT, edit_agents)
    except ConfigError as exc:
        print(f"  ✗ {exc}")
        return 1

    for phase, specs in (
        (PhaseName.CONTEXT, context_specs),
        (PhaseName.PRETRANSLATION, pretranslation_specs),
        (PhaseName.TRANSLATE, translate_specs),
        (PhaseName.QA, qa_specs),
        (PhaseName.EDIT, edit_specs),
    ):
        if not specs:
            print(f"  ⊘ {phase.value}: no agents configured")
            continue
        for spec in specs:
            print(f"  ✓ {phase.value}: {spec.name} v{spec.version}")

    def _require_specs(phase: PhaseName, specs: list[_AgentProfileSpec]) -> bool:
        if args.phase in ["all", phase.value] and not specs:
            print(f"\n  ✗ No agents configured for {phase.value} phase")
            return False
        return True

    if not (
        _require_specs(PhaseName.CONTEXT, context_specs)
        and _require_specs(PhaseName.PRETRANSLATION, pretranslation_specs)
        and _require_specs(PhaseName.TRANSLATE, translate_specs)
        and _require_specs(PhaseName.QA, qa_specs)
        and _require_specs(PhaseName.EDIT, edit_specs)
    ):
        return 1

    # Step 3: Validate input for context phase
    print("\n[3/8] Validating input...")
    try:
        validate_scene_input(source_lines)
        print("  ✓ All lines have scene_id")
    except Exception as e:
        print(f"  ⚠ Scene validation: {e}")
        if args.phase in ["all", "context"]:
            print("  ✗ Cannot run context phase without scene_id")
            return 1

    scene_groups = group_lines_by_scene(source_lines)
    print(f"  ✓ Found {len(scene_groups)} scene(s)")

    for scene_id, lines in list(scene_groups.items())[:3]:
        print(f"    - {scene_id}: {len(lines)} lines")
    if len(scene_groups) > 3:
        print(f"    ... and {len(scene_groups) - 3} more")

    # Check for mock mode
    if args.mock:
        print("\n[4/8] Context phase (mock)...")
        print("  ⊘ Mock mode - skipping LLM calls")

        print("\n[5/8] Pretranslation phase (mock)...")
        print("  ⊘ Mock mode - skipping LLM calls")

        print("\n[6/8] Translate phase (mock)...")
        print("  ⊘ Mock mode - skipping LLM calls")

        # Show what would be processed
        chunks = chunk_lines(source_lines, args.chunk_size)
        print(f"\n  Would process {len(chunks)} chunk(s) for translation")
        for i, chunk in enumerate(chunks[:2]):
            formatted = format_lines_for_prompt(chunk)
            print(f"\n  Chunk {i + 1} preview ({len(chunk)} lines):")
            for line in formatted.split("\n")[:3]:
                print(f"    {line}")
            if len(chunk) > 3:
                print(f"    ... and {len(chunk) - 3} more")

        print("\n[7/8] QA phase (mock)...")
        print("  ⊘ Mock mode - showing what would run:")
        print("  • Deterministic: line_length, empty_translation, whitespace")
        if qa_specs:
            print("  • LLM-based:")
            for spec in qa_specs:
                print(f"    - {spec.name}")
        else:
            print("  • LLM-based: (none configured)")
        if args.style_guide.exists():
            print(f"  • Style guide: {args.style_guide}")
        else:
            print(f"  • Style guide: (not found at {args.style_guide})")

        print("\n[8/8] Edit phase (mock)...")
        if edit_specs:
            print("  • LLM-based:")
            for spec in edit_specs:
                print(f"    - {spec.name}")
        else:
            print("  • LLM-based: (none configured)")

        print("\n" + "=" * 70)
        print("✓ Agent validation complete (structure only)")
        return 0

    phases_to_run: list[PhaseName] = []
    if args.phase in ["all", "context"]:
        phases_to_run.append(PhaseName.CONTEXT)
    if args.phase in ["all", "pretranslation"]:
        phases_to_run.append(PhaseName.PRETRANSLATION)
    if args.phase in ["all", "translate"]:
        phases_to_run.append(PhaseName.TRANSLATE)
    if args.phase in ["all", "qa"]:
        phases_to_run.append(PhaseName.QA)
    if args.phase in ["all", "edit"]:
        phases_to_run.append(PhaseName.EDIT)

    if resolved_config is None:
        base_url = args.base_url
        model_id = args.model
        api_key_env = "RENTL_LOCAL_API_KEY"
        api_key = args.api_key or os.environ.get(api_key_env, "")
        if not base_url:
            print("\n  ✗ No base_url configured. Set in rentl.toml or use --base-url")
            return 1
        if not model_id:
            print("\n  ✗ No model_id configured. Set in rentl.toml or use --model")
            return 1
        if not api_key:
            print(f"\n  ✗ No API key. Set {api_key_env} or use --api-key")
            print("  ⊘ Run with --mock to skip LLM calls")
            return 1

        print(f"\n  Model: {model_id}")
        print(f"  Base URL: {base_url}")
        print("  Structured output: tool-only (enforced)")
        print(f"  Source: {source_lang} → Target: {target_lang}")

        def build_phase_config(phase: PhaseName) -> ProfileAgentConfig:
            return ProfileAgentConfig(
                api_key=api_key,
                base_url=base_url,
                model_id=model_id,
            )

    else:
        config = resolved_config.config
        api_keys: dict[PhaseName, str] = {}
        try:
            for phase in phases_to_run:
                api_keys[phase] = _resolve_api_key(config, phase, args.api_key)
        except ConfigError as exc:
            print(f"\n  ✗ {exc}")
            print("  ⊘ Run with --mock to skip LLM calls")
            return 1

        sample_model = (
            args.model or _resolve_phase_model(config, PhaseName.CONTEXT).model_id
        )
        sample_endpoint = _resolve_endpoint_config(
            config, _resolve_phase_model(config, PhaseName.CONTEXT)
        )
        sample_base_url = args.base_url or sample_endpoint.base_url
        print(f"\n  Model: {sample_model}")
        print(f"  Base URL: {sample_base_url}")
        print("  Structured output: tool-only (enforced)")
        print(f"  Source: {source_lang} → Target: {target_lang}")

        def build_phase_config(phase: PhaseName) -> ProfileAgentConfig:
            return _build_profile_agent_config(
                config,
                phase,
                api_key=api_keys[phase],
                base_url_override=args.base_url,
                model_override=args.model,
            )

    # Step 4: Run Context Phase (Scene Summarizer)
    scene_summaries: list[SceneSummary] = []

    if args.phase in ["all", "context"]:
        print("\n[4/8] Context phase (Scene Summarizer)...")
        concurrency = args.concurrency
        print(f"  Running {len(scene_groups)} scene(s) (concurrency={concurrency})...")

        for spec in context_specs:
            phase_config = build_phase_config(PhaseName.CONTEXT)
            print(f"  Agent: {spec.name}")

            async def run_scene(
                scene_id: str,
                scene_lines: list[SourceLine],
                semaphore: asyncio.Semaphore,
                phase_config: ProfileAgentConfig = phase_config,
                profile_path: Path = spec.path,
            ) -> tuple[str, ContextPhaseOutput]:
                """Run summarizer on a single scene.

                Returns:
                    Tuple of scene_id and context phase output.
                """
                async with semaphore:
                    print(f"    Starting {scene_id} ({len(scene_lines)} lines)...")
                    agent = create_context_agent_from_profile(
                        profile_path=profile_path,
                        prompts_dir=prompts_dir,
                        config=phase_config,
                        source_lang=source_lang,
                        target_lang=target_lang,
                    )
                    payload = ContextPhaseInput(
                        run_id=uuid7(),
                        source_lines=scene_lines,
                    )
                    result = await agent.run(payload)
                    print(f"    ✓ Completed {scene_id}")
                    return scene_id, result

            async def run_all_scenes() -> list[
                tuple[str, ContextPhaseOutput] | BaseException
            ]:
                """Run all scenes with concurrency limit.

                Returns:
                    List of results or exceptions from execution.
                """
                semaphore = asyncio.Semaphore(concurrency)
                tasks = [
                    run_scene(scene_id, lines, semaphore)
                    for scene_id, lines in scene_groups.items()
                ]
                return await asyncio.gather(*tasks, return_exceptions=True)

            try:
                results = asyncio.run(run_all_scenes())

                errors: list[Exception] = []
                summaries: list[SceneSummary] = []
                for result in results:
                    if isinstance(result, BaseException):
                        errors.append(
                            result
                            if isinstance(result, Exception)
                            else Exception(str(result))
                        )
                    elif isinstance(result, tuple):
                        _, scene_result = result
                        summaries.extend(scene_result.scene_summaries)

                if errors:
                    print(f"  ⚠ {len(errors)} scene(s) failed")
                    for err in errors[:3]:
                        print(f"    - {err}")

                scene_summaries = summaries
                print(f"  ✓ Generated {len(scene_summaries)} scene summary(ies)")

                for summary in scene_summaries[:3]:
                    print(f"\n  [{summary.scene_id}]")
                    print(f"    Summary: {summary.summary[:100]}...")
                    print(f"    Characters: {', '.join(summary.characters[:5])}")

            except Exception as exc:
                print(f"  ✗ Context phase failed: {exc}")
                traceback.print_exc()
                return 1
    else:
        print("\n[4/8] Context phase (skipped)")

    # Step 5: Run Pretranslation Phase (Idiom Labeler)
    pretranslation_annotations: list[PretranslationAnnotation] = []
    term_candidates: list[TermCandidate] = []

    if args.phase in ["all", "pretranslation"]:
        print("\n[5/8] Pretranslation phase (Idiom Labeler)...")

        try:
            for spec in pretranslation_specs:
                phase_config = build_phase_config(PhaseName.PRETRANSLATION)
                print(f"  Agent: {spec.name}")
                agent = create_pretranslation_agent_from_profile(
                    profile_path=spec.path,
                    prompts_dir=prompts_dir,
                    config=phase_config,
                    chunk_size=args.chunk_size,
                    source_lang=source_lang,
                    target_lang=target_lang,
                )

                payload = PretranslationPhaseInput(
                    run_id=uuid7(),
                    source_lines=source_lines,
                    scene_summaries=scene_summaries or None,
                )

                chunks = chunk_lines(source_lines, args.chunk_size)
                print(f"  Processing {len(chunks)} chunk(s)...")

                result = asyncio.run(agent.run(payload))

                # Save annotations for translate phase
                pretranslation_annotations = result.annotations
                term_candidates = result.term_candidates

                print(f"  ✓ Found {len(result.annotations)} idiom(s)")

                if result.annotations:
                    print("\n  Idioms found:")
                    for ann in result.annotations[:5]:
                        print(f"\n  [{ann.line_id}] {ann.value}")
                        idiom_type = (
                            ann.metadata.get("idiom_type") if ann.metadata else "N/A"
                        )
                        print(f"    Type: {idiom_type}")
                        explanation = ann.notes[:80] if ann.notes else "N/A"
                        print(f"    Explanation: {explanation}...")
                    if len(result.annotations) > 5:
                        print(f"\n  ... and {len(result.annotations) - 5} more")
                else:
                    print("\n  No idioms identified in the input text.")

        except Exception as exc:
            print(f"  ✗ Pretranslation phase failed: {exc}")
            traceback.print_exc()
            return 1
    else:
        print("\n[5/8] Pretranslation phase (skipped)")

    # Step 6: Run Translate Phase (Direct Translator)
    translated_lines: list[TranslatedLine] = []
    all_issues: list[QaIssue] = []
    style_guide_content = ""

    if args.phase in ["all", "translate"]:
        print("\n[6/8] Translate phase (Direct Translator)...")

        try:
            for spec in translate_specs:
                phase_config = build_phase_config(PhaseName.TRANSLATE)
                print(f"  Agent: {spec.name}")
                agent = create_translate_agent_from_profile(
                    profile_path=spec.path,
                    prompts_dir=prompts_dir,
                    config=phase_config,
                    chunk_size=args.chunk_size,
                    source_lang=source_lang,
                    target_lang=target_lang,
                )

                payload = TranslatePhaseInput(
                    run_id=uuid7(),
                    target_language=target_lang,
                    source_lines=source_lines,
                    scene_summaries=scene_summaries or None,
                    pretranslation_annotations=pretranslation_annotations or None,
                    term_candidates=term_candidates or None,
                )

                chunks = chunk_lines(source_lines, args.chunk_size)
                print(f"  Processing {len(chunks)} chunk(s)...")

                result = asyncio.run(agent.run(payload))

                print(f"  ✓ Translated {len(result.translated_lines)} line(s)")

                # Save for QA phase
                translated_lines = result.translated_lines

                if result.translated_lines:
                    print("\n  Sample translations:")
                    for line in result.translated_lines[:5]:
                        print(f"\n  [{line.line_id}]")
                        source_preview = (
                            line.source_text[:50] if line.source_text else "N/A"
                        )
                        print(f"    Source: {source_preview}...")
                        translation_preview = line.text[:50] if line.text else "N/A"
                        print(f"    Translation: {translation_preview}...")
                    if len(result.translated_lines) > 5:
                        print(f"\n  ... and {len(result.translated_lines) - 5} more")

        except Exception as exc:
            print(f"  ✗ Translate phase failed: {exc}")
            traceback.print_exc()
            return 1
    else:
        print("\n[6/8] Translate phase (skipped)")

    # Step 7: Run QA Phase (Deterministic + LLM-based)
    if args.phase in ["all", "qa"]:
        print("\n[7/8] QA phase...")

        # Load style guide
        if args.style_guide.exists():
            style_guide_content = args.style_guide.read_text()
            print(f"  Loaded style guide: {args.style_guide}")
        else:
            print(f"  ⚠ Style guide not found: {args.style_guide}")

        # Check if we have translated lines
        if not translated_lines:
            print("  ⚠ No translated lines available - skipping QA")
        else:
            # 7a. Run DETERMINISTIC checks first (fast, free)
            print("  Running deterministic checks...")
            runner = DeterministicQaRunner(get_default_registry())
            runner.configure_check("line_length", QaSeverity.MAJOR, {"max_length": 256})
            runner.configure_check("empty_translation", QaSeverity.CRITICAL, None)
            runner.configure_check("untranslated_line", QaSeverity.MINOR, None)
            runner.configure_check("whitespace", QaSeverity.MINOR, None)

            deterministic_issues = runner.run_checks(translated_lines)
            print(f"  ✓ Deterministic: {len(deterministic_issues)} issue(s)")

            # 7b. Run LLM-BASED Style Guide Critic (if not mock mode)
            llm_issues: list[QaIssue] = []
            if args.mock:
                print("  ⊘ Mock mode - skipping LLM-based QA")
                print("    Would run:")
                for spec in qa_specs:
                    print(f"      - {spec.name}")
            else:
                try:
                    for spec in qa_specs:
                        print(f"  Running {spec.name} (LLM)...")
                        phase_config = build_phase_config(PhaseName.QA)
                        qa_agent = create_qa_agent_from_profile(
                            profile_path=spec.path,
                            prompts_dir=prompts_dir,
                            config=phase_config,
                            chunk_size=args.chunk_size,
                            source_lang=source_lang,
                            target_lang=target_lang,
                        )

                        qa_input = QaPhaseInput(
                            run_id=uuid7(),
                            target_language=target_lang,
                            source_lines=source_lines,
                            translated_lines=translated_lines,
                            style_guide=style_guide_content,
                        )

                        qa_output = asyncio.run(qa_agent.run(qa_input))
                        llm_issues.extend(qa_output.issues)
                    print(f"  ✓ LLM-based: {len(llm_issues)} issue(s)")
                except Exception as e:
                    print(f"  ⚠ LLM-based QA failed: {e}")
                    traceback.print_exc()

            # 7c. Display ALL issues
            all_issues = list(deterministic_issues) + list(llm_issues)
            print(f"\n  Total QA issues: {len(all_issues)}")

            if all_issues:
                # Display by category
                # Note: use_enum_values=True means these may already be strings
                by_category: dict[str, int] = {}
                for issue in all_issues:
                    cat = (
                        issue.category.value
                        if hasattr(issue.category, "value")
                        else str(issue.category)
                    )
                    by_category[cat] = by_category.get(cat, 0) + 1

                for cat, count in sorted(by_category.items()):
                    print(f"    {cat}: {count}")

                # Show sample issues
                print("\n  Sample issues:")
                for issue in all_issues[:5]:
                    severity = (
                        issue.severity.value
                        if hasattr(issue.severity, "value")
                        else str(issue.severity)
                    )
                    category = (
                        issue.category.value
                        if hasattr(issue.category, "value")
                        else str(issue.category)
                    )
                    message = issue.message[:60] if issue.message else "N/A"
                    print(f"    [{severity}] {category}: {message}...")
                if len(all_issues) > 5:
                    print(f"\n  ... and {len(all_issues) - 5} more")
    else:
        print("\n[7/8] QA phase (skipped)")

    # Step 8: Run Edit Phase (Basic Editor)
    edited_lines: list[TranslatedLine] = []
    if args.phase in ["all", "edit"]:
        print("\n[8/8] Edit phase (Basic Editor)...")

        if not translated_lines:
            print("  ⚠ No translated lines available - skipping edit")
        else:
            try:
                for spec in edit_specs:
                    phase_config = build_phase_config(PhaseName.EDIT)
                    print(f"  Agent: {spec.name}")
                    edit_agent = create_edit_agent_from_profile(
                        profile_path=spec.path,
                        prompts_dir=prompts_dir,
                        config=phase_config,
                        source_lang=source_lang,
                        target_lang=target_lang,
                    )

                    edit_input = EditPhaseInput(
                        run_id=uuid7(),
                        target_language=target_lang,
                        translated_lines=translated_lines,
                        qa_issues=all_issues or None,
                        reviewer_notes=None,
                        scene_summaries=scene_summaries or None,
                        context_notes=None,
                        project_context=None,
                        pretranslation_annotations=pretranslation_annotations or None,
                        term_candidates=term_candidates or None,
                        glossary=None,
                        style_guide=style_guide_content or None,
                    )

                    edit_output = asyncio.run(edit_agent.run(edit_input))
                    edited_lines = edit_output.edited_lines
                    print(f"  ✓ Edited {len(edited_lines)} line(s)")

                    if edit_output.change_log:
                        print(f"  ✓ Applied {len(edit_output.change_log)} change(s)")
                        for change in edit_output.change_log[:5]:
                            print(
                                f"    - {change.line_id}: {change.reason or 'edited'}"
                            )
                    else:
                        print("  ⊘ No edits applied")
            except Exception as exc:
                print(f"  ✗ Edit phase failed: {exc}")
                traceback.print_exc()
                return 1
    else:
        print("\n[8/8] Edit phase (skipped)")

    print("\n" + "=" * 70)
    print("✓ Agent validation complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
