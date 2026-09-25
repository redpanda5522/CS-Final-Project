# Senior Project Backend

A minimal FastAPI backend, ready for project requirements to be added.

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

```bash
source .venv/bin/activate
fastapi dev
```

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

## Structure

```text
app/
  __init__.py
  main.py              # App creation and router registration
  routers/
    __init__.py
    health.py          # GET /health
pyproject.toml         # Package metadata, dependencies, and FastAPI entry point
```

Add endpoint modules under `app/routers/`, then register each router with
`app.include_router(...)` in `app/main.py`. Add request/response models, business
logic, persistence, and authentication as the backend requirements become clear.

`/health` checks application liveness only. It does not check external services.
Local environment files and virtual environments are ignored by Git.

Reference: [FastAPI application structure](https://fastapi.tiangolo.com/tutorial/bigger-applications/).
