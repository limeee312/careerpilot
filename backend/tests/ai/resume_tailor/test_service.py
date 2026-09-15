"""Resume Tailor v1 orchestration and retry-policy tests."""

from collections.abc import Mapping
from typing import Any

import pytest
from pydantic import BaseModel

from app.ai.client import StructuredAIResponse, TokenUsage
from app.ai.errors import (
    AIConfigurationError,
    AIInputError,
    AIInvalidOutputError,
    AIProviderError,
    AITimeoutError,
)
from app.ai.resume_tailor import (
    RESUME_TAILOR_PROMPT_V1,
    RESUME_TAILOR_SKILL_NAME,
    RESUME_TAILOR_VERSION,
    ResumeTailorOutput,
    TailorInput,
    tailor_resume,
)
from tests.ai.job_matcher.test_schemas import parsed_job
from tests.ai.test_context_builder import (
    EXPERIENCE_ID,
    PROJECT_ID,
    SKILL_ID,
    parsed_job_output,
    resume_data,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class StubAIClient:
    """Return or raise queued values while retaining every call."""

    def __init__(self, *results: object) -> None:
        self.results = list(results)
        self.calls: list[dict[str, object]] = []

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        input_data: BaseModel | Mapping[str, object],
        response_model: type[BaseModel],
        model: str | None = None,
    ) -> StructuredAIResponse[Any]:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "input_data": input_data,
                "response_model": response_model,
                "model": model,
            }
        )
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result  # type: ignore[return-value]


def grounded_output() -> ResumeTailorOutput:
    return ResumeTailorOutput.model_validate(
        {
            "professional_summary": "具备数据分析与流程优化实践。",
            "experiences": [
                {
                    "source_id": str(EXPERIENCE_ID),
                    "include": True,
                    "order": 1,
                    "bullets": [
                        {
                            "text": (
                                "梳理近三年业务需求及全流程耗时数据，"
                                "定位流程异常并推动优化。"
                            ),
                            "evidence_refs": [
                                {
                                    "source_field": "description",
                                    "source_quote": (
                                        "梳理近三年业务需求及全流程耗时数据"
                                    ),
                                },
                                {
                                    "source_field": "achievements",
                                    "source_quote": "定位流程异常并推动优化",
                                },
                            ],
                        }
                    ],
                }
            ],
            "projects": [
                {
                    "source_id": str(PROJECT_ID),
                    "include": True,
                    "order": 1,
                    "bullets": [
                        {
                            "text": (
                                "设计数据周报 PRD，形成自动化质量监控方案并"
                                "推进研发评审。"
                            ),
                            "evidence_refs": [
                                {
                                    "source_field": "description",
                                    "source_quote": "设计数据周报 PRD",
                                },
                                {
                                    "source_field": "achievements",
                                    "source_quote": (
                                        "形成自动化质量监控方案并推进研发评审"
                                    ),
                                },
                            ],
                        }
                    ],
                }
            ],
            "skill_order": [str(SKILL_ID)],
            "improvement_suggestions": [
                {
                    "job_requirement": "熟悉 SQL",
                    "current_status": "NO_EVIDENCE",
                    "suggestion": "完成真实 SQL 项目后再补充相关经历。",
                    "do_not_claim_yet": True,
                }
            ],
            "warnings": ["SQL 尚无证据，未加入正式简历内容。"],
        }
    )


def structured_response(
    output: ResumeTailorOutput | None = None,
) -> StructuredAIResponse[ResumeTailorOutput]:
    return StructuredAIResponse(
        output=output or grounded_output(),
        model="test-model",
        request_id="req_tailor_test",
        token_usage=TokenUsage(
            input_tokens=300,
            output_tokens=180,
            total_tokens=480,
        ),
    )


@pytest.mark.anyio
async def test_tailor_resume_returns_grounded_draft_and_trace_metadata() -> None:
    client = StubAIClient(structured_response())

    result = await tailor_resume(
        resume_data(),
        parsed_job_output(),
        match_strengths=["数据分析与流程优化有直接证据"],
        match_gaps=["当前材料没有 SQL 使用证据。"],
        ai_client=client,
    )

    assert result.output.experiences[0].source_id == str(EXPERIENCE_ID)
    assert result.skill_name == RESUME_TAILOR_SKILL_NAME
    assert result.prompt_version == RESUME_TAILOR_VERSION
    assert result.model == "test-model"
    assert result.attempts == 1
    assert result.request_id == "req_tailor_test"
    assert result.token_usage is not None
    assert result.token_usage.total_tokens == 480
    assert result.tailor_input == client.calls[0]["input_data"]
    assert isinstance(client.calls[0]["input_data"], TailorInput)
    assert client.calls[0]["system_prompt"] == RESUME_TAILOR_PROMPT_V1
    assert client.calls[0]["response_model"] is ResumeTailorOutput


@pytest.mark.anyio
async def test_tailor_resume_retries_once_when_draft_is_not_grounded() -> None:
    invalid = grounded_output().model_copy(deep=True)
    invalid.experiences[0].bullets[0].text = "推动流程优化，使效率提升30%。"
    client = StubAIClient(structured_response(invalid), structured_response())

    result = await tailor_resume(
        resume_data(),
        parsed_job_output(),
        match_strengths=[],
        match_gaps=[],
        ai_client=client,
    )

    assert result.attempts == 2
    assert len(client.calls) == 2


@pytest.mark.anyio
@pytest.mark.parametrize(
    "first_error",
    [
        AITimeoutError("timed out"),
        AIInvalidOutputError("invalid schema"),
        AIProviderError("server failed", status_code=503, retryable=True),
    ],
)
async def test_tailor_resume_retries_documented_transient_failures(
    first_error: Exception,
) -> None:
    client = StubAIClient(first_error, structured_response())

    result = await tailor_resume(
        resume_data(),
        parsed_job_output(),
        match_strengths=[],
        match_gaps=[],
        ai_client=client,
    )

    assert result.attempts == 2
    assert len(client.calls) == 2


@pytest.mark.anyio
async def test_tailor_resume_stops_after_one_retry() -> None:
    client = StubAIClient(
        AITimeoutError("first timeout"),
        AITimeoutError("second timeout"),
    )

    with pytest.raises(AITimeoutError, match="second timeout"):
        await tailor_resume(
            resume_data(),
            parsed_job_output(),
            match_strengths=[],
            match_gaps=[],
            ai_client=client,
        )

    assert len(client.calls) == 2


@pytest.mark.anyio
@pytest.mark.parametrize(
    "error",
    [
        AIProviderError("bad request", status_code=400, retryable=False),
        AIProviderError("rate limited", status_code=429, retryable=False),
    ],
)
async def test_tailor_resume_does_not_retry_non_server_provider_errors(
    error: AIProviderError,
) -> None:
    client = StubAIClient(error, structured_response())

    with pytest.raises(AIProviderError) as captured:
        await tailor_resume(
            resume_data(),
            parsed_job_output(),
            match_strengths=[],
            match_gaps=[],
            ai_client=client,
        )

    assert captured.value is error
    assert len(client.calls) == 1


@pytest.mark.anyio
async def test_tailor_resume_does_not_catch_configuration_errors() -> None:
    error = AIConfigurationError("model missing")
    client = StubAIClient(error, structured_response())

    with pytest.raises(AIConfigurationError) as captured:
        await tailor_resume(
            resume_data(),
            parsed_job_output(),
            match_strengths=[],
            match_gaps=[],
            ai_client=client,
        )

    assert captured.value is error
    assert len(client.calls) == 1


@pytest.mark.anyio
@pytest.mark.parametrize("resume", [None, resume_data(include_content=False)])
async def test_tailor_resume_rejects_invalid_input_before_provider_call(
    resume: object,
) -> None:
    client = StubAIClient()

    with pytest.raises(AIInputError):
        await tailor_resume(
            resume,  # type: ignore[arg-type]
            parsed_job_output(),
            match_strengths=[],
            match_gaps=[],
            ai_client=client,
        )

    assert client.calls == []


@pytest.mark.anyio
async def test_tailor_resume_rejects_job_without_requirements_before_call() -> None:
    job = parsed_job()
    job["requirements"] = []
    client = StubAIClient()

    with pytest.raises(AIInputError, match="no requirements"):
        await tailor_resume(
            resume_data(),
            type(parsed_job_output()).model_validate(job),
            match_strengths=[],
            match_gaps=[],
            ai_client=client,
        )

    assert client.calls == []
