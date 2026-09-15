"""Resume Tailor draft assembly tests without a database."""

from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.ai.context_builder import build_tailor_context
from app.ai.resume_tailor import ResumeTailorResult
from app.models.job import Job
from app.models.matching import JobMatchResult
from app.services import resume_tailor as resume_tailor_service
from app.services.resume_tailor import (
    GeneratedResumeTailorDraft,
    ResumeTailorSourceInvalidError,
    generate_resume_tailor_draft,
    serialize_resume_tailor_draft,
)
from tests.ai.resume_tailor.test_service import grounded_output
from tests.ai.test_context_builder import parsed_job_output, resume_data


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def source_records() -> tuple[Job, JobMatchResult]:
    resume = resume_data()
    job = Job(
        id=uuid4(),
        user_id=uuid4(),
        company_name="目标公司",
        title="产品运营",
        raw_jd="负责用户行为数据分析并推动产品与运营策略持续优化。",
    )
    result = JobMatchResult(
        id=uuid4(),
        user_id=job.user_id,
        job_id=job.id,
        resume_master_id=resume.id,
        job_parse_result_id=uuid4(),
        eligibility_status="WARN",
        total_score=Decimal("76.00"),
        confidence_score=Decimal("80.00"),
        confidence_level="MEDIUM",
        recommendation_level="STRONG",
        recommendation="条件待核实，核心职责匹配。",
        strengths=["数据分析与流程优化有直接证据"],
        gaps=[
            {
                "requirement_key": "R3",
                "importance": "LOW",
                "gap": "当前材料没有 SQL 使用证据。",
                "improvement_direction": "补充真实 SQL 项目。",
            }
        ],
        resume_snapshot=resume.model_dump(mode="json"),
        job_snapshot={"parsed_job": parsed_job_output().model_dump(mode="json")},
        prompt_version="job_matcher_v1",
        model="matcher-model",
    )
    return job, result


def tailor_result() -> ResumeTailorResult:
    resume = resume_data()
    parsed_job = parsed_job_output()
    context = build_tailor_context(
        resume=resume,
        parsed_job=parsed_job,
        match_strengths=["数据分析与流程优化有直接证据"],
        match_gaps=["当前材料没有 SQL 使用证据。"],
    )
    return ResumeTailorResult(
        output=grounded_output(),
        tailor_input=context,
        skill_name="resume_tailor",
        prompt_version="resume_tailor_v1",
        model="tailor-model",
        attempts=1,
        request_id="req-tailor",
        token_usage=None,
    )


@pytest.mark.anyio
async def test_draft_uses_current_match_snapshots_and_persisted_guidance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job, match_result = source_records()
    session = AsyncMock()
    getter = AsyncMock(return_value=(job, match_result))
    tailored = tailor_result()
    tailor = AsyncMock(return_value=tailored)
    monkeypatch.setattr(resume_tailor_service, "get_job_match_detail", getter)
    monkeypatch.setattr(resume_tailor_service, "tailor_resume", tailor)
    user_id = job.user_id

    generated = await generate_resume_tailor_draft(
        session,
        user_id,
        job.id,
        object(),  # type: ignore[arg-type]
    )

    getter.assert_awaited_once_with(session, user_id, job.id)
    called_resume, called_job = tailor.await_args.args[:2]
    assert called_resume == resume_data()
    assert called_job == parsed_job_output()
    assert tailor.await_args.kwargs["match_strengths"] == match_result.strengths
    assert tailor.await_args.kwargs["match_gaps"] == ["当前材料没有 SQL 使用证据。"]
    assert generated.tailor_result is tailored
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("invalid_field", "invalid_value"),
    [
        ("resume_snapshot", {}),
        ("job_snapshot", {}),
        ("gaps", [{"unexpected": "value"}]),
        ("strengths", {"unexpected": "value"}),
    ],
)
async def test_invalid_immutable_source_snapshot_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    invalid_field: str,
    invalid_value: object,
) -> None:
    job, match_result = source_records()
    setattr(match_result, invalid_field, invalid_value)
    monkeypatch.setattr(
        resume_tailor_service,
        "get_job_match_detail",
        AsyncMock(return_value=(job, match_result)),
    )

    with pytest.raises(ResumeTailorSourceInvalidError):
        await generate_resume_tailor_draft(
            AsyncMock(),
            job.user_id,
            job.id,
            object(),  # type: ignore[arg-type]
        )


def test_draft_response_keeps_source_snapshot_and_trace_metadata() -> None:
    job, match_result = source_records()
    generated = GeneratedResumeTailorDraft(
        job=job,
        match_result=match_result,
        source_resume=resume_data(),
        tailor_result=tailor_result(),
    )

    data = serialize_resume_tailor_draft(generated)

    assert data.job_id == job.id
    assert data.match_result_id == match_result.id
    assert data.resume_master_id == resume_data().id
    assert data.source_resume_snapshot.basic_info.name == "应被移除的姓名"
    assert data.draft.skill_order == [str(resume_data().skills[0].id)]
    assert data.prompt_version == "resume_tailor_v1"
    assert data.model == "tailor-model"
