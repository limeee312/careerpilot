"""OpenAI Responses API adapter tests without live provider calls."""

import json
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock

import httpx2
import pytest
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI
from pydantic import ValidationError

from app.ai.client import OpenAIResponsesClient
from app.ai.errors import (
    AIConfigurationError,
    AIInvalidOutputError,
    AIProviderError,
    AITimeoutError,
)
from app.ai.job_parser.schemas import JobParserInput, JobParserOutput
from tests.ai.job_parser.test_schemas import parser_input, parser_output


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def openai_adapter(parse_result: object) -> tuple[OpenAIResponsesClient, AsyncMock]:
    parse = AsyncMock(return_value=parse_result)
    provider = Mock()
    provider.responses.parse = parse
    adapter = OpenAIResponsesClient(
        api_key="server-secret",
        default_model="configured-model",
        client=cast(AsyncOpenAI, provider),
    )
    return adapter, parse


def provider_response(*, output: JobParserOutput | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        output_parsed=output,
        model="resolved-model",
        _request_id="req_job_parser_1",
        usage=SimpleNamespace(
            input_tokens=101,
            output_tokens=42,
            total_tokens=143,
        ),
    )


@pytest.mark.anyio
async def test_adapter_requests_strict_output_and_returns_trace_metadata() -> None:
    parsed_output = JobParserOutput.model_validate(parser_output())
    adapter, parse = openai_adapter(provider_response(output=parsed_output))
    input_value = JobParserInput.model_validate(parser_input())

    result = await adapter.generate_structured(
        system_prompt="parser instructions",
        input_data=input_value,
        response_model=JobParserOutput,
    )

    assert result.output == parsed_output
    assert result.model == "resolved-model"
    assert result.request_id == "req_job_parser_1"
    assert result.token_usage is not None
    assert result.token_usage.total_tokens == 143
    parse.assert_awaited_once()
    call = parse.await_args.kwargs
    assert call["model"] == "configured-model"
    assert call["instructions"] == "parser instructions"
    assert call["text_format"] is JobParserOutput
    assert call["store"] is False
    assert json.loads(call["input"]) == input_value.model_dump(mode="json")


@pytest.mark.anyio
async def test_adapter_allows_an_explicit_model_override() -> None:
    output = JobParserOutput.model_validate(parser_output())
    adapter, parse = openai_adapter(provider_response(output=output))

    await adapter.generate_structured(
        system_prompt="parser instructions",
        input_data=parser_input(),
        response_model=JobParserOutput,
        model="one-off-model",
    )

    assert parse.await_args.kwargs["model"] == "one-off-model"


@pytest.mark.parametrize(
    ("api_key", "model"),
    [("", "configured-model"), ("server-secret", "")],
)
def test_adapter_rejects_missing_server_configuration(
    api_key: str,
    model: str,
) -> None:
    with pytest.raises(AIConfigurationError):
        OpenAIResponsesClient(api_key=api_key, default_model=model)


@pytest.mark.anyio
async def test_adapter_maps_provider_timeout_to_stable_error() -> None:
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    adapter, parse = openai_adapter(provider_response())
    parse.side_effect = APITimeoutError(request)

    with pytest.raises(AITimeoutError) as captured:
        await adapter.generate_structured(
            system_prompt="parser instructions",
            input_data=parser_input(),
            response_model=JobParserOutput,
        )

    assert captured.value.retryable is True


@pytest.mark.anyio
@pytest.mark.parametrize(("status_code", "retryable"), [(500, True), (429, False)])
async def test_adapter_only_marks_server_status_errors_as_retryable(
    status_code: int,
    retryable: bool,
) -> None:
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx2.Response(status_code, request=request)
    adapter, parse = openai_adapter(provider_response())
    parse.side_effect = APIStatusError(
        "provider failure",
        response=response,
        body={},
    )

    with pytest.raises(AIProviderError) as captured:
        await adapter.generate_structured(
            system_prompt="parser instructions",
            input_data=parser_input(),
            response_model=JobParserOutput,
        )

    assert captured.value.status_code == status_code
    assert captured.value.retryable is retryable


@pytest.mark.anyio
async def test_adapter_does_not_retry_connection_failures_at_skill_boundary() -> None:
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    adapter, parse = openai_adapter(provider_response())
    parse.side_effect = APIConnectionError(request=request)

    with pytest.raises(AIProviderError) as captured:
        await adapter.generate_structured(
            system_prompt="parser instructions",
            input_data=parser_input(),
            response_model=JobParserOutput,
        )

    assert captured.value.retryable is False


@pytest.mark.anyio
async def test_adapter_maps_schema_validation_failure_to_invalid_output() -> None:
    try:
        JobParserOutput.model_validate({})
    except ValidationError as validation_error:
        provider_error = validation_error

    adapter, parse = openai_adapter(provider_response())
    parse.side_effect = provider_error

    with pytest.raises(AIInvalidOutputError):
        await adapter.generate_structured(
            system_prompt="parser instructions",
            input_data=parser_input(),
            response_model=JobParserOutput,
        )


@pytest.mark.anyio
async def test_adapter_rejects_empty_structured_output() -> None:
    adapter, _ = openai_adapter(provider_response(output=None))

    with pytest.raises(AIProviderError) as captured:
        await adapter.generate_structured(
            system_prompt="parser instructions",
            input_data=parser_input(),
            response_model=JobParserOutput,
        )

    assert captured.value.retryable is False
