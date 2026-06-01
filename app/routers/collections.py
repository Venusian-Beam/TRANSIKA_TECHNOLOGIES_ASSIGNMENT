"""
HTTP endpoints for payment collections.

Security note: The ``collection_id`` path parameter is validated as a
UUID by Pydantic before reaching service code, preventing path-traversal
or injection attacks via malformed identifiers.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.models.collections import CollectionRequest, CollectionResponse
from app.models.responses import ErrorResponse
from app.services import collections as collection_service
from app.storage.memory import MemoryStore, get_collection_store

router = APIRouter(
    prefix="/collections",
    tags=["Collections"],
)


@router.post(
    "/initiate",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate a payment collection",
    description=(
        "Create a new collection request. The collection begins in "
        "``pending`` status, transitions to ``processing`` after 10 s, "
        "and reaches ``completed`` after 20 s."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def initiate_collection(
    request: CollectionRequest,
    store: MemoryStore = Depends(get_collection_store),
) -> CollectionResponse:
    """Create a new payment collection."""
    return collection_service.initiate_collection(request, store)


@router.get(
    "/{collection_id}",
    response_model=CollectionResponse,
    summary="Retrieve a collection",
    description=(
        "Look up a collection by its UUID. The returned ``status`` field "
        "reflects the current lifecycle state based on elapsed time."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Collection not found"},
    },
)
def get_collection(
    collection_id: UUID,
    store: MemoryStore = Depends(get_collection_store),
) -> CollectionResponse:
    """Retrieve collection details by ID."""
    return collection_service.get_collection(str(collection_id), store)
