"""Authenticated endpoints for job batches and their match results."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AIClient, OpenAIResponsesClient
from app.ai.errors import AIConfigurationError
from app.database import get_db_session
from app.dependencies import get_current_user
from app.errors import APIError
from app.models.user import User
from app.schemas.job import JobBatchCreate, JobBatchResponse
from app.schemas.job_match import JobMatchBatchResultResponse
from app.services.job import create_job_batch, serialize_job_batch
from app.services.match_analysis import (
    BatchAnalysisInProgressError,
    BatchEmptyError,
    BatchNotFoundError,
    ResumeRequiredError,
    analyze_job_match_batch,
    get_job_match_batch,
    serialize_job_match_batch,
)

router = APIRouter(prefix="/job-match", tags=["job-match"])


def get_ai_client() -> AIClient:
    """Build the server-side provider client without exposing its credentials."""

    try:
        return OpenAIResponsesClient.from_settings()
    except AIConfigurationError as error:
        raise APIError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="AI_PROVIDER_ERROR",
            message="AI 服务尚未配置",
        ) from error


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


def _raise_batch_api_error(error: Exception) -> None:
    if isinstance(error, BatchNotFoundError):
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="BATCH_NOT_FOUND",
            message="职位批次不存在",
        ) from error
    if isinstance(error, ResumeRequiredError):
        raise APIError(
            status_code=status.HTTP_409_CONFLICT,
            code="RESUME_REQUIRED",
            message="请先创建简历母版",
        ) from error
    if isinstance(error, BatchEmptyError):
        raise APIError(
            status_code=status.HTTP_409_CONFLICT,
            code="BATCH_EMPTY",
            message="职位批次不能为空",
        ) from error
    if isinstance(error, BatchAnalysisInProgressError):
        raise APIError(
            status_code=status.HTTP_409_CONFLICT,
            code="BATCH_PROCESSING",
            message="该职位批次正在分析",
        ) from error
    raise error


@router.post(
    "/batches/{batch_id}/analyze",
    response_model=JobMatchBatchResultResponse,
)
async def analyze_manual_job_batch(
    batch_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    ai_client: Annotated[AIClient, Depends(get_ai_client)],
) -> JobMatchBatchResultResponse:
    """Run Parser and Matcher for every job with per-job failure isolation."""

    try:
        batch = await analyze_job_match_batch(
            session,
            current_user.id,
            batch_id,
            ai_client,
        )
    except (
        BatchNotFoundError,
        ResumeRequiredError,
        BatchEmptyError,
        BatchAnalysisInProgressError,
    ) as error:
        _raise_batch_api_error(error)
    return JobMatchBatchResultResponse(data=serialize_job_match_batch(batch))


@router.get(
    "/batches/{batch_id}/results",
    response_model=JobMatchBatchResultResponse,
)
@router.get(
    "/{batch_id}",
    response_model=JobMatchBatchResultResponse,
)
async def read_job_match_batch(
    batch_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> JobMatchBatchResultResponse:
    """Return current-run results for a user-owned batch."""

    try:
        batch = await get_job_match_batch(session, current_user.id, batch_id)
    except BatchNotFoundError as error:
        _raise_batch_api_error(error)
    return JobMatchBatchResultResponse(data=serialize_job_match_batch(batch))
