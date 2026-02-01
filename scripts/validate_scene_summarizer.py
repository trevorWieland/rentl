#!/usr/bin/env python3
"""Manual validation script for Scene Summarizer agent.

This script validates the Scene Summarizer agent by:
1. Loading the agent profile from TOML
2. Creating a context agent
3. Running it against sample input (optional: real JSONL file)
4. Displaying the output

Usage:
    python scripts/validate_scene_summarizer.py [--input FILE] [--model MODEL]

Examples:
    # Validate with mock data (no LLM call)
    python scripts/validate_scene_summarizer.py --mock

    # Validate with real LLM (requires API key)
    python scripts/validate_scene_summarizer.py --model gpt-4o-mini

    # Validate with JSONL input file
    python scripts/validate_scene_summarizer.py --input scenes.jsonl --model gpt-4o-mini
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
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


def main() -> int:
    """Run the validation script.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = argparse.ArgumentParser(
        description="Validate Scene Summarizer agent",
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
        help="Model ID to use (default: from rentl.toml pipeline.default_model.model_id, fallback: gpt-4o-mini)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock data only (no LLM call)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="API key (or set env var from rentl.toml api_key_env, default: RENTL_LOCAL_API_KEY)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="API base URL (default: from rentl.toml endpoint.base_url, fallback: OpenAI)",
    )
    parser.add_argument(
        "--concurrent",
        action="store_true",
        help="Process scenes concurrently (one agent call per scene)",
    )

    args = parser.parse_args()

    # Load .env file if present (same as main CLI)
    from dotenv import load_dotenv

    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path, override=False)

    def normalize_id(value: str) -> str:
        """Normalize ID to match HumanReadableId pattern: ^[a-z]+_[0-9]+$"""
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

    # Import after path setup
    from rentl_agents import (
        get_default_agents_dir,
        get_default_prompts_dir,
        load_agent_profile,
    )
    from rentl_agents.context import (
        format_scene_lines,
        group_lines_by_scene,
        validate_scene_input,
    )
    from rentl_agents.runtime import ProfileAgentConfig
    from rentl_agents.wiring import create_context_agent_from_profile
    from rentl_schemas.io import SourceLine
    from rentl_schemas.phases import ContextPhaseInput

    print("=" * 60)
    print("Scene Summarizer Agent Validation")
    print("=" * 60)

    # Step 1: Load profile
    print("\n[1/4] Loading agent profile...")
    profile_path = get_default_agents_dir() / "context" / "scene_summarizer.toml"
    try:
        profile = load_agent_profile(profile_path)
        print(f"  ✓ Loaded: {profile.meta.name} v{profile.meta.version}")
        print(f"  ✓ Phase: {profile.meta.phase}")
        print(f"  ✓ Output schema: {profile.meta.output_schema}")
        print(f"  ✓ Requires scene_id: {profile.requirements.scene_id_required}")
    except Exception as e:
        print(f"  ✗ Failed to load profile: {e}")
        return 1

    # Step 2: Create sample input or load from file
    print("\n[2/4] Preparing input data...")
    if args.input:
        print(f"  Loading from: {args.input}")
        source_lines = []
        line_counter = 0
        with args.input.open() as f:
            for line in f:
                data = json.loads(line)
                # Normalize IDs to match HumanReadableId pattern
                data["line_id"] = f"line_{line_counter:04d}"
                data["scene_id"] = normalize_id(data.get("scene_id", "scene_0"))
                data["route_id"] = normalize_id(data.get("route_id", "route_0"))
                source_lines.append(SourceLine.model_validate(data))
                line_counter += 1
        print(f"  ✓ Loaded {len(source_lines)} lines")
    else:
        print("  Using sample data...")
        source_lines = [
            SourceLine(
                line_id="line_001",
                text="おはよう、田中さん!",
                speaker="佐藤",
                route_id="main_001",
                scene_id="scene_001",
            ),
            SourceLine(
                line_id="line_002",
                text="おはようございます。今日はいい天気ですね。",
                speaker="田中",
                route_id="main_001",
                scene_id="scene_001",
            ),
            SourceLine(
                line_id="line_003",
                text="そうですね。散歩に行きませんか?",
                speaker="佐藤",
                route_id="main_001",
                scene_id="scene_001",
            ),
        ]
        print(f"  ✓ Created {len(source_lines)} sample lines")

    # Step 3: Validate input
    print("\n[3/4] Validating input...")
    try:
        validate_scene_input(source_lines)
        print("  ✓ All lines have scene_id")
    except Exception as e:
        print(f"  ✗ Validation failed: {e}")
        return 1

    scene_groups = group_lines_by_scene(source_lines)
    print(f"  ✓ Grouped into {len(scene_groups)} scene(s)")

    for scene_id, lines in scene_groups.items():
        print(f"\n  Scene: {scene_id} ({len(lines)} lines)")
        formatted = format_scene_lines(lines)
        for line in formatted.split("\n")[:3]:  # Show first 3 lines
            print(f"    {line}")
        if len(lines) > 3:
            print(f"    ... and {len(lines) - 3} more lines")

    # Step 4: Run agent (if not mock mode)
    print("\n[4/4] Agent execution...")
    if args.mock:
        print("  ⊘ Mock mode - skipping LLM call")
        print("  ✓ Agent validation complete (structure only)")
        return 0

    # Get API key from rentl.toml config or args
    import os

    # Load rentl.toml to get the api_key_env
    rentl_toml_path = Path("rentl.toml")
    api_key_env = "RENTL_LOCAL_API_KEY"  # Default matching rentl.toml.example
    base_url_from_config = None
    model_from_config = None

    if rentl_toml_path.exists():
        try:
            import tomllib

            with rentl_toml_path.open("rb") as f:
                config = tomllib.load(f)
            if "endpoint" in config:
                endpoint = config["endpoint"]
                if "api_key_env" in endpoint:
                    api_key_env = endpoint["api_key_env"]
                if "base_url" in endpoint and not args.base_url:
                    base_url_from_config = endpoint["base_url"]
            if "pipeline" in config and "default_model" in config["pipeline"]:
                default_model = config["pipeline"]["default_model"]
                if "model_id" in default_model and not args.model:
                    model_from_config = default_model["model_id"]
            print(f"  Loaded config from rentl.toml (using {api_key_env})")
        except Exception as e:
            print(f"  ⚠ Could not load rentl.toml: {e}")
            print(f"  Falling back to default env var: {api_key_env}")

    api_key = args.api_key or os.environ.get(api_key_env)
    if not api_key:
        print(f"  ✗ No API key provided. Use --api-key or set {api_key_env}")
        print("  ⊘ Run with --mock to skip LLM call")
        return 1

    # Use base_url and model from config if not overridden by args
    effective_base_url = (
        args.base_url or base_url_from_config or "https://api.openai.com/v1"
    )
    effective_model = args.model or model_from_config or "gpt-4o-mini"

    print(f"  Model: {effective_model}")
    print(f"  Base URL: {effective_base_url}")

    try:
        config = ProfileAgentConfig(
            api_key=api_key,
            base_url=effective_base_url,
            model_id=effective_model,
        )

        if args.concurrent:
            # Process scenes concurrently
            print(f"  Running {len(scene_groups)} scenes concurrently...")

            async def run_scene(scene_id, scene_lines):
                """Run agent on a single scene."""
                agent = create_context_agent_from_profile(
                    profile_path=profile_path,
                    prompts_dir=get_default_prompts_dir(),
                    config=config,
                )
                payload = ContextPhaseInput(
                    run_id=uuid7(),
                    source_lines=scene_lines,
                )
                result = await agent.run(payload)
                return scene_id, result

            async def run_all_scenes():
                tasks = [
                    run_scene(scene_id, lines)
                    for scene_id, lines in scene_groups.items()
                ]
                return await asyncio.gather(*tasks, return_exceptions=True)

            results = asyncio.run(run_all_scenes())

            # Collect all summaries
            all_summaries = []
            errors = []
            for result in results:
                if isinstance(result, Exception):
                    errors.append(result)
                else:
                    scene_id, scene_result = result
                    all_summaries.extend(scene_result.scene_summaries)

            if errors:
                print(f"  ✗ {len(errors)} scene(s) failed:")
                for err in errors:
                    print(f"    - {err}")
                if len(errors) == len(results):
                    return 1

            print("\n" + "=" * 60)
            print("Results (Concurrent Processing)")
            print("=" * 60)

            for summary in all_summaries:
                print(f"\nScene: {summary.scene_id}")
                print(f"Summary: {summary.summary}")
                print(f"Characters: {', '.join(summary.characters)}")

            print(f"\n✓ Processed {len(all_summaries)} scenes concurrently!")
            return 0
        else:
            # Process all scenes together (sequential/aggregated)
            agent = create_context_agent_from_profile(
                profile_path=profile_path,
                prompts_dir=get_default_prompts_dir(),
                config=config,
            )

            payload = ContextPhaseInput(
                run_id=uuid7(),
                source_lines=source_lines,
            )

            print("  Running agent on all scenes...")
            result = asyncio.run(agent.run(payload))

            print("\n" + "=" * 60)
            print("Results")
            print("=" * 60)

            for summary in result.scene_summaries:
                print(f"\nScene: {summary.scene_id}")
                print(f"Summary: {summary.summary}")
                print(f"Characters: {', '.join(summary.characters)}")

            print("\n✓ Agent execution successful!")
            return 0

    except Exception as e:
        print(f"  ✗ Agent execution failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
