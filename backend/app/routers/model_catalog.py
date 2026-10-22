"""The models the frontend can offer in its dropdown."""

from fastapi import APIRouter

from app.schemas import DEFAULT_MODEL, ModelCatalog
from app.services import predictor

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("")
def list_models() -> ModelCatalog:
    """List every model, whether it is available, and which file formats it accepts."""
    return ModelCatalog(defaultModel=DEFAULT_MODEL, models=predictor.list_models())
