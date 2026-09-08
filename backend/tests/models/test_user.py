"""User model contract tests."""

from sqlalchemy import DateTime, String

from app.models.user import User


def test_user_matches_database_contract() -> None:
    columns = User.__table__.columns

    assert set(columns.keys()) == {
        "id",
        "email",
        "password_hash",
        "name",
        "created_at",
        "updated_at",
    }
    assert columns.id.primary_key
    assert columns.id.default is not None
    assert columns.id.default.is_callable

    assert isinstance(columns.email.type, String)
    assert columns.email.type.length == 320
    assert not columns.email.nullable

    assert isinstance(columns.password_hash.type, String)
    assert columns.password_hash.type.length == 255
    assert not columns.password_hash.nullable

    assert isinstance(columns.name.type, String)
    assert columns.name.type.length == 100
    assert columns.name.nullable

    for timestamp_name in ("created_at", "updated_at"):
        timestamp = columns[timestamp_name]
        assert isinstance(timestamp.type, DateTime)
        assert timestamp.type.timezone
        assert not timestamp.nullable
        assert timestamp.server_default is not None


def test_user_email_index_is_unique_and_named() -> None:
    indexes = {index.name: index for index in User.__table__.indexes}

    assert set(indexes) == {"users_email_idx"}
    assert indexes["users_email_idx"].unique
    assert [column.name for column in indexes["users_email_idx"].columns] == ["email"]


def test_user_normalizes_email_before_persistence() -> None:
    user = User(
        email="  Candidate.Name@Example.COM  ",
        password_hash="not-a-plain-text-password",
    )

    assert user.email == "candidate.name@example.com"
    assert user.name is None
