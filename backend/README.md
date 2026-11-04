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

## Analysis endpoints

These implement the frontend contract in
[`frontend/docs/backend-handoff.md`](../frontend/docs/backend-handoff.md).

- `POST /api/analyses/manual`: JSON catheter measurements (1 to 4 catheters). Units of
  `unspecified` default to `C` for temperature and `g` (contact force) for pressure.
- `POST /api/analyses/file`: multipart field `file` containing one procedure as `.csv`,
  `.json`, or `.xlsx` (10 MiB maximum). The `id`, `recur`, and `redo` columns are dropped.
- `GET /api/analyses?limit=50&offset=0`: saved analyses, newest first, in the frontend's
  `AnalysisRecord` shape. The frontend does not call this yet.
- `GET /api/analyses/{analysisId}`: one saved analysis, plus its submitted `input`.

Each prediction is saved to the `analyses` table with its input: the validated manual
request, or the parsed file row. If the save fails, the API returns 503 rather than an
unsaved prediction.

Predictions are currently a **stub** (`probability` 0.5, `modelVersion` `stub-v0`). See the
TODOs in `app/services/predictor.py` for where the trained model plugs in.

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
    analyses.py        # POST /api/analyses/file and /api/analyses/manual
  services/
    __init__.py
    analysis_store.py  # Save and load analyses
    file_parser.py     # Upload validation and CSV/JSON/XLSX parsing
    predictor.py       # Prediction stub (TODO: trained model)
migrations/            # Alembic migrations
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
`app.include_router(...)` in `app/main.py`. There is no authentication yet.

`/health` checks application liveness only. It does not check external services.
Local environment files and virtual environments are ignored by Git.

Reference: [FastAPI application structure](https://fastapi.tiangolo.com/tutorial/bigger-applications/).
