"""Application and timeline SQLAlchemy contracts."""

from sqlalchemy import DateTime, Enum, SmallInteger, String, Text

from app.models.application import (
    Application,
    ApplicationEvent,
    ApplicationStage,
    ApplicationStatus,
)
from app.models.user import User


def test_application_matches_database_contract() -> None:
    columns = Application.__table__.columns

    assert set(columns.keys()) == {
        "id",
        "user_id",
        "job_id",
        "resume_version_id",
        "company_name",
        "job_title",
        "job_url",
        "applied_at",
        "current_stage",
        "current_round",
        "process_status",
        "note",
        "created_at",
        "updated_at",
    }
    assert isinstance(columns.company_name.type, String)
    assert columns.company_name.type.length == 200
    assert isinstance(columns.job_title.type, String)
    assert columns.job_title.type.length == 300
    assert isinstance(columns.job_url.type, Text)
    assert isinstance(columns.applied_at.type, DateTime)
    assert isinstance(columns.current_stage.type, Enum)
    assert columns.current_stage.type.enums == [
        stage.value for stage in ApplicationStage
    ]
    assert isinstance(columns.current_round.type, SmallInteger)
    assert isinstance(columns.process_status.type, Enum)
    assert columns.process_status.type.enums == [
        status.value for status in ApplicationStatus
    ]

    foreign_keys = {
        (
            element.parent.name,
            element.target_fullname,
            constraint.ondelete,
        )
        for constraint in Application.__table__.foreign_key_constraints
        for element in constraint.elements
    }
    assert ("user_id", "users.id", "CASCADE") in foreign_keys
    assert ("job_id", "jobs.id", "SET NULL") in foreign_keys
    assert (
        "resume_version_id",
        "resume_versions.id",
        "SET NULL",
    ) in foreign_keys
    assert {index.name for index in Application.__table__.indexes} == {
        "applications_user_status_idx",
        "applications_user_updated_idx",
    }


def test_application_event_owns_flexible_timeline() -> None:
    columns = ApplicationEvent.__table__.columns

    assert isinstance(columns.event_type.type, Enum)
    assert isinstance(columns.custom_event_name.type, String)
    assert columns.custom_event_name.type.length == 200
    assert isinstance(columns.round_no.type, SmallInteger)
    assert isinstance(columns.occurred_at.type, DateTime)
    foreign_key = next(iter(columns.application_id.foreign_keys))
    assert foreign_key.target_fullname == "applications.id"
    assert foreign_key.ondelete == "CASCADE"

    events_relationship = Application.__mapper__.relationships["events"]
    user_relationship = User.__mapper__.relationships["applications"]
    assert "delete-orphan" in events_relationship.cascade
    assert events_relationship.passive_deletes
    assert "delete-orphan" in user_relationship.cascade
