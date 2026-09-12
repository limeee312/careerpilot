"""Resume-Job Matcher v1 orchestration with a single controlled retry."""

from dataclasses import dataclass

from app.ai.client import AIClient, StructuredAIResponse, TokenUsage
from app.ai.context_builder import build_match_context
from app.ai.errors import AIInvalidOutputError, AIProviderError, AITimeoutError
from app.ai.job_matcher.constants import (
    JOB_MATCHER_SKILL_NAME,
    JOB_MATCHER_VERSION,
    MAX_JOB_MATCHER_ATTEMPTS,
)
from app.ai.job_matcher.prompt import JOB_MATCHER_PROMPT_V1
from app.ai.job_matcher.schemas import MatcherInput, MatcherOutput
from app.ai.job_matcher.validator import validate_matcher_output
from app.ai.job_parser.schemas import JobParserOutput
from app.schemas.resume import ResumeMasterData


@dataclass(frozen=True, slots=True)
class JobMatcherResult:
    """Validated Matcher output and metadata needed by future persistence."""

    output: MatcherOutput
    matcher_input: MatcherInput
    skill_name: str
    prompt_version: str
    model: str
    attempts: int
    request_id: str | None
    token_usage: TokenUsage | None


def is_retryable_matcher_error(error: Exception) -> bool:
    """Apply the documented timeout, 5xx, and invalid-output retry policy."""

    return isinstance(error, (AITimeoutError, AIInvalidOutputError)) or (
        isinstance(error, AIProviderError) and error.retryable
    )


async def match_job(
    resume: ResumeMasterData | None,
    parsed_job: JobParserOutput,
    ai_client: AIClient,
) -> JobMatcherResult:
    """Match one redacted resume to one parsed job with one eligible retry."""

    matcher_input = build_match_context(resume=resume, parsed_job=parsed_job)

    for attempt in range(1, MAX_JOB_MATCHER_ATTEMPTS + 1):
        try:
            response: StructuredAIResponse[
                MatcherOutput
            ] = await ai_client.generate_structured(
                system_prompt=JOB_MATCHER_PROMPT_V1,
                input_data=matcher_input,
                response_model=MatcherOutput,
            )
            output = validate_matcher_output(matcher_input, response.output)
        except (AITimeoutError, AIInvalidOutputError, AIProviderError) as error:
            if attempt >= MAX_JOB_MATCHER_ATTEMPTS or not is_retryable_matcher_error(
                error
            ):
                raise
            continue

        return JobMatcherResult(
            output=output,
            matcher_input=matcher_input,
            skill_name=JOB_MATCHER_SKILL_NAME,
            prompt_version=JOB_MATCHER_VERSION,
            model=response.model,
            attempts=attempt,
            request_id=response.request_id,
            token_usage=response.token_usage,
        )

    raise RuntimeError("unreachable Resume-Job Matcher retry state")
