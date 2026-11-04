"""FastAPI application. Model endpoints arrive with the phase 1 models."""

from fastapi import FastAPI

from nemesis_ml import __version__

app = FastAPI(title="nemesis-ml", version=__version__)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe used by Docker Compose and monitoring."""
    return {"status": "ok", "service": "ml", "version": __version__}
