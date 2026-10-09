"""FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routers import analyses, health

app = FastAPI(
    title="Senior Project API",
    description="Backend API for Senior Project.",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(analyses.router)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    """Return FastAPI's standard 422 shape without echoing submitted values.

    The default handler includes each invalid `input`, which leaks submitted data back
    and fails to serialize non-finite numbers such as NaN.
    """
    detail = [
        {key: value for key, value in item.items() if key in ("type", "loc", "msg")}
        for item in error.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": detail})
