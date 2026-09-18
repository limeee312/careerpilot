"""Create applications and flexible timeline events.

Revision ID: 008_create_applications
Revises: 007_create_resume_versions
Create Date: 2026-09-18

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008_create_applications"
down_revision: str | None = "007_create_resume_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

application_stage_enum = sa.Enum(
    "APPLICATION",
    "RESUME_SCREEN",
    "ASSESSMENT",
    "WRITTEN_TEST",
    "AI_INTERVIEW",
    "INTERVIEW",
    "OFFER",
    "OTHER",
    name="application_stage",
    native_enum=False,
    create_constraint=True,
    length=30,
)
application_status_enum = sa.Enum(
    "ACTIVE",
    "REJECTED",
    "OFFER",
    "WITHDRAWN",
    name="application_status",
    native_enum=False,
    create_constraint=True,
    length=20,
)
application_event_type_enum = sa.Enum(
    "APPLICATION",
    "RESUME_SCREEN",
    "ASSESSMENT",
    "WRITTEN_TEST",
    "AI_INTERVIEW",
    "INTERVIEW",
    "OFFER",
    "OTHER",
    name="application_event_type",
    native_enum=False,
    create_constraint=True,
    length=30,
)
application_event_outcome_enum = sa.Enum(
    "PENDING",
    "PASSED",
    "FAILED",
    "COMPLETED",
    "CANCELLED",
    name="application_event_outcome",
    native_enum=False,
    create_constraint=True,
    length=30,
)


def upgrade() -> None:
    """Create owner-scoped applications and cascade-owned event timelines."""

    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "resume_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("job_title", sa.String(length=300), nullable=False),
        sa.Column("job_url", sa.Text(), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "current_stage",
            application_stage_enum,
            server_default="APPLICATION",
            nullable=False,
        ),
        sa.Column("current_round", sa.SmallInteger(), nullable=True),
        sa.Column(
            "process_status",
            application_status_enum,
            server_default="ACTIVE",
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "current_round IS NULL OR current_round > 0",
            name="applications_current_round_positive_ck",
        ),
        sa.CheckConstraint(
            "(current_stage = 'INTERVIEW' AND current_round IS NOT NULL) OR "
            "(current_stage <> 'INTERVIEW' AND current_round IS NULL)",
            name="applications_interview_round_ck",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["resume_version_id"],
            ["resume_versions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "applications_user_status_idx",
        "applications",
        ["user_id", "process_status"],
        unique=False,
    )
    op.create_index(
        "applications_user_updated_idx",
        "applications",
        ["user_id", sa.text("updated_at DESC")],
        unique=False,
    )

    op.create_table(
        "application_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "event_type",
            application_event_type_enum,
            nullable=False,
        ),
        sa.Column(
            "custom_event_name",
            sa.String(length=200),
            nullable=True,
        ),
        sa.Column("round_no", sa.SmallInteger(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "outcome",
            application_event_outcome_enum,
            nullable=True,
        ),
        sa.Column("note", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "round_no IS NULL OR round_no > 0",
            name="application_events_round_positive_ck",
        ),
        sa.CheckConstraint(
            "(event_type = 'INTERVIEW' AND round_no IS NOT NULL) OR "
            "(event_type <> 'INTERVIEW' AND round_no IS NULL)",
            name="application_events_interview_round_ck",
        ),
        sa.CheckConstraint(
            "event_type <> 'OTHER' OR "
            "(custom_event_name IS NOT NULL AND "
            "length(trim(custom_event_name)) > 0)",
            name="application_events_other_name_ck",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "application_events_application_occurred_idx",
        "application_events",
        ["application_id", "occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove application timelines and applications."""

    op.drop_index(
        "application_events_application_occurred_idx",
        table_name="application_events",
    )
    op.drop_table("application_events")
    op.drop_index("applications_user_updated_idx", table_name="applications")
    op.drop_index("applications_user_status_idx", table_name="applications")
    op.drop_table("applications")
