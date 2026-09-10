"""Structured resume master and section persistence models."""

from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    false,
)
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class ExperienceType(StrEnum):
    """Supported categories for a candidate's experience."""

    WORK = "WORK"
    INTERNSHIP = "INTERNSHIP"
    CAMPUS = "CAMPUS"
    OTHER = "OTHER"


class ResumeMaster(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The single editable source resume owned by one user."""

    __tablename__ = "resume_masters"
    __table_args__ = (Index("resume_masters_user_id_idx", "user_id", unique=True),)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    job_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="resume_master")
    educations: Mapped[list["ResumeEducation"]] = relationship(
        back_populates="resume_master",
        cascade="all, delete-orphan",
        order_by="ResumeEducation.sort_order",
    )
    experiences: Mapped[list["ResumeExperience"]] = relationship(
        back_populates="resume_master",
        cascade="all, delete-orphan",
        order_by="ResumeExperience.sort_order",
    )
    projects: Mapped[list["ResumeProject"]] = relationship(
        back_populates="resume_master",
        cascade="all, delete-orphan",
        order_by="ResumeProject.sort_order",
    )
    skills: Mapped[list["ResumeSkill"]] = relationship(
        back_populates="resume_master",
        cascade="all, delete-orphan",
        order_by="ResumeSkill.sort_order",
    )


class ResumeEducation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One education item belonging to a resume master."""

    __tablename__ = "resume_educations"
    __table_args__ = (
        Index("resume_educations_resume_master_id_idx", "resume_master_id"),
    )

    resume_master_id: Mapped[UUID] = mapped_column(
        ForeignKey("resume_masters.id", ondelete="CASCADE"),
        nullable=False,
    )
    school: Mapped[str] = mapped_column(String(200), nullable=False)
    degree: Mapped[str] = mapped_column(String(100), nullable=False)
    major: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    gpa: Mapped[str | None] = mapped_column(String(50), nullable=True)
    courses: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    resume_master: Mapped["ResumeMaster"] = relationship(back_populates="educations")


class ResumeExperience(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One original work, internship, campus, or other experience."""

    __tablename__ = "resume_experiences"
    __table_args__ = (
        Index("resume_experiences_resume_master_id_idx", "resume_master_id"),
    )

    resume_master_id: Mapped[UUID] = mapped_column(
        ForeignKey("resume_masters.id", ondelete="CASCADE"),
        nullable=False,
    )
    experience_type: Mapped[ExperienceType] = mapped_column(
        SQLAlchemyEnum(ExperienceType, name="experience_type"),
        nullable=False,
    )
    organization: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    achievements: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    resume_master: Mapped["ResumeMaster"] = relationship(back_populates="experiences")


class ResumeProject(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One project item belonging to a resume master."""

    __tablename__ = "resume_projects"
    __table_args__ = (
        Index("resume_projects_resume_master_id_idx", "resume_master_id"),
    )

    resume_master_id: Mapped[UUID] = mapped_column(
        ForeignKey("resume_masters.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str | None] = mapped_column(String(200), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    background: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    achievements: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    resume_master: Mapped["ResumeMaster"] = relationship(back_populates="projects")


class ResumeSkill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One explicitly claimed skill belonging to a resume master."""

    __tablename__ = "resume_skills"
    __table_args__ = (
        Index("resume_skills_resume_master_id_idx", "resume_master_id"),
        Index(
            "resume_skills_resume_master_name_idx",
            "resume_master_id",
            "skill_name",
            unique=True,
        ),
    )

    resume_master_id: Mapped[UUID] = mapped_column(
        ForeignKey("resume_masters.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_name: Mapped[str] = mapped_column(String(150), nullable=False)
    skill_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    proficiency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    resume_master: Mapped["ResumeMaster"] = relationship(back_populates="skills")
