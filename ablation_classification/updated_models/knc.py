import pandas as pd
import warnings
import numpy as np
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.neighbors import NearestCentroid
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix, 
    roc_auc_score, average_precision_score, log_loss, brier_score_loss
)
from sklearn.linear_model import LogisticRegression
from sklearn.feature_selection import VarianceThreshold
from sklearn.inspection import permutation_importance
from scipy.special import expit, logit

warnings.filterwarnings('ignore')

RANDOM_SEED = 45
N_SPLITS = 5

# Load data
ablation_data = pd.read_csv('data.csv')
ablation_data = ablation_data.dropna(subset=['recur'])

cols_to_drop = [
    'ablationdata_pfa', 'applications_pfa', 'detectorsversion',
    'grids_pfa', 'rawpositions_pfa', 'sites_pfa',
    'visitagsessions_pfa', 'visitagsettings_pfa', 'vvversion', 'id'
]

ablation_data = ablation_data.drop(
    columns=cols_to_drop, errors='ignore'
)

print(ablation_data.describe())

# Separate features and target
X = ablation_data.drop(columns=['recur'])
y = ablation_data['recur']

# Keep numeric features only
X = X.select_dtypes(include=['number'])

# Split into training and independent test sets
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=RANDOM_SEED,
    stratify=y
)

# Build pipeline
pipeline = Pipeline([
    ("var", VarianceThreshold(threshold=0.05)),
    ("model", NearestCentroid(
        metric="euclidean",
        shrink_threshold=0.3
    ))
])

# Define stratified 5-fold cross-validation
cv = StratifiedKFold(
    n_splits=N_SPLITS,
    shuffle=True,
    random_state=RANDOM_SEED
)

# Cross-validate using the training set only
scoring = {
    "accuracy": "accuracy",
    "precision": "precision_weighted",
    "recall": "recall_weighted",
    "f1": "f1_weighted",
    "roc_auc": "roc_auc"
}

cv_results = cross_validate(
    pipeline,
    X_train,
    y_train,
    cv=cv,
    scoring=scoring,
    return_train_score=False,
    error_score="raise"
)

# Display cross-validation results
print("\n===== 5-Fold Cross-Validation Results =====")

for metric in scoring:
    scores = cv_results[f"test_{metric}"]
    print(
        f"{metric.upper()}: "
        f"{scores.mean():.4f} +/- {scores.std():.4f}"
    )

# Fit the model on the complete training set
pipeline.fit(X_train, y_train)

# Evaluate on the independent test set
y_pred = pipeline.predict(X_test)

# NearestCentroid has no predict_proba().
# Use decision scores for binary ROC AUC.
y_score = pipeline.decision_function(X_test)

# Convert decision scores to probabilities [0, 1] using sigmoid
y_prob = expit(y_score)

print("\n===== Independent Test Set Results =====")
print("Accuracy:", accuracy_score(y_test, y_pred))

print(
    "\nClassification Report:\n",
    classification_report(y_test, y_pred, zero_division=0)
)

print(
    "\nConfusion Matrix:\n",
    confusion_matrix(y_test, y_pred)
)

# --- Compute Additional Metrics ---
print("\n===== Advanced Performance & Calibration Metrics =====")

# 1. Log Loss
logloss = log_loss(y_test, y_prob)
print(f"Log Loss: {logloss:.4f}")

# 2. AUROC
if len(pipeline.classes_) == 2:
    positive_class_index = list(pipeline.classes_).index(
        sorted(pipeline.classes_)[-1]
    )
    if y_score.ndim == 1:
        auc_score = roc_auc_score(
            y_test,
            y_score if positive_class_index == 1 else -y_score
        )
    else:
        auc_score = roc_auc_score(
            y_test,
            y_score[:, positive_class_index]
        )
    print(f"ROC AUC: {auc_score:.4f}")
else:
    print("ROC AUC is reported only for binary classification in this example.")

# 3. AUPRC (Area Under Precision-Recall Curve)
auprc = average_precision_score(y_test, y_prob)
print(f"AUPRC: {auprc:.4f}")

# 4. Brier Score
brier = brier_score_loss(y_test, y_prob)
print(f"Brier Score: {brier:.4f}")

# 5. Scaled Brier Score (1 - Brier / Brier_reference)
p_prevalence = y_test.mean()
brier_ref = p_prevalence * (1 - p_prevalence)
scaled_brier = 1 - (brier / brier_ref) if brier_ref > 0 else 0.0
print(f"Scaled Brier Score: {scaled_brier:.4f}")

# 6 & 7. Calibration Intercept (Calibration-in-the-large) & Calibration Slope
eps = 1e-15
y_prob_clipped = np.clip(y_prob, eps, 1 - eps)
log_odds = logit(y_prob_clipped)

calib_model = LogisticRegression(solver='lbfgs')
calib_model.fit(log_odds.reshape(-1, 1), y_test)
calibration_slope = calib_model.coef_[0][0]
calibration_intercept = calib_model.intercept_[0]

print(f"Calibration-in-the-large (Intercept): {calibration_intercept:.4f}")
print(f"Calibration Slope: {calibration_slope:.4f}")

# 8. Observed / Expected (O/E) Ratio
observed_events = y_test.sum()
expected_events = y_prob.sum()
oe_ratio = observed_events / expected_events if expected_events > 0 else float('nan')
print(f"Observed/Expected (O/E) Ratio: {oe_ratio:.4f}")


# Compute permutation importance on the test set
perm_result = permutation_importance(
    pipeline, 
    X_test, 
    y_test, 
    scoring="roc_auc", 
    n_repeats=10, 
    random_state=RANDOM_SEED
)

# Organize results into a DataFrame
feature_importances = pd.DataFrame({
    "feature": X_test.columns,
    "importance_mean": perm_result.importances_mean,
    "importance_std": perm_result.importances_std
}).sort_values(by="importance_mean", ascending=False)

print("\n===== Top 10 Features by Permutation Importance =====")
print(feature_importances.head(10))
