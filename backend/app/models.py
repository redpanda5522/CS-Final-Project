"""ORM models. Change the schema with an Alembic migration (see README)."""

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import CheckConstraint, DateTime, Float, String, Text, func
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
