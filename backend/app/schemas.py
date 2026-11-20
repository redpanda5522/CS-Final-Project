"""Request and response models for the analysis API.

These mirror the frontend contract in frontend/docs/backend-handoff.md.
"""

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "catheter-regions-v2"
GROUPING_VERSION = "left-named-column-v1"
MAX_CATHETERS = 4

RegionId = Literal["la", "ra", "lspv", "lipv", "rspv", "ripv", "svc", "ivc"]
# The frontend dropdown is built from GET /api/models.
ModelName = Literal["logistic", "random_forest", "xgboost", "k_nearest"]
DEFAULT_MODEL: ModelName = "logistic"
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
    # snake_case to match the frontend's request body.
    model_name: ModelName = DEFAULT_MODEL
    schemaVersion: Literal["catheter-regions-v2"]
    groupingVersion: Literal["left-named-column-v1"]
    units: Units
    catheters: Annotated[list[Catheter], Field(min_length=1, max_length=MAX_CATHETERS)]


class PerformanceMetrics(StrictModel):
    """Held-out evaluation metrics for the model, with success (recur=0) positive."""

    accuracy: Annotated[float, Field(ge=0, le=1)] | None = None
    precision: Annotated[float, Field(ge=0, le=1)] | None = None
    recall: Annotated[float, Field(ge=0, le=1)] | None = None
    f1: Annotated[float, Field(ge=0, le=1)] | None = None
    auroc: Annotated[float, Field(ge=0, le=1)] | None = None
    auprc: Annotated[float, Field(ge=0, le=1)] | None = None
    logLoss: Annotated[float, Field(ge=0)] | None = None
    brierScore: Annotated[float, Field(ge=0, le=1)] | None = None
    scaledBrierScore: float | None = None
    calibrationIntercept: float | None = None
    calibrationSlope: float | None = None
    observedExpectedRatio: Annotated[float, Field(ge=0)] | None = None


class AnalysisResult(BaseModel):
    analysisId: Annotated[str, Field(min_length=1)]
    predictedOutcome: Literal["success", "failure"]
    # P(success), not confidence in the predicted class.
    probability: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    outcomeDefinition: Annotated[str, Field(min_length=1)]
    modelVersion: str | None = None
    performanceMetrics: PerformanceMetrics | None = None

# Result of training a classification model
class ModelTrainingResult(BaseModel):
    modelName: Annotated[str, Field(min_length=1)]
    modelVersion: str
    targetColumn: Annotated[str, Field(min_length=1)]
    classificationType: Literal["binary", "multiclass"]
    classLabels: Annotated[list[str], Field(min_length=2)]
    compatibleWithOutcomeAnalysis: bool
    rowsTrained: Annotated[int, Field(ge=1)]
    featureCount: Annotated[int, Field(ge=1)]
    validationRows: Annotated[int, Field(ge=1)]
    accuracy: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    performanceMetrics: PerformanceMetrics | None = None


class ModelOption(BaseModel):
    id: ModelName
    label: str
    # False when the artifact failed to load; selecting it returns 503.
    available: bool
    # File formats the model accepts: raw data.csv columns and/or the combined columns.
    inputFormats: list[Literal["raw", "combined"]]


class ModelCatalog(BaseModel):
    defaultModel: ModelName
    models: list[ModelOption]


class AnalysisRecord(AnalysisResult):
    """A saved analysis, matching the frontend's AnalysisRecord type."""

    inputMode: Literal["file", "manual"]
    modelName: ModelName | None = None
    sourceName: str
    createdAt: datetime
    isDemo: Literal[False] = False


class AnalysisDetail(AnalysisRecord):
    # Manual: the validated request. File: the parsed procedure row.
    input: dict[str, Any]


# Accounts. Emails use the same simple check as the frontend form.
EMAIL_PATTERN = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
NewPassword = Annotated[str, Field(min_length=8, max_length=256)]


class AccountCreate(StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    email: Annotated[str, Field(max_length=254, pattern=EMAIL_PATTERN)]
    organization: Annotated[str, Field(max_length=120)] = ""
    # The upper bound keeps one request from making password hashing expensive.
    password: NewPassword

    # Strip before the length and email checks. Not the password: spaces count there.
    @field_validator("name", "email", "organization", mode="before")
    @classmethod
    def strip(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class SignInRequest(StrictModel):
    email: Annotated[str, Field(max_length=254)]
    password: Annotated[str, Field(max_length=256)]


class PasswordChange(StrictModel):
    currentPassword: Annotated[str, Field(max_length=256)]
    newPassword: NewPassword


class PasswordResetRequest(StrictModel):
    email: Annotated[str, Field(max_length=254)]


class PasswordResetConfirm(StrictModel):
    token: Annotated[str, Field(min_length=1, max_length=128)]
    newPassword: NewPassword


class Account(BaseModel):
    """Matches the frontend's Account type."""

    id: str
    name: str
    email: str
    organization: str


# Heart disease detection (the HeartDisease page).
class HeartDiseaseOption(BaseModel):
    value: int
    label: str


class HeartDiseaseField(BaseModel):
    name: str
    label: str
    type: Literal["number", "select"]
    unit: str | None = None
    min: float | None = None
    max: float | None = None
    options: list[HeartDiseaseOption] | None = None


class HeartDiseaseModel(BaseModel):
    available: bool
    reason: str | None
    modelVersion: str | None
    fields: list[HeartDiseaseField]


class HeartDiseaseRequest(StrictModel):
    # Values are checked against the field list in app/services/heart_disease.py.
    features: dict[str, float]


class HeartDiseaseResult(BaseModel):
    predictedClass: Literal["positive", "negative"]
    # P(heart disease present).
    positiveClassProbability: Annotated[float, Field(ge=0, le=1)]
    modelVersion: str
