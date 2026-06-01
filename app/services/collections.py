"""
Business logic for payment collections.

This service owns the rules for creating collections and computing
their time-based status transitions.  It is intentionally stateless
with respect to HTTP — storage is injected as a dependency.

Security note: The ``resolve_status`` helper is a pure function of
elapsed time with no user-controllable inputs, preventing any
client-side status manipulation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.constants.currencies import (
    COLLECTION_COMPLETED_DELAY,
    COLLECTION_PROCESSING_DELAY,
    Currency,
)
from app.exceptions.handlers import (
    CollectionNotFoundError,
    UnsupportedCurrencyError,
)
from app.models.collections import (
    CollectionRequest,
    CollectionResponse,
    CollectionStatus,
)
from app.storage.memory import MemoryStore


def _validate_currency(currency: str) -> None:
    """
    Ensure *currency* is a member of the ``Currency`` enum.

    Security note: This is a defence-in-depth check.  Pydantic already
    validates the enum, but service-layer validation ensures safety even
    if the model is bypassed in internal code paths.
    """
    try:
        Currency(currency)
    except ValueError:
        raise UnsupportedCurrencyError(currency)


def resolve_status(created_at: datetime) -> CollectionStatus:
    """
    Derive the current collection status from wall-clock elapsed time.

    Returns:
        ``pending``    — < 10 s since creation
        ``processing`` — 10–19 s since creation
        ``completed``  — ≥ 20 s since creation
    """
    elapsed: float = (datetime.now(timezone.utc) - created_at).total_seconds()

    if elapsed >= COLLECTION_COMPLETED_DELAY:
        return CollectionStatus.COMPLETED
    if elapsed >= COLLECTION_PROCESSING_DELAY:
        return CollectionStatus.PROCESSING
    return CollectionStatus.PENDING


def initiate_collection(
    request: CollectionRequest,
    store: MemoryStore,
) -> CollectionResponse:
    """
    Create a new collection record.

    The collection starts in ``pending`` status and transitions
    automatically based on wall-clock time (see ``resolve_status``).
    """
    _validate_currency(request.currency)

    collection_id = uuid4()
    now = datetime.now(timezone.utc)

    record: dict = {
        "collection_id": str(collection_id),
        "currency": request.currency,
        "amount": request.amount,
        "customer_name": request.customer_name,
        "reference": request.reference,
        "status": CollectionStatus.PENDING,
        "created_at": now.isoformat(),
    }
    store.save(str(collection_id), record)

    return CollectionResponse(
        collection_id=collection_id,
        currency=request.currency,
        amount=request.amount,
        customer_name=request.customer_name,
        reference=request.reference,
        status=CollectionStatus.PENDING,
        created_at=now,
    )


def get_collection(
    collection_id: str,
    store: MemoryStore,
) -> CollectionResponse:
    """
    Retrieve a collection and compute its current status.

    Raises:
        CollectionNotFoundError: If no record matches *collection_id*.
    """
    record = store.get(collection_id)
    if record is None:
        raise CollectionNotFoundError(collection_id)

    created_at = datetime.fromisoformat(record["created_at"])
    current_status = resolve_status(created_at)

    return CollectionResponse(
        collection_id=record["collection_id"],
        currency=record["currency"],
        amount=record["amount"],
        customer_name=record["customer_name"],
        reference=record["reference"],
        status=current_status,
        created_at=created_at,
    )
