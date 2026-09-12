"""Job Parser v1 orchestration and retry-policy tests."""

from collections.abc import Mapping
from typing import Any

import pytest
from pydantic import BaseModel

from app.ai.client import StructuredAIResponse, TokenUsage
from app.ai.errors import (
    AIConfigurationError,
    AIInvalidOutputError,
    AIProviderError,
    AITimeoutError,
)
from app.ai.job_parser import (
    JOB_PARSER_PROMPT_V1,
    JOB_PARSER_SKILL_NAME,
    JOB_PARSER_VERSION,
    JobParserInput,
    JobParserOutput,
    parse_job,
)
from tests.ai.job_parser.test_schemas import parser_input, parser_output


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
    output: JobParserOutput | None = None,
) -> StructuredAIResponse[JobParserOutput]:
    return StructuredAIResponse(
        output=output or JobParserOutput.model_validate(parser_output()),
        model="test-model",
        request_id="req_parser_test",
        token_usage=TokenUsage(
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        ),
    )


def valid_input() -> JobParserInput:
    return JobParserInput.model_validate(parser_input())


@pytest.mark.anyio
async def test_parse_job_returns_grounded_output_and_trace_metadata() -> None:
    client = StubAIClient(structured_response())

    result = await parse_job(valid_input(), client)

    assert result.output.requirements[0].requirement_key == "R1"
    assert result.skill_name == JOB_PARSER_SKILL_NAME
    assert result.prompt_version == JOB_PARSER_VERSION
    assert result.model == "test-model"
    assert result.attempts == 1
    assert result.request_id == "req_parser_test"
    assert result.token_usage is not None
    assert result.token_usage.total_tokens == 150
    assert len(client.calls) == 1
    assert client.calls[0]["system_prompt"] == JOB_PARSER_PROMPT_V1
    assert client.calls[0]["input_data"] == valid_input()
    assert client.calls[0]["response_model"] is JobParserOutput


@pytest.mark.anyio
async def test_parse_job_retries_once_when_quote_is_not_grounded() -> None:
    invalid_data = parser_output()
    invalid_data["requirements"][0]["source_quote"] = "JD 中不存在的要求"  # type: ignore[index]
    invalid_output = JobParserOutput.model_validate(invalid_data)
    client = StubAIClient(
        structured_response(invalid_output),
        structured_response(),
    )

    result = await parse_job(valid_input(), client)

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
async def test_parse_job_retries_documented_transient_failures(
    first_error: Exception,
) -> None:
    client = StubAIClient(first_error, structured_response())

    result = await parse_job(valid_input(), client)

    assert result.attempts == 2
    assert len(client.calls) == 2


@pytest.mark.anyio
async def test_parse_job_stops_after_one_retry() -> None:
    client = StubAIClient(
        AITimeoutError("first timeout"),
        AITimeoutError("second timeout"),
    )

    with pytest.raises(AITimeoutError, match="second timeout"):
        await parse_job(valid_input(), client)

    assert len(client.calls) == 2


@pytest.mark.anyio
@pytest.mark.parametrize(
    "error",
    [
        AIProviderError("bad request", status_code=400, retryable=False),
        AIProviderError("rate limited", status_code=429, retryable=False),
    ],
)
async def test_parse_job_does_not_retry_non_server_provider_errors(
    error: AIProviderError,
) -> None:
    client = StubAIClient(error, structured_response())

    with pytest.raises(AIProviderError) as captured:
        await parse_job(valid_input(), client)

    assert captured.value is error
    assert len(client.calls) == 1


@pytest.mark.anyio
async def test_parse_job_does_not_catch_configuration_errors() -> None:
    error = AIConfigurationError("model missing")
    client = StubAIClient(error, structured_response())

    with pytest.raises(AIConfigurationError) as captured:
        await parse_job(valid_input(), client)

    assert captured.value is error
    assert len(client.calls) == 1
