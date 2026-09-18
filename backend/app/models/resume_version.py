"""Saved, job-targeted resume snapshots."""

from enum import StrEnum
from uuid import UUID

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, ForeignKeyConstraint, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ResumeVersionStatus(StrEnum):
    """Persistence lifecycle for a targeted resume version."""

    DRAFT = "DRAFT"
    SAVED = "SAVED"


class ResumeVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An immutable-source, user-confirmed targeted resume."""

    __tablename__ = "resume_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["job_id", "user_id"],
            ["jobs.id", "jobs.user_id"],
            ondelete="CASCADE",
            name="resume_versions_job_owner_fkey",
        ),
        ForeignKeyConstraint(
            ["resume_master_id", "user_id"],
            ["resume_masters.id", "resume_masters.user_id"],
            ondelete="CASCADE",
            name="resume_versions_resume_owner_fkey",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    resume_master_id: Mapped[UUID] = mapped_column(nullable=False)
    job_id: Mapped[UUID] = mapped_column(nullable=False)
    match_result_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("job_match_results.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ResumeVersionStatus] = mapped_column(
        SQLAlchemyEnum(
            ResumeVersionStatus,
            name="resume_version_status",
            native_enum=False,
            create_constraint=True,
            length=20,
        ),
        default=ResumeVersionStatus.SAVED,
        server_default=ResumeVersionStatus.SAVED.value,
        nullable=False,
    )
    content: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    source_resume_snapshot: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
    )
    source_job_snapshot: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
    )
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)


Index(
    "resume_versions_user_created_idx",
    ResumeVersion.user_id,
    ResumeVersion.created_at.desc(),
)
Index("resume_versions_job_id_idx", ResumeVersion.job_id)
