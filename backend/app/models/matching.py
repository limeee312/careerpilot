"""Immutable job parsing and resume-to-job match persistence models."""

from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.matching import (
    AssessmentStatus,
    ConfidenceLevel,
    EligibilityStatus,
    EvidenceGrade,
    MatchDimension,
    RecommendationLevel,
    RequirementType,
)
from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.resume import ResumeMaster
    from app.models.user import User


class AIStatus(StrEnum):
    """Lifecycle state for one AI-derived persistence record."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class JobParseResult(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One versioned Job Parser run; reruns append instead of overwrite."""

    __tablename__ = "job_parse_results"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "job_id",
            name="job_parse_results_id_job_id_key",
        ),
    )

    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    ai_run_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=True,
    )
    status: Mapped[AIStatus] = mapped_column(
        SQLAlchemyEnum(AIStatus, name="ai_status"),
        default=AIStatus.PENDING,
        server_default=AIStatus.PENDING.value,
        nullable=False,
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    job: Mapped["Job"] = relationship(back_populates="parse_results")
    requirements: Mapped[list["JobRequirement"]] = relationship(
        back_populates="parse_result",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="JobRequirement.sort_order",
    )


Index(
    "job_parse_results_job_created_idx",
    JobParseResult.job_id,
    JobParseResult.created_at.desc(),
)


class JobRequirement(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One atomic, source-grounded requirement extracted from a JD."""

    __tablename__ = "job_requirements"
    __table_args__ = (
        CheckConstraint(
            "importance IN (1, 2)",
            name="job_requirements_importance_ck",
        ),
        CheckConstraint(
            "sort_order >= 1",
            name="job_requirements_sort_order_positive_ck",
        ),
        CheckConstraint(
            "(requirement_type = 'HARD' AND dimension IS NULL) OR "
            "(requirement_type <> 'HARD' AND dimension IS NOT NULL)",
            name="job_requirements_dimension_contract_ck",
        ),
        UniqueConstraint(
            "job_parse_result_id",
            "sort_order",
            name="job_requirements_parse_sort_key",
        ),
        Index("job_requirements_parse_result_id_idx", "job_parse_result_id"),
    )

    job_parse_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_parse_results.id", ondelete="CASCADE"),
        nullable=False,
    )
    requirement_type: Mapped[RequirementType] = mapped_column(
        SQLAlchemyEnum(RequirementType, name="requirement_type"),
        nullable=False,
    )
    dimension: Mapped[MatchDimension | None] = mapped_column(
        SQLAlchemyEnum(MatchDimension, name="match_dimension"),
        nullable=True,
    )
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_quote: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    parse_result: Mapped[JobParseResult] = relationship(back_populates="requirements")

    @property
    def requirement_key(self) -> str:
        """Reconstruct the stable R1..Rn contract key from persisted order."""

        return f"R{self.sort_order}"


class JobMatchResult(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable outcome for one resume snapshot and one parsed job."""

    __tablename__ = "job_match_results"
    __table_args__ = (
        CheckConstraint(
            "total_score >= 0 AND total_score <= 100",
            name="job_match_results_total_score_range_ck",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 100",
            name="job_match_results_confidence_score_range_ck",
        ),
        ForeignKeyConstraint(
            ["job_id", "user_id"],
            ["jobs.id", "jobs.user_id"],
            ondelete="CASCADE",
            name="job_match_results_job_owner_fkey",
        ),
        ForeignKeyConstraint(
            ["resume_master_id", "user_id"],
            ["resume_masters.id", "resume_masters.user_id"],
            ondelete="CASCADE",
            name="job_match_results_resume_owner_fkey",
        ),
        ForeignKeyConstraint(
            ["job_parse_result_id", "job_id"],
            ["job_parse_results.id", "job_parse_results.job_id"],
            ondelete="CASCADE",
            name="job_match_results_parse_job_fkey",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[UUID] = mapped_column(nullable=False)
    resume_master_id: Mapped[UUID] = mapped_column(nullable=False)
    job_parse_result_id: Mapped[UUID] = mapped_column(nullable=False)
    ai_run_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=True,
    )
    eligibility_status: Mapped[EligibilityStatus] = mapped_column(
        SQLAlchemyEnum(EligibilityStatus, name="eligibility_status"),
        nullable=False,
    )
    total_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    confidence_level: Mapped[ConfidenceLevel] = mapped_column(
        SQLAlchemyEnum(
            ConfidenceLevel,
            name="confidence_level",
            native_enum=False,
            create_constraint=True,
            length=20,
        ),
        nullable=False,
    )
    recommendation_level: Mapped[RecommendationLevel] = mapped_column(
        SQLAlchemyEnum(
            RecommendationLevel,
            name="recommendation_level",
            native_enum=False,
            create_constraint=True,
            length=30,
        ),
        nullable=False,
    )
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    strengths: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )
    gaps: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        default=list,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )
    resume_snapshot: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
    )
    job_snapshot: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
    )
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)

    user: Mapped["User"] = relationship(viewonly=True)
    job: Mapped["Job"] = relationship(back_populates="match_results")
    resume_master: Mapped["ResumeMaster"] = relationship(viewonly=True)
    parse_result: Mapped[JobParseResult] = relationship(viewonly=True)
    gate_checks: Mapped[list["MatchGateCheck"]] = relationship(
        back_populates="match_result",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    requirement_assessments: Mapped[list["MatchRequirementAssessment"]] = relationship(
        back_populates="match_result",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    dimension_scores: Mapped[list["MatchDimensionScore"]] = relationship(
        back_populates="match_result",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="MatchDimensionScore.dimension",
    )


Index(
    "job_match_results_job_created_idx",
    JobMatchResult.job_id,
    JobMatchResult.created_at.desc(),
)
Index(
    "job_match_results_user_created_idx",
    JobMatchResult.user_id,
    JobMatchResult.created_at.desc(),
)


class MatchGateCheck(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One hard-gate assessment and its grounded resume evidence."""

    __tablename__ = "match_gate_checks"
    __table_args__ = (
        UniqueConstraint(
            "match_result_id",
            "job_requirement_id",
            name="match_gate_checks_result_requirement_key",
        ),
        Index("match_gate_checks_match_result_id_idx", "match_result_id"),
    )

    match_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_match_results.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_requirements.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[EligibilityStatus] = mapped_column(
        SQLAlchemyEnum(EligibilityStatus, name="eligibility_status"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    resume_evidence: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        default=list,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )

    match_result: Mapped[JobMatchResult] = relationship(back_populates="gate_checks")
    requirement: Mapped[JobRequirement] = relationship()


class MatchRequirementAssessment(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One scored, evidence-capped non-hard requirement assessment."""

    __tablename__ = "match_requirement_assessments"
    __table_args__ = (
        CheckConstraint(
            "match_level >= 0 AND match_level <= 4",
            name="match_requirement_assessments_match_level_range_ck",
        ),
        CheckConstraint(
            "evidence_cap >= 0 AND evidence_cap <= 4",
            name="match_requirement_assessments_evidence_cap_range_ck",
        ),
        CheckConstraint(
            "weighted_score >= 0",
            name="match_requirement_assessments_weighted_score_nonnegative_ck",
        ),
        UniqueConstraint(
            "match_result_id",
            "job_requirement_id",
            name="match_requirement_assessments_result_requirement_key",
        ),
        Index(
            "match_requirement_assessments_match_result_id_idx",
            "match_result_id",
        ),
    )

    match_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_match_results.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_requirements.id", ondelete="CASCADE"),
        nullable=False,
    )
    match_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    evidence_grade: Mapped[EvidenceGrade] = mapped_column(
        SQLAlchemyEnum(EvidenceGrade, name="evidence_grade"),
        nullable=False,
    )
    evidence_cap: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    weighted_score: Mapped[Decimal] = mapped_column(
        Numeric(6, 3),
        nullable=False,
    )
    assessment_status: Mapped[AssessmentStatus] = mapped_column(
        SQLAlchemyEnum(
            AssessmentStatus,
            name="assessment_status",
            native_enum=False,
            create_constraint=True,
            length=30,
        ),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    resume_evidence: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        default=list,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )

    match_result: Mapped[JobMatchResult] = relationship(
        back_populates="requirement_assessments"
    )
    requirement: Mapped[JobRequirement] = relationship()


class MatchDimensionScore(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Precomputed dimension subtotal used by result ordering and UI."""

    __tablename__ = "match_dimension_scores"
    __table_args__ = (
        CheckConstraint(
            "raw_score >= 0 AND raw_score <= max_score",
            name="match_dimension_scores_raw_score_range_ck",
        ),
        CheckConstraint(
            "max_score > 0",
            name="match_dimension_scores_max_score_positive_ck",
        ),
        CheckConstraint(
            "normalized_score >= 0 AND normalized_score <= 100",
            name="match_dimension_scores_normalized_score_range_ck",
        ),
        UniqueConstraint(
            "match_result_id",
            "dimension",
            name="match_dimension_scores_result_dimension_key",
        ),
        Index("match_dimension_scores_match_result_id_idx", "match_result_id"),
    )

    match_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_match_results.id", ondelete="CASCADE"),
        nullable=False,
    )
    dimension: Mapped[MatchDimension] = mapped_column(
        SQLAlchemyEnum(MatchDimension, name="match_dimension"),
        nullable=False,
    )
    raw_score: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    max_score: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    normalized_score: Mapped[Decimal] = mapped_column(
        Numeric(6, 3),
        nullable=False,
    )

    match_result: Mapped[JobMatchResult] = relationship(
        back_populates="dimension_scores"
    )
