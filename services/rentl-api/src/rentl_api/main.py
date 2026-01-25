"""API entry point - thin adapter over rentl-core."""

import uvicorn
from fastapi import FastAPI

from rentl_core import VERSION

app = FastAPI(
    title="rentl",
    description="Agentic localization pipeline API",
    version=str(VERSION),
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Dictionary containing status and version.
    """
    return {"status": "ok", "version": str(VERSION)}


def main() -> None:
    """Run the API server."""
    uvicorn.run("rentl_api.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
