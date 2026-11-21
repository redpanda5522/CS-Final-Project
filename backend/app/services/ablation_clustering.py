"""Ablation-site patient clustering using the pre-trained PCA/KMeans artifact."""

import io
import logging
from functools import lru_cache
from pathlib import Path, PurePath

import joblib
import numpy as np
import pandas as pd

from app.services.file_parser import MAX_UPLOAD_BYTES

logger = logging.getLogger(__name__)
MODEL_PATH = Path(__file__).resolve().parent / "clustering_models" / "clustering_models.joblib"

EXPECTED_COLUMNS = [
    "Session", "ChannelID", "SiteIndex", "X", "Y", "Z", "DurationTime",
    "AverageForce", "MaxTemperature", "MaxPower", "BaseImpedance",
    "ImpedanceDrop", "FTI", "RFIndex", "TagIndexStatus",
]
CONTINUOUS_COLUMNS = [
    "X", "Y", "Z", "DurationTime", "AverageForce", "MaxTemperature",
    "MaxPower", "BaseImpedance", "ImpedanceDrop", "FTI", "RFIndex",
]
MISSING_SENTINELS = (-10000, -10000.0)


class AblationSiteInputError(ValueError):
    """The uploaded file does not contain usable ablation-site data."""


class ClusteringModelUnavailableError(RuntimeError):
    """The saved PCA/KMeans artifact could not be loaded or used."""


@lru_cache(maxsize=1)
def _load_model() -> dict:
    """Load and validate the clustering pipeline once for fast repeat analyses."""
    try:
        artifact = joblib.load(MODEL_PATH)
        required = {"imputer", "scaler", "kmeans", "pca", "feature_columns", "X_scaled"}
        if not isinstance(artifact, dict) or not required.issubset(artifact):
            raise ValueError("The clustering artifact is missing required pipeline objects.")
        columns = artifact["feature_columns"]
        feature_count = len(columns)
        scaled_samples = np.asarray(artifact["X_scaled"])
        if (
            not columns
            or artifact["imputer"].n_features_in_ != feature_count
            or artifact["scaler"].n_features_in_ != feature_count
            or artifact["kmeans"].n_features_in_ != feature_count
            or artifact["pca"].n_features_in_ != feature_count
            or artifact["pca"].n_components_ != 2
            or scaled_samples.ndim != 2
            or scaled_samples.shape[1] != feature_count
            or scaled_samples.shape[0] != len(artifact["kmeans"].labels_)
            or not np.isfinite(scaled_samples).all()
        ):
            raise ValueError("The clustering artifact has incompatible feature dimensions.")
        return artifact
    except Exception as error:
        logger.exception("Could not load clustering model from %s", MODEL_PATH)
        raise ClusteringModelUnavailableError(
            "The ablation-site clustering model is unavailable on this server."
        ) from error


def _patient_features(content: bytes, filename: str | None) -> dict[str, float]:
    if not content:
        raise AblationSiteInputError("The uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise AblationSiteInputError("The uploaded file exceeds the 10 MiB limit.")
    if PurePath(filename or "").suffix.lower() != ".txt":
        raise AblationSiteInputError(
            "Upload one whitespace-delimited .txt file with a header row for one patient."
        )
    try:
        text = content.decode("utf-8-sig")
        frame = pd.read_csv(io.StringIO(text), sep=r"\s+", header=0, engine="python")
    except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as error:
        raise AblationSiteInputError("The ablation-site text file could not be parsed.") from error

    frame.columns = [str(column).strip() for column in frame.columns]
    missing = [column for column in EXPECTED_COLUMNS if column not in frame.columns]
    if missing:
        raise AblationSiteInputError(
            f"The ablation-site file is missing required columns: {', '.join(missing)}."
        )

    frame = frame[EXPECTED_COLUMNS].copy()
    for column in EXPECTED_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.replace(list(MISSING_SENTINELS), np.nan)
    frame = frame.dropna(subset=["Session", "SiteIndex"])
    if frame.empty:
        raise AblationSiteInputError(
            "The file has no usable site rows with Session and SiteIndex values."
        )

    features: dict[str, float] = {
        "num_sites": float(len(frame)),
        "num_sessions": float(frame["Session"].nunique()),
        "num_channels": float(frame["ChannelID"].nunique()),
    }
    for column in CONTINUOUS_COLUMNS:
        values = frame[column].dropna()
        stats = ("mean", "std", "min", "max", "median")
        if values.empty:
            for stat in stats:
                features[f"{column}_{stat}"] = float("nan")
        else:
            features[f"{column}_mean"] = float(values.mean())
            features[f"{column}_std"] = float(values.std())
            features[f"{column}_min"] = float(values.min())
            features[f"{column}_max"] = float(values.max())
            features[f"{column}_median"] = float(values.median())
    return features


def analyze_ablation_sites(content: bytes, filename: str | None) -> dict:
    """Extract one patient's site features and project/cluster them with the artifact."""
    features = _patient_features(content, filename)
    artifact = _load_model()
    columns = artifact["feature_columns"]
    row = pd.DataFrame(
        [{column: features.get(column, np.nan) for column in columns}],
        columns=columns,
    ).replace([np.inf, -np.inf], np.nan)
    scaled = artifact["scaler"].transform(artifact["imputer"].transform(row))
    kmeans = artifact["kmeans"]
    pca = artifact["pca"]
    patient_pca = pca.transform(scaled)[0]
    cluster = int(kmeans.predict(scaled)[0])

    labels = np.asarray(kmeans.labels_, dtype=int)
    centers = np.asarray(kmeans.cluster_centers_, dtype=float)
    scaled_samples = np.asarray(artifact["X_scaled"], dtype=float)
    if (
        labels.size == 0
        or np.any(labels < 0)
        or np.any(labels >= len(centers))
        or scaled_samples.ndim != 2
        or scaled_samples.shape[0] != len(labels)
        or scaled_samples.shape[1] != len(columns)
    ):
        raise ClusteringModelUnavailableError(
            "The clustering model does not contain valid training samples and assignments."
        )
    training_pca = pca.transform(scaled_samples)
    cluster_sizes = np.bincount(labels, minlength=len(centers))
    overall_mean = np.average(centers, axis=0, weights=cluster_sizes)
    between_cluster_ss = (
        cluster_sizes[:, None] * (centers - overall_mean) ** 2
    ).sum(axis=0)
    total_contribution = float(between_cluster_ss.sum())
    contributions = (
        between_cluster_ss / total_contribution * 100
        if total_contribution > 0
        else np.zeros_like(between_cluster_ss)
    )
    top_features = np.argsort(contributions)[::-1][:15]

    return {
        "sourceName": filename or "Uploaded patient data",
        "numSites": int(features["num_sites"]),
        "numSessions": int(features["num_sessions"]),
        "cluster": cluster,
        "modelVersion": "clustering_models.joblib",
        "pca": {
            "point": {"x": float(patient_pca[0]), "y": float(patient_pca[1])},
            "trainingPoints": [
                {"cluster": int(label), "x": float(point[0]), "y": float(point[1])}
                for label, point in zip(labels, training_pca, strict=True)
            ],
            "explainedVariance": [
                float(pca.explained_variance_ratio_[0]),
                float(pca.explained_variance_ratio_[1]),
            ],
        },
        "featureContributions": [
            {
                "feature": str(columns[index]),
                "contributionPercent": float(contributions[index]),
            }
            for index in top_features
        ],
    }
