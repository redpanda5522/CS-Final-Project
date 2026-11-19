import pandas as pd
import numpy as np
import re
import warnings

from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    log_loss,
    roc_auc_score,
)
from sklearn.linear_model import LogisticRegression
from sklearn.feature_selection import VarianceThreshold
from sklearn.preprocessing import StandardScaler
from sklearn.inspection import permutation_importance
from scipy.special import logit

warnings.filterwarnings('ignore')

def build_features(X):
    out = {}
    # per-site contact force columns, e.g. la_p1477_contactforce -> region 'la'
    cf = [c for c in X.columns if re.match(r'^[a-z0-9]+_p\d+_contactforce$', c)]
    for region in {c.split('_p')[0] for c in cf}:
        cols = [c for c in cf if c.startswith(region + '_p')]
        sub = X[cols]
        out[f'{region}_cf_n_sites'] = (sub > 0).sum(axis=1)
        out[f'{region}_cf_mean'] = sub.where(sub > 0).mean(axis=1)
        out[f'{region}_cf_max'] = sub.max(axis=1)
    # RF application columns
    for kind in ['rf_', 'temperaturesinrf_', 'contactforceinrf_']:
        cols = [c for c in X.columns if c.startswith(kind)]
        out[f'{kind}total'] = X[cols].sum(axis=1)
        out[f'{kind}n_nonzero'] = (X[cols] > 0).sum(axis=1)
    # the remaining non-per-site columns (the *_car, *_ecg_export, etc.)
    rest = [c for c in X.columns if not re.match(r'^[a-z0-9]+_p\d+_contactforce$', c)
            and not c.startswith(('rf_', 'temperaturesinrf_', 'contactforceinrf_'))]
    return pd.concat([pd.DataFrame(out), X[rest]], axis=1)

def _create_pipeline():
    return Pipeline([
        ("var", VarianceThreshold(threshold=0.02)),
        # ("scaler", StandardScaler()),
        ("clf", XGBClassifier(
            eval_metric='auc',
            random_state=45,
            learning_rate=0.1,
            max_depth=3,
            n_estimators=50,
            subsample=1.0,
            colsample_bytree=1.0,
        )),
    ])


def predictTest_grid(trainFeatures, trainLabels, testFeatures):

    pipeline = Pipeline([
        ("var", VarianceThreshold(threshold=0.02)),
        ("scaler", StandardScaler()),
        # ("sel", SelectKBest(k=50, score_func=chi2)),
        ("clf", XGBClassifier(
            eval_metric='auc',
            random_state=45,
        ))
    ])

    # Define hyperparameter grid
    param_grid = {
        # 'sel__k': [25, 50, 100],
        'clf__n_estimators': [30, 50, 70],
        'clf__learning_rate': [0.05, 0.1, 0.15],
        'clf__max_depth': [2, 3, 4],
        'clf__subsample': [0.6, 0.8, 1.0],
        'clf__colsample_bytree': [0.6, 0.8, 1.0]
    }

    # Setup GridSearchCV
    grid_search = GridSearchCV(
        estimator=pipeline,
        param_grid=param_grid,
        cv=5,               # 5-fold cross-validation
        scoring='roc_auc',  # Use AUC for evaluation
        n_jobs=-1
    )

    # Fit GridSearchCV
    grid_search.fit(trainFeatures, trainLabels)

    # Best model
    best_model = grid_search.best_estimator_

    # Predict probabilities for the positive class
    testOutputs = best_model.predict(testFeatures)
    y_prob = best_model.predict_proba(testFeatures)[:, 1]

    # Optionally, print the best parameters
    print("Best parameters found:", grid_search.best_params_)

    return testOutputs, y_prob

def predictTest(trainFeatures, trainLabels, testFeatures):
    pipe = _create_pipeline()
    pipe.fit(trainFeatures, trainLabels)
    testOutputs = pipe.predict(testFeatures)
    y_prob = pipe.predict_proba(testFeatures)[:, 1]

    '''
    var_step = pipe.named_steps["var"]
    mask = var_step.get_support()

    print("Before:", len(mask))
    print("Kept:", mask.sum())
    print("Removed:", (~mask).sum())
    '''
    return testOutputs, y_prob


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
    # X_feat = build_features(X)
    # print(X.shape, "->", X_feat.shape)

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

    









