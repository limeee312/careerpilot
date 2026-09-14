"""Owner-filtered retrieval and serialization for the job match detail page."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.job_matcher.scoring import round_score_for_display
from app.models.job import Job
from app.models.matching import (
    JobMatchResult,
    JobParseResult,
    MatchGateCheck,
    MatchRequirementAssessment,
)
from app.schemas.job_detail import (
    DimensionScoreDetailData,
    HardGateDetailData,
    JobMatchDetailData,
    JobRequirementData,
    MatchGapDetailData,
    RequirementAssessmentDetailData,
    ResumeEvidenceData,
)
from app.services.match_analysis import current_job_match_result


class JobNotFoundError(Exception):
    """Raised when a job does not exist within the current user's scope."""


class MatchResultNotFoundError(Exception):
    """Raised when the job's current parse run has no successful match."""


def _detail_query(*, job_id: UUID, user_id: UUID):
    return (
        select(Job)
        .where(Job.id == job_id, Job.user_id == user_id)
        .execution_options(populate_existing=True)
        .options(
            selectinload(Job.parse_results).selectinload(JobParseResult.requirements),
            selectinload(Job.match_results).selectinload(
                JobMatchResult.dimension_scores
            ),
            selectinload(Job.match_results)
            .selectinload(JobMatchResult.gate_checks)
            .selectinload(MatchGateCheck.requirement),
            selectinload(Job.match_results)
            .selectinload(JobMatchResult.requirement_assessments)
            .selectinload(MatchRequirementAssessment.requirement),
        )
    )


async def get_job_match_detail(
    session: AsyncSession,
    user_id: UUID,
    job_id: UUID,
) -> tuple[Job, JobMatchResult]:
    """Load only the current successful result for a user-owned job."""

    job = await session.scalar(_detail_query(job_id=job_id, user_id=user_id))
    if job is None:
        raise JobNotFoundError
    result = current_job_match_result(job)
    if result is None:
        raise MatchResultNotFoundError
    return job, result


def _serialize_requirement(requirement) -> JobRequirementData:
    return JobRequirementData(
        id=requirement.id,
        requirement_key=requirement.requirement_key,
        requirement_type=requirement.requirement_type,
        dimension=requirement.dimension,
        requirement_text=requirement.requirement_text,
        source_quote=requirement.source_quote,
        importance=requirement.importance,
    )


def _serialize_evidence(items: list[dict[str, object]]) -> list[ResumeEvidenceData]:
    return [ResumeEvidenceData.model_validate(item) for item in items]


def serialize_job_match_detail(
    job: Job,
    result: JobMatchResult,
) -> JobMatchDetailData:
    """Build the evidence-rich detail without recomputing any AI judgment."""

    parse_result = next(
        record
        for record in job.parse_results
        if record.id == result.job_parse_result_id
    )
    gates = sorted(
        result.gate_checks,
        key=lambda item: item.requirement.sort_order,
    )
    assessments = sorted(
        result.requirement_assessments,
        key=lambda item: item.requirement.sort_order,
    )

    return JobMatchDetailData(
        job_id=job.id,
        batch_id=job.batch_id,
        result_id=result.id,
        company_name=job.company_name,
        title=job.title,
        location=job.location,
        department=job.department,
        source_url=job.source_url,
        role_summary=parse_result.summary,
        eligibility_status=result.eligibility_status,
        total_score=result.total_score,
        display_score=round_score_for_display(result.total_score),
        confidence_score=result.confidence_score,
        confidence_level=result.confidence_level,
        recommendation_level=result.recommendation_level,
        recommendation=result.recommendation,
        strengths=list(result.strengths),
        gaps=[MatchGapDetailData.model_validate(item) for item in result.gaps],
        dimension_scores=[
            DimensionScoreDetailData(
                dimension=item.dimension,
                raw_score=item.raw_score,
                max_score=item.max_score,
                normalized_score=item.normalized_score,
            )
            for item in result.dimension_scores
        ],
        hard_gates=[
            HardGateDetailData(
                requirement=_serialize_requirement(item.requirement),
                status=item.status,
                reason=item.reason,
                evidence=_serialize_evidence(item.resume_evidence),
            )
            for item in gates
        ],
        requirement_assessments=[
            RequirementAssessmentDetailData(
                requirement=_serialize_requirement(item.requirement),
                match_level=item.match_level,
                evidence_grade=item.evidence_grade,
                evidence_cap=item.evidence_cap,
                weighted_score=item.weighted_score,
                status=item.assessment_status,
                reason=item.reason,
                evidence=_serialize_evidence(item.resume_evidence),
            )
            for item in assessments
        ],
        analyzed_at=result.created_at,
    )
