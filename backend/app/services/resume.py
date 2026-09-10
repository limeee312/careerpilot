"""Transactional persistence operations for a user's resume master."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.resume import (
    ResumeEducation,
    ResumeExperience,
    ResumeMaster,
    ResumeProject,
    ResumeSkill,
)
from app.schemas.resume import (
    EducationData,
    ExperienceData,
    ProjectData,
    ResumeBasicInfo,
    ResumeMasterData,
    ResumeMasterUpsert,
    SkillData,
    date_to_year_month,
    year_month_to_date,
)


class ResumeSectionNotFoundError(Exception):
    """Raised when a submitted section ID is not owned by the current resume."""


class DuplicateResumeSkillError(Exception):
    """Raised when a resume contains duplicate skill names."""


class ResumeSaveConflictError(Exception):
    """Raised when concurrent requests both try to create the same master."""


def _resume_query(user_id: UUID):
    return (
        select(ResumeMaster)
        .where(ResumeMaster.user_id == user_id)
        .options(
            selectinload(ResumeMaster.educations),
            selectinload(ResumeMaster.experiences),
            selectinload(ResumeMaster.projects),
            selectinload(ResumeMaster.skills),
        )
    )


async def get_resume_master(
    session: AsyncSession,
    user_id: UUID,
) -> ResumeMaster | None:
    """Load only the resume master owned by the authenticated user."""

    return await session.scalar(_resume_query(user_id))


def _sync_educations(master: ResumeMaster, payload: ResumeMasterUpsert) -> None:
    existing = {item.id: item for item in master.educations}
    desired: list[ResumeEducation] = []

    for sort_order, submitted in enumerate(payload.education):
        if submitted.id is None:
            item = ResumeEducation()
        else:
            item = existing.pop(submitted.id, None)
            if item is None:
                raise ResumeSectionNotFoundError
        item.school = submitted.school
        item.degree = submitted.degree
        item.major = submitted.major
        item.start_date = year_month_to_date(submitted.start_date)
        item.end_date = year_month_to_date(submitted.end_date)
        item.gpa = submitted.gpa
        item.courses = submitted.courses
        item.description = submitted.description
        item.sort_order = sort_order
        desired.append(item)

    master.educations = desired


def _sync_experiences(master: ResumeMaster, payload: ResumeMasterUpsert) -> None:
    existing = {item.id: item for item in master.experiences}
    desired: list[ResumeExperience] = []

    for sort_order, submitted in enumerate(payload.experiences):
        if submitted.id is None:
            item = ResumeExperience()
        else:
            item = existing.pop(submitted.id, None)
            if item is None:
                raise ResumeSectionNotFoundError
        item.experience_type = submitted.experience_type
        item.organization = submitted.organization
        item.position = submitted.position
        item.start_date = year_month_to_date(submitted.start_date)
        item.end_date = year_month_to_date(submitted.end_date)
        item.is_current = submitted.is_current
        item.description = submitted.description
        item.achievements = submitted.achievements
        item.sort_order = sort_order
        desired.append(item)

    master.experiences = desired


def _sync_projects(master: ResumeMaster, payload: ResumeMasterUpsert) -> None:
    existing = {item.id: item for item in master.projects}
    desired: list[ResumeProject] = []

    for sort_order, submitted in enumerate(payload.projects):
        if submitted.id is None:
            item = ResumeProject()
        else:
            item = existing.pop(submitted.id, None)
            if item is None:
                raise ResumeSectionNotFoundError
        item.name = submitted.name
        item.role = submitted.role
        item.start_date = year_month_to_date(submitted.start_date)
        item.end_date = year_month_to_date(submitted.end_date)
        item.background = submitted.background
        item.description = submitted.description
        item.achievements = submitted.achievements
        item.sort_order = sort_order
        desired.append(item)

    master.projects = desired


def _sync_skills(master: ResumeMaster, payload: ResumeMasterUpsert) -> None:
    existing = {item.id: item for item in master.skills}
    desired: list[ResumeSkill] = []

    for sort_order, submitted in enumerate(payload.skills):
        if submitted.id is None:
            item = ResumeSkill()
        else:
            item = existing.pop(submitted.id, None)
            if item is None:
                raise ResumeSectionNotFoundError
        item.skill_name = submitted.skill_name
        item.skill_category = submitted.skill_category
        item.proficiency = submitted.proficiency
        item.sort_order = sort_order
        desired.append(item)

    master.skills = desired


def _constraint_name(error: IntegrityError) -> str | None:
    diagnostic = getattr(error.orig, "diag", None)
    return getattr(diagnostic, "constraint_name", None)


async def upsert_resume_master(
    session: AsyncSession,
    user_id: UUID,
    payload: ResumeMasterUpsert,
) -> ResumeMaster:
    """Create or fully reconcile all resume sections in one transaction."""

    try:
        master = await get_resume_master(session, user_id)
        if master is None:
            master = ResumeMaster(user_id=user_id)
            session.add(master)
        else:
            master.updated_at = datetime.now(UTC)

        basic_info = payload.basic_info
        master.name = basic_info.name
        master.phone = basic_info.phone
        master.email = str(basic_info.email) if basic_info.email is not None else None
        master.city = basic_info.city
        master.job_status = basic_info.job_status
        master.summary = basic_info.summary

        _sync_educations(master, payload)
        _sync_experiences(master, payload)
        _sync_projects(master, payload)
        _sync_skills(master, payload)

        await session.commit()
    except ResumeSectionNotFoundError:
        await session.rollback()
        raise
    except IntegrityError as error:
        await session.rollback()
        constraint_name = _constraint_name(error)
        if constraint_name == "resume_skills_resume_master_name_idx":
            raise DuplicateResumeSkillError from error
        if constraint_name == "resume_masters_user_id_idx":
            raise ResumeSaveConflictError from error
        raise
    except Exception:
        await session.rollback()
        raise

    return master


def serialize_resume_master(master: ResumeMaster) -> ResumeMasterData:
    """Build the public API payload while hiding storage-only date precision."""

    return ResumeMasterData(
        id=master.id,
        basic_info=ResumeBasicInfo(
            name=master.name,
            phone=master.phone,
            email=master.email,
            city=master.city,
            job_status=master.job_status,
            summary=master.summary,
        ),
        education=[
            EducationData(
                id=item.id,
                school=item.school,
                degree=item.degree,
                major=item.major,
                start_date=date_to_year_month(item.start_date),
                end_date=date_to_year_month(item.end_date),
                gpa=item.gpa,
                courses=item.courses,
                description=item.description,
            )
            for item in sorted(master.educations, key=lambda item: item.sort_order)
        ],
        experiences=[
            ExperienceData(
                id=item.id,
                experience_type=item.experience_type,
                organization=item.organization,
                position=item.position,
                start_date=date_to_year_month(item.start_date),
                end_date=date_to_year_month(item.end_date),
                is_current=item.is_current,
                description=item.description,
                achievements=item.achievements,
            )
            for item in sorted(master.experiences, key=lambda item: item.sort_order)
        ],
        projects=[
            ProjectData(
                id=item.id,
                name=item.name,
                role=item.role,
                start_date=date_to_year_month(item.start_date),
                end_date=date_to_year_month(item.end_date),
                background=item.background,
                description=item.description,
                achievements=item.achievements,
            )
            for item in sorted(master.projects, key=lambda item: item.sort_order)
        ],
        skills=[
            SkillData(
                id=item.id,
                skill_name=item.skill_name,
                skill_category=item.skill_category,
                proficiency=item.proficiency,
            )
            for item in sorted(master.skills, key=lambda item: item.sort_order)
        ],
        created_at=master.created_at,
        updated_at=master.updated_at,
    )
