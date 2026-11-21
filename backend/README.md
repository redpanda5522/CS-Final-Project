# Senior Project Backend

A minimal FastAPI backend, ready for project requirements to be added.

## Run everything with Docker

From the repository root, start Postgres, the API, and the frontend together:

```bash
docker-compose up --build
```

- App: <http://localhost:8080> (nginx serves the built frontend and proxies `/api`)
- API docs: <http://localhost:8000/docs>
- Postgres: `localhost:5432`, user/password `postgres`, database `senior_project`

Migrations run automatically when the backend container starts. Data persists in the
`postgres-data` volume; `docker-compose down -v` deletes it. To change the credentials or
the Postgres host port, copy `.env.example` to `.env` in the repository root.

Models trained through `POST /api/analyses/train` are saved in the `model-artifacts`
volume, so they survive restarts and rebuilds. The volume starts as a copy of the models
bundled in `app/services/models/`. If the bundled models change, or to discard trained
models, stop the stack and delete the volume:

```bash
docker-compose down
docker volume rm seniorproject_model-artifacts
```

## Setup

Use Python 3.11 or newer. Run these commands from this directory:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

If Python is installed under a different command, substitute that command when
creating the virtual environment. On this Mac, Python 3.11 is also available at
`/opt/homebrew/bin/python3.11`.

## Run locally

The API needs Postgres. Start only the database container, apply migrations, then run
the server:

```bash
docker-compose -f ../docker-compose.yml up -d db
source .venv/bin/activate
alembic upgrade head
fastapi dev
```

The connection defaults to
`postgresql+psycopg://postgres:postgres@localhost:5432/senior_project`. Set
`DATABASE_URL` to use a different database.

The development server reloads when you edit the code. Stop it with `Ctrl+C`.

- API docs: <http://127.0.0.1:8000/docs>
- Alternative docs: <http://127.0.0.1:8000/redoc>
- OpenAPI schema: <http://127.0.0.1:8000/openapi.json>
- Health check: <http://127.0.0.1:8000/health>

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

For a server without development reload:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Tests

```bash
python -m pip install -e '.[dev]'
pytest
```

The tests need neither Postgres nor patient data: they replace the database session and
build input rows from the columns each model was trained on.

## Analysis endpoints

These implement the frontend contract in
[`frontend/docs/backend-handoff.md`](../frontend/docs/backend-handoff.md).

- `POST /api/analyses/manual`: JSON catheter measurements (1 to 4 catheters) plus an
  optional `model_name`. The request is validated, then refused with 501 and not saved:
  the trained models take recorded-data flags, not catheter measurements (see the TODO in
  `predict_from_manual`). Units of `unspecified` default to `C` and `g` (contact force).
- `POST /api/analyses/file`: multipart fields `file` (`.csv`, `.json`, or `.xlsx`, 10 MiB
  maximum), an optional `model_name`, and an optional `row_index`. A file with several rows
  needs `row_index` (0-based, blank rows not counted), and only that row is analyzed and
  saved, with the file name stored as e.g. `data.csv (row 3)`. The `id`, `recur`, and
  `redo` columns are dropped.
- `POST /api/analyses/ablation-sites`: multipart field `file` (one whitespace-delimited
  `.txt` patient file, 10 MiB maximum). It summarizes site measurements using the
  `unsupervised_model_v2.py` feature schema, then uses the cached
  `app/services/clustering_models/clustering_models.joblib` imputer, scaler, KMeans model, and PCA
  projection and saved `X_scaled` training samples. The response includes the assigned
  cluster, projected PCA point, every projected training sample colored by its KMeans
  cluster, and the top 15 between-cluster feature contributions. This exploratory result
  is not saved with outcome analyses and is not a clinical outcome prediction. The
  clustering artifact is stored in `app/services/clustering_models/`, outside the persistent
  volume used for user-trained outcome models.
- `POST /api/analyses/train` (requires sign-in, otherwise 401): multipart fields `file` (`.csv`, `.json`, or `.xlsx`, 10 MiB
  maximum), `target_column` (defaults to `recur`), and `model_name` (`xgboost`). The
  target can contain numeric or categorical labels and must have at least two classes,
  with at least two rows per class for stratified validation. The endpoint automatically
  selects binary logistic or multiclass soft-probability XGBoost and calculates held-out
  accuracy. Each run is saved to a uniquely timestamped file in
  `app/services/models/`; the API loads the newest timestamped model on startup and
  retains earlier model files. Its
  response includes classification type and class labels. Only a binary model trained
  on the `recur` target with labels `0` and `1` is compatible with the existing success/failure outcome-analysis
  endpoint; other classifiers are saved and guarded from being interpreted as that
  binary outcome.
- `GET /api/analyses?limit=50&offset=0` (requires sign-in): the account's saved analyses,
  newest first, in the frontend's `AnalysisRecord` shape plus `modelName`. The frontend
  loads it after sign-in.
- `GET /api/analyses/{analysisId}` (requires sign-in): one of the account's analyses, plus
  its submitted `input`.

Each prediction is saved to the `analyses` table with its input: the validated manual
request, or the parsed file row. If the save fails, the API returns 503 rather than an
unsaved prediction.

### Model selection

`model_name` is `logistic` (the default), `random_forest`, `xgboost`, or `k_nearest`
(labelled "Nearest centroid": `knc.py` trains a `NearestCentroid` classifier). An unknown
name returns 422; a model whose artifact failed to load at startup returns 503, and the
other models keep working.

The frontend builds its dropdown from `GET /api/models`, which lists every model with its
label, whether it loaded, and which file formats it accepts:

```json
{"defaultModel": "logistic", "models": [
  {"id": "k_nearest", "label": "Nearest centroid", "available": true, "inputFormats": ["raw"]}
]}
```

To add a model, add it to `MODEL_SPECS` in `app/services/predictor.py` and to `ModelName`
in `app/schemas.py` (a test checks they match). The frontend picks it up automatically.

Artifacts live in `app/services/models/`. Each model is aligned to the columns it was
trained on:

- `logistic`, `random_forest`, and `xgboost` use the combined columns from
  `clean_data.py`. A raw `data.csv`-style upload is combined the same way first, so both
  file formats give the same prediction.
- `k_nearest` uses the raw columns, including the `v` columns. It rejects a combined-column
  file with 422, because the raw columns cannot be recovered from it.

File uploads use the trained models. Manual entry returns 501 until catheter
measurements map to model features.

## Accounts

Accounts are stored in the `users` table. Passwords are kept only as salted scrypt
hashes. Signing in creates a row in `user_sessions` and sets an httpOnly, SameSite=Strict
`session` cookie holding a random token; only the token's SHA-256 is stored. Sessions last
7 days. Set `COOKIE_SECURE=true` when the app is served over HTTPS.

- `POST /api/accounts`: JSON `name`, `email`, `organization` (optional), `password`
  (8 to 256 characters). Creates the account, signs it in, and returns 201. A used email
  returns 409.
- `POST /api/accounts/sign-in`: JSON `email`, `password`. Wrong details return 401. After
  5 wrong passwords in a row the account is locked for 15 minutes: every attempt, even
  with the right password, returns 429 with `Retry-After`. A successful sign-in or a
  password reset clears the count.
- `POST /api/accounts/sign-out`: ends the session (204).
- `GET /api/accounts/me`: the signed-in account, or 401.
- `POST /api/accounts/password` (signed in): JSON `currentPassword`, `newPassword`. A wrong
  current password returns 403. Other sessions for the account are signed out.
- `POST /api/accounts/password-reset`: JSON `email`. Always returns 202 with the same
  message, so it does not reveal which emails have accounts. For a real account it sends
  a single-use link to `APP_URL/account/reset?token=...` that expires in 30 minutes, at
  most once a minute; a new link replaces the old one.
- `POST /api/accounts/password-reset/confirm`: JSON `token`, `newPassword`. An invalid,
  used, or expired token returns 400. Every session for the account is signed out.

Reset links are emailed through SMTP when `SMTP_HOST` is set (see `.env.example` for
`SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`). Without it the link is
written to the backend log, for local development:

```bash
docker-compose logs backend | grep "reset link"
```

Analyses run while signed in are saved with the account's `user_id`.
`GET /api/analyses` and `GET /api/analyses/{analysisId}` require sign-in and return only
that account's analyses (another account's analysis is a 404). Analyses run while signed
out are saved without an owner and cannot be listed.

## Heart disease detection

`GET /api/heart-disease/model` lists the input fields for the frontend's Heart Disease
page, and `POST /api/heart-disease/predict` takes `{"features": {...}}` with every field
and returns `predictedClass` (`positive` means heart disease present),
`positiveClassProbability`, and `modelVersion`. Out-of-range or unknown values return
422. Predictions are not saved.

The model is a copy of `cardiodisease_detection/models/xgboost_model.joblib` (trained by
`cardiodisease_detection/XGboost.py` on the UCI Heart Disease dataset) in
`app/services/heart_disease_models/`. Copy it again after retraining.

To use the real backend from the Vite dev server, set `VITE_USE_MOCK_API=false` in
`frontend/.env.local` and run both servers. Vite proxies `/api` to port 8000.

## Structure

```text
app/
  __init__.py
  main.py              # App creation, router registration, validation error format
  db.py                # Engine, sessions, DATABASE_URL
  models.py            # SQLAlchemy tables
  schemas.py           # Request/response models for the analysis API
  routers/
    __init__.py
    health.py          # GET /health
    analyses.py        # /api/analyses: file, manual, train, list, detail
    model_catalog.py   # GET /api/models (the frontend's model dropdown)
    accounts.py        # /api/accounts: create, sign in, sign out, current account
    heart_disease.py   # /api/heart-disease: field list and prediction
  auth.py              # Session cookie and the signed-in-user dependency
  services/
    __init__.py
    accounts.py        # Password hashing, users, sessions, lockout, resets
    analysis_store.py  # Save and load analyses
    file_parser.py     # Upload validation and CSV/JSON/XLSX parsing
    heart_disease.py   # Heart disease model and its input fields
    mailer.py          # Password reset emails (or log lines without SMTP)
    predictor.py       # Ablation outcome models
    training.py        # XGBoost training
migrations/            # Alembic migrations
tests/                 # pytest suite
alembic.ini
Dockerfile
pyproject.toml         # Package metadata, dependencies, and FastAPI entry point
```

To change the schema, edit `app/models.py`, then generate and review a migration:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

Add endpoint modules under `app/routers/`, then register each router with
`app.include_router(...)` in `app/main.py`. To require sign-in on an endpoint, add a
`CurrentUser` parameter (from `app.auth`).

`/health` checks application liveness only. It does not check external services.
Local environment files and virtual environments are ignored by Git.

Reference: [FastAPI application structure](https://fastapi.tiangolo.com/tutorial/bigger-applications/).
