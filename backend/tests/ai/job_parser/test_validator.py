"""Job Parser source-quote grounding tests."""

import pytest

from app.ai.errors import AIInvalidOutputError
from app.ai.job_parser.schemas import JobParserInput, JobParserOutput
from app.ai.job_parser.validator import validate_job_parser_output
from tests.ai.job_parser.test_schemas import RAW_JD, parser_output


def valid_input() -> JobParserInput:
    return JobParserInput(
        company_name="示例科技",
        title="产品运营",
        raw_jd=RAW_JD,
    )


def test_grounded_source_quotes_are_accepted() -> None:
    output = JobParserOutput.model_validate(parser_output())

    assert validate_job_parser_output(valid_input(), output) is output


def test_source_quote_comparison_normalizes_unicode_whitespace() -> None:
    data = parser_output()
    data["requirements"][0]["source_quote"] = (  # type: ignore[index]
        "负责产品用户运营策略\n制定 与执行"
    )
    output = JobParserOutput.model_validate(data)

    assert validate_job_parser_output(valid_input(), output) is output


def test_ungrounded_source_quote_raises_stable_ai_error() -> None:
    data = parser_output()
    data["requirements"][2]["source_quote"] = "熟练使用 Python"  # type: ignore[index]
    output = JobParserOutput.model_validate(data)

    with pytest.raises(AIInvalidOutputError) as error:
        validate_job_parser_output(valid_input(), output)

    assert error.value.code == "AI_INVALID_OUTPUT"
    assert "R3" in str(error.value)
