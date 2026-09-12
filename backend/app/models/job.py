"""Job comparison batch and immutable raw job input models."""

from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.matching import JobMatchResult, JobParseResult
    from app.models.user import User


class BatchStatus(StrEnum):
    """Lifecycle states for one multi-job comparison request."""

    DRAFT = "DRAFT"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    PARTIAL_FAILED = "PARTIAL_FAILED"
    FAILED = "FAILED"


class JobMatchBatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user-owned group of up to five jobs compared together."""

    __tablename__ = "job_match_batches"
    __table_args__ = (
        CheckConstraint(
            "total_jobs >= 0 AND total_jobs <= 5",
            name="job_match_batches_total_jobs_range_ck",
        ),
        CheckConstraint(
            "successful_jobs >= 0 AND failed_jobs >= 0",
            name="job_match_batches_result_counts_nonnegative_ck",
        ),
        CheckConstraint(
            "successful_jobs + failed_jobs <= total_jobs",
            name="job_match_batches_result_counts_within_total_ck",
        ),
        UniqueConstraint(
            "id",
            "user_id",
            name="job_match_batches_id_user_id_key",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[BatchStatus] = mapped_column(
        SQLAlchemyEnum(BatchStatus, name="batch_status"),
        default=BatchStatus.DRAFT,
        server_default=BatchStatus.DRAFT.value,
        nullable=False,
    )
    total_jobs: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    successful_jobs: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    failed_jobs: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="job_match_batches")
    jobs: Mapped[list["Job"]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="Job.created_at",
    )


Index(
    "job_match_batches_user_created_idx",
    JobMatchBatch.user_id,
    JobMatchBatch.created_at.desc(),
)


class Job(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One user-supplied job whose original description remains immutable."""

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "user_id",
            name="jobs_id_user_id_key",
        ),
        ForeignKeyConstraint(
            ["batch_id", "user_id"],
            ["job_match_batches.id", "job_match_batches.user_id"],
            ondelete="CASCADE",
            name="jobs_batch_owner_fkey",
        ),
        Index("jobs_batch_id_idx", "batch_id"),
        Index("jobs_user_id_idx", "user_id"),
    )

    batch_id: Mapped[UUID] = mapped_column(nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    department: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_jd: Mapped[str] = mapped_column(Text, nullable=False)

    batch: Mapped[JobMatchBatch] = relationship(back_populates="jobs")
    parse_results: Mapped[list["JobParseResult"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="JobParseResult.created_at",
    )
    match_results: Mapped[list["JobMatchResult"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="JobMatchResult.created_at",
    )
