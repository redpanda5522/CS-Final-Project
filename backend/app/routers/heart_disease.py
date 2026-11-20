"""Heart disease detection endpoints used by the frontend's HeartDisease page."""

from fastapi import APIRouter, HTTPException

from app.schemas import HeartDiseaseModel, HeartDiseaseRequest, HeartDiseaseResult
from app.services import heart_disease

router = APIRouter(prefix="/api/heart-disease", tags=["heart disease"])


@router.get("/model", response_model_exclude_none=True)
def model_config() -> HeartDiseaseModel:
    """The model's input fields, or why it is unavailable."""
    return heart_disease.model_config()


@router.post("/predict")
def predict(request: HeartDiseaseRequest) -> HeartDiseaseResult:
    try:
        return heart_disease.predict(request.features)
    except heart_disease.HeartDiseaseInputError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except heart_disease.HeartDiseaseUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
