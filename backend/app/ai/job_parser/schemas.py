"""Pydantic contracts for the versioned Job Parser output."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.matching import MatchDimension, RequirementType

NonEmptyText = Annotated[str, Field(min_length=1)]


class JobParserSchema(BaseModel):
    """Reject unknown fields and normalize surrounding whitespace."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class JobParserInput(JobParserSchema):
    """Only job facts are sent to the parser; it never receives a resume."""

    company_name: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    location: str | None = Field(default=None, max_length=200)
    raw_jd: str = Field(min_length=50)

    @field_validator("location", mode="before")
    @classmethod
    def normalize_blank_location(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class ParsedRequirement(JobParserSchema):
    """One atomic requirement grounded in an exact JD quote."""

    requirement_key: str = Field(pattern=r"^R[1-9]\d*$")
    requirement_type: RequirementType
    dimension: MatchDimension | None
    requirement_text: NonEmptyText
    source_quote: NonEmptyText
    importance: Literal[1, 2]

    @model_validator(mode="after")
    def validate_dimension_contract(self) -> Self:
        if self.requirement_type is RequirementType.HARD:
            if self.dimension is not None:
                raise ValueError("HARD requirements must not have a match dimension")
        elif self.dimension is None:
            raise ValueError("non-HARD requirements must have a match dimension")
        return self


class JobParserOutput(JobParserSchema):
    """Structured, unscored interpretation of one raw job description."""

    role_summary: NonEmptyText
    responsibilities_summary: list[NonEmptyText]
    requirements: list[ParsedRequirement]
    business_domains: list[NonEmptyText]
    tools: list[NonEmptyText]
    ambiguous_points: list[NonEmptyText]

    @field_validator("requirements")
    @classmethod
    def validate_requirement_keys(
        cls, requirements: list[ParsedRequirement]
    ) -> list[ParsedRequirement]:
        keys = [requirement.requirement_key for requirement in requirements]
        expected = [f"R{index}" for index in range(1, len(requirements) + 1)]
        if keys != expected:
            raise ValueError("requirement keys must be unique and sequential from R1")
        return requirements
