"""Create saved job-targeted resume versions.

Revision ID: 007_create_resume_versions
Revises: 006_create_job_match_tables
Create Date: 2026-09-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007_create_resume_versions"
down_revision: str | None = "006_create_job_match_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

resume_version_status_enum = sa.Enum(
    "DRAFT",
    "SAVED",
    name="resume_version_status",
    native_enum=False,
    create_constraint=True,
    length=20,
)


def upgrade() -> None:
    """Create version content and immutable source snapshots."""

    op.create_table(
        "resume_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "resume_master_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "match_result_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            resume_version_status_enum,
            server_default="SAVED",
            nullable=False,
        ),
        sa.Column(
            "content",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "source_resume_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "source_job_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["job_id", "user_id"],
            ["jobs.id", "jobs.user_id"],
            ondelete="CASCADE",
            name="resume_versions_job_owner_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["match_result_id"],
            ["job_match_results.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["resume_master_id", "user_id"],
            ["resume_masters.id", "resume_masters.user_id"],
            ondelete="CASCADE",
            name="resume_versions_resume_owner_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "resume_versions_user_created_idx",
        "resume_versions",
        ["user_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "resume_versions_job_id_idx",
        "resume_versions",
        ["job_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove saved resume versions."""

    op.drop_index("resume_versions_job_id_idx", table_name="resume_versions")
    op.drop_index(
        "resume_versions_user_created_idx",
        table_name="resume_versions",
    )
    op.drop_table("resume_versions")
