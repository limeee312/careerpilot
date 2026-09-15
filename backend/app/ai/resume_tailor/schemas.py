"""Pydantic contracts for the versioned Resume Tailor."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ai.job_parser.schemas import JobParserOutput

NonEmptyText = Annotated[str, Field(min_length=1)]
SourceId = Annotated[str, Field(min_length=1)]
type ImprovementStatus = Literal[
    "NO_EVIDENCE",
    "WEAK_EVIDENCE",
    "PARTIAL_MATCH",
]


class ResumeTailorSchema(BaseModel):
    """Reject unknown fields and normalize surrounding whitespace."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SourceExperience(ResumeTailorSchema):
    """One immutable experience identity plus its editable source text."""

    source_id: SourceId
    experience_type: NonEmptyText
    organization: NonEmptyText
    position: NonEmptyText
    start_date: NonEmptyText | None
    end_date: NonEmptyText | None
    description: NonEmptyText
    achievements: NonEmptyText | None


class SourceProject(ResumeTailorSchema):
    """One immutable project identity plus its editable source text."""

    source_id: SourceId
    name: NonEmptyText
    role: NonEmptyText | None
    description: NonEmptyText
    achievements: NonEmptyText | None


class SourceSkill(ResumeTailorSchema):
    """One existing skill that the model may only reorder."""

    source_id: SourceId
    skill_name: NonEmptyText


class TailorInput(ResumeTailorSchema):
    """PII-free source facts, target job, and persisted match guidance."""

    resume_summary: NonEmptyText | None
    experiences: list[SourceExperience]
    projects: list[SourceProject]
    skills: list[SourceSkill]
    parsed_job: JobParserOutput
    match_strengths: list[NonEmptyText]
    match_gaps: list[NonEmptyText]


class EvidenceReference(ResumeTailorSchema):
    """A verbatim source quote supporting a generated bullet."""

    source_field: Literal["description", "achievements"]
    source_quote: NonEmptyText


class TailoredBullet(ResumeTailorSchema):
    """One rewritten bullet with mandatory source evidence."""

    text: NonEmptyText
    evidence_refs: list[EvidenceReference] = Field(min_length=1)


class TailoredSourceItem(ResumeTailorSchema):
    """Shared include/order contract for experiences and projects."""

    source_id: SourceId
    include: bool
    order: int | None = Field(default=None, ge=1)
    bullets: list[TailoredBullet]

    @model_validator(mode="after")
    def validate_include_contract(self) -> Self:
        if self.include and (self.order is None or not self.bullets):
            raise ValueError("included items require an order and at least one bullet")
        if not self.include and (self.order is not None or self.bullets):
            raise ValueError("excluded items must not contain an order or bullets")
        return self


class TailoredExperience(TailoredSourceItem):
    """Selection and grounded rewrite for one source experience."""


class TailoredProject(TailoredSourceItem):
    """Selection and grounded rewrite for one source project."""


class ImprovementSuggestion(ResumeTailorSchema):
    """Future work that must never be represented as a current fact."""

    job_requirement: NonEmptyText
    current_status: ImprovementStatus
    suggestion: NonEmptyText
    do_not_claim_yet: Literal[True] = True


class ResumeTailorOutput(ResumeTailorSchema):
    """Unpersisted, evidence-grounded Resume Tailor draft."""

    professional_summary: NonEmptyText | None
    experiences: list[TailoredExperience]
    projects: list[TailoredProject]
    skill_order: list[SourceId]
    improvement_suggestions: list[ImprovementSuggestion]
    warnings: list[NonEmptyText]
