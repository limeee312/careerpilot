"""Public contracts for one evidence-grounded job match detail page."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.matching import (
    AssessmentStatus,
    ConfidenceLevel,
    EligibilityStatus,
    EvidenceGrade,
    MatchDimension,
    RecommendationLevel,
    RequirementType,
)

EvidenceSourceType = Literal[
    "education",
    "experience",
    "project",
    "skill",
    "summary",
]
GapImportance = Literal["HIGH", "MEDIUM", "LOW"]


class JobDetailSchema(BaseModel):
    """Strict response base for the job detail API."""

    model_config = ConfigDict(extra="forbid")


class ResumeEvidenceData(JobDetailSchema):
    """A persisted, source-addressable quote from the resume snapshot."""

    source_type: EvidenceSourceType | None
    source_id: str | None
    source_quote: str | None


class JobRequirementData(JobDetailSchema):
    """One atomic, JD-grounded requirement from the current parse run."""

    id: UUID
    requirement_key: str
    requirement_type: RequirementType
    dimension: MatchDimension | None
    requirement_text: str
    source_quote: str
    importance: Literal[1, 2]


class HardGateDetailData(JobDetailSchema):
    """One hard requirement, its eligibility decision, and evidence."""

    requirement: JobRequirementData
    status: EligibilityStatus
    reason: str
    evidence: list[ResumeEvidenceData]


class RequirementAssessmentDetailData(JobDetailSchema):
    """One non-hard requirement assessment with its score contribution."""

    requirement: JobRequirementData
    match_level: int = Field(ge=0, le=4)
    evidence_grade: EvidenceGrade
    evidence_cap: int = Field(ge=0, le=4)
    weighted_score: Decimal
    status: AssessmentStatus
    reason: str
    evidence: list[ResumeEvidenceData]


class DimensionScoreDetailData(JobDetailSchema):
    """One applicable dimension; omitted dimensions are N/A rather than zero."""

    dimension: MatchDimension
    raw_score: Decimal
    max_score: Decimal
    normalized_score: Decimal


class MatchGapDetailData(JobDetailSchema):
    """A current evidence gap and a future-facing improvement direction."""

    requirement_key: str
    importance: GapImportance
    gap: str
    improvement_direction: str


class JobMatchDetailData(JobDetailSchema):
    """Complete current-run detail for one user-owned matched job."""

    job_id: UUID
    batch_id: UUID
    result_id: UUID
    company_name: str
    title: str
    location: str | None
    department: str | None
    source_url: str | None
    role_summary: str | None
    eligibility_status: EligibilityStatus
    total_score: Decimal
    display_score: int
    confidence_score: Decimal
    confidence_level: ConfidenceLevel
    recommendation_level: RecommendationLevel
    recommendation: str
    strengths: list[str]
    gaps: list[MatchGapDetailData]
    dimension_scores: list[DimensionScoreDetailData]
    hard_gates: list[HardGateDetailData]
    requirement_assessments: list[RequirementAssessmentDetailData]
    analyzed_at: datetime


class JobMatchDetailResponse(JobDetailSchema):
    data: JobMatchDetailData
