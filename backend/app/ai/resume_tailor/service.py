"""Resume Tailor v1 orchestration with a single controlled retry."""

from dataclasses import dataclass

from app.ai.client import AIClient, StructuredAIResponse, TokenUsage
from app.ai.context_builder import build_tailor_context
from app.ai.errors import AIInvalidOutputError, AIProviderError, AITimeoutError
from app.ai.job_parser.schemas import JobParserOutput
from app.ai.resume_tailor.constants import (
    MAX_RESUME_TAILOR_ATTEMPTS,
    RESUME_TAILOR_SKILL_NAME,
    RESUME_TAILOR_VERSION,
)
from app.ai.resume_tailor.prompt import RESUME_TAILOR_PROMPT_V1
from app.ai.resume_tailor.schemas import ResumeTailorOutput, TailorInput
from app.ai.resume_tailor.validator import validate_resume_tailor_output
from app.schemas.resume import ResumeMasterData


@dataclass(frozen=True, slots=True)
class ResumeTailorResult:
    """Validated draft plus trace metadata for later version persistence."""

    output: ResumeTailorOutput
    tailor_input: TailorInput
    skill_name: str
    prompt_version: str
    model: str
    attempts: int
    request_id: str | None
    token_usage: TokenUsage | None


def is_retryable_tailor_error(error: Exception) -> bool:
    """Apply the documented timeout, 5xx, and invalid-output retry policy."""

    return isinstance(error, (AITimeoutError, AIInvalidOutputError)) or (
        isinstance(error, AIProviderError) and error.retryable
    )


async def tailor_resume(
    resume: ResumeMasterData | None,
    parsed_job: JobParserOutput,
    *,
    match_strengths: list[str],
    match_gaps: list[str],
    ai_client: AIClient,
) -> ResumeTailorResult:
    """Create one validated draft without persisting or mutating its sources."""

    tailor_input = build_tailor_context(
        resume=resume,
        parsed_job=parsed_job,
        match_strengths=match_strengths,
        match_gaps=match_gaps,
    )

    for attempt in range(1, MAX_RESUME_TAILOR_ATTEMPTS + 1):
        try:
            response: StructuredAIResponse[
                ResumeTailorOutput
            ] = await ai_client.generate_structured(
                system_prompt=RESUME_TAILOR_PROMPT_V1,
                input_data=tailor_input,
                response_model=ResumeTailorOutput,
            )
            output = validate_resume_tailor_output(tailor_input, response.output)
        except (AITimeoutError, AIInvalidOutputError, AIProviderError) as error:
            if attempt >= MAX_RESUME_TAILOR_ATTEMPTS or not is_retryable_tailor_error(
                error
            ):
                raise
            continue

        return ResumeTailorResult(
            output=output,
            tailor_input=tailor_input,
            skill_name=RESUME_TAILOR_SKILL_NAME,
            prompt_version=RESUME_TAILOR_VERSION,
            model=response.model,
            attempts=attempt,
            request_id=response.request_id,
            token_usage=response.token_usage,
        )

    raise RuntimeError("unreachable Resume Tailor retry state")
