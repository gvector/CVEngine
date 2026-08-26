"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from cvengine.api.routes import build_router
from cvengine.observability import setup_logging
from cvengine.services import CVEngine


def create_app(engine: CVEngine | None = None) -> FastAPI:
    """Create the FastAPI application with the /v1 router attached.

    :param engine: optional pre-built engine (created eagerly if omitted)
    :return: the configured application
    """
    setup_logging()
    app = FastAPI(title="CVEngine", version="0.1.0")
    app.state.engine = engine if engine is not None else CVEngine()
    app.include_router(build_router(app.state.engine))
    return app
