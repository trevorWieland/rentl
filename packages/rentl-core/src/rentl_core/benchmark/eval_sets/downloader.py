"""Evaluation set downloader for Katawa Shoujo KSRE scripts."""

import hashlib
from collections.abc import Callable
from pathlib import Path

import httpx


class KatawaShoujoDownloader:
    """Downloads Katawa Shoujo script files from KSRE GitHub repository."""

    KSRE_RAW_BASE = (
        "https://raw.githubusercontent.com/fleetingheart/ksre/master/game/tl/jp"
    )

    def __init__(
        self,
        cache_dir: Path | None = None,
        progress_callback: Callable[[str, int, int], None] | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the downloader.

        Args:
            cache_dir: Directory to cache downloaded files
                (default: ~/.cache/rentl/eval_sets/katawa-shoujo)
            progress_callback: Optional callback for progress reporting
                (file_name, current, total)
            http_client: Optional pre-configured HTTP client for dependency
                injection. If None, a client is created per download call.
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "rentl" / "eval_sets" / "katawa-shoujo"
        self.cache_dir = cache_dir
        self.progress_callback = progress_callback
        self._http_client = http_client

    async def download_scripts(
        self,
        script_files: list[str],
        hash_manifest: dict[str, str] | None = None,
    ) -> dict[str, Path]:
        """Download script files from KSRE repository.

        Args:
            script_files: List of .rpy script file names to download
                (e.g., ["script-a1-sunday.rpy"])
            hash_manifest: Optional dict of filename -> SHA-256 hash
                for validation

        Returns:
            Dict mapping filename to local cached path
        """
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        results: dict[str, Path] = {}

        if self._http_client is not None:
            results = await self._download_with_client(
                self._http_client, script_files, hash_manifest
            )
        else:
            async with httpx.AsyncClient(timeout=30.0) as client:
                results = await self._download_with_client(
                    client, script_files, hash_manifest
                )

        return results

    async def _download_with_client(
        self,
        client: httpx.AsyncClient,
        script_files: list[str],
        hash_manifest: dict[str, str] | None,
    ) -> dict[str, Path]:
        """Download scripts using the given HTTP client.

        Args:
            client: HTTP client to use for downloads
            script_files: List of script file names to download
            hash_manifest: Optional hash manifest for validation

        Returns:
            Dict mapping filename to local cached path

        Raises:
            ValueError: If hash validation fails or script not in manifest
        """
        results: dict[str, Path] = {}

        for idx, script_file in enumerate(script_files, 1):
            if self.progress_callback:
                self.progress_callback(script_file, idx, len(script_files))

            cached_path = self.cache_dir / script_file

            # Enforce manifest coverage: all scripts must have hash
            # entry
            if hash_manifest is not None and script_file not in hash_manifest:
                raise ValueError(
                    f"Script '{script_file}' not found in hash manifest. "
                    f"All requested scripts must have a corresponding hash entry."
                )

            # Check if file exists and hash matches (skip download if cached)
            if cached_path.exists() and hash_manifest:
                existing_hash = self._compute_sha256(cached_path)
                expected_hash = hash_manifest.get(script_file)
                if expected_hash and existing_hash == expected_hash:
                    results[script_file] = cached_path
                    continue

            # Download the file
            url = f"{self.KSRE_RAW_BASE}/{script_file}"
            response = await client.get(url)
            response.raise_for_status()

            # Write to cache
            cached_path.write_bytes(response.content)

            # Validate hash if manifest provided
            if hash_manifest:
                actual_hash = self._compute_sha256(cached_path)
                expected_hash = hash_manifest[script_file]  # Already validated above
                if actual_hash != expected_hash:
                    cached_path.unlink()  # Remove invalid file
                    raise ValueError(
                        f"Hash validation failed for {script_file}: "
                        f"expected {expected_hash}, got {actual_hash}"
                    )

            results[script_file] = cached_path

        return results

    def _compute_sha256(self, file_path: Path) -> str:
        """Compute SHA-256 hash of a file.

        Args:
            file_path: Path to the file to hash

        Returns:
            Hexadecimal SHA-256 hash string
        """
        sha256_hash = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
