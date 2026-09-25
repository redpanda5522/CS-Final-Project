"""FastAPI application entry point."""

from fastapi import FastAPI

from app.routers import health

app = FastAPI(
    title="Senior Project API",
    description="Backend API for Senior Project.",
    version="0.1.0",
)

app.include_router(health.router)
