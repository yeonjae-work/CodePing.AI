from __future__ import annotations
import logging
from importlib import import_module
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.config.database import create_tables
from shared.config.settings import get_settings
from shared.utils.logging import setup_detailed_logging

"""Main FastAPI application with modular router auto-discovery."""

# Import models to register them with SQLAlchemy
# Note: Models are now in PyPI packages
# from modules.data_storage.models import Event

# Configure detailed logging
setup_detailed_logging()
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title="Git Diff Monitor",
        description="Modular monolith for monitoring git repository changes",
        version="1.0.0",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Auto-discover and include module routers
    _auto_include_routers(app)

    return app


def _auto_include_routers(app: FastAPI) -> None:
    """Include routers from PyPI packages."""

    # List of PyPI packages that provide routers
    pypi_routers = [
        "universal_webhook_receiver.router",
        # Add other PyPI package routers here as needed
    ]

    for router_module_name in pypi_routers:
        try:
            # Import router from PyPI package
            router_module = import_module(router_module_name)

            if hasattr(router_module, "router"):
                app.include_router(router_module.router)
                logger.info("✅ Included router from %s", router_module_name)
            else:
                logger.warning("⚠️  No 'router' found in %s", router_module_name)

        except ImportError as exc:
            logger.warning("⚠️  Failed to import %s: %s", router_module_name, exc)
        except Exception as exc:
            logger.error(
                "❌ Failed to include router from %s: %s", router_module_name, exc
            )


# Create app instance
app = create_app()


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("🚀 Starting Git Diff Monitor...")

    # Create database tables
    try:
        await create_tables()
        logger.info("✅ Database tables created/verified")
    except Exception as exc:
        logger.error("❌ Failed to create database tables: %s", exc)

    # Log configuration
    settings = get_settings()
    logger.info("📊 Database: %s", settings.database_url)
    logger.info("🔧 Celery: %s", settings.celery_broker_url)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("🛑 Shutting down Git Diff Monitor...")


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {"message": "Git Diff Monitor API", "status": "healthy", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9000)
