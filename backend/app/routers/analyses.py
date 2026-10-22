"""Procedure outcome analysis endpoints used by the frontend.

Handlers are sync functions so FastAPI runs them, and their blocking database
and parsing work, in its threadpool.
"""

import json
import logging
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import (
    DEFAULT_MODEL,
    AnalysisDetail,
    AnalysisRecord,
    AnalysisResult,
    ManualAnalysisRequest,
    ModelName,
)
from app.services import analysis_store, predictor
from app.services.file_parser import MAX_UPLOAD_BYTES, FileParseError, parse_procedure_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analyses", tags=["analyses"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/file", response_model_exclude_none=True)
def analyze_file(
    file: UploadFile,
    session: SessionDep,
    model_name: Annotated[ModelName, Form()] = DEFAULT_MODEL,
) -> AnalysisResult:
    """Analyze one procedure from an uploaded .csv, .json, or .xlsx file."""
    # Read one byte past the limit so an oversized upload is detected without reading all of it.
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    try:
        row = parse_procedure_file(file.filename, content)
    except FileParseError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error
    result = _predict(predictor.predict_from_file, row, model_name)
    # to_json converts NaN to null and NumPy scalars to plain JSON values.
    input_data = json.loads(row.to_json(orient="records"))[0]
    _save(session, result, "file", model_name, file.filename or "Uploaded file", input_data)
    return result


@router.post("/manual", response_model_exclude_none=True)
def analyze_manual(request: ManualAnalysisRequest, session: SessionDep) -> AnalysisResult:
    """Analyze one procedure from manually entered catheter measurements."""
    result = _predict(predictor.predict_from_manual, request, request.model_name)
    # model_name is stored in its own column, not with the procedure input.
    input_data = request.model_dump(mode="json", exclude={"model_name"})
    _save(session, result, "manual", request.model_name, "Manual entry", input_data)
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


def _predict(predict, data, model_name: ModelName) -> AnalysisResult:
    """Run a predictor, turning failures into JSON errors the frontend can display."""
    try:
        return predict(data, model_name)
    except predictor.PredictionInputError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except predictor.ModelUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        logger.exception("Prediction failed with the %s model", model_name)
        raise HTTPException(
            status_code=500, detail=f"The {model_name} model could not process this input."
        ) from error


def _save(
    session: Session,
    result: AnalysisResult,
    input_mode: Literal["file", "manual"],
    model_name: ModelName,
    source_name: str,
    input_data: dict[str, Any],
) -> None:
    # Do not return a prediction the user cannot find again later.
    try:
        analysis_store.save_analysis(
            session, result, input_mode, model_name, source_name, input_data
        )
    except SQLAlchemyError as error:
        session.rollback()
        raise HTTPException(
            status_code=503, detail="The analysis could not be saved. Please try again."
        ) from error
