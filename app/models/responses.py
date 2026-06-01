"""
Consistent API response envelope.

Every response — success or error — is wrapped in a uniform structure
so that clients can rely on a single parsing contract.

Security note: The ``ErrorResponse`` intentionally omits stack traces
and internal identifiers.  ``details`` should only contain data that is
safe for external consumers.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error envelope returned for all non-2xx responses."""

    code: str = Field(
        ...,
        description="Machine-readable error code.",
        examples=["UNSUPPORTED_CURRENCY"],
    )
    message: str = Field(
        ...,
        description="Human-readable error description.",
        examples=["Currency 'XYZ' is not supported."],
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional structured data for debugging.",
    )
