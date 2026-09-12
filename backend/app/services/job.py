"""Transactional persistence for manually imported job batches."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobMatchBatch
from app.schemas.job import JobBatchCreate, JobBatchData, JobData


async def create_job_batch(
    session: AsyncSession,
    user_id: UUID,
    payload: JobBatchCreate,
) -> JobMatchBatch:
    """Persist one batch and every raw Job in a single transaction."""

    batch = JobMatchBatch(
        user_id=user_id,
        name=payload.name,
        total_jobs=len(payload.jobs),
        jobs=[
            Job(
                user_id=user_id,
                company_name=item.company_name,
                title=item.title,
                location=item.location,
                department=item.department,
                source_url=str(item.source_url)
                if item.source_url is not None
                else None,
                raw_jd=item.raw_jd,
            )
            for item in payload.jobs
        ],
    )
    session.add(batch)

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return batch


def serialize_job_batch(batch: JobMatchBatch) -> JobBatchData:
    """Return a stable API representation without exposing user ownership IDs."""

    return JobBatchData(
        id=batch.id,
        name=batch.name,
        status=batch.status,
        total_jobs=batch.total_jobs,
        successful_jobs=batch.successful_jobs,
        failed_jobs=batch.failed_jobs,
        jobs=[
            JobData(
                id=job.id,
                company_name=job.company_name,
                title=job.title,
                location=job.location,
                department=job.department,
                source_url=job.source_url,
                raw_jd=job.raw_jd,
                created_at=job.created_at,
                updated_at=job.updated_at,
            )
            for job in batch.jobs
        ],
        created_at=batch.created_at,
        updated_at=batch.updated_at,
    )
