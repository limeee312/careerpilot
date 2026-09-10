"""Resume request validation and serialization tests."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.resume import (
    ExperienceType,
    ResumeEducation,
    ResumeExperience,
    ResumeMaster,
    ResumeSkill,
)
from app.schemas.resume import ResumeMasterUpsert
from app.services.resume import serialize_resume_master


def valid_payload() -> dict:
    return {
        "basic_info": {
            "name": "  张三  ",
            "phone": " ",
            "email": "resume@example.com",
            "city": "杭州",
            "job_status": "求职中",
            "summary": " ",
        },
        "education": [
            {
                "school": "XX大学",
                "degree": "硕士",
                "major": "应用语言学",
                "start_date": "2024-09",
                "end_date": "2027-06",
            }
        ],
        "experiences": [
            {
                "experience_type": "INTERNSHIP",
                "organization": "示例公司",
                "position": "产品运营实习生",
                "start_date": "2026-01",
                "end_date": None,
                "is_current": True,
                "description": "整理用户反馈并推动流程优化。",
            }
        ],
        "projects": [],
        "skills": [{"skill_name": "Python"}],
    }


def test_resume_payload_normalizes_blanks_and_accepts_year_months() -> None:
    payload = ResumeMasterUpsert.model_validate(valid_payload())

    assert payload.basic_info.name == "张三"
    assert payload.basic_info.phone is None
    assert payload.basic_info.summary is None
    assert payload.education[0].start_date == "2024-09"
    assert payload.experiences[0].experience_type is ExperienceType.INTERNSHIP


@pytest.mark.parametrize("year_month", ["2024", "2024-9", "2024-13", "0000-01"])
def test_resume_payload_rejects_invalid_year_month(year_month: str) -> None:
    data = valid_payload()
    data["education"][0]["start_date"] = year_month

    with pytest.raises(ValidationError):
        ResumeMasterUpsert.model_validate(data)


def test_resume_payload_rejects_reversed_dates() -> None:
    data = valid_payload()
    data["education"][0]["start_date"] = "2027-07"

    with pytest.raises(ValidationError):
        ResumeMasterUpsert.model_validate(data)


def test_current_experience_cannot_have_an_end_month() -> None:
    data = valid_payload()
    data["experiences"][0]["end_date"] = "2026-08"

    with pytest.raises(ValidationError):
        ResumeMasterUpsert.model_validate(data)


def test_resume_payload_rejects_duplicate_section_ids_or_skill_names() -> None:
    section_id = str(uuid4())
    duplicate_ids = valid_payload()
    duplicate_ids["skills"] = [
        {"id": section_id, "skill_name": "Python"},
        {"id": section_id, "skill_name": "SQL"},
    ]
    duplicate_skills = valid_payload()
    duplicate_skills["skills"] = [
        {"skill_name": "Python"},
        {"skill_name": "Python"},
    ]

    with pytest.raises(ValidationError):
        ResumeMasterUpsert.model_validate(duplicate_ids)
    with pytest.raises(ValidationError):
        ResumeMasterUpsert.model_validate(duplicate_skills)


def test_resume_serializer_returns_month_precision_and_stable_ids() -> None:
    now = datetime.now(UTC)
    education_id = uuid4()
    experience_id = uuid4()
    skill_id = uuid4()
    master = ResumeMaster(
        id=uuid4(),
        user_id=uuid4(),
        name="张三",
        created_at=now,
        updated_at=now,
        educations=[
            ResumeEducation(
                id=education_id,
                school="XX大学",
                degree="硕士",
                major="应用语言学",
                start_date=date(2024, 9, 1),
                end_date=date(2027, 6, 1),
                sort_order=0,
            )
        ],
        experiences=[
            ResumeExperience(
                id=experience_id,
                experience_type=ExperienceType.INTERNSHIP,
                organization="示例公司",
                position="产品运营实习生",
                start_date=date(2026, 1, 1),
                end_date=None,
                is_current=True,
                description="推动流程优化。",
                sort_order=0,
            )
        ],
        skills=[ResumeSkill(id=skill_id, skill_name="Python", sort_order=0)],
    )

    serialized = serialize_resume_master(master)

    assert serialized.education[0].id == education_id
    assert serialized.education[0].start_date == "2024-09"
    assert serialized.education[0].end_date == "2027-06"
    assert serialized.experiences[0].id == experience_id
    assert serialized.experiences[0].end_date is None
    assert serialized.skills[0].id == skill_id
