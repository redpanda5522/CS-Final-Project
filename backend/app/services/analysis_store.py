"""Persist and load analyses."""

from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Analysis
from app.schemas import AnalysisDetail, AnalysisRecord, AnalysisResult


def save_analysis(
    session: Session,
    result: AnalysisResult,
    input_mode: Literal["file", "manual"],
    source_name: str,
    input_data: dict[str, Any],
) -> Analysis:
    analysis = Analysis(
        analysis_id=result.analysisId,
        input_mode=input_mode,
        source_name=source_name,
        input_data=input_data,
        predicted_outcome=result.predictedOutcome,
        probability=result.probability,
        outcome_definition=result.outcomeDefinition,
        model_version=result.modelVersion,
    )
    session.add(analysis)
    session.commit()
    return analysis


def list_analyses(session: Session, limit: int, offset: int) -> list[AnalysisRecord]:
    rows = session.scalars(
        select(Analysis)
        .order_by(Analysis.created_at.desc(), Analysis.analysis_id)
        .limit(limit)
        .offset(offset)
    )
    return [to_record(row) for row in rows]


def get_analysis(session: Session, analysis_id: str) -> AnalysisDetail | None:
    row = session.get(Analysis, analysis_id)
    if row is None:
        return None
    return AnalysisDetail(**to_record(row).model_dump(), input=row.input_data)


def to_record(row: Analysis) -> AnalysisRecord:
    return AnalysisRecord(
        analysisId=row.analysis_id,
        predictedOutcome=row.predicted_outcome,
        probability=row.probability,
        outcomeDefinition=row.outcome_definition,
        modelVersion=row.model_version,
        inputMode=row.input_mode,
        sourceName=row.source_name,
        createdAt=row.created_at,
    )
