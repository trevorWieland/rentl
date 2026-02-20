"""API entry point - thin adapter over rentl-core."""

from datetime import UTC, datetime

import uvicorn
from fastapi import FastAPI

from rentl_core import VERSION
from rentl_schemas.responses import ApiResponse, MetaInfo

app = FastAPI(
    title="rentl",
    description="Agentic localization pipeline API",
    version=str(VERSION),
)


@app.get("/health")
async def health() -> ApiResponse[dict[str, str]]:
    """Health check endpoint.

    Returns:
        ApiResponse envelope containing status and version.
    """
    return ApiResponse[dict[str, str]](
        data={"status": "ok", "version": str(VERSION)},
        error=None,
        meta=MetaInfo(
            timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            request_id=None,
        ),
    )


def main() -> None:
    """Run the API server."""
    uvicorn.run("rentl_api.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
