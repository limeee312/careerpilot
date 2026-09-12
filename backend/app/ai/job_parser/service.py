"""Job Parser v1 orchestration with a single controlled retry."""

from dataclasses import dataclass

from app.ai.client import AIClient, StructuredAIResponse, TokenUsage
from app.ai.errors import AIInvalidOutputError, AIProviderError, AITimeoutError
from app.ai.job_parser.constants import (
    JOB_PARSER_SKILL_NAME,
    JOB_PARSER_VERSION,
    MAX_JOB_PARSER_ATTEMPTS,
)
from app.ai.job_parser.prompt import JOB_PARSER_PROMPT_V1
from app.ai.job_parser.schemas import JobParserInput, JobParserOutput
from app.ai.job_parser.validator import validate_job_parser_output


@dataclass(frozen=True, slots=True)
class JobParserResult:
    """Validated parser output and metadata needed by future persistence."""

    output: JobParserOutput
    skill_name: str
    prompt_version: str
    model: str
    attempts: int
    request_id: str | None
    token_usage: TokenUsage | None


def is_retryable_parser_error(error: Exception) -> bool:
    """Apply the documented timeout, 5xx, and invalid-output retry policy."""

    return isinstance(error, (AITimeoutError, AIInvalidOutputError)) or (
        isinstance(error, AIProviderError) and error.retryable
    )


async def parse_job(
    parser_input: JobParserInput,
    ai_client: AIClient,
) -> JobParserResult:
    """Parse and ground one JD, retrying one eligible failure at most once."""

    for attempt in range(1, MAX_JOB_PARSER_ATTEMPTS + 1):
        try:
            response: StructuredAIResponse[
                JobParserOutput
            ] = await ai_client.generate_structured(
                system_prompt=JOB_PARSER_PROMPT_V1,
                input_data=parser_input,
                response_model=JobParserOutput,
            )
            output = validate_job_parser_output(parser_input, response.output)
        except (AITimeoutError, AIInvalidOutputError, AIProviderError) as error:
            if attempt >= MAX_JOB_PARSER_ATTEMPTS or not is_retryable_parser_error(
                error
            ):
                raise
            continue

        return JobParserResult(
            output=output,
            skill_name=JOB_PARSER_SKILL_NAME,
            prompt_version=JOB_PARSER_VERSION,
            model=response.model,
            attempts=attempt,
            request_id=response.request_id,
            token_usage=response.token_usage,
        )

    raise RuntimeError("unreachable Job Parser retry state")
