"""FastAPI application initialization and configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analysis, health, improvement
from app.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance.

    Args:
        settings: Optional Settings instance. If not provided,
            the cached default settings are loaded.

    Returns:
        Configured FastAPI application.
    """
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Untangle: NLP-based writing analysis and controlled "
            "reconstruction system. Phase 1 provides the backend foundation, "
            "configuration, and health endpoints. Phase 2 provides deterministic "
            "text analysis. Phase 3 provides reviewable text improvement suggestions."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        debug=settings.debug,
    )

    # Enable CORS for local frontend integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Override get_settings dependency with instance settings
    app.dependency_overrides[get_settings] = lambda: settings

    # Register error handlers
    register_exception_handlers(app)

    # Register API routers with configurable prefix
    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(analysis.router, prefix=settings.api_prefix)
    app.include_router(improvement.router, prefix=settings.api_prefix)

    return app


app = create_app()
