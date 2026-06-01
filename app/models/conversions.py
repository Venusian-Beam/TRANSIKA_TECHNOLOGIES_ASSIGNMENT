"""
Pydantic v2 models for the FX conversion domain.

Security note: ``source_currency`` and ``target_currency`` are
validated as ``Currency`` enums — unknown codes are rejected at the
Pydantic layer before touching service logic.  ``amount`` is
constrained to > 0.  The ``collection_id`` and ``quote_id`` fields
use Python's ``UUID`` type to guarantee well-formed identifiers.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.constants.currencies import Currency


# ---------------------------------------------------------------------------
# Quote
# ---------------------------------------------------------------------------

class QuoteRequest(BaseModel):
    """Inbound payload for ``POST /conversions/quote``."""

    source_currency: Currency = Field(
        ...,
        description="Currency the customer is paying in.",
        examples=["GHS"],
    )
    target_currency: Currency = Field(
        ...,
        description="Currency the beneficiary will receive.",
        examples=["USD"],
    )
    amount: float = Field(
        ...,
        gt=0,
        description="Amount in source currency to convert.",
        examples=[1000.00],
    )

    model_config = {"str_strip_whitespace": True}


class QuoteResponse(BaseModel):
    """Outbound payload for a generated FX quote."""

    quote_id: UUID
    source_currency: Currency
    target_currency: Currency
    source_amount: float
    exchange_rate: float
    converted_amount: float
    fee_usd: float
    expires_at: datetime
    created_at: datetime


# ---------------------------------------------------------------------------
# Conversion execution
# ---------------------------------------------------------------------------

class ExecuteRequest(BaseModel):
    """Inbound payload for ``POST /conversions/execute``."""

    quote_id: UUID = Field(
        ...,
        description="Previously obtained quote identifier.",
    )
    collection_id: UUID = Field(
        ...,
        description="Collection that funds this conversion.",
    )


class TransferResponse(BaseModel):
    """Outbound payload after a conversion is successfully executed."""

    transfer_id: UUID
    quote_id: UUID
    collection_id: UUID
    source_currency: Currency
    target_currency: Currency
    source_amount: float
    converted_amount: float
    fee_usd: float
    exchange_rate: float
    status: str = "processing"
    created_at: datetime
