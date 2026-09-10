"""Job batch ownership, constraints, and cascades against CI PostgreSQL."""

import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.database import AsyncSessionFactory
from app.models.job import BatchStatus, Job, JobMatchBatch
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


def make_job(*, user_id: UUID, company: str, title: str) -> Job:
    return Job(
        user_id=user_id,
        company_name=company,
        title=title,
        raw_jd=f"{title} 的原始职位描述，不允许被 AI 覆盖。",
    )


async def test_job_batch_enforces_owner_counts_and_database_cascade() -> None:
    first_email = f"batch-owner-{uuid4().hex}@example.com"
    second_email = f"batch-other-{uuid4().hex}@example.com"

    try:
        async with AsyncSessionFactory() as session:
            first = User(
                email=first_email,
                password_hash="integration-only-hash",
            )
            second = User(
                email=second_email,
                password_hash="integration-only-hash",
            )
            session.add_all([first, second])
            await session.flush()

            batch = JobMatchBatch(
                user_id=first.id,
                name="产品运营岗位比较",
                total_jobs=2,
                jobs=[
                    make_job(user_id=first.id, company="示例甲", title="产品运营"),
                    make_job(user_id=first.id, company="示例乙", title="用户运营"),
                ],
            )
            session.add(batch)
            await session.commit()

            batch_id = batch.id
            first_id = first.id
            second_id = second.id
            assert batch.status is BatchStatus.DRAFT
            assert batch.successful_jobs == 0
            assert batch.failed_jobs == 0
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(Job)
                    .where(Job.batch_id == batch_id)
                )
                == 2
            )

            session.add(
                Job(
                    batch_id=batch_id,
                    user_id=second_id,
                    company_name="越权公司",
                    title="越权职位",
                    raw_jd="该职位不能加入其他用户的批次。",
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

            await session.execute(
                delete(JobMatchBatch).where(JobMatchBatch.id == batch_id)
            )
            await session.commit()

            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(Job)
                    .where(Job.batch_id == batch_id)
                )
                == 0
            )
            assert (
                await session.scalar(
                    select(func.count()).select_from(User).where(User.id == first_id)
                )
                == 1
            )
    finally:
        async with AsyncSessionFactory() as session:
            await session.execute(
                delete(User).where(User.email.in_([first_email, second_email]))
            )
            await session.commit()


async def test_batch_rejects_more_than_five_jobs_and_user_delete_cascades() -> None:
    email = f"batch-limits-{uuid4().hex}@example.com"

    try:
        async with AsyncSessionFactory() as session:
            user = User(email=email, password_hash="integration-only-hash")
            session.add(user)
            await session.commit()
            user_id = user.id

            invalid_batch = JobMatchBatch(user_id=user_id, total_jobs=6)
            session.add(invalid_batch)
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

            batch = JobMatchBatch(
                user_id=user_id,
                total_jobs=1,
                jobs=[
                    make_job(
                        user_id=user_id,
                        company="示例公司",
                        title="数据运营",
                    )
                ],
            )
            session.add(batch)
            await session.commit()
            batch_id = batch.id

            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()

            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(JobMatchBatch)
                    .where(JobMatchBatch.id == batch_id)
                )
                == 0
            )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(Job)
                    .where(Job.batch_id == batch_id)
                )
                == 0
            )
    finally:
        async with AsyncSessionFactory() as session:
            await session.execute(delete(User).where(User.email == email))
            await session.commit()
