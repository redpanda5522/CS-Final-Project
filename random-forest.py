import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import warnings

warnings.filterwarnings('ignore')

RANDOM_SEED = 45

ablation_data = pd.read_csv('data.csv')
ablation_data = ablation_data.dropna(subset=['recur'])

cols_to_drop = ['ablationdata_pfa',	'applications_pfa',	'detectorsversion',	'grids_pfa', 'rawpositions_pfa',	'sites_pfa',	'visitagsessions_pfa',	'visitagsettings_pfa',	'vvversion']

ablation_data = ablation_data.drop(columns=cols_to_drop)

x = ablation_data[[col for col in ablation_data.columns if col != 'recur']]
y = ablation_data['recur']


X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=RANDOM_SEED)

rf_classifier = RandomForestClassifier(n_estimators=100, random_state=RANDOM_SEED)
rf_classifier.fit(X_train, y_train)

y_pred = rf_classifier.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)
classification_rep = classification_report(y_test, y_pred)

print(f"Accuracy: {accuracy:.2f}")
print("\nClassification Report:\n", classification_rep)

# sample = X_test.iloc[0:1]
# prediction = rf_classifier.predict(sample)

# sample_dict = sample.iloc[0].to_dict()
# print(f"\nSample Passenger: {sample_dict}")
# print(f"Predicted Survival: {'Survived' if prediction[0] == 1 else 'Did Not Survive'}")