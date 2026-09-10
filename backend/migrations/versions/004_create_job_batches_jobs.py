"""Create job comparison batches and immutable raw jobs.

Revision ID: 004_create_job_batches_jobs
Revises: 003_create_resume_sections
Create Date: 2026-09-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_create_job_batches_jobs"
down_revision: str | None = "003_create_resume_sections"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

batch_status_enum = postgresql.ENUM(
    "DRAFT",
    "PROCESSING",
    "COMPLETED",
    "PARTIAL_FAILED",
    "FAILED",
    name="batch_status",
    create_type=False,
)


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def upgrade() -> None:
    """Create the batch aggregate and its user-owned raw jobs."""

    batch_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "job_match_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column(
            "status",
            batch_status_enum,
            server_default="DRAFT",
            nullable=False,
        ),
        sa.Column("total_jobs", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "successful_jobs",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("failed_jobs", sa.Integer(), server_default="0", nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "successful_jobs >= 0 AND failed_jobs >= 0",
            name="job_match_batches_result_counts_nonnegative_ck",
        ),
        sa.CheckConstraint(
            "successful_jobs + failed_jobs <= total_jobs",
            name="job_match_batches_result_counts_within_total_ck",
        ),
        sa.CheckConstraint(
            "total_jobs >= 0 AND total_jobs <= 5",
            name="job_match_batches_total_jobs_range_ck",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "user_id",
            name="job_match_batches_id_user_id_key",
        ),
    )
    op.create_index(
        "job_match_batches_user_created_idx",
        "job_match_batches",
        ["user_id", sa.text("created_at DESC")],
        unique=False,
    )

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("department", sa.String(length=200), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("raw_jd", sa.Text(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["batch_id", "user_id"],
            ["job_match_batches.id", "job_match_batches.user_id"],
            name="jobs_batch_owner_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("jobs_batch_id_idx", "jobs", ["batch_id"], unique=False)
    op.create_index("jobs_user_id_idx", "jobs", ["user_id"], unique=False)


def downgrade() -> None:
    """Remove raw jobs, batches, and their enum type."""

    op.drop_index("jobs_user_id_idx", table_name="jobs")
    op.drop_index("jobs_batch_id_idx", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index(
        "job_match_batches_user_created_idx",
        table_name="job_match_batches",
    )
    op.drop_table("job_match_batches")
    batch_status_enum.drop(op.get_bind(), checkfirst=True)
