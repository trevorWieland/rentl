"""Secret-scanning validation for rentl config files."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from pathlib import Path

from rentl_schemas.redaction import DEFAULT_PATTERNS


def looks_like_secret(value: str) -> bool:
    """Check if a string looks like a secret value rather than an env var name.

    Args:
        value: String to check

    Returns:
        True if the value matches known secret patterns
    """
    # Env var names are typically UPPERCASE_WITH_UNDERSCORES
    # If it looks like an env var name, it's not a secret
    if value.isupper() and "_" in value and not any(c in value for c in "=-: "):
        return False

    # Check against default secret patterns
    for pattern in DEFAULT_PATTERNS:
        if pattern.compiled and pattern.compiled.search(value):
            return True

    return False


def _toml_get(data: object, *keys: str) -> object:
    """Walk a chain of string keys into nested parsed data.

    Each level must be a Mapping; returns None if any key is missing
    or a level isn't a Mapping.

    Returns:
        The value at the end of the key chain, or None.
    """
    current = data
    for key in keys:
        if not hasattr(current, "get"):
            return None
        current = current.get(key)  # type: ignore[union-attr]
        if current is None:
            return None
    return current


def _toml_get_str(data: object, *keys: str, default: str = "") -> str:
    """Walk keys and return the leaf as a string.

    Returns:
        The string value, or *default* if not found.
    """
    val = _toml_get(data, *keys)
    return str(val) if val is not None else default


def _toml_get_list(data: object, *keys: str) -> list[object]:
    """Walk keys and return the leaf as a list.

    Returns:
        The list value, or empty list if not found.
    """
    val = _toml_get(data, *keys)
    return list(val) if isinstance(val, list) else []


def check_config_secrets(
    config_data: Mapping[str, object],
    project_dir: Path,
) -> list[str]:
    """Scan a parsed config dict and project directory for hardcoded secrets.

    Checks api_key_env values for actual secrets (not env var names) and
    warns if .env files exist and are not in .gitignore.

    Args:
        config_data: Parsed TOML config dictionary
        project_dir: Project root directory (parent of config file)

    Returns:
        List of finding descriptions. Empty list means no issues found.
    """
    findings: list[str] = []

    # Check endpoint.api_key_env
    api_key_env = _toml_get_str(config_data, "endpoint", "api_key_env")
    if api_key_env and looks_like_secret(api_key_env):
        findings.append(
            f"endpoint.api_key_env contains what looks like a secret value: "
            f"'{api_key_env[:20]}...' (should be an env var name like "
            "RENTL_OPENROUTER_API_KEY)"
        )

    # Check endpoints.endpoints[].api_key_env (multi-endpoint configs)
    for idx, entry in enumerate(_toml_get_list(config_data, "endpoints", "endpoints")):
        ep_api_key = _toml_get_str(entry, "api_key_env")
        if ep_api_key and looks_like_secret(ep_api_key):
            provider_name = _toml_get_str(entry, "provider_name", default=f"[{idx}]")
            findings.append(
                f"endpoints.endpoints[{idx}] ({provider_name}) "
                f"api_key_env contains what looks like a secret value: "
                f"'{ep_api_key[:20]}...' (should be an env var name like "
                "RENTL_OPENROUTER_API_KEY)"
            )

    # Check .env files in project directory
    env_file = project_dir / ".env"

    if env_file.exists():
        _check_env_file(env_file, project_dir, findings)

    return findings


def _check_env_file(
    env_file: Path,
    project_dir: Path,
    findings: list[str],
) -> None:
    """Check .env file git-tracking status and append findings."""
    is_git_repo = False
    try:
        # First check if we're in a git repository
        git_check = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        is_git_repo = git_check.returncode == 0

        if is_git_repo:
            # Check if .env is tracked
            result = subprocess.run(
                ["git", "ls-files", "--error-unmatch", ".env"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                check=False,
            )
            # Exit code 0 means file is tracked
            if result.returncode == 0:
                findings.append(
                    f".env file at {env_file} is tracked by git "
                    "(should be in .gitignore to avoid committing secrets)"
                )
            else:
                # .env exists but is not tracked; use git check-ignore
                check_ignore = subprocess.run(
                    ["git", "check-ignore", ".env"],
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                # Exit code 0 means .env is ignored; non-zero means not ignored
                if check_ignore.returncode != 0:
                    findings.append(
                        f".env file exists at {env_file} but is not in "
                        ".gitignore (risk of committing secrets)"
                    )
    except Exception:
        # If git command fails, treat as non-git repo
        is_git_repo = False

    # If not a git repo, fall back to simple .gitignore substring check
    if not is_git_repo:
        gitignore_file = project_dir / ".gitignore"
        if gitignore_file.exists():
            with gitignore_file.open() as gitignore:
                gitignore_contents = gitignore.read()
                # Parse .gitignore line-by-line (no git available for check-ignore)
                gitignore_lines = [
                    line.strip()
                    for line in gitignore_contents.splitlines()
                    if line.strip() and not line.startswith("#")
                ]
                # Match .env exactly or as a pattern (e.g., *.env)
                if ".env" not in gitignore_lines and "*.env" not in gitignore_lines:
                    findings.append(
                        f".env file exists at {env_file} but is not in .gitignore "
                        "(risk of committing secrets)"
                    )
        else:
            findings.append(
                f".env file exists at {env_file} but no .gitignore found "
                "(risk of committing secrets)"
            )
