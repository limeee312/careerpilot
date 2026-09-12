"""Pydantic contracts for the versioned Resume-Job Matcher."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ai.job_parser.schemas import JobParserOutput
from app.domain.matching import (
    AssessmentStatus,
    EligibilityStatus,
    EvidenceGrade,
    MatchLevel,
)

NonEmptyText = Annotated[str, Field(min_length=1)]
SourceId = Annotated[str, Field(min_length=1)]
type EvidenceSourceType = Literal[
    "education",
    "experience",
    "project",
    "skill",
    "summary",
]
type GapImportance = Literal["HIGH", "MEDIUM", "LOW"]


class MatcherSchema(BaseModel):
    """Reject unknown fields and normalize surrounding whitespace."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ResumeEvidenceItem(MatcherSchema):
    """One redacted, source-addressable unit of resume evidence."""

    source_type: EvidenceSourceType
    source_id: SourceId | None
    content: NonEmptyText


class MatcherInput(MatcherSchema):
    """A parsed job and redacted resume evidence, without career preferences."""

    parsed_job: JobParserOutput
    resume_evidence: list[ResumeEvidenceItem]


class GateEvidence(MatcherSchema):
    """Optional evidence for one hard-gate decision."""

    source_type: EvidenceSourceType | None
    source_id: SourceId | None
    source_quote: NonEmptyText | None

    @model_validator(mode="after")
    def validate_nullable_evidence_tuple(self) -> Self:
        has_source = self.source_type is not None
        has_quote = self.source_quote is not None
        if has_source != has_quote:
            raise ValueError(
                "gate evidence source_type and source_quote must both be set or null"
            )
        if self.source_id is not None and not has_source:
            raise ValueError("gate evidence source_id requires source_type")
        return self


class GateAssessment(MatcherSchema):
    """The model's evidence-based assessment of one HARD requirement."""

    requirement_key: str = Field(pattern=r"^R[1-9]\d*$")
    status: EligibilityStatus
    reason: NonEmptyText
    evidence: list[GateEvidence]


class ResumeEvidenceRef(MatcherSchema):
    """A verbatim resume quote supporting one capability assessment."""

    source_type: EvidenceSourceType
    source_id: SourceId | None
    source_quote: NonEmptyText


class RequirementAssessment(MatcherSchema):
    """The model's unscored assessment of one non-HARD requirement."""

    requirement_key: str = Field(pattern=r"^R[1-9]\d*$")
    match_level: MatchLevel
    evidence_grade: EvidenceGrade
    status: AssessmentStatus
    reason: NonEmptyText
    evidence: list[ResumeEvidenceRef]


class MatchGap(MatcherSchema):
    """An evidence gap and a future improvement direction."""

    requirement_key: str = Field(pattern=r"^R[1-9]\d*$")
    importance: GapImportance
    gap: NonEmptyText
    improvement_direction: NonEmptyText


class MatcherOutput(MatcherSchema):
    """Requirement-level AI judgments; all aggregate scores stay backend-owned."""

    gate_assessments: list[GateAssessment]
    requirement_assessments: list[RequirementAssessment]
    strengths: list[NonEmptyText]
    gaps: list[MatchGap]
    overall_reasoning: NonEmptyText
