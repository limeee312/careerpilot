"""Validate, assemble, and retrieve saved targeted resume versions."""

from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context_builder import build_tailor_context
from app.ai.errors import AIInputError, AIInvalidOutputError
from app.ai.resume_tailor.schemas import ResumeTailorOutput
from app.ai.resume_tailor.validator import validate_resume_tailor_output
from app.models.matching import JobMatchResult
from app.models.resume_version import ResumeVersion, ResumeVersionStatus
from app.schemas.resume import ResumeMasterData
from app.schemas.resume_version import (
    ResumeVersionContent,
    ResumeVersionCreate,
    ResumeVersionData,
    ResumeVersionEducation,
    ResumeVersionExperience,
    ResumeVersionListItem,
    ResumeVersionProject,
    ResumeVersionSkill,
)
from app.services.resume_tailor import (
    ResumeTailorSourceInvalidError,
    resolve_resume_tailor_source,
)


class ResumeVersionSourceNotFoundError(Exception):
    """Raised when the selected match result is outside the user's scope."""


class ResumeVersionNotFoundError(Exception):
    """Raised when a saved version is outside the user's scope."""


class ResumeVersionInvalidDraftError(Exception):
    """Raised when edited content no longer passes the truth boundary."""


def _job_labels(snapshot: dict[str, object]) -> tuple[str, str]:
    company = snapshot.get("company_name")
    title = snapshot.get("title")
    if not isinstance(company, str) or not company.strip():
        raise ResumeVersionInvalidDraftError
    if not isinstance(title, str) or not title.strip():
        raise ResumeVersionInvalidDraftError
    return company.strip(), title.strip()


def _assemble_content(
    source: ResumeMasterData,
    draft: ResumeTailorOutput,
) -> ResumeVersionContent:
    experience_by_id = {str(item.id): item for item in source.experiences}
    project_by_id = {str(item.id): item for item in source.projects}
    skill_by_id = {str(item.id): item for item in source.skills}

    experiences = []
    for tailored in sorted(
        (item for item in draft.experiences if item.include),
        key=lambda item: item.order or 0,
    ):
        item = experience_by_id[tailored.source_id]
        experiences.append(
            ResumeVersionExperience(
                source_id=item.id,
                experience_type=item.experience_type,
                organization=item.organization,
                position=item.position,
                start_date=item.start_date,
                end_date=item.end_date,
                is_current=item.is_current,
                bullets=[bullet.text for bullet in tailored.bullets],
            )
        )

    projects = []
    for tailored in sorted(
        (item for item in draft.projects if item.include),
        key=lambda item: item.order or 0,
    ):
        item = project_by_id[tailored.source_id]
        projects.append(
            ResumeVersionProject(
                source_id=item.id,
                name=item.name,
                role=item.role,
                start_date=item.start_date,
                end_date=item.end_date,
                background=item.background,
                bullets=[bullet.text for bullet in tailored.bullets],
            )
        )

    return ResumeVersionContent(
        summary=draft.professional_summary,
        education=[
            ResumeVersionEducation(
                source_id=item.id,
                school=item.school,
                degree=item.degree,
                major=item.major,
                start_date=item.start_date,
                end_date=item.end_date,
                gpa=item.gpa,
                courses=item.courses,
                description=item.description,
            )
            for item in source.education
        ],
        experiences=experiences,
        projects=projects,
        skills=[
            ResumeVersionSkill(
                source_id=skill_by_id[source_id].id,
                skill_name=skill_by_id[source_id].skill_name,
                skill_category=skill_by_id[source_id].skill_category,
                proficiency=skill_by_id[source_id].proficiency,
            )
            for source_id in draft.skill_order
        ],
    )


def _serialize_list_item(version: ResumeVersion) -> ResumeVersionListItem:
    company, title = _job_labels(version.source_job_snapshot)
    return ResumeVersionListItem(
        id=version.id,
        resume_master_id=version.resume_master_id,
        job_id=version.job_id,
        match_result_id=version.match_result_id,
        name=version.name,
        status=version.status,
        company_name=company,
        job_title=title,
        prompt_version=version.prompt_version,
        model=version.model,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


def serialize_resume_version(version: ResumeVersion) -> ResumeVersionData:
    """Return a validated version without recomputing its content."""

    item = _serialize_list_item(version)
    try:
        content = ResumeVersionContent.model_validate(version.content)
        source = _validate_resume_snapshot(version.source_resume_snapshot)
    except (ValidationError, ResumeTailorSourceInvalidError) as error:
        raise ResumeVersionInvalidDraftError from error
    return ResumeVersionData(
        **item.model_dump(),
        content=content,
        source_resume_snapshot=source,
        source_job_snapshot=version.source_job_snapshot,
    )


def _validate_resume_snapshot(snapshot: object) -> ResumeMasterData:
    try:
        return ResumeMasterData.model_validate(snapshot)
    except (TypeError, ValidationError) as error:
        raise ResumeTailorSourceInvalidError from error


async def create_resume_version(
    session: AsyncSession,
    user_id: UUID,
    payload: ResumeVersionCreate,
) -> ResumeVersion:
    """Persist one SAVED version only after deterministic revalidation."""

    result = await session.scalar(
        select(JobMatchResult).where(
            JobMatchResult.id == payload.match_result_id,
            JobMatchResult.user_id == user_id,
        )
    )
    if result is None:
        raise ResumeVersionSourceNotFoundError

    try:
        source, parsed_job, strengths, gaps = resolve_resume_tailor_source(result)
        tailor_input = build_tailor_context(
            resume=source,
            parsed_job=parsed_job,
            match_strengths=strengths,
            match_gaps=gaps,
        )
        draft = validate_resume_tailor_output(tailor_input, payload.draft)
        content = _assemble_content(source, draft)
        company, title = _job_labels(result.job_snapshot)
    except (
        AIInputError,
        AIInvalidOutputError,
        KeyError,
        ResumeTailorSourceInvalidError,
        ValidationError,
    ) as error:
        raise ResumeVersionInvalidDraftError from error

    version = ResumeVersion(
        user_id=user_id,
        resume_master_id=result.resume_master_id,
        job_id=result.job_id,
        match_result_id=result.id,
        name=payload.name or f"{company} - {title}",
        status=ResumeVersionStatus.SAVED,
        content=content.model_dump(mode="json"),
        source_resume_snapshot=source.model_dump(mode="json"),
        source_job_snapshot=dict(result.job_snapshot),
        prompt_version=payload.prompt_version,
        model=payload.model,
    )
    session.add(version)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(version)
    return version


async def list_resume_versions(
    session: AsyncSession,
    user_id: UUID,
) -> list[ResumeVersion]:
    """List only the current user's saved versions, newest first."""

    return list(
        await session.scalars(
            select(ResumeVersion)
            .where(
                ResumeVersion.user_id == user_id,
                ResumeVersion.status == ResumeVersionStatus.SAVED,
            )
            .order_by(ResumeVersion.created_at.desc())
        )
    )


async def get_resume_version(
    session: AsyncSession,
    user_id: UUID,
    version_id: UUID,
) -> ResumeVersion:
    """Load one version within the authenticated user's scope."""

    version = await session.scalar(
        select(ResumeVersion).where(
            ResumeVersion.id == version_id,
            ResumeVersion.user_id == user_id,
            ResumeVersion.status == ResumeVersionStatus.SAVED,
        )
    )
    if version is None:
        raise ResumeVersionNotFoundError
    return version


def serialize_resume_version_list_item(
    version: ResumeVersion,
) -> ResumeVersionListItem:
    return _serialize_list_item(version)
