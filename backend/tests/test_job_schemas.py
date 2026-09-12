"""Manual job batch request validation tests."""

import pytest
from pydantic import ValidationError

from app.schemas.job import JobBatchCreate


def valid_job() -> dict[str, object]:
    return {
        "company_name": "  示例科技  ",
        "title": "  产品运营  ",
        "location": "  杭州  ",
        "department": " ",
        "source_url": "https://example.com/jobs/123",
        "raw_jd": (
            "  负责产品用户运营策略制定与执行，通过用户行为数据分析发现问题，"
            "并联动产品、研发和市场团队推进运营项目落地。  "
        ),
    }


def test_job_batch_normalizes_fields_and_accepts_one_to_five_jobs() -> None:
    payload = JobBatchCreate.model_validate(
        {"name": "  秋招重点岗位  ", "jobs": [valid_job()]}
    )

    assert payload.name == "秋招重点岗位"
    assert payload.jobs[0].company_name == "示例科技"
    assert payload.jobs[0].title == "产品运营"
    assert payload.jobs[0].location == "杭州"
    assert payload.jobs[0].department is None
    assert str(payload.jobs[0].source_url) == "https://example.com/jobs/123"
    assert payload.jobs[0].raw_jd.startswith("负责产品用户运营")


@pytest.mark.parametrize("jobs", [[], [valid_job() for _ in range(6)]])
def test_job_batch_rejects_job_count_outside_range(jobs: list[dict]) -> None:
    with pytest.raises(ValidationError):
        JobBatchCreate.model_validate({"jobs": jobs})


def test_job_batch_rejects_short_jd() -> None:
    job = valid_job()
    job["raw_jd"] = "这份职位描述不足五十个字符。"

    with pytest.raises(ValidationError):
        JobBatchCreate.model_validate({"jobs": [job]})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("company_name", " "),
        ("title", " "),
        ("source_url", "not-a-url"),
    ],
)
def test_job_batch_rejects_invalid_required_fields(field: str, value: str) -> None:
    job = valid_job()
    job[field] = value

    with pytest.raises(ValidationError):
        JobBatchCreate.model_validate({"jobs": [job]})


def test_job_batch_rejects_unknown_fields() -> None:
    job = valid_job()
    job["invented_field"] = "not allowed"

    with pytest.raises(ValidationError):
        JobBatchCreate.model_validate({"jobs": [job]})
