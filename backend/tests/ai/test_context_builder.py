"""Privacy and evidence-addressability checks for resume AI contexts."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.ai.context_builder import (
    build_match_context,
    build_resume_evidence,
    build_tailor_context,
)
from app.ai.errors import AIInputError
from app.ai.job_parser.schemas import JobParserOutput
from app.models.resume import ExperienceType
from app.schemas.resume import (
    EducationData,
    ExperienceData,
    ProjectData,
    ResumeBasicInfo,
    ResumeMasterData,
    SkillData,
)
from tests.ai.job_matcher.test_schemas import parsed_job

RESUME_ID = UUID("00000000-0000-0000-0000-000000000001")
EDUCATION_ID = UUID("00000000-0000-0000-0000-000000000002")
EXPERIENCE_ID = UUID("00000000-0000-0000-0000-000000000003")
PROJECT_ID = UUID("00000000-0000-0000-0000-000000000004")
SKILL_ID = UUID("00000000-0000-0000-0000-000000000005")
NOW = datetime(2026, 9, 12, tzinfo=UTC)


def resume_data(*, include_content: bool = True) -> ResumeMasterData:
    return ResumeMasterData(
        id=RESUME_ID,
        basic_info=ResumeBasicInfo(
            name="应被移除的姓名",
            phone="13800000000",
            email="private@example.com",
            city="应被移除的精确城市",
            job_status="应被移除的求职状态",
            summary="关注数据驱动的产品运营。" if include_content else None,
        ),
        education=(
            [
                EducationData(
                    id=EDUCATION_ID,
                    school="华东大学",
                    degree="本科",
                    major="管理学",
                    start_date="2023-09",
                    end_date="2027-06",
                    gpa="3.8/4.0",
                    courses="统计学",
                    description=None,
                )
            ]
            if include_content
            else []
        ),
        experiences=(
            [
                ExperienceData(
                    id=EXPERIENCE_ID,
                    experience_type=ExperienceType.INTERNSHIP,
                    organization="示例科技",
                    position="产品运营实习生",
                    start_date="2025-06",
                    end_date=None,
                    is_current=True,
                    description="梳理近三年业务需求及全流程耗时数据。",
                    achievements="定位流程异常并推动优化。",
                )
            ]
            if include_content
            else []
        ),
        projects=(
            [
                ProjectData(
                    id=PROJECT_ID,
                    name="运营数据周报",
                    role="产品负责人",
                    start_date="2025-01",
                    end_date="2025-05",
                    background="减少人工汇总工作。",
                    description="设计数据周报 PRD。",
                    achievements="形成自动化质量监控方案并推进研发评审。",
                )
            ]
            if include_content
            else []
        ),
        skills=(
            [
                SkillData(
                    id=SKILL_ID,
                    skill_name="Python",
                    skill_category="数据分析",
                    proficiency="熟练",
                )
            ]
            if include_content
            else []
        ),
        created_at=NOW,
        updated_at=NOW,
    )


def parsed_job_output() -> JobParserOutput:
    return JobParserOutput.model_validate(parsed_job())


def test_resume_context_uses_a_pii_excluding_field_allowlist() -> None:
    evidence = build_resume_evidence(resume_data())
    serialized = "\n".join(item.content for item in evidence)

    for excluded in (
        "应被移除的姓名",
        "13800000000",
        "private@example.com",
        "应被移除的精确城市",
        "应被移除的求职状态",
    ):
        assert excluded not in serialized

    assert "关注数据驱动的产品运营" in serialized
    assert "华东大学" in serialized
    assert "示例科技" in serialized


def test_resume_context_preserves_source_ids_and_relevant_fact_order() -> None:
    evidence = build_resume_evidence(resume_data())

    assert [item.source_type for item in evidence] == [
        "education",
        "experience",
        "project",
        "skill",
        "summary",
    ]
    assert [item.source_id for item in evidence] == [
        str(EDUCATION_ID),
        str(EXPERIENCE_ID),
        str(PROJECT_ID),
        str(SKILL_ID),
        None,
    ]
    assert "结束年月：至今" in evidence[1].content
    assert "成果：定位流程异常并推动优化。" in evidence[1].content


def test_match_context_combines_parsed_job_with_redacted_evidence() -> None:
    context = build_match_context(
        resume=resume_data(),
        parsed_job=parsed_job_output(),
    )

    assert context.parsed_job.requirements[0].requirement_key == "R1"
    assert len(context.resume_evidence) == 5
    assert set(context.model_dump()) == {"parsed_job", "resume_evidence"}


@pytest.mark.parametrize("resume", [None, resume_data(include_content=False)])
def test_match_context_rejects_a_missing_or_empty_resume(
    resume: ResumeMasterData | None,
) -> None:
    with pytest.raises(AIInputError) as captured:
        build_match_context(resume=resume, parsed_job=parsed_job_output())

    assert captured.value.code == "AI_INVALID_INPUT"
    assert captured.value.retryable is False


def test_match_context_rejects_a_parsed_job_without_requirements() -> None:
    job = parsed_job()
    job["requirements"] = []

    with pytest.raises(AIInputError, match="no requirements"):
        build_match_context(
            resume=resume_data(),
            parsed_job=JobParserOutput.model_validate(job),
        )


def test_tailor_context_excludes_pii_and_education() -> None:
    context = build_tailor_context(
        resume=resume_data(),
        parsed_job=parsed_job_output(),
        match_strengths=["数据分析有直接证据"],
        match_gaps=["SQL 尚无证据"],
    )
    serialized = context.model_dump_json()

    for excluded in (
        "应被移除的姓名",
        "13800000000",
        "private@example.com",
        "应被移除的精确城市",
        "华东大学",
        "管理学",
    ):
        assert excluded not in serialized

    assert context.experiences[0].source_id == str(EXPERIENCE_ID)
    assert context.projects[0].source_id == str(PROJECT_ID)
    assert context.skills[0].source_id == str(SKILL_ID)
    assert context.experiences[0].end_date == "至今"
    assert context.match_strengths == ["数据分析有直接证据"]
    assert context.match_gaps == ["SQL 尚无证据"]
