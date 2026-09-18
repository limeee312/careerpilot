"""User-owned job applications and their flexible timeline events."""

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class ApplicationStage(StrEnum):
    """Supported hiring stages while still allowing a named OTHER event."""

    APPLICATION = "APPLICATION"
    RESUME_SCREEN = "RESUME_SCREEN"
    ASSESSMENT = "ASSESSMENT"
    WRITTEN_TEST = "WRITTEN_TEST"
    AI_INTERVIEW = "AI_INTERVIEW"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    OTHER = "OTHER"


class ApplicationStatus(StrEnum):
    """Lifecycle state of the full hiring process."""

    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    OFFER = "OFFER"
    WITHDRAWN = "WITHDRAWN"


class ApplicationEventOutcome(StrEnum):
    """Optional outcome attached to a timeline event."""

    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


def _stage_enum(name: str) -> SQLAlchemyEnum:
    return SQLAlchemyEnum(
        ApplicationStage,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=30,
    )


class Application(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A durable application snapshot optionally linked to source records."""

    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint(
            "current_round IS NULL OR current_round > 0",
            name="applications_current_round_positive_ck",
        ),
        CheckConstraint(
            "(current_stage = 'INTERVIEW' AND current_round IS NOT NULL) OR "
            "(current_stage <> 'INTERVIEW' AND current_round IS NULL)",
            name="applications_interview_round_ck",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    resume_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    job_title: Mapped[str] = mapped_column(String(300), nullable=False)
    job_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    current_stage: Mapped[ApplicationStage] = mapped_column(
        _stage_enum("application_stage"),
        default=ApplicationStage.APPLICATION,
        server_default=ApplicationStage.APPLICATION.value,
        nullable=False,
    )
    current_round: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    process_status: Mapped[ApplicationStatus] = mapped_column(
        SQLAlchemyEnum(
            ApplicationStatus,
            name="application_status",
            native_enum=False,
            create_constraint=True,
            length=20,
        ),
        default=ApplicationStatus.ACTIVE,
        server_default=ApplicationStatus.ACTIVE.value,
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="applications")
    events: Mapped[list["ApplicationEvent"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=lambda: (
            ApplicationEvent.occurred_at,
            ApplicationEvent.created_at,
        ),
    )


Index(
    "applications_user_status_idx",
    Application.user_id,
    Application.process_status,
)
Index(
    "applications_user_updated_idx",
    Application.user_id,
    Application.updated_at.desc(),
)


class ApplicationEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One ordered milestone in an application's hiring timeline."""

    __tablename__ = "application_events"
    __table_args__ = (
        CheckConstraint(
            "round_no IS NULL OR round_no > 0",
            name="application_events_round_positive_ck",
        ),
        CheckConstraint(
            "(event_type = 'INTERVIEW' AND round_no IS NOT NULL) OR "
            "(event_type <> 'INTERVIEW' AND round_no IS NULL)",
            name="application_events_interview_round_ck",
        ),
        CheckConstraint(
            "event_type <> 'OTHER' OR "
            "(custom_event_name IS NOT NULL AND length(trim(custom_event_name)) > 0)",
            name="application_events_other_name_ck",
        ),
    )

    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[ApplicationStage] = mapped_column(
        _stage_enum("application_event_type"),
        nullable=False,
    )
    custom_event_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    round_no: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    outcome: Mapped[ApplicationEventOutcome | None] = mapped_column(
        SQLAlchemyEnum(
            ApplicationEventOutcome,
            name="application_event_outcome",
            native_enum=False,
            create_constraint=True,
            length=30,
        ),
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    application: Mapped[Application] = relationship(back_populates="events")


Index(
    "application_events_application_occurred_idx",
    ApplicationEvent.application_id,
    ApplicationEvent.occurred_at,
)
