---
standard: api-response-format
category: architecture
score: 92
importance: High
violations_count: 1
date: 2026-02-18
status: violations-found
---

# Standards Audit: API Response Format Envelope Compliance

**Standard:** `architecture/api-response-format`
**Date:** 2026-02-18
**Score:** 92/100
**Importance:** High

## Summary

The codebase has strong adoption of the `ApiResponse`/`ErrorResponse` pydantic envelope for CLI output paths, with centralized helpers in `services/rentl-cli/src/rentl/main.py` and shared schema definitions in `packages/rentl-schemas/src/rentl_schemas/responses.py`. The main gap is a single non-enveloped API endpoint in the FastAPI service (`/health`). That endpoint breaks the project’s stated contract and creates a response-shape inconsistency at the external API boundary.

## Violations

### Violation 1: Health endpoint returns raw dict instead of envelope

- **File:** `services/rentl-api/src/rentl_api/main.py:16`
- **Severity:** High
- **Evidence:**
  ```python
  @app.get("/health")
  async def health() -> dict[str, str]:
      return {"status": "ok", "version": str(VERSION)}
  ```
- **Recommendation:** Return a `ApiResponse` envelope model and include `meta.timestamp` (and optionally request metadata), with `error=None` on success. Example:
  ```python
  from rentl_schemas.responses import ApiResponse, MetaInfo

  @app.get("/health")
  async def health() -> ApiResponse[dict[str, str]]:
      return ApiResponse(
          data={"status": "ok", "version": str(VERSION)},
          error=None,
          meta=MetaInfo(timestamp=_now_timestamp()),
      )
  ```

## Compliant Examples

- `packages/rentl-schemas/src/rentl_schemas/responses.py:53` — Uses a generic `ApiResponse[ResponseData]` schema with typed `data`, `error`, and required `meta`.
- `services/rentl-cli/src/rentl/main.py:761` — `validate-connection` command wraps success payload in `ApiResponse` and prints serialized envelope.
- `services/rentl-cli/src/rentl/main.py:1000` — `run-pipeline` command uses the standardized envelope for success output.
- `services/rentl-cli/src/rentl/main.py:1158` — `status --json` path wraps status output in `ApiResponse`.
- `services/rentl-cli/src/rentl/main.py:3456` — `_error_response` helper enforces `data=None` and `error` payload for failure cases.

## Scoring Rationale

- **Coverage:** About 90%+ of response-producing interfaces that use CLI JSON output and shared response schemas are envelope-compliant; only one active service endpoint violates.
- **Severity:** Single high-severity violation because it creates an inconsistent contract at an external API boundary.
- **Trend:** Newer CLI and schema code consistently follows the standard; the FastAPI service still has legacy-style raw response construction.
- **Risk:** Non-envelope `/health` responses can break generic clients and centralized parsing logic expecting `{data, error, meta}`.
