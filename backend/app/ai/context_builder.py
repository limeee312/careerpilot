"""Privacy-preserving context builders shared by resume-based AI skills."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.ai.errors import AIInputError
from app.ai.job_parser.schemas import JobParserOutput
from app.schemas.resume import ResumeMasterData

if TYPE_CHECKING:
    from app.ai.job_matcher.schemas import MatcherInput, ResumeEvidenceItem
    from app.ai.resume_tailor.schemas import TailorInput


def _render_fields(fields: list[tuple[str, object | None]]) -> str:
    """Render only explicitly allowlisted, populated resume fields."""

    return "\n".join(
        f"{label}：{value}" for label, value in fields if value is not None
    )


def build_resume_evidence(resume: ResumeMasterData) -> list[ResumeEvidenceItem]:
    """Convert a resume into source-grounded evidence without basic-info PII."""

    from app.ai.job_matcher.schemas import ResumeEvidenceItem

    evidence: list[ResumeEvidenceItem] = []

    for item in resume.education:
        evidence.append(
            ResumeEvidenceItem(
                source_type="education",
                source_id=str(item.id),
                content=_render_fields(
                    [
                        ("学校", item.school),
                        ("学历", item.degree),
                        ("专业", item.major),
                        ("开始年月", item.start_date),
                        ("结束年月", item.end_date),
                        ("GPA", item.gpa),
                        ("相关课程", item.courses),
                        ("补充说明", item.description),
                    ]
                ),
            )
        )

    for item in resume.experiences:
        evidence.append(
            ResumeEvidenceItem(
                source_type="experience",
                source_id=str(item.id),
                content=_render_fields(
                    [
                        ("经历类型", item.experience_type),
                        ("机构", item.organization),
                        ("职位", item.position),
                        ("开始年月", item.start_date),
                        ("结束年月", "至今" if item.is_current else item.end_date),
                        ("经历描述", item.description),
                        ("成果", item.achievements),
                    ]
                ),
            )
        )

    for item in resume.projects:
        evidence.append(
            ResumeEvidenceItem(
                source_type="project",
                source_id=str(item.id),
                content=_render_fields(
                    [
                        ("项目名称", item.name),
                        ("角色", item.role),
                        ("开始年月", item.start_date),
                        ("结束年月", item.end_date),
                        ("项目背景", item.background),
                        ("项目描述", item.description),
                        ("成果", item.achievements),
                    ]
                ),
            )
        )

    for item in resume.skills:
        evidence.append(
            ResumeEvidenceItem(
                source_type="skill",
                source_id=str(item.id),
                content=_render_fields(
                    [
                        ("技能", item.skill_name),
                        ("分类", item.skill_category),
                        ("熟练度", item.proficiency),
                    ]
                ),
            )
        )

    if resume.basic_info.summary is not None:
        evidence.append(
            ResumeEvidenceItem(
                source_type="summary",
                source_id=None,
                content=resume.basic_info.summary,
            )
        )

    return evidence


def build_match_context(
    *,
    resume: ResumeMasterData | None,
    parsed_job: JobParserOutput,
) -> MatcherInput:
    """Build the complete redacted input for one Matcher invocation."""

    from app.ai.job_matcher.schemas import MatcherInput

    if resume is None:
        raise AIInputError("resume does not exist")
    if not parsed_job.requirements:
        raise AIInputError("parsed job contains no requirements")

    resume_evidence = build_resume_evidence(resume)
    if not resume_evidence:
        raise AIInputError("resume contains no matchable evidence")

    return MatcherInput(
        parsed_job=parsed_job,
        resume_evidence=resume_evidence,
    )


def build_tailor_context(
    *,
    resume: ResumeMasterData | None,
    parsed_job: JobParserOutput,
    match_strengths: list[str],
    match_gaps: list[str],
) -> TailorInput:
    """Build a PII-free, source-addressable Resume Tailor input."""

    from app.ai.resume_tailor.schemas import (
        SourceExperience,
        SourceProject,
        SourceSkill,
        TailorInput,
    )

    if resume is None:
        raise AIInputError("resume does not exist")
    if not parsed_job.requirements:
        raise AIInputError("parsed job contains no requirements")
    if not (
        resume.basic_info.summary
        or resume.experiences
        or resume.projects
        or resume.skills
    ):
        raise AIInputError("resume contains no tailorable content")

    return TailorInput(
        resume_summary=resume.basic_info.summary,
        experiences=[
            SourceExperience(
                source_id=str(item.id),
                experience_type=item.experience_type.value,
                organization=item.organization,
                position=item.position,
                start_date=item.start_date,
                end_date="至今" if item.is_current else item.end_date,
                description=item.description,
                achievements=item.achievements,
            )
            for item in resume.experiences
        ],
        projects=[
            SourceProject(
                source_id=str(item.id),
                name=item.name,
                role=item.role,
                description=item.description,
                achievements=item.achievements,
            )
            for item in resume.projects
        ],
        skills=[
            SourceSkill(
                source_id=str(item.id),
                skill_name=item.skill_name,
            )
            for item in resume.skills
        ],
        parsed_job=parsed_job,
        match_strengths=match_strengths,
        match_gaps=match_gaps,
    )
