"""Batch Job Parser/Matcher orchestration and immutable result persistence."""

from collections.abc import Sequence
from typing import Final
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.client import AIClient
from app.ai.errors import (
    AIConfigurationError,
    AIInputError,
    AIInvalidOutputError,
    AIProviderError,
    AITimeoutError,
)
from app.ai.job_matcher.scoring import (
    MatchRankingCandidate,
    MatchScoringError,
    rank_match_candidates,
    round_score_for_display,
)
from app.ai.job_matcher.service import match_job
from app.ai.job_parser.constants import JOB_PARSER_VERSION
from app.ai.job_parser.schemas import JobParserInput
from app.ai.job_parser.service import parse_job
from app.domain.matching import MatchDimension
from app.models.job import BatchStatus, Job, JobMatchBatch
from app.models.matching import (
    AIStatus,
    JobMatchResult,
    JobParseResult,
    JobRequirement,
    MatchDimensionScore,
    MatchGateCheck,
    MatchRequirementAssessment,
)
from app.schemas.job_match import (
    JobAnalysisStatus,
    JobMatchBatchResultData,
    JobMatchResultItemData,
    MatchResultSummaryData,
)
from app.services.resume import get_resume_master, serialize_resume_master

AI_PROCESSING_ERRORS: Final = (
    AIConfigurationError,
    AIInputError,
    AIInvalidOutputError,
    AIProviderError,
    AITimeoutError,
    MatchScoringError,
)


class BatchNotFoundError(Exception):
    """Raised when the batch does not belong to the current user."""


class ResumeRequiredError(Exception):
    """Raised when analysis has no Resume Master snapshot to use."""


class BatchEmptyError(Exception):
    """Raised when a batch contains no jobs."""


class BatchAnalysisInProgressError(Exception):
    """Raised when another analysis run already owns the batch."""


def _batch_query(*, batch_id: UUID, user_id: UUID):
    return (
        select(JobMatchBatch)
        .where(
            JobMatchBatch.id == batch_id,
            JobMatchBatch.user_id == user_id,
        )
        .execution_options(populate_existing=True)
        .options(
            selectinload(JobMatchBatch.jobs).selectinload(Job.parse_results),
            selectinload(JobMatchBatch.jobs)
            .selectinload(Job.match_results)
            .selectinload(JobMatchResult.dimension_scores),
        )
    )


async def get_job_match_batch(
    session: AsyncSession,
    user_id: UUID,
    batch_id: UUID,
) -> JobMatchBatch:
    """Load a result batch only through its authenticated owner."""

    batch = await session.scalar(_batch_query(batch_id=batch_id, user_id=user_id))
    if batch is None:
        raise BatchNotFoundError
    return batch


def _configured_model(ai_client: AIClient) -> str:
    value = getattr(ai_client, "default_model", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "unknown"


def _latest_by_created_at(records: Sequence):
    if not records:
        return None
    return max(records, key=lambda record: (record.created_at, str(record.id)))


def _error_code(error: Exception) -> str:
    if isinstance(error, MatchScoringError):
        return "AI_INVALID_OUTPUT"
    code = getattr(error, "code", None)
    return code if isinstance(code, str) else "AI_PROVIDER_ERROR"


async def _set_batch_progress(
    session: AsyncSession,
    batch_id: UUID,
    *,
    successful_jobs: int,
    failed_jobs: int,
    status: BatchStatus = BatchStatus.PROCESSING,
) -> None:
    await session.execute(
        update(JobMatchBatch)
        .where(JobMatchBatch.id == batch_id)
        .values(
            status=status,
            successful_jobs=successful_jobs,
            failed_jobs=failed_jobs,
        )
    )
    await session.commit()


def _build_parse_record(job: Job, *, model: str) -> JobParseResult:
    return JobParseResult(
        job_id=job.id,
        status=AIStatus.PENDING,
        prompt_version=JOB_PARSER_VERSION,
        model=model,
    )


async def _parse_and_persist(
    session: AsyncSession,
    job: Job,
    parse_record: JobParseResult,
    ai_client: AIClient,
):
    parse_record.status = AIStatus.PROCESSING
    await session.commit()

    result = await parse_job(
        JobParserInput(
            company_name=job.company_name,
            title=job.title,
            location=job.location,
            raw_jd=job.raw_jd,
        ),
        ai_client,
    )

    parse_record.status = AIStatus.SUCCESS
    parse_record.summary = result.output.role_summary
    parse_record.prompt_version = result.prompt_version
    parse_record.model = result.model
    parse_record.error_code = None
    requirement_records = [
        JobRequirement(
            job_parse_result_id=parse_record.id,
            requirement_type=requirement.requirement_type,
            dimension=requirement.dimension,
            requirement_text=requirement.requirement_text,
            source_quote=requirement.source_quote,
            importance=requirement.importance,
            sort_order=index,
        )
        for index, requirement in enumerate(result.output.requirements, start=1)
    ]
    session.add_all(requirement_records)
    await session.commit()
    requirement_ids = {
        requirement.requirement_key: record.id
        for requirement, record in zip(
            result.output.requirements,
            requirement_records,
            strict=True,
        )
    }
    return result, requirement_ids


def _build_match_result(
    *,
    user_id: UUID,
    job: Job,
    resume_id: UUID,
    resume_snapshot: dict[str, object],
    parse_result_id: UUID,
    requirement_ids: dict[str, UUID],
    parser_output,
    matcher_result,
) -> JobMatchResult:
    assessment_by_key = {
        assessment.requirement_key: assessment
        for assessment in matcher_result.output.requirement_assessments
    }
    requirement_score_by_key = {
        score.requirement_key: score
        for score in matcher_result.score.requirement_scores
    }

    persisted = JobMatchResult(
        user_id=user_id,
        job_id=job.id,
        resume_master_id=resume_id,
        job_parse_result_id=parse_result_id,
        eligibility_status=matcher_result.score.eligibility_status,
        total_score=matcher_result.score.total_score,
        confidence_score=matcher_result.score.confidence_score,
        confidence_level=matcher_result.score.confidence_level,
        recommendation_level=matcher_result.score.recommendation_level,
        recommendation=matcher_result.score.recommendation,
        strengths=list(matcher_result.output.strengths),
        gaps=[gap.model_dump(mode="json") for gap in matcher_result.output.gaps],
        resume_snapshot=resume_snapshot,
        job_snapshot={
            "id": str(job.id),
            "company_name": job.company_name,
            "title": job.title,
            "location": job.location,
            "department": job.department,
            "source_url": job.source_url,
            "raw_jd": job.raw_jd,
            "parsed_job": parser_output.model_dump(mode="json"),
        },
        prompt_version=matcher_result.prompt_version,
        model=matcher_result.model,
    )

    persisted.gate_checks = [
        MatchGateCheck(
            job_requirement_id=requirement_ids[assessment.requirement_key],
            status=assessment.status,
            reason=assessment.reason,
            resume_evidence=[
                evidence.model_dump(mode="json") for evidence in assessment.evidence
            ],
        )
        for assessment in matcher_result.output.gate_assessments
    ]
    persisted.requirement_assessments = [
        MatchRequirementAssessment(
            job_requirement_id=requirement_ids[requirement_key],
            match_level=int(assessment.match_level),
            evidence_grade=assessment.evidence_grade,
            evidence_cap=requirement_score_by_key[requirement_key].evidence_cap,
            weighted_score=requirement_score_by_key[requirement_key].weighted_score,
            assessment_status=assessment.status,
            reason=assessment.reason,
            resume_evidence=[
                evidence.model_dump(mode="json") for evidence in assessment.evidence
            ],
        )
        for requirement_key, assessment in assessment_by_key.items()
    ]
    persisted.dimension_scores = [
        MatchDimensionScore(
            dimension=score.dimension,
            raw_score=score.raw_score,
            max_score=score.max_score,
            normalized_score=score.normalized_score,
        )
        for score in matcher_result.score.dimension_scores
    ]
    return persisted


async def analyze_job_match_batch(
    session: AsyncSession,
    user_id: UUID,
    batch_id: UUID,
    ai_client: AIClient,
) -> JobMatchBatch:
    """Analyze each job independently and append the current run's results."""

    batch = await session.scalar(
        _batch_query(batch_id=batch_id, user_id=user_id).with_for_update()
    )
    if batch is None:
        raise BatchNotFoundError
    if batch.status is BatchStatus.PROCESSING:
        raise BatchAnalysisInProgressError
    if not batch.jobs:
        raise BatchEmptyError

    resume = await get_resume_master(session, user_id)
    if resume is None:
        raise ResumeRequiredError
    resume_data = serialize_resume_master(resume)
    resume_snapshot = resume_data.model_dump(mode="json")

    parse_records = {
        job.id: _build_parse_record(job, model=_configured_model(ai_client))
        for job in batch.jobs
    }
    session.add_all(parse_records.values())
    batch.status = BatchStatus.PROCESSING
    batch.successful_jobs = 0
    batch.failed_jobs = 0
    await session.commit()

    successful_jobs = 0
    failed_jobs = 0
    total_jobs = batch.total_jobs
    try:
        for job in batch.jobs:
            parse_record = parse_records[job.id]
            parser_succeeded = False
            try:
                parser_result, requirement_ids = await _parse_and_persist(
                    session,
                    job,
                    parse_record,
                    ai_client,
                )
                parser_succeeded = True
                matcher_result = await match_job(
                    resume_data,
                    parser_result.output,
                    ai_client,
                )
                persisted = _build_match_result(
                    user_id=user_id,
                    job=job,
                    resume_id=resume_data.id,
                    resume_snapshot=resume_snapshot,
                    parse_result_id=parse_record.id,
                    requirement_ids=requirement_ids,
                    parser_output=parser_result.output,
                    matcher_result=matcher_result,
                )
                session.add(persisted)
                await session.commit()
            except AI_PROCESSING_ERRORS as error:
                if not parser_succeeded:
                    await session.execute(
                        update(JobParseResult)
                        .where(JobParseResult.id == parse_record.id)
                        .values(
                            status=AIStatus.FAILED,
                            error_code=_error_code(error),
                        )
                    )
                    await session.commit()
                failed_jobs += 1
            else:
                successful_jobs += 1

            await _set_batch_progress(
                session,
                batch_id,
                successful_jobs=successful_jobs,
                failed_jobs=failed_jobs,
            )
    except Exception:
        await session.rollback()
        await _set_batch_progress(
            session,
            batch_id,
            successful_jobs=successful_jobs,
            failed_jobs=total_jobs - successful_jobs,
            status=BatchStatus.FAILED,
        )
        raise

    if successful_jobs == total_jobs:
        final_status = BatchStatus.COMPLETED
    elif successful_jobs:
        final_status = BatchStatus.PARTIAL_FAILED
    else:
        final_status = BatchStatus.FAILED
    await _set_batch_progress(
        session,
        batch_id,
        successful_jobs=successful_jobs,
        failed_jobs=failed_jobs,
        status=final_status,
    )
    return await get_job_match_batch(session, user_id, batch_id)


def _responsibility_score(result: JobMatchResult):
    return next(
        (
            score.normalized_score
            for score in result.dimension_scores
            if score.dimension is MatchDimension.RESPONSIBILITY
        ),
        None,
    )


def current_job_match_result(job: Job):
    """Return only the match associated with the job's latest parse run."""

    latest_parse = _latest_by_created_at(job.parse_results)
    latest_match = _latest_by_created_at(job.match_results)
    if (
        latest_parse is None
        or latest_match is None
        or latest_match.job_parse_result_id != latest_parse.id
    ):
        return None
    return latest_match


def _analysis_status(
    batch_status: BatchStatus,
    job: Job,
    result: JobMatchResult | None,
) -> JobAnalysisStatus:
    if result is not None:
        return JobAnalysisStatus.COMPLETED
    latest_parse = _latest_by_created_at(job.parse_results)
    if latest_parse is not None:
        if latest_parse.status is AIStatus.PENDING:
            return JobAnalysisStatus.PENDING
        if latest_parse.status is AIStatus.PROCESSING:
            return JobAnalysisStatus.PARSING
        if (
            latest_parse.status is AIStatus.SUCCESS
            and batch_status is BatchStatus.PROCESSING
        ):
            return JobAnalysisStatus.MATCHING
        if latest_parse.status is AIStatus.FAILED:
            return JobAnalysisStatus.FAILED
    if batch_status is BatchStatus.DRAFT:
        return JobAnalysisStatus.PENDING
    return JobAnalysisStatus.FAILED


def serialize_job_match_batch(batch: JobMatchBatch) -> JobMatchBatchResultData:
    """Serialize current-run results with deterministic normal/blocked ordering."""

    results_by_job = {job.id: current_job_match_result(job) for job in batch.jobs}
    result_by_id = {
        str(result.id): result
        for result in results_by_job.values()
        if result is not None
    }
    ranking = rank_match_candidates(
        [
            MatchRankingCandidate(
                match_id=str(result.id),
                eligibility_status=result.eligibility_status,
                total_score=result.total_score,
                responsibility_score_rate=_responsibility_score(result),
                confidence_score=result.confidence_score,
            )
            for result in result_by_id.values()
        ]
    )
    ranking_metadata = {
        ranked.candidate.match_id: (
            ranked.rank,
            ranked.near_tie_group,
            ranked.is_tied,
        )
        for ranked in ranking.ranked
    }
    ordered_result_ids = [ranked.candidate.match_id for ranked in ranking.ranked]
    ordered_result_ids.extend(candidate.match_id for candidate in ranking.blocked)
    result_order = {
        match_id: index for index, match_id in enumerate(ordered_result_ids)
    }
    original_job_order = {job.id: index for index, job in enumerate(batch.jobs)}
    ordered_jobs = sorted(
        batch.jobs,
        key=lambda job: (
            results_by_job[job.id] is None,
            result_order.get(
                str(results_by_job[job.id].id) if results_by_job[job.id] else "",
                len(result_order),
            ),
            original_job_order[job.id],
        ),
    )

    items: list[JobMatchResultItemData] = []
    for job in ordered_jobs:
        result = results_by_job[job.id]
        summary = None
        if result is not None:
            rank, near_tie_group, is_tied = ranking_metadata.get(
                str(result.id),
                (None, None, False),
            )
            summary = MatchResultSummaryData(
                id=result.id,
                rank=rank,
                near_tie_group=near_tie_group,
                is_tied=is_tied,
                eligibility_status=result.eligibility_status,
                total_score=result.total_score,
                display_score=round_score_for_display(result.total_score),
                confidence_score=result.confidence_score,
                confidence_level=result.confidence_level,
                recommendation_level=result.recommendation_level,
                recommendation=result.recommendation,
                created_at=result.created_at,
            )
        latest_parse = _latest_by_created_at(job.parse_results)
        items.append(
            JobMatchResultItemData(
                job_id=job.id,
                company_name=job.company_name,
                title=job.title,
                location=job.location,
                department=job.department,
                source_url=job.source_url,
                analysis_status=_analysis_status(batch.status, job, result),
                error_code=(
                    latest_parse.error_code
                    if latest_parse is not None
                    and latest_parse.status is AIStatus.FAILED
                    else None
                ),
                result=summary,
            )
        )

    return JobMatchBatchResultData(
        id=batch.id,
        name=batch.name,
        status=batch.status,
        total_jobs=batch.total_jobs,
        successful_jobs=batch.successful_jobs,
        failed_jobs=batch.failed_jobs,
        jobs=items,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
    )
