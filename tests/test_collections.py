"""
Tests for the collections endpoints.

Covers:
1. Successful collection initiation
2. Unsupported currency rejection
3. Status lifecycle transitions (pending → processing → completed)
4. Collection not found (404)
5. Validation error for negative amount
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models.collections import CollectionStatus


# -----------------------------------------------------------------------
# 1. Successful collection initiation
# -----------------------------------------------------------------------

class TestInitiateCollection:
    """POST /collections/initiate — happy path and edge cases."""

    def test_successful_initiation(self, client: TestClient) -> None:
        """A valid request creates a collection with ``pending`` status."""
        payload = {
            "currency": "GHS",
            "amount": 500.00,
            "customer_name": "Kwame Asante",
            "reference": "INV-2025-001",
        }
        response = client.post("/collections/initiate", json=payload)

        assert response.status_code == 201
        body = response.json()
        assert body["currency"] == "GHS"
        assert body["amount"] == 500.00
        assert body["customer_name"] == "Kwame Asante"
        assert body["reference"] == "INV-2025-001"
        assert body["status"] == CollectionStatus.PENDING
        assert "collection_id" in body
        assert "created_at" in body

    def test_all_supported_currencies(self, client: TestClient) -> None:
        """Every supported currency is accepted."""
        for currency in ("GHS", "NGN", "KES", "ZAR", "USD"):
            payload = {
                "currency": currency,
                "amount": 100.00,
                "customer_name": "Test User",
                "reference": f"REF-{currency}",
            }
            response = client.post("/collections/initiate", json=payload)
            assert response.status_code == 201, f"Failed for {currency}"


# -----------------------------------------------------------------------
# 2. Unsupported currency rejection
# -----------------------------------------------------------------------

class TestUnsupportedCurrency:
    """POST /collections/initiate — invalid currency codes."""

    def test_unsupported_currency_rejected(self, client: TestClient) -> None:
        """An unknown currency code returns a 422 validation error."""
        payload = {
            "currency": "XYZ",
            "amount": 100.00,
            "customer_name": "Test User",
            "reference": "REF-001",
        }
        response = client.post("/collections/initiate", json=payload)

        assert response.status_code == 422
        body = response.json()
        assert body["code"] == "VALIDATION_ERROR"

    def test_empty_currency_rejected(self, client: TestClient) -> None:
        """An empty currency string returns a validation error."""
        payload = {
            "currency": "",
            "amount": 100.00,
            "customer_name": "Test User",
            "reference": "REF-001",
        }
        response = client.post("/collections/initiate", json=payload)
        assert response.status_code == 422


# -----------------------------------------------------------------------
# 3. Status lifecycle
# -----------------------------------------------------------------------

class TestCollectionStatus:
    """GET /collections/{id} — time-based status transitions."""

    def test_pending_status(self, client: TestClient) -> None:
        """A freshly created collection is ``pending``."""
        payload = {
            "currency": "NGN",
            "amount": 50000.00,
            "customer_name": "Adebayo Ogunlesi",
            "reference": "REF-NGN-001",
        }
        create_resp = client.post("/collections/initiate", json=payload)
        collection_id = create_resp.json()["collection_id"]

        get_resp = client.get(f"/collections/{collection_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == CollectionStatus.PENDING

    def test_processing_status_after_10s(self, client: TestClient) -> None:
        """After 10 seconds the status transitions to ``processing``."""
        payload = {
            "currency": "KES",
            "amount": 10000.00,
            "customer_name": "Wanjiku Kamau",
            "reference": "REF-KES-001",
        }
        create_resp = client.post("/collections/initiate", json=payload)
        collection_id = create_resp.json()["collection_id"]

        # Simulate 15 seconds elapsed
        fake_now = datetime.now(timezone.utc) + timedelta(seconds=15)
        with patch(
            "app.services.collections.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            get_resp = client.get(f"/collections/{collection_id}")
            assert get_resp.json()["status"] == CollectionStatus.PROCESSING

    def test_completed_status_after_20s(self, client: TestClient) -> None:
        """After 20 seconds the status transitions to ``completed``."""
        payload = {
            "currency": "ZAR",
            "amount": 2500.00,
            "customer_name": "Sipho Dlamini",
            "reference": "REF-ZAR-001",
        }
        create_resp = client.post("/collections/initiate", json=payload)
        collection_id = create_resp.json()["collection_id"]

        # Simulate 25 seconds elapsed
        fake_now = datetime.now(timezone.utc) + timedelta(seconds=25)
        with patch(
            "app.services.collections.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            get_resp = client.get(f"/collections/{collection_id}")
            assert get_resp.json()["status"] == CollectionStatus.COMPLETED


# -----------------------------------------------------------------------
# 4. Collection not found
# -----------------------------------------------------------------------

class TestCollectionNotFound:
    """GET /collections/{id} — missing records."""

    def test_nonexistent_collection_returns_404(
        self, client: TestClient
    ) -> None:
        """A random UUID returns a 404 with the standard error envelope."""
        import uuid

        fake_id = str(uuid.uuid4())
        response = client.get(f"/collections/{fake_id}")

        assert response.status_code == 404
        body = response.json()
        assert body["code"] == "COLLECTION_NOT_FOUND"


# -----------------------------------------------------------------------
# 5. Validation errors
# -----------------------------------------------------------------------

class TestCollectionValidation:
    """POST /collections/initiate — input validation."""

    def test_negative_amount_rejected(self, client: TestClient) -> None:
        """A negative amount returns a validation error."""
        payload = {
            "currency": "GHS",
            "amount": -100.00,
            "customer_name": "Test User",
            "reference": "REF-001",
        }
        response = client.post("/collections/initiate", json=payload)
        assert response.status_code == 422

    def test_zero_amount_rejected(self, client: TestClient) -> None:
        """Zero amount returns a validation error."""
        payload = {
            "currency": "GHS",
            "amount": 0,
            "customer_name": "Test User",
            "reference": "REF-001",
        }
        response = client.post("/collections/initiate", json=payload)
        assert response.status_code == 422

    def test_missing_required_field(self, client: TestClient) -> None:
        """Omitting a required field returns a validation error."""
        payload = {
            "currency": "GHS",
            "amount": 100.00,
            # customer_name and reference omitted
        }
        response = client.post("/collections/initiate", json=payload)
        assert response.status_code == 422
