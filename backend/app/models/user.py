"""User account persistence model."""

from typing import TYPE_CHECKING

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.job import JobMatchBatch
    from app.models.resume import ResumeMaster


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """CareerPilot account owner.

    Authentication email and resume contact email are intentionally separate.
    """

    __tablename__ = "users"
    __table_args__ = (Index("users_email_idx", "email", unique=True),)

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resume_master: Mapped["ResumeMaster | None"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        single_parent=True,
        uselist=False,
    )
    job_match_batches: Mapped[list["JobMatchBatch"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @validates("email")
    def normalize_email(self, _: str, value: str) -> str:
        """Normalize account email before SQLAlchemy persists it."""

        return value.strip().lower()
