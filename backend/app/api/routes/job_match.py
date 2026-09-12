"""Authenticated endpoints for manually imported job batches."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.job import JobBatchCreate, JobBatchResponse
from app.services.job import create_job_batch, serialize_job_batch

router = APIRouter(prefix="/job-match", tags=["job-match"])


@router.post(
    "/batches",
    response_model=JobBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_manual_job_batch(
    payload: JobBatchCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> JobBatchResponse:
    """Create one DRAFT batch containing one to five raw jobs."""

    batch = await create_job_batch(session, current_user.id, payload)
    return JobBatchResponse(data=serialize_job_batch(batch))
