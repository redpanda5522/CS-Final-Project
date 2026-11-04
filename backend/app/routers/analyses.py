"""Procedure outcome analysis endpoints used by the frontend.

Handlers are sync functions so FastAPI runs them, and their blocking database
and parsing work, in its threadpool.
"""

import json
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import AnalysisDetail, AnalysisRecord, AnalysisResult, ManualAnalysisRequest
from app.services import analysis_store, predictor
from app.services.file_parser import MAX_UPLOAD_BYTES, FileParseError, parse_procedure_file

router = APIRouter(prefix="/api/analyses", tags=["analyses"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/file", response_model_exclude_none=True)
def analyze_file(file: UploadFile, session: SessionDep) -> AnalysisResult:
    """Analyze one procedure from an uploaded .csv, .json, or .xlsx file."""
    # Read one byte past the limit so an oversized upload is detected without reading all of it.
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    try:
        row = parse_procedure_file(file.filename, content)
    except FileParseError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error
    result = predictor.predict_from_file(row)
    # to_json converts NaN to null and NumPy scalars to plain JSON values.
    input_data = json.loads(row.to_json(orient="records"))[0]
    _save(session, result, "file", file.filename or "Uploaded file", input_data)
    return result


@router.post("/manual", response_model_exclude_none=True)
def analyze_manual(request: ManualAnalysisRequest, session: SessionDep) -> AnalysisResult:
    """Analyze one procedure from manually entered catheter measurements."""
    result = predictor.predict_from_manual(request)
    _save(session, result, "manual", "Manual entry", request.model_dump(mode="json"))
    return result


@router.get("", response_model_exclude_none=True)
def list_analyses(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AnalysisRecord]:
    """List saved analyses, newest first."""
    return analysis_store.list_analyses(session, limit, offset)


@router.get("/{analysis_id}", response_model_exclude_none=True)
def get_analysis(analysis_id: str, session: SessionDep) -> AnalysisDetail:
    """Return one saved analysis, including its submitted input."""
    analysis = analysis_store.get_analysis(session, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return analysis


def _save(
    session: Session,
    result: AnalysisResult,
    input_mode: Literal["file", "manual"],
    source_name: str,
    input_data: dict[str, Any],
) -> None:
    # Do not return a prediction the user cannot find again later.
    try:
        analysis_store.save_analysis(session, result, input_mode, source_name, input_data)
    except SQLAlchemyError as error:
        session.rollback()
        raise HTTPException(
            status_code=503, detail="The analysis could not be saved. Please try again."
        ) from error
