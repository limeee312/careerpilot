"""Generate a reviewable Resume Tailor draft from immutable match snapshots."""

from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

from pydantic import Field, TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AIClient
from app.ai.job_matcher.schemas import MatchGap
from app.ai.job_parser.schemas import JobParserOutput
from app.ai.resume_tailor.service import ResumeTailorResult, tailor_resume
from app.models.job import Job
from app.models.matching import JobMatchResult
from app.schemas.resume import ResumeMasterData
from app.schemas.resume_tailor import ResumeTailorDraftData
from app.services.job_detail import get_job_match_detail


class ResumeTailorSourceInvalidError(Exception):
    """Raised when a successful match lacks a valid immutable source snapshot."""


@dataclass(frozen=True, slots=True)
class GeneratedResumeTailorDraft:
    """Source records and validated AI output before public serialization."""

    job: Job
    match_result: JobMatchResult
    source_resume: ResumeMasterData
    tailor_result: ResumeTailorResult


MatchStrength = Annotated[str, Field(min_length=1)]
MATCH_STRENGTHS_ADAPTER = TypeAdapter(list[MatchStrength])
MATCH_GAPS_ADAPTER = TypeAdapter(list[MatchGap])


def _validate_snapshot(model: type[Any], value: object):
    try:
        return model.model_validate(value)
    except (TypeError, ValidationError) as error:
        raise ResumeTailorSourceInvalidError from error


def _parsed_job_from_result(result: JobMatchResult) -> JobParserOutput:
    snapshot = result.job_snapshot
    if not isinstance(snapshot, dict) or "parsed_job" not in snapshot:
        raise ResumeTailorSourceInvalidError
    return _validate_snapshot(JobParserOutput, snapshot["parsed_job"])


def _match_gaps(result: JobMatchResult) -> list[str]:
    try:
        return [item.gap for item in MATCH_GAPS_ADAPTER.validate_python(result.gaps)]
    except (TypeError, ValidationError) as error:
        raise ResumeTailorSourceInvalidError from error


def _match_strengths(result: JobMatchResult) -> list[str]:
    try:
        return MATCH_STRENGTHS_ADAPTER.validate_python(result.strengths)
    except (TypeError, ValidationError) as error:
        raise ResumeTailorSourceInvalidError from error


async def generate_resume_tailor_draft(
    session: AsyncSession,
    user_id: UUID,
    job_id: UUID,
    ai_client: AIClient,
) -> GeneratedResumeTailorDraft:
    """Tailor the current match snapshot without writing any database row."""

    job, match_result = await get_job_match_detail(session, user_id, job_id)
    source_resume = _validate_snapshot(
        ResumeMasterData,
        match_result.resume_snapshot,
    )
    parsed_job = _parsed_job_from_result(match_result)
    tailor_result = await tailor_resume(
        source_resume,
        parsed_job,
        match_strengths=_match_strengths(match_result),
        match_gaps=_match_gaps(match_result),
        ai_client=ai_client,
    )
    return GeneratedResumeTailorDraft(
        job=job,
        match_result=match_result,
        source_resume=source_resume,
        tailor_result=tailor_result,
    )


def serialize_resume_tailor_draft(
    generated: GeneratedResumeTailorDraft,
) -> ResumeTailorDraftData:
    """Expose the draft with trace metadata needed by CP-024 persistence."""

    result = generated.tailor_result
    return ResumeTailorDraftData(
        job_id=generated.job.id,
        match_result_id=generated.match_result.id,
        resume_master_id=generated.match_result.resume_master_id,
        company_name=generated.job.company_name,
        job_title=generated.job.title,
        source_resume_snapshot=generated.source_resume,
        draft=result.output,
        skill_name=result.skill_name,
        prompt_version=result.prompt_version,
        model=result.model,
        attempts=result.attempts,
    )
