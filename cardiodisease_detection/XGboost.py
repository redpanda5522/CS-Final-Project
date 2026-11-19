import pandas as pd
import warnings
import joblib

from sklearn.metrics import accuracy_score
import xgboost as xgb
from sklearn.model_selection import train_test_split
import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score
from ucimlrepo import fetch_ucirepo 

warnings.filterwarnings('ignore')

RANDOM_SEED = 45

  
# fetch dataset 
heart_disease = fetch_ucirepo(id=45) 
  
# data (as pandas dataframes) 
X = heart_disease.data.features 
y = heart_disease.data.targets
y = (y > 0).astype(int) # Convert to 0 and 1s 
  

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
)

xgb_train = xgb.DMatrix(X_train, y_train, enable_categorical=True)
xgb_test = xgb.DMatrix(X_test, y_test, enable_categorical=True)

params = {
    'objective': 'binary:logistic',
    'max_depth': 3,
    'learning_rate': 0.1,
}
n=50
model = xgb.train(params=params,dtrain=xgb_train,num_boost_round=n)

print(model.feature_names)

preds = model.predict(xgb_test)  # Predicted probabilities (0-1)

# Convert probabilities to binary predictions
preds_binary = np.round(preds)

joblib.dump(model, "./models/xgboost_model.joblib")

print("Accuracy:", accuracy_score(y_test, preds_binary))
print("\nClassification Report:\n", classification_report(y_test, preds_binary))
print("\nConfusion Matrix:\n", confusion_matrix(y_test, preds_binary))

# Use probabilities, NOT rounded predictions, for ROC AUC
print("\nROC AUC:", roc_auc_score(y_test, preds))