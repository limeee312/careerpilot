"""Create immutable resume-to-job match result tables.

Revision ID: 006_create_job_match_tables
Revises: 005_create_job_parse_tables
Create Date: 2026-09-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_create_job_match_tables"
down_revision: str | None = "005_create_job_parse_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

eligibility_status_enum = postgresql.ENUM(
    "PASS",
    "WARN",
    "FAIL",
    name="eligibility_status",
    create_type=False,
)
evidence_grade_enum = postgresql.ENUM(
    "A",
    "B",
    "C",
    "X",
    name="evidence_grade",
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
confidence_level_enum = sa.Enum(
    "HIGH",
    "MEDIUM",
    "LOW",
    name="confidence_level",
    native_enum=False,
    create_constraint=True,
    length=20,
)
recommendation_level_enum = sa.Enum(
    "BLOCKED",
    "PRIORITY",
    "STRONG",
    "SELECTIVE",
    "LOW",
    name="recommendation_level",
    native_enum=False,
    create_constraint=True,
    length=30,
)
assessment_status_enum = sa.Enum(
    "MATCHED",
    "PARTIAL",
    "CONFIRMED_GAP",
    "UNKNOWN",
    name="assessment_status",
    native_enum=False,
    create_constraint=True,
    length=30,
)


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def upgrade() -> None:
    """Create match aggregates, evidence rows, and dimension subtotals."""

    bind = op.get_bind()
    eligibility_status_enum.create(bind, checkfirst=True)
    evidence_grade_enum.create(bind, checkfirst=True)

    op.create_unique_constraint(
        "resume_masters_id_user_id_key",
        "resume_masters",
        ["id", "user_id"],
    )

    op.create_table(
        "job_match_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "resume_master_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "job_parse_result_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("ai_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "eligibility_status",
            eligibility_status_enum,
            nullable=False,
        ),
        sa.Column("total_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column(
            "confidence_score",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
        ),
        sa.Column("confidence_level", confidence_level_enum, nullable=False),
        sa.Column(
            "recommendation_level",
            recommendation_level_enum,
            nullable=False,
        ),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column(
            "strengths",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "gaps",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "resume_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "job_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        _created_at(),
        sa.CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 100",
            name="job_match_results_confidence_score_range_ck",
        ),
        sa.CheckConstraint(
            "total_score >= 0 AND total_score <= 100",
            name="job_match_results_total_score_range_ck",
        ),
        sa.ForeignKeyConstraint(
            ["job_id", "user_id"],
            ["jobs.id", "jobs.user_id"],
            ondelete="CASCADE",
            name="job_match_results_job_owner_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["job_parse_result_id", "job_id"],
            ["job_parse_results.id", "job_parse_results.job_id"],
            ondelete="CASCADE",
            name="job_match_results_parse_job_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["resume_master_id", "user_id"],
            ["resume_masters.id", "resume_masters.user_id"],
            ondelete="CASCADE",
            name="job_match_results_resume_owner_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "job_match_results_job_created_idx",
        "job_match_results",
        ["job_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "job_match_results_user_created_idx",
        "job_match_results",
        ["user_id", sa.text("created_at DESC")],
        unique=False,
    )

    op.create_table(
        "match_gate_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "match_result_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "job_requirement_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("status", eligibility_status_enum, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "resume_evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        _created_at(),
        sa.ForeignKeyConstraint(
            ["job_requirement_id"],
            ["job_requirements.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["match_result_id"],
            ["job_match_results.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "match_result_id",
            "job_requirement_id",
            name="match_gate_checks_result_requirement_key",
        ),
    )
    op.create_index(
        "match_gate_checks_match_result_id_idx",
        "match_gate_checks",
        ["match_result_id"],
        unique=False,
    )

    op.create_table(
        "match_requirement_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "match_result_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "job_requirement_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("match_level", sa.SmallInteger(), nullable=False),
        sa.Column("evidence_grade", evidence_grade_enum, nullable=False),
        sa.Column("evidence_cap", sa.SmallInteger(), nullable=False),
        sa.Column(
            "weighted_score",
            sa.Numeric(precision=6, scale=3),
            nullable=False,
        ),
        sa.Column("assessment_status", assessment_status_enum, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "resume_evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        _created_at(),
        sa.CheckConstraint(
            "evidence_cap >= 0 AND evidence_cap <= 4",
            name="match_requirement_assessments_evidence_cap_range_ck",
        ),
        sa.CheckConstraint(
            "match_level >= 0 AND match_level <= 4",
            name="match_requirement_assessments_match_level_range_ck",
        ),
        sa.CheckConstraint(
            "weighted_score >= 0",
            name="match_requirement_assessments_weighted_score_nonnegative_ck",
        ),
        sa.ForeignKeyConstraint(
            ["job_requirement_id"],
            ["job_requirements.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["match_result_id"],
            ["job_match_results.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "match_result_id",
            "job_requirement_id",
            name="match_requirement_assessments_result_requirement_key",
        ),
    )
    op.create_index(
        "match_requirement_assessments_match_result_id_idx",
        "match_requirement_assessments",
        ["match_result_id"],
        unique=False,
    )

    op.create_table(
        "match_dimension_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "match_result_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("dimension", match_dimension_enum, nullable=False),
        sa.Column(
            "raw_score",
            sa.Numeric(precision=6, scale=3),
            nullable=False,
        ),
        sa.Column(
            "max_score",
            sa.Numeric(precision=6, scale=3),
            nullable=False,
        ),
        sa.Column(
            "normalized_score",
            sa.Numeric(precision=6, scale=3),
            nullable=False,
        ),
        _created_at(),
        sa.CheckConstraint(
            "max_score > 0",
            name="match_dimension_scores_max_score_positive_ck",
        ),
        sa.CheckConstraint(
            "normalized_score >= 0 AND normalized_score <= 100",
            name="match_dimension_scores_normalized_score_range_ck",
        ),
        sa.CheckConstraint(
            "raw_score >= 0 AND raw_score <= max_score",
            name="match_dimension_scores_raw_score_range_ck",
        ),
        sa.ForeignKeyConstraint(
            ["match_result_id"],
            ["job_match_results.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "match_result_id",
            "dimension",
            name="match_dimension_scores_result_dimension_key",
        ),
    )
    op.create_index(
        "match_dimension_scores_match_result_id_idx",
        "match_dimension_scores",
        ["match_result_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove match aggregates, evidence rows, and enum types."""

    op.drop_index(
        "match_dimension_scores_match_result_id_idx",
        table_name="match_dimension_scores",
    )
    op.drop_table("match_dimension_scores")
    op.drop_index(
        "match_requirement_assessments_match_result_id_idx",
        table_name="match_requirement_assessments",
    )
    op.drop_table("match_requirement_assessments")
    op.drop_index(
        "match_gate_checks_match_result_id_idx",
        table_name="match_gate_checks",
    )
    op.drop_table("match_gate_checks")
    op.drop_index(
        "job_match_results_user_created_idx",
        table_name="job_match_results",
    )
    op.drop_index(
        "job_match_results_job_created_idx",
        table_name="job_match_results",
    )
    op.drop_table("job_match_results")
    op.drop_constraint(
        "resume_masters_id_user_id_key",
        "resume_masters",
        type_="unique",
    )

    bind = op.get_bind()
    evidence_grade_enum.drop(bind, checkfirst=True)
    eligibility_status_enum.drop(bind, checkfirst=True)
