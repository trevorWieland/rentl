#!/usr/bin/env python3
"""Manual validation script for rentl phase agents.

This script validates the pipeline agents by running them in sequence:
1. Scene Summarizer (context phase) - produces scene summaries
2. Idiom Labeler (pretranslation phase) - identifies idioms using summaries
3. Direct Translator (translate phase) - produces translated lines

Usage:
    uv run python scripts/validate_agents.py [--input FILE] [--model MODEL]

Examples:
    # Validate with mock data (no LLM call)
    uv run python scripts/validate_agents.py --mock

    # Validate with real LLM (requires API key)
    uv run python scripts/validate_agents.py --model gpt-4o-mini

    # Validate with JSONL input file (full pipeline)
    uv run python scripts/validate_agents.py --input sample_scenes.jsonl

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
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid7

# Add package to path for standalone execution
sys.path.insert(
    0, str(Path(__file__).parent.parent / "packages" / "rentl-agents" / "src")
)
sys.path.insert(
    0, str(Path(__file__).parent.parent / "packages" / "rentl-schemas" / "src")
)
sys.path.insert(
    0, str(Path(__file__).parent.parent / "packages" / "rentl-core" / "src")
)

if TYPE_CHECKING:
    from rentl_schemas.phases import (
        ContextPhaseOutput,
        PretranslationAnnotation,
        SceneSummary,
    )


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


def load_config() -> tuple[str, str, str, str, str]:
    """Load configuration from rentl.toml.

    Returns:
        Tuple of (api_key_env, base_url, model_id, source_lang, target_lang).

    Raises:
        ConfigError: If rentl.toml is missing or cannot be parsed.
    """
    rentl_toml_path = Path("rentl.toml")

    if not rentl_toml_path.exists():
        raise ConfigError(
            "rentl.toml not found in current directory.\n"
            "Either create rentl.toml or provide --model and --base-url CLI arguments."
        )

    import tomllib

    try:
        with rentl_toml_path.open("rb") as f:
            config = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"Failed to parse rentl.toml: {e}") from e

    # Extract endpoint settings (required)
    if "endpoint" not in config:
        raise ConfigError(
            "rentl.toml missing [endpoint] section.\n"
            "Required keys: base_url, api_key_env"
        )

    endpoint = config["endpoint"]
    if "base_url" not in endpoint:
        raise ConfigError("rentl.toml [endpoint] missing 'base_url'")
    if "api_key_env" not in endpoint:
        raise ConfigError("rentl.toml [endpoint] missing 'api_key_env'")

    base_url = endpoint["base_url"]
    api_key_env = endpoint["api_key_env"]

    # Extract model settings (required)
    if "pipeline" not in config or "default_model" not in config["pipeline"]:
        raise ConfigError(
            "rentl.toml missing [pipeline.default_model] section.\n"
            "Required keys: model_id"
        )

    default_model = config["pipeline"]["default_model"]
    if "model_id" not in default_model:
        raise ConfigError("rentl.toml [pipeline.default_model] missing 'model_id'")

    model_id = default_model["model_id"]

    # Extract language settings (optional, with defaults)
    source_lang = "ja"
    target_lang = "en"

    if "project" in config and "languages" in config["project"]:
        languages = config["project"]["languages"]
        if "source_language" in languages:
            source_lang = languages["source_language"]
        if languages.get("target_languages"):
            target_lang = languages["target_languages"][0]

    return (
        api_key_env,
        base_url,
        model_id,
        source_lang,
        target_lang,
    )


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
        choices=["all", "context", "pretranslation", "translate", "qa"],
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
    parser.add_argument(
        "--output-mode",
        type=str,
        choices=["auto", "tool", "prompted"],
        default="auto",
        help="Structured output mode: 'auto' (detect from provider), "
        "'prompted' (json_schema, for OpenRouter), "
        "'tool' (tool_choice:required, for LM Studio/OpenAI). Default: auto",
    )

    args = parser.parse_args()

    # Load .env file if present
    from dotenv import load_dotenv

    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path, override=False)

    # Import after path setup
    from rentl_agents import (
        chunk_lines,
        format_lines_for_prompt,
        get_default_agents_dir,
        get_default_prompts_dir,
        load_agent_profile,
    )
    from rentl_agents.context import (
        group_lines_by_scene,
        validate_scene_input,
    )
    from rentl_agents.runtime import ProfileAgentConfig
    from rentl_agents.wiring import (
        create_context_agent_from_profile,
        create_pretranslation_agent_from_profile,
        create_qa_agent_from_profile,
        create_translate_agent_from_profile,
    )
    from rentl_schemas.io import SourceLine, TranslatedLine
    from rentl_schemas.phases import (
        ContextPhaseInput,
        ContextPhaseOutput,
        PretranslationPhaseInput,
        TranslatePhaseInput,
    )

    print("=" * 70)
    print("rentl Agent Validation")
    print("=" * 70)

    # Load configuration
    import os

    # Try to load from rentl.toml first
    config_api_key_env: str | None = None
    config_base_url: str | None = None
    config_model_id: str | None = None
    source_lang = "ja"
    target_lang = "en"

    try:
        (
            config_api_key_env,
            config_base_url,
            config_model_id,
            source_lang,
            target_lang,
        ) = load_config()
        print("\n  ✓ Loaded config from rentl.toml")
    except ConfigError as e:
        # Config loading failed - check if CLI args provide what we need
        if not args.model or not args.base_url:
            print(f"\n  ✗ Configuration error: {e}")
            print("\n  Either fix rentl.toml or provide both --model and --base-url")
            return 1
        print("\n  ⚠ rentl.toml not loaded, using CLI arguments")

    # Resolve final values - CLI args override config
    api_key_env = config_api_key_env or "RENTL_LOCAL_API_KEY"
    base_url = args.base_url or config_base_url
    model_id = args.model or config_model_id

    # Final validation - these must be set
    if not base_url:
        print("\n  ✗ No base_url configured. Set in rentl.toml or use --base-url")
        return 1
    if not model_id:
        print("\n  ✗ No model_id configured. Set in rentl.toml or use --model")
        return 1

    api_key = args.api_key or os.environ.get(api_key_env, "")

    # Step 1: Load input data
    print("\n[1/6] Loading input data...")
    if args.input:
        print(f"  Loading from: {args.input}")
        source_lines: list[SourceLine] = []
        line_counter = 0
        with args.input.open() as f:
            for line in f:
                data = json.loads(line)
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
    print("\n[2/6] Loading agent profiles...")
    agents_dir = get_default_agents_dir()
    prompts_dir = get_default_prompts_dir()

    scene_summarizer_path = agents_dir / "context" / "scene_summarizer.toml"
    idiom_labeler_path = agents_dir / "pretranslation" / "idiom_labeler.toml"
    direct_translator_path = agents_dir / "translate" / "direct_translator.toml"

    try:
        scene_profile = load_agent_profile(scene_summarizer_path)
        name = scene_profile.meta.name
        version = scene_profile.meta.version
        print(f"  ✓ Scene Summarizer: {name} v{version}")

        idiom_profile = load_agent_profile(idiom_labeler_path)
        name = idiom_profile.meta.name
        version = idiom_profile.meta.version
        print(f"  ✓ Idiom Labeler: {name} v{version}")

        translate_profile = load_agent_profile(direct_translator_path)
        name = translate_profile.meta.name
        version = translate_profile.meta.version
        print(f"  ✓ Direct Translator: {name} v{version}")
    except Exception as e:
        print(f"  ✗ Failed to load profiles: {e}")
        return 1

    # Step 3: Validate input for context phase
    print("\n[3/6] Validating input...")
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
        print("\n[4/7] Context phase (mock)...")
        print("  ⊘ Mock mode - skipping LLM calls")

        print("\n[5/7] Pretranslation phase (mock)...")
        print("  ⊘ Mock mode - skipping LLM calls")

        print("\n[6/7] Translate phase (mock)...")
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

        print("\n[7/7] QA phase (mock)...")
        print("  ⊘ Mock mode - showing what would run:")
        print("  • Deterministic: line_length, empty_translation, whitespace")
        print("  • LLM-based: style_guide_critic")
        if args.style_guide.exists():
            print(f"  • Style guide: {args.style_guide}")
        else:
            print(f"  • Style guide: (not found at {args.style_guide})")

        print("\n" + "=" * 70)
        print("✓ Agent validation complete (structure only)")
        return 0

    # Check API key
    if not api_key:
        print(f"\n  ✗ No API key. Set {api_key_env} or use --api-key")
        print("  ⊘ Run with --mock to skip LLM calls")
        return 1

    print(f"\n  Model: {model_id}")
    print(f"  Base URL: {base_url}")
    print(f"  Output mode: {args.output_mode}")
    print(f"  Source: {source_lang} → Target: {target_lang}")

    config = ProfileAgentConfig(
        api_key=api_key,
        base_url=base_url,
        model_id=model_id,
        output_mode=args.output_mode,
    )

    # Step 4: Run Context Phase (Scene Summarizer)
    scene_summaries: list[SceneSummary] = []

    if args.phase in ["all", "context"]:
        print("\n[4/7] Context phase (Scene Summarizer)...")
        concurrency = args.concurrency
        print(f"  Running {len(scene_groups)} scene(s) (concurrency={concurrency})...")

        async def run_scene(
            scene_id: str,
            scene_lines: list[SourceLine],
            semaphore: asyncio.Semaphore,
        ) -> tuple[str, ContextPhaseOutput]:
            """Run summarizer on a single scene.

            Returns:
                Tuple of scene_id and context phase output.
            """
            async with semaphore:
                print(f"    Starting {scene_id} ({len(scene_lines)} lines)...")
                agent = create_context_agent_from_profile(
                    profile_path=scene_summarizer_path,
                    prompts_dir=prompts_dir,
                    config=config,
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

        async def run_all_scenes() -> list[object]:
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
            for result in results:
                if isinstance(result, BaseException):
                    errors.append(
                        result
                        if isinstance(result, Exception)
                        else Exception(str(result))
                    )
                elif isinstance(result, tuple):
                    _, scene_result = result
                    if isinstance(scene_result, ContextPhaseOutput):
                        scene_summaries.extend(scene_result.scene_summaries)

            if errors:
                print(f"  ⚠ {len(errors)} scene(s) failed")
                for err in errors[:3]:
                    print(f"    - {err}")

            print(f"  ✓ Generated {len(scene_summaries)} scene summary(ies)")

            for summary in scene_summaries[:3]:
                print(f"\n  [{summary.scene_id}]")
                print(f"    Summary: {summary.summary[:100]}...")
                print(f"    Characters: {', '.join(summary.characters[:5])}")

        except Exception as e:
            print(f"  ✗ Context phase failed: {e}")
            import traceback

            traceback.print_exc()
            return 1
    else:
        print("\n[4/7] Context phase (skipped)")

    # Step 5: Run Pretranslation Phase (Idiom Labeler)
    pretranslation_annotations: list[PretranslationAnnotation] = []

    if args.phase in ["all", "pretranslation"]:
        print("\n[5/7] Pretranslation phase (Idiom Labeler)...")

        try:
            agent = create_pretranslation_agent_from_profile(
                profile_path=idiom_labeler_path,
                prompts_dir=prompts_dir,
                config=config,
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

        except Exception as e:
            print(f"  ✗ Pretranslation phase failed: {e}")
            import traceback

            traceback.print_exc()
            return 1
    else:
        print("\n[5/7] Pretranslation phase (skipped)")

    # Step 6: Run Translate Phase (Direct Translator)
    translated_lines: list[TranslatedLine] = []

    if args.phase in ["all", "translate"]:
        print("\n[6/7] Translate phase (Direct Translator)...")

        try:
            agent = create_translate_agent_from_profile(
                profile_path=direct_translator_path,
                prompts_dir=prompts_dir,
                config=config,
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

        except Exception as e:
            print(f"  ✗ Translate phase failed: {e}")
            import traceback

            traceback.print_exc()
            return 1
    else:
        print("\n[6/7] Translate phase (skipped)")

    # Step 7: Run QA Phase (Deterministic + LLM-based)
    if args.phase in ["all", "qa"]:
        print("\n[7/7] QA phase...")

        # Load style guide
        style_guide_content = ""
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
            from rentl_core.qa import DeterministicQaRunner, get_default_registry
            from rentl_schemas.primitives import QaSeverity

            runner = DeterministicQaRunner(get_default_registry())
            runner.configure_check("line_length", QaSeverity.MAJOR, {"max_length": 256})
            runner.configure_check("empty_translation", QaSeverity.CRITICAL, None)
            runner.configure_check("whitespace", QaSeverity.MINOR, None)

            deterministic_issues = runner.run_checks(translated_lines)
            print(f"  ✓ Deterministic: {len(deterministic_issues)} issue(s)")

            # 7b. Run LLM-BASED Style Guide Critic (if not mock mode)
            from rentl_schemas.qa import QaIssue

            llm_issues: list[QaIssue] = []
            if args.mock:
                print("  ⊘ Mock mode - skipping LLM-based QA")
                print("    Would run: style_guide_critic")
            else:
                print("  Running style guide critic (LLM)...")
                try:
                    from rentl_schemas.phases import QaPhaseInput

                    style_guide_critic_path = (
                        agents_dir / "qa" / "style_guide_critic.toml"
                    )
                    qa_agent = create_qa_agent_from_profile(
                        profile_path=style_guide_critic_path,
                        prompts_dir=prompts_dir,
                        config=config,
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
                    llm_issues = qa_output.issues
                    print(f"  ✓ LLM-based: {len(llm_issues)} issue(s)")
                except Exception as e:
                    print(f"  ⚠ LLM-based QA failed: {e}")
                    import traceback

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
        print("\n[7/7] QA phase (skipped)")

    print("\n" + "=" * 70)
    print("✓ Agent validation complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
