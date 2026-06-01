"""
HTTP endpoints for FX conversion quoting and execution.

Security note: Both ``quote_id`` and ``collection_id`` are validated as
UUID types by Pydantic at the schema layer, ensuring only well-formed
identifiers reach service logic.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.models.conversions import (
    ExecuteRequest,
    QuoteRequest,
    QuoteResponse,
    TransferResponse,
)
from app.models.responses import ErrorResponse
from app.services import conversions as conversion_service
from app.storage.memory import (
    MemoryStore,
    get_collection_store,
    get_quote_store,
    get_transfer_store,
)

router = APIRouter(
    prefix="/conversions",
    tags=["Conversions"],
)


@router.post(
    "/quote",
    response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request an FX quote",
    description=(
        "Generate a time-limited FX quote for a given currency pair "
        "and amount. The quote includes the exchange rate, converted "
        "amount, and service fee.  Quotes expire after 60 seconds."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
    },
)
def create_quote(
    request: QuoteRequest,
    store: MemoryStore = Depends(get_quote_store),
) -> QuoteResponse:
    """Generate a new FX conversion quote."""
    return conversion_service.create_quote(request, store)


@router.post(
    "/execute",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute an FX conversion",
    description=(
        "Execute a previously quoted FX conversion. The referenced "
        "quote must still be valid (not expired) and the associated "
        "collection must have reached ``completed`` status."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Quote or collection not found"},
        409: {"model": ErrorResponse, "description": "Collection not completed"},
        410: {"model": ErrorResponse, "description": "Quote expired"},
    },
)
def execute_conversion(
    request: ExecuteRequest,
    quote_store: MemoryStore = Depends(get_quote_store),
    collection_store: MemoryStore = Depends(get_collection_store),
    transfer_store: MemoryStore = Depends(get_transfer_store),
) -> TransferResponse:
    """Execute a quoted FX conversion."""
    return conversion_service.execute_conversion(
        request, quote_store, collection_store, transfer_store
    )
