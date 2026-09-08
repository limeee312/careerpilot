"""CareerPilot FastAPI application."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.database import check_database_connection, dispose_database_engine
from app.errors import install_exception_handlers


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Release shared resources when the application stops."""

    yield
    await dispose_database_engine()


settings = get_settings()

app = FastAPI(
    title="CareerPilot API",
    description="Backend API for 职航 CareerPilot.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
install_exception_handlers(app)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness probe that does not depend on external services."""

    return {
        "status": "ok",
        "service": "careerpilot-backend",
        "environment": settings.app_env,
    }


@app.get("/health/ready", tags=["system"])
async def readiness() -> dict[str, str]:
    """Readiness probe that verifies the PostgreSQL connection."""

    if not await check_database_connection():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        )
    return {"status": "ready", "database": "connected"}
