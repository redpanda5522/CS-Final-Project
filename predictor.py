import joblib
import pandas as pd
import xgboost as xgb
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent / "models"

MODEL_MAP = {
    "logistic": {"model": joblib.load(MODEL_DIR / "logistic_model.joblib"), "version": "logistic_regression_v1"},
    "random_forest": {"model": joblib.load(MODEL_DIR / "random_forest_model.joblib"), "version":"random_forest_v1"},
    "xgboost": {"model": joblib.load(MODEL_DIR / "xgboost_model.joblib"), "version": "xgboost"},
    #"nueral": joblib.load(MODEL_DIR / "neural_net_model.joblib"),
}

def _prepare_features(row: pd.DataFrame) -> pd.DataFrame:
    """Make the uploaded DataFrame match the model's training schema."""
    return row

def predict_from_file(row: pd.DataFrame, model_name: str) -> int:
    """Predict from one parsed procedure row."""
    prepared_row = _prepare_features(row)
    model_info = MODEL_MAP[model_name]
    model = model_info["model"]
    modelVersion = model_info["version"]
    if(model_name in ["logistic", "random_forest"]):
        prob_of_success = model.predict_proba(prepared_row)[0][0]
        return prob_of_success
    elif(model_name in ["xgboost"]):
        prob_of_success = 1 - model.predict(xgb.DMatrix(prepared_row))[0]
        return prob_of_success
    elif(model_name in ["nueral"]):
        return 
    else:
        raise Exception("Invalid model name")

    return None
    

ablation_data = pd.read_csv('test_data.csv')
cols_to_drop = [
    'ablationdata_pfa', 'applications_pfa', 'detectorsversion',
    'grids_pfa', 'rawpositions_pfa', 'sites_pfa',
    'visitagsessions_pfa', 'visitagsettings_pfa', 'vvversion', 'id', 'recur'
]
ablation_data = ablation_data.drop(columns=cols_to_drop, errors='ignore')

print(predict_from_file(ablation_data, "xgboost"))