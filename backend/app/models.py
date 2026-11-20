"""ORM models. Change the schema with an Alembic migration (see README)."""

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Analysis(Base):
    __tablename__ = "analyses"
    __table_args__ = (
        CheckConstraint("input_mode IN ('file', 'manual')", name="input_mode_valid"),
        CheckConstraint("predicted_outcome IN ('success', 'failure')", name="predicted_outcome_valid"),
        CheckConstraint("probability >= 0 AND probability <= 1", name="probability_range"),
    )

    analysis_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    input_mode: Mapped[Literal["file", "manual"]] = mapped_column(String(16))
    source_name: Mapped[str] = mapped_column(Text)
    # Manual: the validated request (units after defaulting). File: the parsed procedure row.
    input_data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    predicted_outcome: Mapped[Literal["success", "failure"]] = mapped_column(String(16))
    probability: Mapped[float] = mapped_column(Float)
    outcome_definition: Mapped[str] = mapped_column(Text)
    model_version: Mapped[str | None] = mapped_column(String(64))
    performance_metrics: Mapped[dict[str, float] | None] = mapped_column(JSONB)
    # The model the client selected. Empty for rows saved before model selection existed.
    model_name: Mapped[str | None] = mapped_column(String(32))
    # The signed-in account that ran it. Empty for signed-out analyses, which nobody can list.
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), index=True
    )


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Stored lowercased, so the unique index is case-insensitive.
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    organization: Mapped[str] = mapped_column(String(120), default="")
    # scrypt$<n>$<r>$<p>$<salt hex>$<hash hex>; the password itself is never stored.
    password_hash: Mapped[str] = mapped_column(Text)
    # Consecutive wrong passwords; sign-in is locked until locked_until after too many.
    failed_sign_ins: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserSession(Base):
    """A signed-in browser. The cookie holds a random token; only its SHA-256 is stored."""

    __tablename__ = "user_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PasswordResetToken(Base):
    """A single-use password reset link. Only the token's SHA-256 is stored."""

    __tablename__ = "password_reset_tokens"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
