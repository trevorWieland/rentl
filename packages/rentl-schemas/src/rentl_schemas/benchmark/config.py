"""Configuration models for benchmark evaluation."""

from pydantic import BaseModel, Field


class SliceConfig(BaseModel):
    """Configuration for a subset slice of an evaluation set."""

    name: str = Field(
        description="Unique identifier for this slice (e.g., 'demo', 'act1')"
    )
    description: str = Field(
        description="Human-readable description of what this slice contains"
    )
    scene_ids: list[str] = Field(
        description="List of scene identifiers to include in this slice"
    )
    line_range: tuple[int, int] | None = Field(
        default=None,
        description=(
            "Optional (start, end) line number range to include from each scene"
        ),
    )
    max_lines: int | None = Field(
        default=None,
        description="Optional maximum number of lines to include from this slice",
    )


class EvalSetConfig(BaseModel):
    """Configuration for an evaluation dataset."""

    name: str = Field(
        description="Unique identifier for this evaluation set (e.g., 'katawa-shoujo')"
    )
    source_language: str = Field(
        description="ISO 639-1 language code for source content (e.g., 'ja')"
    )
    target_language: str = Field(
        description="ISO 639-1 language code for target content (e.g., 'en')"
    )
    download_url: str = Field(
        description=(
            "URL to download source material (e.g., GitHub repo raw URL or archive)"
        )
    )
    hash_manifest_path: str = Field(
        description="Path to committed SHA-256 hash manifest file for validation"
    )
    has_reference: bool = Field(
        description="Whether this eval set includes reference translations for scoring"
    )
    slices: list[SliceConfig] = Field(
        default_factory=list,
        description="Predefined slices of this evaluation set (e.g., demo, full)",
    )


class BenchmarkConfig(BaseModel):
    """Configuration for a benchmark run."""

    eval_set: str = Field(
        description="Name of the evaluation set to use (must exist in registry)"
    )
    slice_name: str | None = Field(
        default=None,
        description="Name of slice to evaluate (None = full eval set)",
    )
    judge_model: str = Field(
        description=(
            "Model identifier for LLM judge "
            "(e.g., 'gpt-4o', 'claude-3-5-sonnet-20241022')"
        )
    )
    judge_base_url: str | None = Field(
        default=None,
        description="Optional base URL for judge model API endpoint",
    )
    output_path: str | None = Field(
        default=None,
        description="Optional path to write JSON benchmark report",
    )
