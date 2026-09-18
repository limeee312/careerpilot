"""Resume Version ownership, snapshot, and cascade invariants."""

import os
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.database import AsyncSessionFactory
from app.domain.matching import (
    ConfidenceLevel,
    EligibilityStatus,
    RecommendationLevel,
)
from app.models.job import Job, JobMatchBatch
from app.models.matching import AIStatus, JobMatchResult, JobParseResult
from app.models.resume import ExperienceType, ResumeExperience, ResumeMaster
from app.models.resume_version import ResumeVersion, ResumeVersionStatus
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


def version_record(*, user_id, resume_id, job_id, result_id) -> ResumeVersion:
    return ResumeVersion(
        user_id=user_id,
        resume_master_id=resume_id,
        job_id=job_id,
        match_result_id=result_id,
        name="示例科技 - 产品运营",
        status=ResumeVersionStatus.SAVED,
        content={
            "summary": "岗位版摘要",
            "education": [],
            "experiences": [],
            "projects": [],
            "skills": [],
        },
        source_resume_snapshot={"experiences": [{"organization": "示例科技"}]},
        source_job_snapshot={
            "company_name": "示例科技",
            "title": "产品运营",
        },
        prompt_version="resume_tailor_v1",
        model="test-model",
    )


async def create_source_graph(email: str):
    async with AsyncSessionFactory() as session:
        user = User(email=email, password_hash="integration-only-hash")
        resume = ResumeMaster(
            user=user,
            summary="原始摘要",
            experiences=[
                ResumeExperience(
                    experience_type=ExperienceType.INTERNSHIP,
                    organization="示例科技",
                    position="产品运营实习生",
                    start_date=date(2026, 1, 1),
                    description="分析用户反馈。",
                    sort_order=0,
                )
            ],
        )
        batch = JobMatchBatch(user=user, total_jobs=1)
        session.add_all([resume, batch])
        await session.flush()
        job = Job(
            batch=batch,
            user_id=user.id,
            company_name="示例科技",
            title="产品运营",
            raw_jd="负责用户分析。",
        )
        parse_result = JobParseResult(
            job=job,
            status=AIStatus.SUCCESS,
            summary="负责用户分析。",
            prompt_version="job_parser_v1",
            model="test-model",
        )
        session.add(parse_result)
        await session.flush()
        result = JobMatchResult(
            user_id=user.id,
            job_id=job.id,
            resume_master_id=resume.id,
            job_parse_result_id=parse_result.id,
            eligibility_status=EligibilityStatus.PASS,
            total_score=Decimal("80.00"),
            confidence_score=Decimal("90.00"),
            confidence_level=ConfidenceLevel.HIGH,
            recommendation_level=RecommendationLevel.STRONG,
            recommendation="建议投递。",
            strengths=[],
            gaps=[],
            resume_snapshot={"summary": "原始摘要"},
            job_snapshot={"company_name": "示例科技", "title": "产品运营"},
            prompt_version="job_matcher_v1",
            model="test-model",
        )
        session.add(result)
        await session.commit()
        return user.id, resume.id, resume.experiences[0].id, job.id, result.id


async def test_saved_snapshot_survives_source_section_deletion() -> None:
    email = f"resume-version-{uuid4().hex}@example.com"
    try:
        (
            user_id,
            resume_id,
            experience_id,
            job_id,
            result_id,
        ) = await create_source_graph(email)
        async with AsyncSessionFactory() as session:
            version = version_record(
                user_id=user_id,
                resume_id=resume_id,
                job_id=job_id,
                result_id=result_id,
            )
            session.add(version)
            await session.commit()
            version_id = version.id

            await session.execute(
                delete(ResumeExperience).where(ResumeExperience.id == experience_id)
            )
            await session.commit()

            saved = await session.get(ResumeVersion, version_id)
            assert saved is not None
            assert saved.source_resume_snapshot["experiences"][0]["organization"] == (
                "示例科技"
            )
    finally:
        async with AsyncSessionFactory() as session:
            await session.execute(delete(User).where(User.email == email))
            await session.commit()


async def test_database_rejects_cross_user_resume_version_links() -> None:
    owner_email = f"version-owner-{uuid4().hex}@example.com"
    other_email = f"version-other-{uuid4().hex}@example.com"
    try:
        owner_id, owner_resume_id, _, job_id, result_id = await create_source_graph(
            owner_email
        )
        other_id, _, _, _, _ = await create_source_graph(other_email)
        async with AsyncSessionFactory() as session:
            invalid = version_record(
                user_id=other_id,
                resume_id=owner_resume_id,
                job_id=job_id,
                result_id=result_id,
            )
            session.add(invalid)
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

            assert (
                await session.scalar(select(func.count()).select_from(ResumeVersion))
                == 0
            )
    finally:
        async with AsyncSessionFactory() as session:
            await session.execute(
                delete(User).where(User.email.in_([owner_email, other_email]))
            )
            await session.commit()
