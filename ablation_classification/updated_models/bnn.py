import pandas as pd
import numpy as np
import warnings
import re

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix, 
    roc_auc_score, average_precision_score, log_loss, brier_score_loss
)
from sklearn.feature_selection import VarianceThreshold
from sklearn.inspection import permutation_importance
from scipy.special import logit
from sklearn.linear_model import LogisticRegression

warnings.filterwarnings('ignore')

# Define a simple PyTorch Neural Network for binary classification
class BinaryNeuralNetwork(nn.Module):
    def __init__(self, input_dim):
        super(BinaryNeuralNetwork, self).__init__()
        self.layer1 = nn.Linear(input_dim, 64)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.3)
        self.layer2 = nn.Linear(64, 32)
        self.output = nn.Linear(32, 1) # Outputs raw logit
        
    def forward(self, x):
        x = self.relu(self.layer1(x))
        x = self.dropout(x)
        x = self.relu(self.layer2(x))
        x = self.output(x)
        return x

def predictTest(trainFeatures, trainLabels, testFeatures):
    # 1. Feature selection using VarianceThreshold
    selector = VarianceThreshold(threshold=0.02)
    # selector = SelectKBest(score_func=chi2, k=50)  # Uncomment if you want to use SelectKBest instead
    selector.fit(trainFeatures)
    
    X_train_filtered = selector.transform(trainFeatures)  # Replace with selector.transform(trainFeatures) if using feature selection
    X_test_filtered = selector.transform(testFeatures)    # Replace with selector.transform(testFeatures) if using feature selection

    if hasattr(X_train_filtered, "to_numpy"):
        X_train_filtered = X_train_filtered.to_numpy()
    if hasattr(X_test_filtered, "to_numpy"):
        X_test_filtered = X_test_filtered.to_numpy()
    
    # 2. Convert data to PyTorch Tensors
    X_train_tensor = torch.tensor(X_train_filtered.astype(np.float32), dtype=torch.float32)
    y_train_tensor = torch.tensor(trainLabels.to_numpy().astype(np.float32), dtype=torch.float32).unsqueeze(1)
    
    X_test_tensor = torch.tensor(X_test_filtered.astype(np.float32), dtype=torch.float32)
    
    # 3. Setup DataLoaders for batching
    train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    
    # 4. Initialize model, loss function, and optimizer
    input_dim = X_train_tensor.shape[1]
    model = BinaryNeuralNetwork(input_dim)
    
    criterion = nn.BCEWithLogitsLoss() # Combines Sigmoid activation and Binary Cross Entropy
    optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
    
    # 5. PyTorch Training Loop
    model.train()
    epochs = 50
    for epoch in range(epochs):
        for inputs, targets in train_loader:
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            
    # 6. Inference / Evaluation
    model.eval()
    with torch.no_grad():
        test_logits = model(X_test_tensor)
        test_probs = torch.sigmoid(test_logits).numpy().flatten()
        testOutputs = (test_probs >= 0.5).astype(int)
    
    return testOutputs, test_probs

if __name__ == "__main__":
    RANDOM_SEED = 45
    torch.manual_seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    
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
    