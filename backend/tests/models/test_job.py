"""Job batch and raw job model contract tests."""

from sqlalchemy import Enum, Integer, String, Text

from app.models.job import BatchStatus, Job, JobMatchBatch
from app.models.user import User


def test_job_batch_matches_database_contract() -> None:
    columns = JobMatchBatch.__table__.columns

    assert set(columns.keys()) == {
        "id",
        "user_id",
        "name",
        "status",
        "total_jobs",
        "successful_jobs",
        "failed_jobs",
        "created_at",
        "updated_at",
    }
    assert columns.id.primary_key
    assert columns.user_id.type.python_type.__name__ == "UUID"
    user_foreign_key = next(iter(columns.user_id.foreign_keys))
    assert user_foreign_key.target_fullname == "users.id"
    assert user_foreign_key.ondelete == "CASCADE"
    assert isinstance(columns.name.type, String)
    assert columns.name.type.length == 200
    assert columns.name.nullable
    assert isinstance(columns.status.type, Enum)
    assert columns.status.type.name == "batch_status"
    assert columns.status.type.enums == [status.value for status in BatchStatus]
    assert not columns.status.nullable

    for counter in ("total_jobs", "successful_jobs", "failed_jobs"):
        assert isinstance(columns[counter].type, Integer)
        assert not columns[counter].nullable
        assert columns[counter].server_default is not None

    constraint_names = {
        constraint.name for constraint in JobMatchBatch.__table__.constraints
    }
    assert {
        "job_match_batches_total_jobs_range_ck",
        "job_match_batches_result_counts_nonnegative_ck",
        "job_match_batches_result_counts_within_total_ck",
        "job_match_batches_id_user_id_key",
    }.issubset(constraint_names)

    indexes = {index.name: index for index in JobMatchBatch.__table__.indexes}
    assert set(indexes) == {"job_match_batches_user_created_idx"}
    index = indexes["job_match_batches_user_created_idx"]
    assert index.expressions[0].name == "user_id"
    assert index.expressions[1].element.name == "created_at"
    assert index.expressions[1].modifier.__name__ == "desc_op"


def test_job_preserves_raw_input_and_owner_scope() -> None:
    columns = Job.__table__.columns

    assert set(columns.keys()) == {
        "id",
        "batch_id",
        "user_id",
        "company_name",
        "title",
        "location",
        "department",
        "source_url",
        "raw_jd",
        "created_at",
        "updated_at",
    }
    assert columns.id.primary_key
    assert not columns.batch_id.nullable
    assert not columns.user_id.nullable

    expected_string_lengths = {
        "company_name": 200,
        "title": 300,
        "location": 200,
        "department": 200,
    }
    for name, length in expected_string_lengths.items():
        assert isinstance(columns[name].type, String)
        assert columns[name].type.length == length
    assert not columns.company_name.nullable
    assert not columns.title.nullable
    assert columns.location.nullable
    assert columns.department.nullable
    assert isinstance(columns.source_url.type, Text)
    assert columns.source_url.nullable
    assert isinstance(columns.raw_jd.type, Text)
    assert not columns.raw_jd.nullable

    foreign_keys = {
        (
            tuple(element.parent.name for element in constraint.elements),
            tuple(element.target_fullname for element in constraint.elements),
            constraint.ondelete,
        )
        for constraint in Job.__table__.foreign_key_constraints
    }
    assert (
        ("batch_id", "user_id"),
        ("job_match_batches.id", "job_match_batches.user_id"),
        "CASCADE",
    ) in foreign_keys
    assert (("user_id",), ("users.id",), "CASCADE") in foreign_keys

    indexes = {index.name: index for index in Job.__table__.indexes}
    assert set(indexes) == {"jobs_batch_id_idx", "jobs_user_id_idx"}


def test_job_relationships_own_batch_lifecycle() -> None:
    jobs_relationship = JobMatchBatch.__mapper__.relationships["jobs"]
    user_relationship = User.__mapper__.relationships["job_match_batches"]

    assert "delete-orphan" in jobs_relationship.cascade
    assert jobs_relationship.order_by
    assert "delete-orphan" in user_relationship.cascade
