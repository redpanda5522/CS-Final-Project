import pandas as pd
import warnings

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.neighbors import NearestCentroid
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score
from sklearn.feature_selection import VarianceThreshold, SelectKBest, chi2

warnings.filterwarnings('ignore')

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


X = X.select_dtypes(include=['number'])

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
)

# Build pipeline: fill missing values, then train logistic regression
pipeline = Pipeline([
    ("var", VarianceThreshold(threshold=0.05)),
    ('model', NearestCentroid(
        metric="euclidean", 
        shrink_threshold=0.3)
    )
])
pipeline.fit(X_train, y_train)


y_pred = pipeline.predict(X_test)
y_prob = pipeline.predict_proba(X_test)[:, 1]

# Evaluate
print("Accuracy:", accuracy_score(y_test, y_pred))
print("\nClassification Report:\n", classification_report(y_test, y_pred))
print("\nConfusion Matrix:\n", confusion_matrix(y_test, y_pred))
print("\nROC AUC:", roc_auc_score(y_test, y_prob))