import pandas as pd
import numpy as np
import warnings
import re

from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix, 
    roc_auc_score, average_precision_score, log_loss, brier_score_loss
)
from sklearn.feature_selection import VarianceThreshold
from sklearn.inspection import permutation_importance
from sklearn.calibration import CalibratedClassifierCV
from scipy.special import logit
from sklearn.linear_model import LogisticRegression

warnings.filterwarnings('ignore')

def predictTest(trainFeatures, trainLabels, testFeatures):

    pipe = Pipeline([
        ("var", VarianceThreshold(threshold=0.02)),
        # ("sel", SelectKBest(score_func=chi2, k=100)),
        ("clf", CalibratedClassifierCV(
            estimator = LinearSVC(
                C=1.0,
                penalty="l1",
                loss="squared_hinge",
                class_weight=None,      # try "balanced" if classes are imbalanced
                max_iter=10000,
                    random_state=45,
            ))),
    ])

    pipe.fit(trainFeatures, trainLabels)
    y_pred = pipe.predict(testFeatures)
    y_prob = pipe.predict_proba(testFeatures)[:, 1]
    
    var_step = pipe.named_steps["var"]
    mask = var_step.get_support()          # True = kept, False = removed

    print("Before:", len(mask))
    print("Kept:", mask.sum())
    print("Removed:", (~mask).sum())
    
    return (y_pred, y_prob)

if __name__ == "__main__":
    RANDOM_SEED = 45
    ablation_data = pd.read_csv('data.csv')
    ablation_data = ablation_data.dropna(subset=['recur'])

    cols_to_drop = [
        'ablationdata_pfa', 'applications_pfa', 'detectorsversion',
        'grids_pfa', 'rawpositions_pfa', 'sites_pfa',
        'visitagsessions_pfa', 'visitagsettings_pfa', 'vvversion', 'id'
    ]
    ablation_data = ablation_data.drop(columns=cols_to_drop, errors='ignore')

    X = ablation_data.drop(columns=['recur'])
    y = ablation_data['recur']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )

    y_pred, y_prob = predictTest(X_train, y_train, X_test)

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

    









