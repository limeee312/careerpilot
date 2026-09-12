"""Deterministic trust-boundary checks for Job Parser output."""

import re

from app.ai.errors import AIInvalidOutputError
from app.ai.job_parser.schemas import JobParserInput, JobParserOutput

WHITESPACE_PATTERN = re.compile(r"\s+", flags=re.UNICODE)


def normalize_quote_whitespace(value: str) -> str:
    """Ignore Unicode whitespace while preserving every substantive character."""

    return WHITESPACE_PATTERN.sub("", value)


def validate_job_parser_output(
    parser_input: JobParserInput,
    output: JobParserOutput,
) -> JobParserOutput:
    """Reject any requirement quote that cannot be located in the raw JD."""

    normalized_jd = normalize_quote_whitespace(parser_input.raw_jd)
    for requirement in output.requirements:
        normalized_quote = normalize_quote_whitespace(requirement.source_quote)
        if normalized_quote not in normalized_jd:
            raise AIInvalidOutputError(
                f"{requirement.requirement_key} source_quote is not grounded in raw_jd"
            )
    return output
