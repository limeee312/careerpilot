"""Deterministic truth-boundary checks for Resume Tailor output."""

import re
from collections import Counter
from collections.abc import Iterable

from app.ai.errors import AIInvalidOutputError
from app.ai.resume_tailor.schemas import (
    ResumeTailorOutput,
    SourceExperience,
    SourceProject,
    TailoredBullet,
    TailoredExperience,
    TailoredProject,
    TailorInput,
)

WHITESPACE_PATTERN = re.compile(r"\s+", flags=re.UNICODE)
SENTENCE_BOUNDARY_PATTERN = re.compile(r"[。！？；;\n]+", flags=re.UNICODE)
NUMBER_PATTERN = re.compile(
    r"(?:"
    r"\d+(?:[.,]\d+)*(?:%|％|\+|万亿元|万元|亿元|万|亿|年|个月|月|天|"
    r"小时|人|用户|次|项|个|份|场|条|家|名|倍)?"
    r"|[零〇一二两三四五六七八九十百千万亿]+(?:年|个月|月|天|小时|人|"
    r"用户|次|项|个|份|场|条|家|名|倍)"
    r")"
)
VAGUE_SUMMARY_CLAIMS = (
    "学习能力强",
    "责任心强",
    "热爱互联网",
    "具备优秀沟通能力",
)
WEAK_OWNERSHIP_TERMS = ("参与", "协助", "配合", "支持")
STRONG_OWNERSHIP_TERMS = ("独立负责", "独立完成", "主导", "牵头", "全权负责")
NON_FINAL_STATE_TERMS = ("待评审", "待研发评审", "提案", "原型", "试运行")
FINAL_STATE_TERMS = ("已上线", "正式上线", "正式发布", "投入使用", "取得成果")


def normalize_whitespace(value: str) -> str:
    """Ignore Unicode whitespace while preserving substantive characters."""

    return WHITESPACE_PATTERN.sub("", value)


def _source_text(item: SourceExperience | SourceProject) -> str:
    return "\n".join(
        value for value in (item.description, item.achievements) if value is not None
    )


def _evidence_context(
    source: SourceExperience | SourceProject,
    bullet: TailoredBullet,
) -> str:
    """Return source sentences containing each cited quote."""

    contexts: list[str] = []
    for evidence in bullet.evidence_refs:
        field_value = getattr(source, evidence.source_field)
        if field_value is None:
            continue
        normalized_quote = normalize_whitespace(evidence.source_quote)
        matching_sentences = [
            sentence
            for sentence in SENTENCE_BOUNDARY_PATTERN.split(field_value)
            if normalized_quote in normalize_whitespace(sentence)
        ]
        contexts.extend(matching_sentences or [field_value])
    return "\n".join(contexts)


def _number_tokens(value: str) -> set[str]:
    return {normalize_whitespace(match) for match in NUMBER_PATTERN.findall(value)}


def _validate_source_ids(
    *,
    expected: set[str],
    actual: list[str],
    label: str,
) -> None:
    counts = Counter(actual)
    duplicates = sorted(source_id for source_id, count in counts.items() if count > 1)
    if duplicates:
        raise AIInvalidOutputError(f"{label} contains duplicate source_id values")
    unknown = sorted(set(actual) - expected)
    if unknown:
        raise AIInvalidOutputError(f"{label} references unknown source_id {unknown[0]}")


def _validate_included_order(
    items: Iterable[TailoredExperience | TailoredProject],
    *,
    label: str,
) -> None:
    orders = sorted(
        item.order for item in items if item.include and item.order is not None
    )
    if orders != list(range(1, len(orders) + 1)):
        raise AIInvalidOutputError(
            f"{label} included order must be unique and contiguous"
        )


def _validate_evidence_refs(
    *,
    source: SourceExperience | SourceProject,
    bullet: TailoredBullet,
    label: str,
) -> None:
    for evidence in bullet.evidence_refs:
        field_value = getattr(source, evidence.source_field)
        if field_value is None or normalize_whitespace(
            evidence.source_quote
        ) not in normalize_whitespace(field_value):
            raise AIInvalidOutputError(f"{label} evidence quote is not grounded")


def _validate_numbers(
    *,
    generated: str,
    source: str,
    label: str,
) -> None:
    unsupported = _number_tokens(generated) - _number_tokens(source)
    if unsupported:
        token = sorted(unsupported)[0]
        raise AIInvalidOutputError(f"UNSUPPORTED_NUMBER in {label}: {token}")


def _contains(value: str, terms: Iterable[str]) -> bool:
    return any(term in value for term in terms)


def _validate_claim_strength(
    *,
    generated: str,
    source: str,
    label: str,
) -> None:
    if (
        _contains(source, WEAK_OWNERSHIP_TERMS)
        and _contains(generated, STRONG_OWNERSHIP_TERMS)
        and not _contains(source, STRONG_OWNERSHIP_TERMS)
    ):
        raise AIInvalidOutputError(f"OWNERSHIP_ESCALATION in {label}")

    if (
        _contains(source, NON_FINAL_STATE_TERMS)
        and _contains(generated, FINAL_STATE_TERMS)
        and not _contains(source, FINAL_STATE_TERMS)
    ):
        raise AIInvalidOutputError(f"PROJECT_STATE_ESCALATION in {label}")

    if "团队" in source and _number_tokens(generated) and "团队" not in generated:
        raise AIInvalidOutputError(f"TEAM_RESULT_ATTRIBUTION in {label}")


def _validate_target_tools(
    *,
    generated: str,
    source: str,
    target_tools: list[str],
    label: str,
) -> None:
    normalized_generated = normalize_whitespace(generated).casefold()
    normalized_source = normalize_whitespace(source).casefold()
    for tool in target_tools:
        normalized_tool = normalize_whitespace(tool).casefold()
        if (
            normalized_tool in normalized_generated
            and normalized_tool not in normalized_source
        ):
            raise AIInvalidOutputError(f"UNSUPPORTED_TOOL in {label}: {tool}")


def _validate_tailored_items(
    *,
    source_by_id: dict[str, SourceExperience | SourceProject],
    tailored_items: list[TailoredExperience] | list[TailoredProject],
    target_tools: list[str],
    label: str,
) -> None:
    _validate_source_ids(
        expected=set(source_by_id),
        actual=[item.source_id for item in tailored_items],
        label=label,
    )
    _validate_included_order(tailored_items, label=label)

    for item in tailored_items:
        source = source_by_id[item.source_id]
        complete_source = _source_text(source)
        for index, bullet in enumerate(item.bullets, start=1):
            bullet_label = f"{label} {item.source_id} bullet {index}"
            _validate_evidence_refs(source=source, bullet=bullet, label=bullet_label)
            evidence_context = _evidence_context(source, bullet)
            _validate_numbers(
                generated=bullet.text,
                source=complete_source,
                label=bullet_label,
            )
            _validate_claim_strength(
                generated=bullet.text,
                source=evidence_context,
                label=bullet_label,
            )
            _validate_target_tools(
                generated=bullet.text,
                source=complete_source,
                target_tools=target_tools,
                label=bullet_label,
            )


def validate_resume_tailor_output(
    tailor_input: TailorInput,
    output: ResumeTailorOutput,
) -> ResumeTailorOutput:
    """Reject ungrounded IDs, evidence, metrics, tools, and claim escalation."""

    experience_by_id = {item.source_id: item for item in tailor_input.experiences}
    project_by_id = {item.source_id: item for item in tailor_input.projects}
    _validate_tailored_items(
        source_by_id=experience_by_id,
        tailored_items=output.experiences,
        target_tools=tailor_input.parsed_job.tools,
        label="experiences",
    )
    _validate_tailored_items(
        source_by_id=project_by_id,
        tailored_items=output.projects,
        target_tools=tailor_input.parsed_job.tools,
        label="projects",
    )

    expected_skill_ids = [item.source_id for item in tailor_input.skills]
    if Counter(output.skill_order) != Counter(expected_skill_ids):
        raise AIInvalidOutputError(
            "skill_order must contain every input skill source_id exactly once"
        )

    requirements = {
        normalize_whitespace(item.requirement_text)
        for item in tailor_input.parsed_job.requirements
    }
    for suggestion in output.improvement_suggestions:
        if normalize_whitespace(suggestion.job_requirement) not in requirements:
            raise AIInvalidOutputError(
                "improvement suggestion references an unknown job requirement"
            )

    all_source_text = "\n".join(
        [
            tailor_input.resume_summary or "",
            *(_source_text(item) for item in tailor_input.experiences),
            *(_source_text(item) for item in tailor_input.projects),
            *(item.skill_name for item in tailor_input.skills),
        ]
    )
    if output.professional_summary is not None:
        if _contains(output.professional_summary, VAGUE_SUMMARY_CLAIMS):
            raise AIInvalidOutputError(
                "professional_summary contains an ungrounded claim"
            )
        _validate_numbers(
            generated=output.professional_summary,
            source=all_source_text,
            label="professional_summary",
        )
        _validate_target_tools(
            generated=output.professional_summary,
            source=all_source_text,
            target_tools=tailor_input.parsed_job.tools,
            label="professional_summary",
        )

    return output
