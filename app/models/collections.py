"""
Pydantic v2 models for the collections domain.

Security note: ``Currency`` is validated via enum membership — arbitrary
strings are rejected before they reach service logic.  ``amount`` uses
``gt=0`` to prevent zero-value or negative collection attempts that could
be exploited for fee-free probing.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.constants.currencies import Currency


class CollectionStatus(StrEnum):
    """Lifecycle states for a collection."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"


class CollectionRequest(BaseModel):
    """Inbound payload for ``POST /collections/initiate``."""

    currency: Currency = Field(
        ...,
        description="ISO 4217 code of the currency being collected.",
        examples=["GHS"],
    )
    amount: float = Field(
        ...,
        gt=0,
        description="Amount to collect.  Must be > 0.",
        examples=[1000.00],
    )
    customer_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Full name of the paying customer.",
        examples=["Kwame Asante"],
    )
    reference: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Merchant-supplied idempotency reference.",
        examples=["INV-2025-001"],
    )

    model_config = {"str_strip_whitespace": True}


class CollectionResponse(BaseModel):
    """Outbound payload for a single collection record."""

    collection_id: UUID
    currency: Currency
    amount: float
    customer_name: str
    reference: str
    status: CollectionStatus
    created_at: datetime
