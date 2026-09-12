"""Create versioned Job Parser persistence tables.

Revision ID: 005_create_job_parse_tables
Revises: 004_create_job_batches_jobs
Create Date: 2026-09-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_create_job_parse_tables"
down_revision: str | None = "004_create_job_batches_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ai_status_enum = postgresql.ENUM(
    "PENDING",
    "PROCESSING",
    "SUCCESS",
    "FAILED",
    name="ai_status",
    create_type=False,
)
requirement_type_enum = postgresql.ENUM(
    "HARD",
    "CORE",
    "STANDARD",
    "PREFERRED",
    name="requirement_type",
    create_type=False,
)
match_dimension_enum = postgresql.ENUM(
    "RESPONSIBILITY",
    "TOOLS_METHODS",
    "BUSINESS_DOMAIN",
    "OWNERSHIP",
    "OUTCOME",
    "COMMUNICATION",
    name="match_dimension",
    create_type=False,
)


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def upgrade() -> None:
    """Create append-only parser runs and their atomic requirements."""

    bind = op.get_bind()
    ai_status_enum.create(bind, checkfirst=True)
    requirement_type_enum.create(bind, checkfirst=True)
    match_dimension_enum.create(bind, checkfirst=True)

    op.create_unique_constraint(
        "jobs_id_user_id_key",
        "jobs",
        ["id", "user_id"],
    )

    op.create_table(
        "job_parse_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ai_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            ai_status_enum,
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        _created_at(),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "job_id",
            name="job_parse_results_id_job_id_key",
        ),
    )
    op.create_index(
        "job_parse_results_job_created_idx",
        "job_parse_results",
        ["job_id", sa.text("created_at DESC")],
        unique=False,
    )

    op.create_table(
        "job_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "job_parse_result_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("requirement_type", requirement_type_enum, nullable=False),
        sa.Column("dimension", match_dimension_enum, nullable=True),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column("source_quote", sa.Text(), nullable=False),
        sa.Column("importance", sa.SmallInteger(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        _created_at(),
        sa.CheckConstraint(
            "(requirement_type = 'HARD' AND dimension IS NULL) OR "
            "(requirement_type <> 'HARD' AND dimension IS NOT NULL)",
            name="job_requirements_dimension_contract_ck",
        ),
        sa.CheckConstraint(
            "importance IN (1, 2)",
            name="job_requirements_importance_ck",
        ),
        sa.CheckConstraint(
            "sort_order >= 1",
            name="job_requirements_sort_order_positive_ck",
        ),
        sa.ForeignKeyConstraint(
            ["job_parse_result_id"],
            ["job_parse_results.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_parse_result_id",
            "sort_order",
            name="job_requirements_parse_sort_key",
        ),
    )
    op.create_index(
        "job_requirements_parse_result_id_idx",
        "job_requirements",
        ["job_parse_result_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove Job Parser persistence and its enum types."""

    op.drop_index(
        "job_requirements_parse_result_id_idx",
        table_name="job_requirements",
    )
    op.drop_table("job_requirements")
    op.drop_index(
        "job_parse_results_job_created_idx",
        table_name="job_parse_results",
    )
    op.drop_table("job_parse_results")
    op.drop_constraint("jobs_id_user_id_key", "jobs", type_="unique")

    bind = op.get_bind()
    match_dimension_enum.drop(bind, checkfirst=True)
    requirement_type_enum.drop(bind, checkfirst=True)
    ai_status_enum.drop(bind, checkfirst=True)
