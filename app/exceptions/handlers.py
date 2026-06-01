"""
Custom exception hierarchy for the payment service.

Every domain error inherits from ``ServiceError`` so that the global
exception handler in ``app.main`` can render a uniform JSON envelope.

Security note: Exception messages are carefully worded to avoid leaking
internal implementation details (e.g. storage keys, stack traces) to
API consumers while still providing actionable diagnostics.
"""

from __future__ import annotations

from typing import Any


class ServiceError(Exception):
    """
    Base exception for all domain-level errors.

    Attributes:
        status_code: HTTP status code to return.
        code:        Machine-readable error code for client consumption.
        message:     Human-readable description safe for external display.
        details:     Optional structured data providing additional context.
    """

    def __init__(
        self,
        *,
        status_code: int = 400,
        code: str = "BAD_REQUEST",
        message: str = "The request could not be processed.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


class UnsupportedCurrencyError(ServiceError):
    """Raised when a request references a currency not on the allow-list."""

    def __init__(self, currency: str) -> None:
        super().__init__(
            status_code=400,
            code="UNSUPPORTED_CURRENCY",
            message=f"Currency '{currency}' is not supported.",
            details={"currency": currency},
        )


class UnsupportedCorridorError(ServiceError):
    """Raised when no FX rate exists for the requested currency pair."""

    def __init__(self, source: str, target: str) -> None:
        super().__init__(
            status_code=400,
            code="UNSUPPORTED_CORRIDOR",
            message=f"No FX corridor exists for {source} → {target}.",
            details={"source_currency": source, "target_currency": target},
        )


class CollectionNotFoundError(ServiceError):
    """Raised when a collection_id does not match any stored record."""

    def __init__(self, collection_id: str) -> None:
        super().__init__(
            status_code=404,
            code="COLLECTION_NOT_FOUND",
            message="The requested collection was not found.",
            details={"collection_id": collection_id},
        )


class QuoteNotFoundError(ServiceError):
    """Raised when a quote_id does not match any stored record."""

    def __init__(self, quote_id: str) -> None:
        super().__init__(
            status_code=404,
            code="QUOTE_NOT_FOUND",
            message="The requested quote was not found.",
            details={"quote_id": quote_id},
        )


class QuoteExpiredError(ServiceError):
    """Raised when a quote's TTL has elapsed."""

    def __init__(self, quote_id: str) -> None:
        super().__init__(
            status_code=410,
            code="QUOTE_EXPIRED",
            message="This quote has expired. Please request a new one.",
            details={"quote_id": quote_id},
        )


class CollectionNotCompletedError(ServiceError):
    """Raised when a conversion execution references an incomplete collection."""

    def __init__(self, collection_id: str, current_status: str) -> None:
        super().__init__(
            status_code=409,
            code="COLLECTION_NOT_COMPLETED",
            message=(
                "The associated collection has not completed yet. "
                f"Current status: {current_status}."
            ),
            details={
                "collection_id": collection_id,
                "current_status": current_status,
            },
        )


class InvalidAmountError(ServiceError):
    """Raised when the requested amount is zero or negative."""

    def __init__(self, amount: float) -> None:
        super().__init__(
            status_code=400,
            code="INVALID_AMOUNT",
            message="Amount must be a positive number.",
            details={"amount": amount},
        )
