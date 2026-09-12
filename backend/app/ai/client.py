"""Provider-neutral structured generation contract and OpenAI adapter."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, TypeVar

from openai import (
    APIConnectionError,
    APIResponseValidationError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    ContentFilterFinishReasonError,
    LengthFinishReasonError,
)
from pydantic import BaseModel, ValidationError

from app.ai.errors import (
    AIConfigurationError,
    AIInvalidOutputError,
    AIProviderError,
    AITimeoutError,
)
from app.config import Settings, get_settings

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Provider token counts retained for later AI run persistence."""

    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True, slots=True)
class StructuredAIResponse[ResponseModelT]:
    """Trusted Pydantic output plus provider trace metadata."""

    output: ResponseModelT
    model: str
    request_id: str | None = None
    token_usage: TokenUsage | None = None


class AIClient(Protocol):
    """Stable interface used by every CareerPilot AI skill."""

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        input_data: BaseModel | Mapping[str, object],
        response_model: type[ResponseModelT],
        model: str | None = None,
    ) -> StructuredAIResponse[ResponseModelT]: ...


class OpenAIResponsesClient:
    """Structured Outputs implementation backed by the OpenAI Responses API."""

    def __init__(
        self,
        *,
        api_key: str,
        default_model: str,
        timeout_seconds: float = 30.0,
        client: AsyncOpenAI | None = None,
    ) -> None:
        normalized_key = api_key.strip()
        normalized_model = default_model.strip()
        if not normalized_key:
            raise AIConfigurationError("OPENAI_API_KEY is not configured")
        if not normalized_model:
            raise AIConfigurationError("OPENAI_MODEL is not configured")

        self.default_model = normalized_model
        self._client = client or AsyncOpenAI(
            api_key=normalized_key,
            timeout=timeout_seconds,
            max_retries=0,
        )

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "OpenAIResponsesClient":
        """Build a provider client only from server-side settings."""

        resolved = settings or get_settings()
        api_key = (
            resolved.openai_api_key.get_secret_value()
            if resolved.openai_api_key is not None
            else ""
        )
        return cls(
            api_key=api_key,
            default_model=resolved.openai_model or "",
            timeout_seconds=resolved.openai_timeout_seconds,
        )

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        input_data: BaseModel | Mapping[str, object],
        response_model: type[ResponseModelT],
        model: str | None = None,
    ) -> StructuredAIResponse[ResponseModelT]:
        """Generate one strict Pydantic response without SDK-level retries."""

        selected_model = (model or self.default_model).strip()
        if not selected_model:
            raise AIConfigurationError("OPENAI_MODEL is not configured")

        input_payload = (
            input_data.model_dump(mode="json")
            if isinstance(input_data, BaseModel)
            else dict(input_data)
        )

        try:
            response = await self._client.responses.parse(
                model=selected_model,
                instructions=system_prompt,
                input=json.dumps(input_payload, ensure_ascii=False),
                text_format=response_model,
                store=False,
            )
        except APITimeoutError as error:
            raise AITimeoutError("OpenAI request timed out") from error
        except (
            ValidationError,
            APIResponseValidationError,
            LengthFinishReasonError,
        ) as error:
            raise AIInvalidOutputError(
                "OpenAI response did not satisfy the structured output contract"
            ) from error
        except ContentFilterFinishReasonError as error:
            raise AIProviderError(
                "OpenAI response was blocked by a content filter"
            ) from error
        except APIStatusError as error:
            raise AIProviderError(
                f"OpenAI returned HTTP {error.status_code}",
                status_code=error.status_code,
                retryable=error.status_code >= 500,
            ) from error
        except APIConnectionError as error:
            raise AIProviderError("OpenAI connection failed") from error

        parsed = response.output_parsed
        if parsed is None:
            raise AIProviderError("OpenAI returned no structured output")

        try:
            output = response_model.model_validate(parsed)
        except ValidationError as error:
            raise AIInvalidOutputError(
                "OpenAI response did not satisfy the structured output contract"
            ) from error

        usage = response.usage
        token_usage = (
            TokenUsage(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
            )
            if usage is not None
            else None
        )
        return StructuredAIResponse(
            output=output,
            model=str(response.model),
            request_id=getattr(response, "_request_id", None),
            token_usage=token_usage,
        )
