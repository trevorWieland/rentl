---
standard: async-first-design
category: python
score: 78
importance: High
violations_count: 5
date: 2026-02-18
status: violations-found
---

# Standards Audit: Async-First Design

**Standard:** `python/async-first-design`
**Date:** 2026-02-18
**Score:** 78/100
**Importance:** High

## Summary

The codebase generally uses async patterns and structured concurrency in core runtime and LLM execution paths, but there are real violations where `async` API functions still perform synchronous filesystem I/O. The highest-impact issues are in pipeline orchestration/reporting and agent bootstrap paths because they run inside long-lived async workflows and can block the event loop. The gaps are localized to CLI orchestration helpers, benchmark utilities, and agent initialization/loaders rather than core LLM call primitives.

## Violations

### Violation 1: Synchronous progress/report I/O inside async run pipeline

- **File:** `services/rentl-cli/src/rentl/main.py:2811`
- **Severity:** High
- **Evidence:**
  ```python
  async def _run_pipeline_async(...):
      ...
      progress_updates = _read_progress_updates(bundle.progress_path)
      ...
      _write_run_report(_report_path(...), report_data)
  
  def _read_progress_updates(path: Path) -> list[ProgressUpdate]:
      with path.open("r", encoding="utf-8") as handle:
          for line in handle:
  
  def _write_run_report(path: Path, data: dict[str, JsonValue]) -> None:
      path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
  ```
- **Recommendation:** Convert progress reads/writes to async file I/O (e.g., `aiofiles`/`asyncio.to_thread`) and await them from `_run_pipeline_async` and `_run_phase_async`.

### Violation 2: Async pipeline setup performs synchronous agent/prompt discovery and loading

- **File:** `services/rentl-cli/src/rentl/main.py:2609`
- **Severity:** Critical
- **Evidence:**
  ```python
  def _build_orchestrator(...):
      agent_pools = build_agent_pools(config=config, telemetry_emitter=..., phases=phases)

  def build_agent_pools(...):
      profile_specs = _discover_agent_profile_specs(agents_dir)

  def load_agent_profile(path: Path) -> AgentProfileConfig:
      asyncio.get_running_loop()
      return load_agent_profile_sync(path)

  def load_root_prompt(path: Path) -> RootPromptConfig:
      asyncio.get_running_loop()
      return load_root_prompt_sync(path)
  ```
- **Recommendation:** Make pool construction async (`build_agent_pools` and `load_agent_profile`/`load_root_prompt` call sites) and await true async loaders, or offload sync loader work in threads where initialization is unavoidable.

### Violation 3: Benchmark download async flow uses sync manifest/slice loading and synchronous parser/temp-file operations

- **File:** `services/rentl-cli/src/rentl/main.py:1208`
- **Severity:** Medium
- **Evidence:**
  ```python
  async def _benchmark_download_async(...):
      manifest = EvalSetLoader.load_manifest(normalized_eval_set)
      slices_config = EvalSetLoader.load_slices(normalized_eval_set)

      content_lines = script_path.read_text(encoding="utf-8").splitlines()
      temp_path.write_text(sliced_content, encoding="utf-8")
      parsed = parser.parse_script(temp_path)
      temp_path.unlink()
  ```
  ```python
  class RenpyDialogueParser:
      def parse_script(...):
          content = script_path.read_text(encoding="utf-8")
  ```
- **Recommendation:** Make eval-set manifest/slice loaders and parser I/O async (`anyio/aiofiles` or `asyncio.to_thread`) and avoid blocking inside `_benchmark_download_async`.

### Violation 4: Async benchmark downloader performs blocking file hashing and writes in event-loop context

- **File:** `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:35`
- **Severity:** Medium
- **Evidence:**
  ```python
  async def download_scripts(...):
      if cached_path.exists() and hash_manifest:
          existing_hash = self._compute_sha256(cached_path)
      cached_path.write_bytes(response.content)
      if hash_manifest:
          actual_hash = self._compute_sha256(cached_path)

  def _compute_sha256(self, file_path: Path) -> str:
      with file_path.open("rb") as f:
          for chunk in iter(lambda: f.read(4096), b""):
  ```
- **Recommendation:** Move hash calculation and write operations to `asyncio.to_thread` or provide async-friendly file backend APIs to keep `download_scripts` non-blocking.

### Violation 5: Async `run_doctor` relies on synchronous TOML I/O helpers that can block

- **File:** `packages/rentl-core/src/rentl_core/doctor.py:423`
- **Severity:** Medium
- **Evidence:**
  ```python
  async def run_doctor(...):
      config_valid_check = check_config_valid(config_path)
      if config_valid_check.status == CheckStatus.PASS:
          config = _load_config_sync(config_path)

  def _load_config_sync(config_path: Path) -> RunConfig | None:
      with open(config_path, "rb") as handle:
          payload = tomllib.load(handle)
      if was_migrated:
          backup_path.write_bytes(config_path.read_bytes())
          config_path.write_text(migrated_toml, encoding="utf-8")
  ```
- **Recommendation:** Add async alternatives (`check_config_valid_async`, `_load_config_async`) and have `run_doctor` await them; keep blocking operations in dedicated thread helpers if async backends are not available.

## Compliant Examples

- `packages/rentl-core/src/rentl_core/orchestrator.py:191` — async batch orchestration uses `asyncio.TaskGroup` for concurrent phase execution.
- `packages/rentl-core/src/rentl_core/llm/connection.py:145` — async connection validation uses `asyncio.TaskGroup` across targets.
- `packages/rentl-core/src/rentl_core/benchmark/output_loader.py:29` — async file existence checks and file iteration for output loading.
- `packages/rentl-io/src/rentl_io/storage/filesystem.py:62` — filesystem persistence methods offload blocking file I/O with `asyncio.to_thread`.

## Scoring Rationale

- **Coverage:** Approximately 78% of reviewed async/IO call sites follow async-friendly patterns; the violations are concentrated in CLI orchestration, benchmark bootstrap, and config/diagnostics code.
- **Severity:** High-severity issues exist in pipeline execution and startup paths where blocking I/O can pause the running event loop and delay progress/agent execution.
- **Trend:** Recent core orchestration and LLM connection paths are modern and async-first, while older tooling flows and initialization paths are still synchronous.
- **Risk:** Real risk of degraded throughput and reduced parallelism in async runs, especially for larger workloads and when I/O is frequent.
