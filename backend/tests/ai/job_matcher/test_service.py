"""Resume-Job Matcher v1 orchestration and retry-policy tests."""

from collections.abc import Mapping
from decimal import Decimal
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
from app.ai.job_matcher import (
    JOB_MATCHER_PROMPT_V1,
    JOB_MATCHER_SKILL_NAME,
    JOB_MATCHER_VERSION,
    MatcherInput,
    MatcherOutput,
    match_job,
)
from tests.ai.job_matcher.test_schemas import matcher_output
from tests.ai.test_context_builder import (
    EDUCATION_ID,
    EXPERIENCE_ID,
    parsed_job_output,
    resume_data,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class StubAIClient:
    """Return or raise queued values while retaining each skill call."""

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


def structured_response(
    output: MatcherOutput | None = None,
) -> StructuredAIResponse[MatcherOutput]:
    if output is None:
        data = matcher_output()
        gate_evidence = data["gate_assessments"][0]["evidence"][0]  # type: ignore[index]
        gate_evidence["source_id"] = str(EDUCATION_ID)
        gate_evidence["source_quote"] = "学历：本科"
        requirement_evidence = data["requirement_assessments"][0]["evidence"][0]  # type: ignore[index]
        requirement_evidence["source_id"] = str(EXPERIENCE_ID)
        requirement_evidence["source_quote"] = "定位流程异常并推动优化"
        output = MatcherOutput.model_validate(data)

    return StructuredAIResponse(
        output=output,
        model="test-model",
        request_id="req_matcher_test",
        token_usage=TokenUsage(
            input_tokens=200,
            output_tokens=100,
            total_tokens=300,
        ),
    )


@pytest.mark.anyio
async def test_match_job_returns_grounded_output_and_trace_metadata() -> None:
    client = StubAIClient(structured_response())

    result = await match_job(resume_data(), parsed_job_output(), client)

    assert result.output.requirement_assessments[0].requirement_key == "R2"
    assert result.score.total_score == Decimal("47.73")
    assert result.score.display_score == 48
    assert result.score.confidence_score == Decimal("63.64")
    assert result.skill_name == JOB_MATCHER_SKILL_NAME
    assert result.prompt_version == JOB_MATCHER_VERSION
    assert result.model == "test-model"
    assert result.attempts == 1
    assert result.request_id == "req_matcher_test"
    assert result.token_usage is not None
    assert result.token_usage.total_tokens == 300
    assert result.matcher_input == client.calls[0]["input_data"]
    assert isinstance(client.calls[0]["input_data"], MatcherInput)
    assert client.calls[0]["system_prompt"] == JOB_MATCHER_PROMPT_V1
    assert client.calls[0]["response_model"] is MatcherOutput


@pytest.mark.anyio
async def test_match_job_retries_once_when_evidence_is_not_grounded() -> None:
    invalid_data = matcher_output()
    invalid_data["requirement_assessments"][0]["evidence"][0][  # type: ignore[index]
        "source_quote"
    ] = "简历中不存在的成果"
    invalid_output = MatcherOutput.model_validate(invalid_data)
    client = StubAIClient(
        structured_response(invalid_output),
        structured_response(),
    )

    result = await match_job(resume_data(), parsed_job_output(), client)

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
async def test_match_job_retries_documented_transient_failures(
    first_error: Exception,
) -> None:
    client = StubAIClient(first_error, structured_response())

    result = await match_job(resume_data(), parsed_job_output(), client)

    assert result.attempts == 2
    assert len(client.calls) == 2


@pytest.mark.anyio
async def test_match_job_stops_after_one_retry() -> None:
    client = StubAIClient(
        AITimeoutError("first timeout"),
        AITimeoutError("second timeout"),
    )

    with pytest.raises(AITimeoutError, match="second timeout"):
        await match_job(resume_data(), parsed_job_output(), client)

    assert len(client.calls) == 2


@pytest.mark.anyio
@pytest.mark.parametrize(
    "error",
    [
        AIProviderError("bad request", status_code=400, retryable=False),
        AIProviderError("rate limited", status_code=429, retryable=False),
    ],
)
async def test_match_job_does_not_retry_non_server_provider_errors(
    error: AIProviderError,
) -> None:
    client = StubAIClient(error, structured_response())

    with pytest.raises(AIProviderError) as captured:
        await match_job(resume_data(), parsed_job_output(), client)

    assert captured.value is error
    assert len(client.calls) == 1


@pytest.mark.anyio
async def test_match_job_does_not_catch_configuration_errors() -> None:
    error = AIConfigurationError("model missing")
    client = StubAIClient(error, structured_response())

    with pytest.raises(AIConfigurationError) as captured:
        await match_job(resume_data(), parsed_job_output(), client)

    assert captured.value is error
    assert len(client.calls) == 1


@pytest.mark.anyio
@pytest.mark.parametrize("resume", [None, resume_data(include_content=False)])
async def test_match_job_rejects_invalid_input_before_calling_provider(
    resume: object,
) -> None:
    client = StubAIClient()

    with pytest.raises(AIInputError):
        await match_job(resume, parsed_job_output(), client)  # type: ignore[arg-type]

    assert client.calls == []
