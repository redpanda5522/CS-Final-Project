"""Basic application liveness endpoint."""

from typing import Literal

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, Literal["ok"]]:
    """Confirm the API is running."""
    return {"status": "ok"}
