# References for Integration Test Suite

## Similar Implementations

### Existing validate-connection Integration Test

- **Location:** `tests/integration/cli/test_validate_connection.py`
- **Relevance:** Only existing integration test in the codebase; demonstrates CLI testing patterns
- **Key patterns:**
  - Uses `typer.testing.CliRunner` for CLI invocation
  - Uses `tmp_path` fixture for isolated file system
  - Uses `monkeypatch` to mock LLM runtime and environment variables
  - Creates test config with `_write_connection_config()` helper
  - Validates JSON response structure with `ApiResponse` envelope
  - Uses docstring-style Given/When/Then (to be refactored to pytest-bdd)

**Example pattern (to be refactored to BDD):**

```python
class _FakeRuntime:
    async def run_prompt(
        self, request: LlmPromptRequest, *, api_key: str
    ) -> LlmPromptResponse:
        return LlmPromptResponse(
            model_id=request.runtime.model.model_id,
            output_text="ok",
        )

def test_validate_connection_returns_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Given configured endpoints, when validating, then results are returned."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    config_path = _write_connection_config(tmp_path, workspace_dir)
    
    monkeypatch.setenv("PRIMARY_KEY", "fake-key")
    monkeypatch.setattr(cli_main, "_build_llm_runtime", lambda: _FakeRuntime())
    
    result = runner.invoke(
        cli_main.app, ["validate-connection", "--config", str(config_path)]
    )
    
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["error"] is None
```

### CLI Main Module

- **Location:** `services/rentl-cli/src/rentl_cli/main.py`
- **Relevance:** Source of all CLI commands to test
- **Key commands:**
  - `version` - Display version (line 126)
  - `validate-connection` - Validate BYOK endpoints (line 132)
  - `export` - Export translated lines (line 153)
  - `run-pipeline` - Run full pipeline (line 195)
  - `run-phase` - Run single phase (line 218)

### Storage Adapters

- **Location:** `packages/rentl-io/src/rentl_io/storage/`
- **Relevance:** FileSystem storage implementations to test
- **Key files:**
  - `filesystem.py` - FileSystemRunStateStore, FileSystemArtifactStore, FileSystemLogStore

### Storage Protocols

- **Location:** `packages/rentl-core/src/rentl_core/ports/storage.py`
- **Relevance:** Protocol definitions for storage adapter compliance tests
- **Key protocols:**
  - `RunStateStoreProtocol`
  - `ArtifactStoreProtocol`
  - `LogStoreProtocol`

### BYOK Runtime

- **Location:** `packages/rentl-llm/src/rentl_llm/openai_runtime.py`
- **Relevance:** OpenAI-compatible runtime to test with mock HTTP
- **Key class:** `OpenAICompatibleRuntime`
