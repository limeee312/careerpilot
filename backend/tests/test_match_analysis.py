"""Match batch result serialization and current-run selection tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from app.domain.matching import (
    ConfidenceLevel,
    EligibilityStatus,
    MatchDimension,
    RecommendationLevel,
)
from app.models.job import BatchStatus, Job, JobMatchBatch
from app.models.matching import (
    AIStatus,
    JobMatchResult,
    JobParseResult,
    MatchDimensionScore,
)
from app.schemas.job_match import JobAnalysisStatus
from app.services.match_analysis import serialize_job_match_batch

NOW = datetime(2026, 9, 14, 8, tzinfo=UTC)
USER_ID = uuid4()
RESUME_ID = uuid4()


def build_job_result(
    *,
    company: str,
    score: str,
    responsibility: str,
    eligibility: EligibilityStatus = EligibilityStatus.PASS,
    offset: int = 0,
) -> Job:
    job_id = uuid4()
    parse_id = uuid4()
    created_at = NOW + timedelta(seconds=offset)
    parse_result = JobParseResult(
        id=parse_id,
        job_id=job_id,
        status=AIStatus.SUCCESS,
        summary="负责用户运营。",
        prompt_version="job_parser_v1",
        model="test-model",
        created_at=created_at,
    )
    match_result = JobMatchResult(
        id=uuid4(),
        user_id=USER_ID,
        job_id=job_id,
        resume_master_id=RESUME_ID,
        job_parse_result_id=parse_id,
        eligibility_status=eligibility,
        total_score=Decimal(score),
        confidence_score=Decimal("90.00"),
        confidence_level=ConfidenceLevel.HIGH,
        recommendation_level=(
            RecommendationLevel.BLOCKED
            if eligibility is EligibilityStatus.FAIL
            else RecommendationLevel.STRONG
        ),
        recommendation="测试推荐",
        strengths=[],
        gaps=[],
        resume_snapshot={},
        job_snapshot={},
        prompt_version="job_matcher_v1",
        model="test-model",
        created_at=created_at,
        dimension_scores=[
            MatchDimensionScore(
                id=uuid4(),
                dimension=MatchDimension.RESPONSIBILITY,
                raw_score=Decimal(responsibility),
                max_score=Decimal("100.000"),
                normalized_score=Decimal(responsibility),
                created_at=created_at,
            )
        ],
    )
    return Job(
        id=job_id,
        batch_id=uuid4(),
        user_id=USER_ID,
        company_name=company,
        title="产品运营",
        raw_jd="测试岗位描述" * 20,
        created_at=created_at,
        updated_at=created_at,
        parse_results=[parse_result],
        match_results=[match_result],
    )


def build_batch(jobs: list[Job]) -> JobMatchBatch:
    batch_id = uuid4()
    for job in jobs:
        job.batch_id = batch_id
    return JobMatchBatch(
        id=batch_id,
        user_id=USER_ID,
        name="秋招岗位",
        status=BatchStatus.COMPLETED,
        total_jobs=len(jobs),
        successful_jobs=len(jobs),
        failed_jobs=0,
        jobs=jobs,
        created_at=NOW,
        updated_at=NOW,
    )


def test_result_serialization_applies_near_tie_rules_and_blocks_failures() -> None:
    high_total = build_job_result(
        company="总分更高",
        score="84.00",
        responsibility="70.000",
    )
    high_responsibility = build_job_result(
        company="职责更匹配",
        score="82.00",
        responsibility="90.000",
        offset=1,
    )
    blocked = build_job_result(
        company="硬条件冲突",
        score="95.00",
        responsibility="100.000",
        eligibility=EligibilityStatus.FAIL,
        offset=2,
    )

    data = serialize_job_match_batch(
        build_batch([high_total, high_responsibility, blocked])
    )

    assert [item.company_name for item in data.jobs] == [
        "职责更匹配",
        "总分更高",
        "硬条件冲突",
    ]
    assert [item.result.rank if item.result else None for item in data.jobs] == [
        1,
        2,
        None,
    ]
    assert data.jobs[0].result is not None
    assert data.jobs[0].result.display_score == 82
    assert data.jobs[2].result is not None
    assert data.jobs[2].result.recommendation_level is RecommendationLevel.BLOCKED


def test_new_failed_parse_hides_an_older_successful_result() -> None:
    job = build_job_result(
        company="重新分析失败",
        score="80.00",
        responsibility="80.000",
    )
    job.parse_results.append(
        JobParseResult(
            id=uuid4(),
            job_id=job.id,
            status=AIStatus.FAILED,
            prompt_version="job_parser_v1",
            model="test-model",
            error_code="AI_TIMEOUT",
            created_at=NOW + timedelta(minutes=1),
        )
    )
    batch = build_batch([job])
    batch.status = BatchStatus.FAILED
    batch.successful_jobs = 0
    batch.failed_jobs = 1

    data = serialize_job_match_batch(batch)

    assert data.jobs[0].analysis_status is JobAnalysisStatus.FAILED
    assert data.jobs[0].error_code == "AI_TIMEOUT"
    assert data.jobs[0].result is None


def test_draft_batch_reports_pending_jobs_without_results() -> None:
    job = Job(
        id=uuid4(),
        batch_id=uuid4(),
        user_id=USER_ID,
        company_name="待分析公司",
        title="用户运营",
        raw_jd="测试岗位描述" * 20,
        created_at=NOW,
        updated_at=NOW,
    )
    batch = build_batch([job])
    batch.status = BatchStatus.DRAFT
    batch.successful_jobs = 0

    data = serialize_job_match_batch(batch)

    assert data.jobs[0].analysis_status is JobAnalysisStatus.PENDING
    assert data.jobs[0].result is None
