"""Versioned API router."""

from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.job_match import router as job_match_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.resume import router as resume_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(job_match_router)
api_router.include_router(jobs_router)
api_router.include_router(resume_router)
