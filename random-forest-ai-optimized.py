import pandas as pd
import warnings

from sklearn.model_selection import train_test_split, RandomizedSearchCV, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

warnings.filterwarnings('ignore')

RANDOM_SEED = None

# Load data
ablation_data = pd.read_csv('data_combined.csv')

# Drop rows with missing target
ablation_data = ablation_data.dropna(subset=['recur'])

# Drop columns you don't want
cols_to_drop = [
    'ablationdata_pfa', 'applications_pfa', 'detectorsversion',
    'grids_pfa', 'rawpositions_pfa', 'sites_pfa',
    'visitagsessions_pfa', 'visitagsettings_pfa', 'vvversion', 'id'
]
ablation_data = ablation_data.drop(columns=cols_to_drop, errors='ignore')

# Split features/target
X = ablation_data.drop(columns=['recur'])
y = ablation_data['recur']

# Keep only numeric columns for now
X = X.select_dtypes(include=['number'])

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
)

# Pipeline: impute + model
pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('model', RandomForestClassifier(random_state=RANDOM_SEED, class_weight='balanced'))
])

# Hyperparameter search
param_dist = {
    'model__n_estimators': [100, 200, 300, 500],
    'model__max_depth': [None, 5, 10, 20, 30],
    'model__min_samples_split': [2, 5, 10],
    'model__min_samples_leaf': [1, 2, 4],
    'model__max_features': ['sqrt', 'log2', None]
}

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)

search = RandomizedSearchCV(
    pipeline,
    param_distributions=param_dist,
    n_iter=25,
    cv=cv,
    scoring='f1_macro',
    n_jobs=-1,
    random_state=RANDOM_SEED
)

search.fit(X_train, y_train)

best_model = search.best_estimator_
y_pred = best_model.predict(X_test)

print("Best params:", search.best_params_)
print("Accuracy:", accuracy_score(y_test, y_pred))
print("\nClassification Report:\n", classification_report(y_test, y_pred))
print("\nConfusion Matrix:\n", confusion_matrix(y_test, y_pred))

if len(y.unique()) == 2:
    y_prob = best_model.predict_proba(X_test)[:, 1]
    print("\nROC AUC:", roc_auc_score(y_test, y_prob))