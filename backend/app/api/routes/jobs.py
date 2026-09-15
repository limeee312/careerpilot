"""Authenticated job detail endpoints."""

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AIClient, OpenAIResponsesClient
from app.ai.errors import (
    AIConfigurationError,
    AIInputError,
    AIInvalidOutputError,
    AIProviderError,
    AITimeoutError,
)
from app.database import get_db_session
from app.dependencies import get_current_user
from app.errors import APIError
from app.models.user import User
from app.schemas.job_detail import JobMatchDetailResponse
from app.schemas.resume_tailor import ResumeTailorDraftResponse
from app.services.job_detail import (
    JobNotFoundError,
    MatchResultNotFoundError,
    get_job_match_detail,
    serialize_job_match_detail,
)
from app.services.resume_tailor import (
    ResumeTailorSourceInvalidError,
    generate_resume_tailor_draft,
    serialize_resume_tailor_draft,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_resume_tailor_ai_client() -> AIClient:
    """Build the server-side provider client for direct Tailor requests."""

    try:
        return OpenAIResponsesClient.from_settings()
    except AIConfigurationError as error:
        raise APIError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="AI_PROVIDER_ERROR",
            message="AI 服务尚未配置",
        ) from error


def _raise_job_detail_error(error: Exception) -> NoReturn:
    if isinstance(error, JobNotFoundError):
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="JOB_NOT_FOUND",
            message="职位不存在",
        ) from error
    if isinstance(error, MatchResultNotFoundError):
        raise APIError(
            status_code=status.HTTP_409_CONFLICT,
            code="MATCH_RESULT_NOT_FOUND",
            message="职位尚无可用匹配结果",
        ) from error
    raise error


def _raise_tailor_ai_error(error: Exception) -> NoReturn:
    if isinstance(error, (AIInputError, ResumeTailorSourceInvalidError)):
        raise APIError(
            status_code=status.HTTP_409_CONFLICT,
            code="AI_INVALID_INPUT",
            message="当前匹配结果缺少可用于简历优化的完整快照",
        ) from error
    if isinstance(error, AITimeoutError):
        raise APIError(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            code="AI_TIMEOUT",
            message="AI 简历优化超时，请稍后重试",
        ) from error
    if isinstance(error, AIInvalidOutputError):
        raise APIError(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="AI_INVALID_OUTPUT",
            message="AI 返回的简历草稿未通过真实性校验",
        ) from error
    if isinstance(error, AIProviderError):
        raise APIError(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="AI_PROVIDER_ERROR",
            message="AI 服务暂时不可用",
        ) from error
    raise error


@router.post(
    "/{job_id}/resume-tailor",
    response_model=ResumeTailorDraftResponse,
)
async def create_resume_tailor_draft(
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    ai_client: Annotated[AIClient, Depends(get_resume_tailor_ai_client)],
) -> ResumeTailorDraftResponse:
    """Generate a user-reviewable draft without persisting a Resume Version."""

    try:
        generated = await generate_resume_tailor_draft(
            session,
            current_user.id,
            job_id,
            ai_client,
        )
    except (JobNotFoundError, MatchResultNotFoundError) as error:
        _raise_job_detail_error(error)
    except (
        AIInputError,
        AIInvalidOutputError,
        AIProviderError,
        AITimeoutError,
        ResumeTailorSourceInvalidError,
    ) as error:
        _raise_tailor_ai_error(error)
    return ResumeTailorDraftResponse(data=serialize_resume_tailor_draft(generated))


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
    except (JobNotFoundError, MatchResultNotFoundError) as error:
        _raise_job_detail_error(error)
    return JobMatchDetailResponse(data=serialize_job_match_detail(job, result))
