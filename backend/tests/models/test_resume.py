"""Structured resume model contract tests."""

from sqlalchemy import Boolean, Date, Enum, Integer, String, Text

from app.models.resume import (
    ExperienceType,
    ResumeEducation,
    ResumeExperience,
    ResumeMaster,
    ResumeProject,
    ResumeSkill,
)
from app.models.user import User


def assert_primary_key_and_timestamps(model: type) -> None:
    columns = model.__table__.columns

    assert columns.id.primary_key
    assert columns.id.default is not None
    assert columns.id.default.is_callable
    for timestamp_name in ("created_at", "updated_at"):
        timestamp = columns[timestamp_name]
        assert timestamp.type.timezone
        assert not timestamp.nullable
        assert timestamp.server_default is not None


def assert_master_foreign_key(model: type) -> None:
    foreign_key = next(iter(model.__table__.columns.resume_master_id.foreign_keys))

    assert foreign_key.target_fullname == "resume_masters.id"
    assert foreign_key.ondelete == "CASCADE"


def test_resume_master_matches_database_contract() -> None:
    columns = ResumeMaster.__table__.columns

    assert set(columns.keys()) == {
        "id",
        "user_id",
        "name",
        "phone",
        "email",
        "city",
        "job_status",
        "summary",
        "created_at",
        "updated_at",
    }
    assert_primary_key_and_timestamps(ResumeMaster)

    user_foreign_key = next(iter(columns.user_id.foreign_keys))
    assert user_foreign_key.target_fullname == "users.id"
    assert user_foreign_key.ondelete == "CASCADE"
    assert not columns.user_id.nullable

    expected_string_lengths = {
        "name": 100,
        "phone": 50,
        "email": 320,
        "city": 100,
        "job_status": 100,
    }
    for name, length in expected_string_lengths.items():
        assert isinstance(columns[name].type, String)
        assert columns[name].type.length == length
        assert columns[name].nullable
    assert isinstance(columns.summary.type, Text)
    assert columns.summary.nullable

    indexes = {index.name: index for index in ResumeMaster.__table__.indexes}
    assert set(indexes) == {"resume_masters_user_id_idx"}
    assert indexes["resume_masters_user_id_idx"].unique


def test_resume_education_matches_database_contract() -> None:
    columns = ResumeEducation.__table__.columns

    assert set(columns.keys()) == {
        "id",
        "resume_master_id",
        "school",
        "degree",
        "major",
        "start_date",
        "end_date",
        "gpa",
        "courses",
        "description",
        "sort_order",
        "created_at",
        "updated_at",
    }
    assert_primary_key_and_timestamps(ResumeEducation)
    assert_master_foreign_key(ResumeEducation)
    assert isinstance(columns.school.type, String)
    assert columns.school.type.length == 200
    assert isinstance(columns.degree.type, String)
    assert columns.degree.type.length == 100
    assert isinstance(columns.major.type, String)
    assert columns.major.type.length == 200
    assert isinstance(columns.start_date.type, Date)
    assert isinstance(columns.end_date.type, Date)
    assert not columns.start_date.nullable
    assert not columns.end_date.nullable
    assert columns.gpa.nullable
    assert columns.courses.nullable
    assert columns.description.nullable
    assert isinstance(columns.sort_order.type, Integer)
    assert not columns.sort_order.nullable


def test_resume_experience_matches_database_contract() -> None:
    columns = ResumeExperience.__table__.columns

    assert_primary_key_and_timestamps(ResumeExperience)
    assert_master_foreign_key(ResumeExperience)
    assert isinstance(columns.experience_type.type, Enum)
    assert columns.experience_type.type.name == "experience_type"
    assert columns.experience_type.type.enums == [item.value for item in ExperienceType]
    assert isinstance(columns.organization.type, String)
    assert columns.organization.type.length == 200
    assert isinstance(columns.position.type, String)
    assert columns.position.type.length == 200
    assert not columns.start_date.nullable
    assert columns.end_date.nullable
    assert isinstance(columns.is_current.type, Boolean)
    assert columns.is_current.server_default is not None
    assert not columns.description.nullable
    assert columns.achievements.nullable


def test_resume_project_matches_database_contract() -> None:
    columns = ResumeProject.__table__.columns

    assert_primary_key_and_timestamps(ResumeProject)
    assert_master_foreign_key(ResumeProject)
    assert isinstance(columns.name.type, String)
    assert columns.name.type.length == 200
    assert not columns.name.nullable
    assert columns.role.nullable
    assert columns.start_date.nullable
    assert columns.end_date.nullable
    assert columns.background.nullable
    assert not columns.description.nullable
    assert columns.achievements.nullable


def test_resume_skill_indexes_enforce_name_uniqueness() -> None:
    columns = ResumeSkill.__table__.columns

    assert_primary_key_and_timestamps(ResumeSkill)
    assert_master_foreign_key(ResumeSkill)
    assert isinstance(columns.skill_name.type, String)
    assert columns.skill_name.type.length == 150
    assert isinstance(columns.skill_category.type, String)
    assert columns.skill_category.type.length == 100
    assert isinstance(columns.proficiency.type, String)
    assert columns.proficiency.type.length == 50

    indexes = {index.name: index for index in ResumeSkill.__table__.indexes}
    assert set(indexes) == {
        "resume_skills_resume_master_id_idx",
        "resume_skills_resume_master_name_idx",
    }
    unique_index = indexes["resume_skills_resume_master_name_idx"]
    assert unique_index.unique
    assert [column.name for column in unique_index.columns] == [
        "resume_master_id",
        "skill_name",
    ]


def test_resume_relationships_own_section_lifecycle() -> None:
    relationships = ResumeMaster.__mapper__.relationships

    for relationship_name in ("educations", "experiences", "projects", "skills"):
        relationship = relationships[relationship_name]
        assert "delete-orphan" in relationship.cascade
        assert relationship.passive_deletes is False

    user_relationship = User.__mapper__.relationships["resume_master"]
    assert not user_relationship.uselist
    assert "delete-orphan" in user_relationship.cascade
