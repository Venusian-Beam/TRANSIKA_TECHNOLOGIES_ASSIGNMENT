"""
Business logic for FX quoting and conversion execution.

Security notes:
- Fee calculation uses ``max()`` to enforce the USD 0.50 floor,
  preventing zero-fee bypass on tiny amounts.
- Quote expiry is checked server-side against UTC wall-clock time;
  clients cannot extend the TTL.
- Collection status is re-validated at execution time to prevent
  race conditions between quote creation and execution.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.constants.currencies import (
    FEE_MINIMUM_USD,
    FEE_PERCENTAGE,
    FX_RATES,
    QUOTE_EXPIRY_SECONDS,
)
from app.exceptions.handlers import (
    CollectionNotCompletedError,
    CollectionNotFoundError,
    InvalidAmountError,
    QuoteExpiredError,
    QuoteNotFoundError,
    UnsupportedCorridorError,
)
from app.models.collections import CollectionStatus
from app.models.conversions import (
    ExecuteRequest,
    QuoteRequest,
    QuoteResponse,
    TransferResponse,
)
from app.services.collections import resolve_status
from app.storage.memory import MemoryStore


def _calculate_fee(source_amount: float, exchange_rate: float) -> float:
    """
    Compute the service fee in USD.

    The fee is 1.2 % of the source amount converted to USD, floored
    at USD 0.50.  When the source *is* USD the rate is 1.0.

    Security note: ``max()`` enforces the minimum fee, preventing
    micro-transaction abuse that could bypass the fee entirely.
    """
    usd_equivalent: float = source_amount * exchange_rate
    return round(max(usd_equivalent * FEE_PERCENTAGE, FEE_MINIMUM_USD), 2)


def create_quote(
    request: QuoteRequest,
    store: MemoryStore,
) -> QuoteResponse:
    """
    Generate an FX quote with rate, fee, and 60-second expiry.

    Raises:
        InvalidAmountError:       If ``amount`` is ≤ 0.
        UnsupportedCorridorError: If the currency pair is not configured.
    """
    if request.amount <= 0:
        raise InvalidAmountError(request.amount)

    corridor = (request.source_currency.value, request.target_currency.value)
    rate: float | None = FX_RATES.get(corridor)

    if rate is None:
        raise UnsupportedCorridorError(
            request.source_currency, request.target_currency
        )

    converted_amount: float = round(request.amount * rate, 2)

    # Determine USD-equivalent rate for fee calculation.
    # If converting *to* USD the rate itself works; otherwise look up
    # a source→USD rate, falling back to 1.0 if source *is* USD.
    usd_rate: float
    if request.target_currency == "USD":
        usd_rate = rate
    else:
        usd_rate = FX_RATES.get(
            (request.source_currency.value, "USD"), 1.0
        )

    fee_usd: float = _calculate_fee(request.amount, usd_rate)

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=QUOTE_EXPIRY_SECONDS)
    quote_id = uuid4()

    record: dict = {
        "quote_id": str(quote_id),
        "source_currency": request.source_currency,
        "target_currency": request.target_currency,
        "source_amount": request.amount,
        "exchange_rate": rate,
        "converted_amount": converted_amount,
        "fee_usd": fee_usd,
        "expires_at": expires_at.isoformat(),
        "created_at": now.isoformat(),
    }
    store.save(str(quote_id), record)

    return QuoteResponse(
        quote_id=quote_id,
        source_currency=request.source_currency,
        target_currency=request.target_currency,
        source_amount=request.amount,
        exchange_rate=rate,
        converted_amount=converted_amount,
        fee_usd=fee_usd,
        expires_at=expires_at,
        created_at=now,
    )


def execute_conversion(
    request: ExecuteRequest,
    quote_store: MemoryStore,
    collection_store: MemoryStore,
    transfer_store: MemoryStore,
) -> TransferResponse:
    """
    Execute a previously quoted FX conversion.

    Validation chain (order matters for clear error reporting):
    1. Quote must exist.
    2. Quote must not be expired.
    3. Collection must exist.
    4. Collection must be in ``completed`` status.

    Security note: Each validation step is explicit and fails-fast.
    This prevents partial state changes and ensures the client
    receives the most specific error possible.
    """
    # --- 1. Quote existence ---
    quote = quote_store.get(str(request.quote_id))
    if quote is None:
        raise QuoteNotFoundError(str(request.quote_id))

    # --- 2. Quote expiry ---
    expires_at = datetime.fromisoformat(quote["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        raise QuoteExpiredError(str(request.quote_id))

    # --- 3. Collection existence ---
    collection = collection_store.get(str(request.collection_id))
    if collection is None:
        raise CollectionNotFoundError(str(request.collection_id))

    # --- 4. Collection status ---
    created_at = datetime.fromisoformat(collection["created_at"])
    current_status = resolve_status(created_at)
    if current_status != CollectionStatus.COMPLETED:
        raise CollectionNotCompletedError(
            str(request.collection_id), current_status.value
        )

    # --- All checks passed — create transfer ---
    transfer_id = uuid4()
    now = datetime.now(timezone.utc)

    transfer_record: dict = {
        "transfer_id": str(transfer_id),
        "quote_id": str(request.quote_id),
        "collection_id": str(request.collection_id),
        "source_currency": quote["source_currency"],
        "target_currency": quote["target_currency"],
        "source_amount": quote["source_amount"],
        "converted_amount": quote["converted_amount"],
        "fee_usd": quote["fee_usd"],
        "exchange_rate": quote["exchange_rate"],
        "status": "processing",
        "created_at": now.isoformat(),
    }
    transfer_store.save(str(transfer_id), transfer_record)

    return TransferResponse(
        transfer_id=transfer_id,
        quote_id=request.quote_id,
        collection_id=request.collection_id,
        source_currency=quote["source_currency"],
        target_currency=quote["target_currency"],
        source_amount=quote["source_amount"],
        converted_amount=quote["converted_amount"],
        fee_usd=quote["fee_usd"],
        exchange_rate=quote["exchange_rate"],
        status="processing",
        created_at=now,
    )
