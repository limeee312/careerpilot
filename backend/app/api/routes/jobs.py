"""Authenticated job detail endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import get_current_user
from app.errors import APIError
from app.models.user import User
from app.schemas.job_detail import JobMatchDetailResponse
from app.services.job_detail import (
    JobNotFoundError,
    MatchResultNotFoundError,
    get_job_match_detail,
    serialize_job_match_detail,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}/match", response_model=JobMatchDetailResponse)
@router.get("/{job_id}", response_model=JobMatchDetailResponse)
async def read_job_match_detail(
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> JobMatchDetailResponse:
    """Return the evidence-rich current match for a user-owned job."""

    try:
        job, result = await get_job_match_detail(
            session,
            current_user.id,
            job_id,
        )
    except JobNotFoundError as error:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="JOB_NOT_FOUND",
            message="职位不存在",
        ) from error
    except MatchResultNotFoundError as error:
        raise APIError(
            status_code=status.HTTP_409_CONFLICT,
            code="MATCH_RESULT_NOT_FOUND",
            message="职位尚无可用匹配结果",
        ) from error
    return JobMatchDetailResponse(data=serialize_job_match_detail(job, result))
