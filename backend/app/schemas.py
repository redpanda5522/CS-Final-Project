"""Request and response models for the analysis API.

These mirror the frontend contract in frontend/docs/backend-handoff.md.
"""

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "catheter-regions-v2"
GROUPING_VERSION = "left-named-column-v1"
MAX_CATHETERS = 4

RegionId = Literal["la", "ra", "lspv", "lipv", "rspv", "ripv", "svc", "ivc"]
TemperatureUnit = Literal["unspecified", "C", "F"]
PressureUnit = Literal["unspecified", "g", "mmHg", "kPa"]

# Applied when the client sends "unspecified". "g" is contact force, not pressure.
DEFAULT_TEMPERATURE_UNIT: TemperatureUnit = "C"
DEFAULT_PRESSURE_UNIT: PressureUnit = "g"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Units(StrictModel):
    temperature: TemperatureUnit
    pressure: PressureUnit

    @model_validator(mode="after")
    def apply_defaults(self) -> "Units":
        if self.temperature == "unspecified":
            self.temperature = DEFAULT_TEMPERATURE_UNIT
        if self.pressure == "unspecified":
            self.pressure = DEFAULT_PRESSURE_UNIT
        return self


class Catheter(StrictModel):
    id: UUID
    regionId: RegionId
    temperature: float | None
    pressure: Annotated[float, Field(ge=0)] | None


class ManualAnalysisRequest(StrictModel):
    schemaVersion: Literal["catheter-regions-v2"]
    groupingVersion: Literal["left-named-column-v1"]
    units: Units
    catheters: Annotated[list[Catheter], Field(min_length=1, max_length=MAX_CATHETERS)]


class AnalysisResult(BaseModel):
    analysisId: Annotated[str, Field(min_length=1)]
    predictedOutcome: Literal["success", "failure"]
    # P(success), not confidence in the predicted class.
    probability: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    outcomeDefinition: Annotated[str, Field(min_length=1)]
    modelVersion: str | None = None


class AnalysisRecord(AnalysisResult):
    """A saved analysis, matching the frontend's AnalysisRecord type."""

    inputMode: Literal["file", "manual"]
    sourceName: str
    createdAt: datetime
    isDemo: Literal[False] = False


class AnalysisDetail(AnalysisRecord):
    # Manual: the validated request. File: the parsed procedure row.
    input: dict[str, Any]
