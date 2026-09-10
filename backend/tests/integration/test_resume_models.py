"""Resume persistence invariants against the CI PostgreSQL service."""

import os
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.database import AsyncSessionFactory
from app.models.resume import (
    ExperienceType,
    ResumeEducation,
    ResumeExperience,
    ResumeMaster,
    ResumeProject,
    ResumeSkill,
)
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


async def test_resume_graph_uniqueness_and_database_cascades() -> None:
    email = f"resume-{uuid4().hex}@example.com"
    user = User(email=email, password_hash="integration-only-hash")
    master = ResumeMaster(
        name="Candidate",
        email="resume-contact@example.com",
        summary="Product operations candidate",
        educations=[
            ResumeEducation(
                school="Example University",
                degree="Bachelor",
                major="Information Management",
                start_date=date(2022, 9, 1),
                end_date=date(2026, 6, 30),
                sort_order=0,
            )
        ],
        experiences=[
            ResumeExperience(
                experience_type=ExperienceType.INTERNSHIP,
                organization="Example Company",
                position="Product Operations Intern",
                start_date=date(2025, 6, 1),
                is_current=True,
                description="Analyzed user feedback and improved workflows.",
                sort_order=0,
            )
        ],
        projects=[
            ResumeProject(
                name="Application tracker",
                role="Product owner",
                description="Designed the project requirements and prototype.",
                sort_order=0,
            )
        ],
        skills=[ResumeSkill(skill_name="Python", sort_order=0)],
    )
    user.resume_master = master

    try:
        async with AsyncSessionFactory() as session:
            session.add(user)
            await session.commit()
            user_id = user.id
            master_id = master.id

            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(ResumeMaster)
                    .where(ResumeMaster.id == master_id)
                )
                == 1
            )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(ResumeEducation)
                    .where(ResumeEducation.resume_master_id == master_id)
                )
                == 1
            )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(ResumeExperience)
                    .where(ResumeExperience.resume_master_id == master_id)
                )
                == 1
            )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(ResumeProject)
                    .where(ResumeProject.resume_master_id == master_id)
                )
                == 1
            )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(ResumeSkill)
                    .where(ResumeSkill.resume_master_id == master_id)
                )
                == 1
            )

            session.add(ResumeMaster(user_id=user_id))
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()

            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(ResumeMaster)
                    .where(ResumeMaster.id == master_id)
                )
                == 0
            )
            for model in (
                ResumeEducation,
                ResumeExperience,
                ResumeProject,
                ResumeSkill,
            ):
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(model)
                        .where(model.resume_master_id == master_id)
                    )
                    == 0
                )
    finally:
        async with AsyncSessionFactory() as session:
            await session.execute(delete(User).where(User.email == email))
            await session.commit()
