import pandas as pd
import warnings
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix, 
    roc_auc_score, average_precision_score, log_loss, brier_score_loss
)
from sklearn.feature_selection import VarianceThreshold
from sklearn.inspection import permutation_importance
from scipy.special import logit

warnings.filterwarnings('ignore')

RANDOM_SEED = 45

# Load data
ablation_data = pd.read_csv('data.csv')
ablation_data = ablation_data.dropna(subset=['recur'])

cols_to_drop = [
    'ablationdata_pfa', 'applications_pfa', 'detectorsversion',
    'grids_pfa', 'rawpositions_pfa', 'sites_pfa',
    'visitagsessions_pfa', 'visitagsettings_pfa', 'vvversion', 'id'
]
ablation_data = ablation_data.drop(columns=cols_to_drop, errors='ignore')

# Separate features and target
X = ablation_data.drop(columns=['recur'])
y = ablation_data['recur']

# Keep numeric features only
X = X.select_dtypes(include=['number'])

# Train/Test Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
)

# Build pipeline
pipeline = Pipeline([
    ("var", VarianceThreshold(threshold=0.05)),
    ('model', LogisticRegression(
        penalty='l2',
        solver='liblinear',
        C=0.1,
        class_weight='balanced',
        random_state=RANDOM_SEED,
    ))
])
pipeline.fit(X_train, y_train)

# Evaluate model predictions
y_pred = pipeline.predict(X_test)
y_prob = pipeline.predict_proba(X_test)[:, 1]

print("===== Basic Performance Metrics =====")
print("Accuracy:", accuracy_score(y_test, y_pred))
print("\nClassification Report:\n", classification_report(y_test, y_pred))
print("\nConfusion Matrix:\n", confusion_matrix(y_test, y_pred))

# Ground truth values
y_true = y_test.values

print("\n===== Advanced Performance & Calibration Metrics =====")

# 1. Log Loss
ll = log_loss(y_true, y_prob)
print(f"Log Loss                 : {ll:.4f}")

# 2. AUROC
auroc = roc_auc_score(y_true, y_prob)
print(f"AUROC                    : {auroc:.4f}")

# 3. AUPRC
auprc = average_precision_score(y_true, y_prob)
print(f"AUPRC                    : {auprc:.4f}")

# 4. Brier Score
brier = brier_score_loss(y_true, y_prob)
print(f"Brier Score              : {brier:.4f}")

# 5. Scaled Brier
p_prev = np.mean(y_true)
brier_ref = p_prev * (1 - p_prev)
scaled_brier = 1 - (brier / brier_ref) if brier_ref > 0 else 0.0
print(f"Scaled Brier             : {scaled_brier:.4f}")

# 6 & 7. Calibration Intercept & Calibration Slope (via unregularized scikit-learn LogisticRegression)
eps = 1e-15
y_prob_clipped = np.clip(y_prob, eps, 1 - eps)
log_odds = logit(y_prob_clipped)

calib_model = LogisticRegression(penalty=None, solver='lbfgs')
calib_model.fit(log_odds.reshape(-1, 1), y_true)

calib_intercept = calib_model.intercept_[0]
calib_slope = calib_model.coef_[0][0]

print(f"Calibration Intercept    : {calib_intercept:.4f}")
print(f"Calibration Slope        : {calib_slope:.4f}")

# 8. Observed / Expected (O/E) Ratio
expected_events = np.sum(y_prob)
oe_ratio = np.sum(y_true) / expected_events if expected_events > 0 else np.nan
print(f"O/E Ratio                : {oe_ratio:.4f}")

# Compute permutation importance on the test set
perm_result = permutation_importance(
    pipeline, 
    X_test, 
    y_test, 
    scoring="roc_auc", 
    n_repeats=5, 
    n_jobs=-1,
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