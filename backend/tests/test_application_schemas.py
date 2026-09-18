"""Application request validation and stage semantics."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.application import ApplicationStage, ApplicationStatus
from app.schemas.application import (
    ApplicationCreate,
    ApplicationEventCreate,
    ApplicationStatusUpdate,
)


def test_create_accepts_date_only_manual_snapshot() -> None:
    payload = ApplicationCreate.model_validate(
        {
            "company_name": "  示例科技  ",
            "job_title": "  产品运营  ",
            "applied_at": "2026-09-18",
        }
    )

    assert payload.company_name == "示例科技"
    assert payload.job_title == "产品运营"
    assert payload.applied_at == datetime(2026, 9, 18, tzinfo=UTC)


def test_manual_create_requires_snapshot_labels() -> None:
    with pytest.raises(ValidationError):
        ApplicationCreate.model_validate(
            {"company_name": "示例科技", "applied_at": "2026-09-18"}
        )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {
                "event_type": "INTERVIEW",
                "occurred_at": "2026-09-18T10:00:00+08:00",
            },
            "round_no",
        ),
        (
            {
                "event_type": "OTHER",
                "occurred_at": "2026-09-18T10:00:00+08:00",
            },
            "custom_event_name",
        ),
        (
            {
                "event_type": "ASSESSMENT",
                "round_no": 1,
                "occurred_at": "2026-09-18T10:00:00+08:00",
            },
            "round_no",
        ),
    ],
)
def test_event_details_match_stage(payload: dict, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        ApplicationEventCreate.model_validate(payload)


def test_terminal_status_requires_explicit_interview_round() -> None:
    with pytest.raises(ValidationError, match="current_stage"):
        ApplicationStatusUpdate(process_status=ApplicationStatus.REJECTED)

    update = ApplicationStatusUpdate(
        process_status=ApplicationStatus.REJECTED,
        current_stage=ApplicationStage.INTERVIEW,
        current_round=1,
    )
    assert update.current_round == 1
