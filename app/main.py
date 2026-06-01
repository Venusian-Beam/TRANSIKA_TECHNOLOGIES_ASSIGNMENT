"""
FastAPI application entry-point.

This module wires together routers, registers global exception handlers,
and configures OpenAPI metadata.

Security notes:
- A global handler for ``ServiceError`` ensures that no unhandled domain
  exception leaks raw Python tracebacks to the client.
- A catch-all handler for ``Exception`` returns a generic 500 without
  exposing internal details.  In production, this should also log to a
  monitoring backend (e.g. Sentry).
- ``RequestValidationError`` is overridden so that Pydantic validation
  failures use the same envelope as domain errors.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions.handlers import ServiceError
from app.models.responses import ErrorResponse
from app.routers import collections, conversions

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Transika Payment Collections & FX Conversion API",
    description=(
        "A production-quality service for initiating payment collections "
        "across African currencies and executing FX conversions with "
        "real-time quoting, fee calculation, and lifecycle management."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(collections.router)
app.include_router(conversions.router)

# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(ServiceError)
async def service_error_handler(
    _request: Request, exc: ServiceError
) -> JSONResponse:
    """
    Render all domain errors using the standard ``ErrorResponse`` envelope.

    Security note: Only ``code``, ``message``, and ``details`` are
    returned.  The Python traceback is deliberately omitted.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            code=exc.code,
            message=exc.message,
            details=exc.details,
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Normalise Pydantic / FastAPI validation errors into the standard
    error envelope.

    Security note: Raw validation error objects are serialised, which
    may include field names and types.  This is generally safe for public
    APIs but should be reviewed if the schema contains sensitive field
    names.
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            code="VALIDATION_ERROR",
            message="The request body failed validation.",
            details={"errors": exc.errors()},
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    _request: Request, _exc: Exception
) -> JSONResponse:
    """
    Catch-all for unexpected errors.

    Security note: Never expose the exception message or traceback.
    In production, log ``_exc`` to an observability platform here.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred. Please try again later.",
            details={},
        ).model_dump(),
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    response_model=dict[str, str],
)
def health_check() -> dict[str, str]:
    """Return a simple liveness probe response."""
    return {"status": "healthy"}
