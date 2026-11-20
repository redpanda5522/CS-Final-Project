FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install .

COPY alembic.ini ./
COPY migrations ./migrations

# Training saves new model artifacts in app/services/models, so the app user must own it.
RUN useradd --create-home --uid 10001 appuser \
    && chown appuser:appuser app/services/models
USER appuser

EXPOSE 8000

# Apply pending migrations, then start the API.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
