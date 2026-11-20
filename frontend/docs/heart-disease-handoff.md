# Heart disease page: frontend handoff

The page at `/heart-disease` is implemented in `src/pages/HeartDisease.tsx`. It renders
fields supplied by the model service, submits one set of values, and displays the
returned positive-class probability. It does not choose the model's features,
preprocessing, threshold, or clinical interpretation.

## Endpoints expected by the page

`GET /api/heart-disease/model` returns:

```json
{
  "available": true,
  "reason": null,
  "modelVersion": "heart-xgb-v1",
  "fields": [
    { "name": "feature_name", "label": "Feature label", "type": "number", "unit": "unit", "min": 0, "max": 100 },
    { "name": "category_name", "label": "Category label", "type": "select", "options": [
      { "value": 0, "label": "First choice" },
      { "value": 1, "label": "Second choice" }
    ] }
  ]
}
```

The field examples above are placeholders, not an assertion about the trained model.
The service should supply its exact feature names and valid values. When it cannot
serve predictions, return `available: false`, a human-readable `reason`, and an empty
`fields` list. The page then shows the unavailable state.

`POST /api/heart-disease/predict` accepts JSON with every configured field:

```json
{ "features": { "feature_name": 42, "category_name": 1 } }
```

The success response is:

```json
{
  "predictedClass": "positive",
  "positiveClassProbability": 0.8,
  "modelVersion": "heart-xgb-v1"
}
```

`predictedClass` is `positive` or `negative`; `positiveClassProbability` is a finite
fraction in `[0, 1]`. The backend should validate inputs and return non-2xx responses
with a JSON `detail` message on failure. The frontend validates the response shape.

The merged artifact at `cardiodisease_detection/models/xgboost_model.joblib` is an
XGBoost Booster trained in `cardiodisease_detection/XGboost.py`. Its inference path
uses `DMatrix` and `predict`, so the backend owner will need to adapt that output to
this response contract and provide the exact fields from the trained artifact. The
current backend has no `/api/heart-disease/*` routes; the page shows an error until
they are available. The page does not upload model weights or retrain the model.
