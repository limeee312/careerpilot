"""Request and response contracts for the structured resume master."""

from datetime import date, datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.models.resume import ExperienceType


def _validate_year_month(value: str) -> str:
    try:
        date.fromisoformat(f"{value}-01")
    except ValueError as error:
        raise ValueError("日期必须使用有效的 YYYY-MM 格式") from error
    return value


YearMonth = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
    ),
    AfterValidator(_validate_year_month),
]


def year_month_to_date(value: str | None) -> date | None:
    """Store a month-granularity value as the first day of that month."""

    return date.fromisoformat(f"{value}-01") if value is not None else None


def date_to_year_month(value: date | None) -> str | None:
    """Return a database date without exposing the storage-only day."""

    return value.strftime("%Y-%m") if value is not None else None


class ResumeSchema(BaseModel):
    """Strict resume payload base with consistent whitespace handling."""

    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def normalize_strings(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value


class ResumeBasicInfo(ResumeSchema):
    name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = Field(default=None, max_length=320)
    city: str | None = Field(default=None, max_length=100)
    job_status: str | None = Field(default=None, max_length=100)
    summary: str | None = None


class ResumeSectionInput(ResumeSchema):
    id: UUID | None = None


class EducationInput(ResumeSectionInput):
    school: str = Field(min_length=1, max_length=200)
    degree: str = Field(min_length=1, max_length=100)
    major: str = Field(min_length=1, max_length=200)
    start_date: YearMonth
    end_date: YearMonth
    gpa: str | None = Field(default=None, max_length=50)
    courses: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def validate_date_order(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("教育经历结束年月不能早于开始年月")
        return self


class ExperienceInput(ResumeSectionInput):
    experience_type: ExperienceType
    organization: str = Field(min_length=1, max_length=200)
    position: str = Field(min_length=1, max_length=200)
    start_date: YearMonth
    end_date: YearMonth | None = None
    is_current: bool = False
    description: str = Field(min_length=1)
    achievements: str | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.is_current and self.end_date is not None:
            raise ValueError("当前经历不能填写结束年月")
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("经历结束年月不能早于开始年月")
        return self


class ProjectInput(ResumeSectionInput):
    name: str = Field(min_length=1, max_length=200)
    role: str | None = Field(default=None, max_length=200)
    start_date: YearMonth | None = None
    end_date: YearMonth | None = None
    background: str | None = None
    description: str = Field(min_length=1)
    achievements: str | None = None

    @model_validator(mode="after")
    def validate_date_order(self) -> Self:
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("项目结束年月不能早于开始年月")
        return self


class SkillInput(ResumeSectionInput):
    skill_name: str = Field(min_length=1, max_length=150)
    skill_category: str | None = Field(default=None, max_length=100)
    proficiency: str | None = Field(default=None, max_length=50)


class ResumeMasterUpsert(ResumeSchema):
    basic_info: ResumeBasicInfo = Field(default_factory=ResumeBasicInfo)
    education: list[EducationInput] = Field(default_factory=list)
    experiences: list[ExperienceInput] = Field(default_factory=list)
    projects: list[ProjectInput] = Field(default_factory=list)
    skills: list[SkillInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_section_identity_and_skill_names(self) -> Self:
        for section in (
            self.education,
            self.experiences,
            self.projects,
            self.skills,
        ):
            ids = [item.id for item in section if item.id is not None]
            if len(ids) != len(set(ids)):
                raise ValueError("同一简历分区不能重复提交相同条目")

        skill_names = [skill.skill_name for skill in self.skills]
        if len(skill_names) != len(set(skill_names)):
            raise ValueError("同一简历不能包含重名技能")
        return self


class ResumeSectionData(ResumeSchema):
    id: UUID


class EducationData(ResumeSectionData):
    school: str
    degree: str
    major: str
    start_date: YearMonth
    end_date: YearMonth
    gpa: str | None
    courses: str | None
    description: str | None


class ExperienceData(ResumeSectionData):
    experience_type: ExperienceType
    organization: str
    position: str
    start_date: YearMonth
    end_date: YearMonth | None
    is_current: bool
    description: str
    achievements: str | None


class ProjectData(ResumeSectionData):
    name: str
    role: str | None
    start_date: YearMonth | None
    end_date: YearMonth | None
    background: str | None
    description: str
    achievements: str | None


class SkillData(ResumeSectionData):
    skill_name: str
    skill_category: str | None
    proficiency: str | None


class ResumeMasterData(ResumeSchema):
    id: UUID
    basic_info: ResumeBasicInfo
    education: list[EducationData]
    experiences: list[ExperienceData]
    projects: list[ProjectData]
    skills: list[SkillData]
    created_at: datetime
    updated_at: datetime


class ResumeMasterResponse(ResumeSchema):
    data: ResumeMasterData | None
