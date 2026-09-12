"""
MediSync — FastAPI Application Entry Point

Registers all routers, middleware, and startup/shutdown handlers.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from db.database import engine
from models.models import Base  # noqa — ensures all models are imported before create_all
from api.routes.auth import router as auth_router
from api.routes.appointments import router as appointments_router
from api.routes.notes import router as notes_router
from api.routes.people import patients_router, physicians_router, admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("medisync")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Runs setup on startup and cleanup on shutdown.
    """
    logger.info("MediSync starting up...")

    # Create database tables if they don't exist
    # In production, use Alembic migrations instead
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified")

    # Seed default data if this is a fresh database
    if os.environ.get("SEED_DATABASE", "true").lower() == "true":
        try:
            from db.seed import seed
            await seed()
        except Exception as e:
            logger.warning(f"Seeding skipped or failed: {e}")

    logger.info("MediSync ready")
    yield

    logger.info("MediSync shutting down")
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-Powered Primary Care Management System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — allow the React frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers under /api/v1
PREFIX = settings.API_V1_PREFIX
app.include_router(auth_router, prefix=PREFIX)
app.include_router(appointments_router, prefix=PREFIX)
app.include_router(notes_router, prefix=PREFIX)
app.include_router(patients_router, prefix=PREFIX)
app.include_router(physicians_router, prefix=PREFIX)
app.include_router(admin_router, prefix=PREFIX)


@app.get("/")
async def root():
    return {
        "service": "MediSync API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "operational",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level="info",
    )
