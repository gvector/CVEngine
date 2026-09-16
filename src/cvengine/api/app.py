"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from cvengine.api.routes import build_router
from cvengine.observability import setup_logging
from cvengine.services import CVEngine


def create_app(engine: CVEngine | None = None, viewer: object | None = None) -> FastAPI:
    """Create the FastAPI application with the /v1 router attached.

    :param engine: optional pre-built engine (created eagerly if omitted)
    :param viewer: optional pre-built viewer browser (defaults to a ChromaBrowser
        when ``viewer_enabled`` is configured)
    :return: the configured application
    """
    setup_logging()
    app = FastAPI(title="CVEngine", version="0.1.0")
    app.state.engine = engine if engine is not None else CVEngine()
    app.include_router(build_router(app.state.engine))

    if app.state.engine.settings.viewer_enabled:
        from cvengine.api.viewer import ChromaBrowser, build_viewer_router

        if viewer is None:
            viewer = ChromaBrowser(
                host=app.state.engine.settings.chroma.host,
                port=app.state.engine.settings.chroma.port,
                provider=app.state.engine.embedding,
            )
        app.include_router(build_viewer_router(viewer))

    return app
