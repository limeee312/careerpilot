"""Create structured resume section tables.

Revision ID: 003_create_resume_sections
Revises: 002_create_resume_master
Create Date: 2026-09-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_create_resume_sections"
down_revision: str | None = "002_create_resume_master"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

experience_type_enum = postgresql.ENUM(
    "WORK",
    "INTERNSHIP",
    "CAMPUS",
    "OTHER",
    name="experience_type",
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
    """Create education, experience, project, and skill sections."""

    experience_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "resume_educations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resume_master_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("school", sa.String(length=200), nullable=False),
        sa.Column("degree", sa.String(length=100), nullable=False),
        sa.Column("major", sa.String(length=200), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("gpa", sa.String(length=50), nullable=True),
        sa.Column("courses", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["resume_master_id"],
            ["resume_masters.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "resume_educations_resume_master_id_idx",
        "resume_educations",
        ["resume_master_id"],
        unique=False,
    )

    op.create_table(
        "resume_experiences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resume_master_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("experience_type", experience_type_enum, nullable=False),
        sa.Column("organization", sa.String(length=200), nullable=False),
        sa.Column("position", sa.String(length=200), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "is_current",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("achievements", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["resume_master_id"],
            ["resume_masters.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "resume_experiences_resume_master_id_idx",
        "resume_experiences",
        ["resume_master_id"],
        unique=False,
    )

    op.create_table(
        "resume_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resume_master_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=200), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("background", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("achievements", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["resume_master_id"],
            ["resume_masters.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "resume_projects_resume_master_id_idx",
        "resume_projects",
        ["resume_master_id"],
        unique=False,
    )

    op.create_table(
        "resume_skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resume_master_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_name", sa.String(length=150), nullable=False),
        sa.Column("skill_category", sa.String(length=100), nullable=True),
        sa.Column("proficiency", sa.String(length=50), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["resume_master_id"],
            ["resume_masters.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "resume_skills_resume_master_id_idx",
        "resume_skills",
        ["resume_master_id"],
        unique=False,
    )
    op.create_index(
        "resume_skills_resume_master_name_idx",
        "resume_skills",
        ["resume_master_id", "skill_name"],
        unique=True,
    )


def downgrade() -> None:
    """Remove all structured resume section tables and their enum."""

    op.drop_index(
        "resume_skills_resume_master_name_idx",
        table_name="resume_skills",
    )
    op.drop_index(
        "resume_skills_resume_master_id_idx",
        table_name="resume_skills",
    )
    op.drop_table("resume_skills")
    op.drop_index(
        "resume_projects_resume_master_id_idx",
        table_name="resume_projects",
    )
    op.drop_table("resume_projects")
    op.drop_index(
        "resume_experiences_resume_master_id_idx",
        table_name="resume_experiences",
    )
    op.drop_table("resume_experiences")
    op.drop_index(
        "resume_educations_resume_master_id_idx",
        table_name="resume_educations",
    )
    op.drop_table("resume_educations")
    experience_type_enum.drop(op.get_bind(), checkfirst=True)
