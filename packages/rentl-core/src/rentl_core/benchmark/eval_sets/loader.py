"""Eval set configuration and manifest loader."""

import json
from pathlib import Path

from pydantic import BaseModel, Field


class ScriptSliceConfig(BaseModel):
    """Configuration for a script slice."""

    file: str = Field(description="Script filename")
    line_range: list[int] = Field(description="Line range [start, end] inclusive")


class SliceDefinition(BaseModel):
    """Definition of an evaluation slice."""

    description: str = Field(description="Human-readable description")
    scripts: list[ScriptSliceConfig] = Field(
        description="Scripts and line ranges in this slice"
    )


class SlicesConfig(BaseModel):
    """Collection of slice definitions."""

    slices: dict[str, SliceDefinition] = Field(description="Slice definitions by name")


class ManifestConfig(BaseModel):
    """Eval set manifest with SHA-256 hashes."""

    eval_set_id: str = Field(description="Eval set identifier")
    description: str = Field(description="Human-readable description")
    source: str = Field(description="Source URL or repository")
    scripts: dict[str, str] = Field(
        description="Script filename to SHA-256 hash mapping"
    )


class EvalSetLoader:
    """Loads eval set configuration and manifest files."""

    @staticmethod
    def load_manifest(eval_set_name: str) -> ManifestConfig:
        """Load the manifest for an eval set.

        Args:
            eval_set_name: Name of the eval set (e.g., "katawa_shoujo")

        Returns:
            Loaded manifest configuration

        Raises:
            FileNotFoundError: If manifest file doesn't exist
        """
        manifest_path = Path(__file__).parent / eval_set_name / "manifest.json"

        if not manifest_path.exists():
            raise FileNotFoundError(
                f"Manifest not found for eval set '{eval_set_name}' at {manifest_path}"
            )

        with manifest_path.open() as f:
            data = json.load(f)

        return ManifestConfig.model_validate(data)

    @staticmethod
    def load_slices(eval_set_name: str) -> SlicesConfig:
        """Load the slices configuration for an eval set.

        Args:
            eval_set_name: Name of the eval set (e.g., "katawa_shoujo")

        Returns:
            Loaded slices configuration

        Raises:
            FileNotFoundError: If slices file doesn't exist
        """
        slices_path = Path(__file__).parent / eval_set_name / "slices.json"

        if not slices_path.exists():
            raise FileNotFoundError(
                f"Slices config not found for eval set "
                f"'{eval_set_name}' at {slices_path}"
            )

        with slices_path.open() as f:
            data = json.load(f)

        return SlicesConfig.model_validate(data)

    @staticmethod
    def get_slice_scripts(eval_set_name: str, slice_name: str) -> list[str]:
        """Get the list of script files for a slice.

        Args:
            eval_set_name: Name of the eval set
            slice_name: Name of the slice (e.g., "demo")

        Returns:
            List of script filenames

        Raises:
            KeyError: If slice name doesn't exist
        """
        slices_config = EvalSetLoader.load_slices(eval_set_name)

        if slice_name not in slices_config.slices:
            available = ", ".join(slices_config.slices.keys())
            raise KeyError(
                f"Slice '{slice_name}' not found. Available slices: {available}"
            )

        slice_def = slices_config.slices[slice_name]
        return [script.file for script in slice_def.scripts]
