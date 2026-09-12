"""Match-result snapshots, tenant integrity, constraints, and cascades."""

import os
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.ai.job_parser.schemas import MatchDimension, RequirementType
from app.database import AsyncSessionFactory
from app.models.job import Job, JobMatchBatch
from app.models.matching import (
    AIStatus,
    AssessmentStatus,
    ConfidenceLevel,
    EligibilityStatus,
    EvidenceGrade,
    JobMatchResult,
    JobParseResult,
    JobRequirement,
    MatchDimensionScore,
    MatchGateCheck,
    MatchRequirementAssessment,
    RecommendationLevel,
)
from app.models.resume import ResumeMaster
from app.models.user import User

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.skipif(
        os.getenv("RUN_DB_TESTS") != "1",
        reason="requires an isolated migrated PostgreSQL database",
    ),
]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def build_match_result(
    *,
    user_id: UUID,
    job_id: UUID,
    resume_master_id: UUID,
    parse_result_id: UUID,
    total_score: Decimal = Decimal("82.50"),
) -> JobMatchResult:
    return JobMatchResult(
        user_id=user_id,
        job_id=job_id,
        resume_master_id=resume_master_id,
        job_parse_result_id=parse_result_id,
        eligibility_status=EligibilityStatus.PASS,
        total_score=total_score,
        confidence_score=Decimal("90.00"),
        confidence_level=ConfidenceLevel.HIGH,
        recommendation_level=RecommendationLevel.STRONG,
        recommendation="匹配度较强，可优先准备核心经历。",
        strengths=["用户运营策略有直接证据"],
        gaps=[],
        resume_snapshot={"summary": "原始简历摘要"},
        job_snapshot={"title": "产品运营", "raw_jd": "原始 JD"},
        prompt_version="job_matcher_v1",
        model="test-model",
    )


async def create_source_graph(email: str) -> tuple[UUID, UUID, UUID, UUID, UUID, UUID]:
    async with AsyncSessionFactory() as session:
        user = User(email=email, password_hash="integration-only-hash")
        resume = ResumeMaster(user=user, summary="原始简历摘要")
        batch = JobMatchBatch(user=user, total_jobs=1)
        session.add_all([resume, batch])
        await session.flush()

        job = Job(
            batch=batch,
            user_id=user.id,
            company_name="示例科技",
            title="产品运营",
            raw_jd="负责用户运营策略制定与执行；本科及以上学历。",
        )
        parse_result = JobParseResult(
            job=job,
            status=AIStatus.SUCCESS,
            summary="负责用户运营策略制定与执行。",
            prompt_version="job_parser_v1",
            model="test-model",
        )
        hard = JobRequirement(
            parse_result=parse_result,
            requirement_type=RequirementType.HARD,
            dimension=None,
            requirement_text="本科及以上学历",
            source_quote="本科及以上学历",
            importance=1,
            sort_order=1,
        )
        core = JobRequirement(
            parse_result=parse_result,
            requirement_type=RequirementType.CORE,
            dimension=MatchDimension.RESPONSIBILITY,
            requirement_text="负责用户运营策略制定与执行",
            source_quote="负责用户运营策略制定与执行",
            importance=2,
            sort_order=2,
        )
        session.add(parse_result)
        await session.commit()
        return user.id, resume.id, job.id, parse_result.id, hard.id, core.id


async def test_match_rerun_appends_and_snapshots_survive_source_edits() -> None:
    email = f"match-history-{uuid4().hex}@example.com"

    try:
        (
            user_id,
            resume_id,
            job_id,
            parse_id,
            hard_id,
            core_id,
        ) = await create_source_graph(email)

        async with AsyncSessionFactory() as session:
            first = build_match_result(
                user_id=user_id,
                job_id=job_id,
                resume_master_id=resume_id,
                parse_result_id=parse_id,
            )
            first.gate_checks.append(
                MatchGateCheck(
                    job_requirement_id=hard_id,
                    status=EligibilityStatus.PASS,
                    reason="学历证据明确满足。",
                    resume_evidence=[{"source_type": "education", "quote": "硕士"}],
                )
            )
            first.requirement_assessments.append(
                MatchRequirementAssessment(
                    job_requirement_id=core_id,
                    match_level=3,
                    evidence_grade=EvidenceGrade.B,
                    evidence_cap=3,
                    weighted_score=Decimal("26.250"),
                    assessment_status=AssessmentStatus.MATCHED,
                    reason="有直接用户运营策略经验。",
                    resume_evidence=[
                        {"source_type": "experience", "quote": "制定运营策略"}
                    ],
                )
            )
            first.dimension_scores.append(
                MatchDimensionScore(
                    dimension=MatchDimension.RESPONSIBILITY,
                    raw_score=Decimal("26.250"),
                    max_score=Decimal("35.000"),
                    normalized_score=Decimal("75.000"),
                )
            )
            session.add(first)
            await session.commit()
            first_id = first.id

            resume = await session.get(ResumeMaster, resume_id)
            assert resume is not None
            resume.summary = "一个月后修改的简历摘要"
            await session.commit()

            await session.refresh(first)
            assert first.resume_snapshot == {"summary": "原始简历摘要"}
            assert first.job_snapshot["raw_jd"] == "原始 JD"

            second = build_match_result(
                user_id=user_id,
                job_id=job_id,
                resume_master_id=resume_id,
                parse_result_id=parse_id,
                total_score=Decimal("84.00"),
            )
            session.add(second)
            await session.commit()

            result_ids = list(
                await session.scalars(
                    select(JobMatchResult.id)
                    .where(JobMatchResult.job_id == job_id)
                    .order_by(JobMatchResult.created_at)
                )
            )
            assert len(result_ids) == 2
            assert first_id in result_ids
            assert second.id in result_ids

            await session.execute(delete(Job).where(Job.id == job_id))
            await session.commit()

            for model in (
                JobParseResult,
                JobRequirement,
                JobMatchResult,
                MatchGateCheck,
                MatchRequirementAssessment,
                MatchDimensionScore,
            ):
                assert (
                    await session.scalar(select(func.count()).select_from(model)) == 0
                )
    finally:
        async with AsyncSessionFactory() as session:
            await session.execute(delete(User).where(User.email == email))
            await session.commit()


async def test_match_result_rejects_cross_user_resume_reference() -> None:
    owner_email = f"match-owner-{uuid4().hex}@example.com"
    other_email = f"match-other-{uuid4().hex}@example.com"

    try:
        owner_id, _, job_id, parse_id, _, _ = await create_source_graph(owner_email)
        async with AsyncSessionFactory() as session:
            other = User(
                email=other_email,
                password_hash="integration-only-hash",
                resume_master=ResumeMaster(summary="其他用户简历"),
            )
            session.add(other)
            await session.commit()

            invalid = build_match_result(
                user_id=owner_id,
                job_id=job_id,
                resume_master_id=other.resume_master.id,
                parse_result_id=parse_id,
            )
            session.add(invalid)
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()
    finally:
        async with AsyncSessionFactory() as session:
            await session.execute(
                delete(User).where(User.email.in_([owner_email, other_email]))
            )
            await session.commit()


async def test_database_rejects_invalid_requirement_and_score_ranges() -> None:
    email = f"match-constraints-{uuid4().hex}@example.com"

    try:
        user_id, resume_id, job_id, parse_id, _, _ = await create_source_graph(email)

        async with AsyncSessionFactory() as session:
            invalid_requirement = JobRequirement(
                job_parse_result_id=parse_id,
                requirement_type=RequirementType.HARD,
                dimension=MatchDimension.COMMUNICATION,
                requirement_text="英语可作为工作语言",
                source_quote="英语可作为工作语言",
                importance=1,
                sort_order=3,
            )
            session.add(invalid_requirement)
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

            invalid_score = build_match_result(
                user_id=user_id,
                job_id=job_id,
                resume_master_id=resume_id,
                parse_result_id=parse_id,
                total_score=Decimal("100.01"),
            )
            session.add(invalid_score)
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()
    finally:
        async with AsyncSessionFactory() as session:
            await session.execute(delete(User).where(User.email == email))
            await session.commit()
