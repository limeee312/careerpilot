"""Batch analysis orchestration tests against CI PostgreSQL with fake AI."""

import os
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select

from app.ai.client import StructuredAIResponse
from app.ai.errors import AIProviderError
from app.ai.job_matcher.schemas import MatcherOutput
from app.ai.job_parser.schemas import JobParserOutput
from app.ai.resume_tailor.schemas import ResumeTailorOutput
from app.database import AsyncSessionFactory
from app.domain.matching import MatchDimension, RequirementType
from app.models.job import BatchStatus, Job, JobMatchBatch
from app.models.matching import (
    AIStatus,
    JobMatchResult,
    JobParseResult,
    JobRequirement,
    MatchDimensionScore,
    MatchRequirementAssessment,
)
from app.models.resume import ExperienceType, ResumeExperience, ResumeMaster
from app.models.user import User
from app.schemas.job_match import JobAnalysisStatus
from app.services.job_detail import (
    JobNotFoundError,
    get_job_match_detail,
    serialize_job_match_detail,
)
from app.services.match_analysis import (
    analyze_job_match_batch,
    serialize_job_match_batch,
)
from app.services.resume_tailor import generate_resume_tailor_draft

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


class StubAIClient:
    default_model = "fake-model"

    def __init__(self, *, failing_company: str | None = None) -> None:
        self.failing_company = failing_company
        self.calls = 0

    async def generate_structured(
        self,
        *,
        system_prompt,
        input_data,
        response_model,
        model=None,
    ):
        del system_prompt, model
        self.calls += 1
        if response_model is JobParserOutput:
            if input_data.company_name == self.failing_company:
                raise AIProviderError("simulated non-retryable failure")
            output = JobParserOutput.model_validate(
                {
                    "role_summary": "负责用户运营数据分析。",
                    "responsibilities_summary": ["分析用户行为数据"],
                    "requirements": [
                        {
                            "requirement_key": "R1",
                            "requirement_type": RequirementType.CORE,
                            "dimension": MatchDimension.RESPONSIBILITY,
                            "requirement_text": "分析用户行为数据并推动运营优化",
                            "source_quote": "分析用户行为数据并推动运营优化",
                            "importance": 2,
                        }
                    ],
                    "business_domains": ["用户运营"],
                    "tools": [],
                    "ambiguous_points": [],
                }
            )
        elif response_model is MatcherOutput:
            evidence = next(
                item
                for item in input_data.resume_evidence
                if item.source_type == "experience"
            )
            output = MatcherOutput.model_validate(
                {
                    "gate_assessments": [],
                    "requirement_assessments": [
                        {
                            "requirement_key": "R1",
                            "match_level": 3,
                            "evidence_grade": "B",
                            "status": "MATCHED",
                            "reason": "有直接的数据分析与运营优化经验。",
                            "evidence": [
                                {
                                    "source_type": "experience",
                                    "source_id": evidence.source_id,
                                    "source_quote": "分析用户行为数据并推动运营优化",
                                }
                            ],
                        }
                    ],
                    "strengths": ["用户行为分析有直接证据"],
                    "gaps": [],
                    "overall_reasoning": "核心职责存在可定位的直接证据。",
                }
            )
        elif response_model is ResumeTailorOutput:
            experience = input_data.experiences[0]
            output = ResumeTailorOutput.model_validate(
                {
                    "professional_summary": "具备用户行为分析与运营优化实践。",
                    "experiences": [
                        {
                            "source_id": experience.source_id,
                            "include": True,
                            "order": 1,
                            "bullets": [
                                {
                                    "text": "分析用户行为数据并推动运营优化。",
                                    "evidence_refs": [
                                        {
                                            "source_field": "description",
                                            "source_quote": (
                                                "分析用户行为数据并推动运营优化"
                                            ),
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                    "projects": [],
                    "skill_order": [skill.source_id for skill in input_data.skills],
                    "improvement_suggestions": [],
                    "warnings": [],
                }
            )
        else:  # pragma: no cover - protects the fake's test contract.
            raise AssertionError(f"unexpected response model: {response_model}")
        return StructuredAIResponse(output=output, model=self.default_model)


async def create_analysis_graph(email: str, companies: list[str]):
    async with AsyncSessionFactory() as session:
        user = User(email=email, password_hash="integration-only-hash")
        resume = ResumeMaster(
            user=user,
            summary="关注数据驱动的用户运营。",
            experiences=[
                ResumeExperience(
                    experience_type=ExperienceType.INTERNSHIP,
                    organization="实习公司",
                    position="产品运营实习生",
                    start_date=date(2025, 6, 1),
                    end_date=date(2025, 9, 1),
                    is_current=False,
                    description="分析用户行为数据并推动运营优化",
                    achievements=None,
                    sort_order=0,
                )
            ],
        )
        batch = JobMatchBatch(
            user=user,
            name="集成测试批次",
            total_jobs=len(companies),
        )
        session.add_all([resume, batch])
        await session.flush()
        session.add_all(
            [
                Job(
                    batch_id=batch.id,
                    user_id=user.id,
                    company_name=company,
                    title="用户运营",
                    raw_jd=(
                        "负责制定用户运营策略，分析用户行为数据并推动运营优化，"
                        "联动产品和研发团队推进项目落地并持续复盘迭代。"
                    ),
                )
                for company in companies
            ]
        )
        await session.commit()
        return user.id, batch.id


async def test_batch_analysis_preserves_successes_when_one_job_fails() -> None:
    email = f"analysis-partial-{uuid4().hex}@example.com"
    try:
        user_id, batch_id = await create_analysis_graph(
            email,
            ["成功公司", "失败公司"],
        )
        async with AsyncSessionFactory() as session:
            analyzed = await analyze_job_match_batch(
                session,
                user_id,
                batch_id,
                StubAIClient(failing_company="失败公司"),
            )
            data = serialize_job_match_batch(analyzed)

        assert data.status is BatchStatus.PARTIAL_FAILED
        assert data.successful_jobs == 1
        assert data.failed_jobs == 1
        by_company = {job.company_name: job for job in data.jobs}
        assert by_company["成功公司"].analysis_status is JobAnalysisStatus.COMPLETED
        assert by_company["成功公司"].result is not None
        assert by_company["成功公司"].result.display_score == 75
        assert by_company["失败公司"].analysis_status is JobAnalysisStatus.FAILED
        assert by_company["失败公司"].error_code == "AI_PROVIDER_ERROR"

        async with AsyncSessionFactory() as session:
            assert (
                await session.scalar(select(func.count()).select_from(JobParseResult))
                == 2
            )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(JobParseResult)
                    .where(JobParseResult.status == AIStatus.FAILED)
                )
                == 1
            )
            for model in (
                JobMatchResult,
                JobRequirement,
                MatchRequirementAssessment,
                MatchDimensionScore,
            ):
                assert (
                    await session.scalar(select(func.count()).select_from(model)) == 1
                )
    finally:
        async with AsyncSessionFactory() as session:
            await session.execute(delete(User).where(User.email == email))
            await session.commit()


async def test_reanalysis_appends_a_new_match_result() -> None:
    email = f"analysis-rerun-{uuid4().hex}@example.com"
    try:
        user_id, batch_id = await create_analysis_graph(email, ["重复分析公司"])
        async with AsyncSessionFactory() as session:
            client = StubAIClient()
            first = await analyze_job_match_batch(
                session,
                user_id,
                batch_id,
                client,
            )
            assert first.status is BatchStatus.COMPLETED
            second = await analyze_job_match_batch(
                session,
                user_id,
                batch_id,
                client,
            )
            data = serialize_job_match_batch(second)

        assert data.status is BatchStatus.COMPLETED
        assert data.successful_jobs == 1
        assert data.jobs[0].result is not None
        assert client.calls == 4
        async with AsyncSessionFactory() as session:
            assert (
                await session.scalar(select(func.count()).select_from(JobParseResult))
                == 2
            )
            assert (
                await session.scalar(select(func.count()).select_from(JobMatchResult))
                == 2
            )
    finally:
        async with AsyncSessionFactory() as session:
            await session.execute(delete(User).where(User.email == email))
            await session.commit()


async def test_job_detail_is_owner_filtered_and_eagerly_loads_evidence() -> None:
    email = f"job-detail-{uuid4().hex}@example.com"
    try:
        user_id, batch_id = await create_analysis_graph(email, ["详情测试公司"])
        async with AsyncSessionFactory() as session:
            analyzed = await analyze_job_match_batch(
                session,
                user_id,
                batch_id,
                StubAIClient(),
            )
            job_id = analyzed.jobs[0].id

        async with AsyncSessionFactory() as session:
            job, result = await get_job_match_detail(session, user_id, job_id)
            data = serialize_job_match_detail(job, result)

        assert data.company_name == "详情测试公司"
        assert data.display_score == 75
        assert data.requirement_assessments[0].evidence[0].source_type == "experience"
        assert data.dimension_scores[0].dimension is MatchDimension.RESPONSIBILITY

        async with AsyncSessionFactory() as session:
            with pytest.raises(JobNotFoundError):
                await get_job_match_detail(session, uuid4(), job_id)
    finally:
        async with AsyncSessionFactory() as session:
            await session.execute(delete(User).where(User.email == email))
            await session.commit()


async def test_resume_tailor_returns_a_draft_without_mutating_source_rows() -> None:
    email = f"resume-tailor-{uuid4().hex}@example.com"
    try:
        user_id, batch_id = await create_analysis_graph(email, ["简历优化公司"])
        client = StubAIClient()
        async with AsyncSessionFactory() as session:
            analyzed = await analyze_job_match_batch(
                session,
                user_id,
                batch_id,
                client,
            )
            job_id = analyzed.jobs[0].id
            result_count_before = await session.scalar(
                select(func.count()).select_from(JobMatchResult)
            )

            generated = await generate_resume_tailor_draft(
                session,
                user_id,
                job_id,
                client,
            )
            result_count_after = await session.scalar(
                select(func.count()).select_from(JobMatchResult)
            )

        assert generated.job.id == job_id
        assert generated.tailor_result.prompt_version == "resume_tailor_v1"
        assert generated.tailor_result.output.experiences[0].bullets[0].text == (
            "分析用户行为数据并推动运营优化。"
        )
        assert result_count_after == result_count_before
        assert client.calls == 3
    finally:
        async with AsyncSessionFactory() as session:
            await session.execute(delete(User).where(User.email == email))
            await session.commit()
