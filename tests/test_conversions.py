"""
Tests for the FX conversion endpoints.

Covers:
1. Valid conversion quote generation
2. Unsupported corridor rejection
3. Fee calculation correctness
4. Expired quote rejection
5. Incomplete collection rejection
6. Successful conversion execution
7. Quote not found
8. Collection not found during execution
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.constants.currencies import FEE_MINIMUM_USD, FX_RATES


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _create_collection(client: TestClient, currency: str = "GHS") -> str:
    """Create a collection and return its ID."""
    payload = {
        "currency": currency,
        "amount": 1000.00,
        "customer_name": "Test User",
        "reference": "REF-TEST-001",
    }
    resp = client.post("/collections/initiate", json=payload)
    assert resp.status_code == 201
    return resp.json()["collection_id"]


def _create_quote(
    client: TestClient,
    source: str = "GHS",
    target: str = "USD",
    amount: float = 1000.00,
) -> dict:
    """Create a quote and return the full response body."""
    payload = {
        "source_currency": source,
        "target_currency": target,
        "amount": amount,
    }
    resp = client.post("/conversions/quote", json=payload)
    assert resp.status_code == 201
    return resp.json()


# -----------------------------------------------------------------------
# 1. Valid conversion quote
# -----------------------------------------------------------------------

class TestCreateQuote:
    """POST /conversions/quote — happy path."""

    def test_valid_quote_created(self, client: TestClient) -> None:
        """A valid corridor and amount returns a complete quote."""
        body = _create_quote(client, "GHS", "USD", 1000.00)

        expected_rate = FX_RATES[("GHS", "USD")]
        expected_converted = round(1000.00 * expected_rate, 2)

        assert body["source_currency"] == "GHS"
        assert body["target_currency"] == "USD"
        assert body["source_amount"] == 1000.00
        assert body["exchange_rate"] == expected_rate
        assert body["converted_amount"] == expected_converted
        assert body["fee_usd"] >= FEE_MINIMUM_USD
        assert "quote_id" in body
        assert "expires_at" in body
        assert "created_at" in body

    def test_multiple_corridors(self, client: TestClient) -> None:
        """All configured corridors produce valid quotes."""
        corridors = [
            ("GHS", "USD"),
            ("NGN", "USD"),
            ("KES", "USD"),
            ("ZAR", "USD"),
            ("USD", "GHS"),
            ("USD", "NGN"),
        ]
        for source, target in corridors:
            body = _create_quote(client, source, target, 500.00)
            assert body["exchange_rate"] == FX_RATES[(source, target)]


# -----------------------------------------------------------------------
# 2. Unsupported corridor
# -----------------------------------------------------------------------

class TestUnsupportedCorridor:
    """POST /conversions/quote — missing FX corridors."""

    def test_unsupported_corridor_rejected(
        self, client: TestClient
    ) -> None:
        """A currency pair without a configured rate returns 400."""
        payload = {
            "source_currency": "GHS",
            "target_currency": "KES",
            "amount": 100.00,
        }
        resp = client.post("/conversions/quote", json=payload)

        assert resp.status_code == 400
        body = resp.json()
        assert body["code"] == "UNSUPPORTED_CORRIDOR"


# -----------------------------------------------------------------------
# 3. Fee calculation
# -----------------------------------------------------------------------

class TestFeeCalculation:
    """POST /conversions/quote — fee correctness."""

    def test_fee_is_1_2_percent(self, client: TestClient) -> None:
        """Fee is 1.2 % of the USD-equivalent source amount."""
        body = _create_quote(client, "GHS", "USD", 1000.00)

        rate = FX_RATES[("GHS", "USD")]
        usd_value = 1000.00 * rate
        expected_fee = round(max(usd_value * 0.012, FEE_MINIMUM_USD), 2)

        assert body["fee_usd"] == expected_fee

    def test_fee_minimum_enforced(self, client: TestClient) -> None:
        """Very small amounts still pay the USD 0.50 minimum fee."""
        body = _create_quote(client, "GHS", "USD", 1.00)
        assert body["fee_usd"] == FEE_MINIMUM_USD


# -----------------------------------------------------------------------
# 4. Expired quote rejection
# -----------------------------------------------------------------------

class TestExpiredQuote:
    """POST /conversions/execute — expired quotes."""

    def test_expired_quote_rejected(self, client: TestClient) -> None:
        """Executing an expired quote returns 410."""
        collection_id = _create_collection(client, "GHS")
        quote = _create_quote(client, "GHS", "USD", 1000.00)

        # Fast-forward time past quote expiry (61 seconds)
        future = datetime.now(timezone.utc) + timedelta(seconds=61)

        with patch(
            "app.services.conversions.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = future
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            payload = {
                "quote_id": quote["quote_id"],
                "collection_id": collection_id,
            }
            resp = client.post("/conversions/execute", json=payload)

        assert resp.status_code == 410
        assert resp.json()["code"] == "QUOTE_EXPIRED"


# -----------------------------------------------------------------------
# 5. Incomplete collection rejection
# -----------------------------------------------------------------------

class TestIncompleteCollection:
    """POST /conversions/execute — collection not yet completed."""

    def test_pending_collection_rejected(self, client: TestClient) -> None:
        """A pending collection cannot fund a conversion (409)."""
        collection_id = _create_collection(client, "GHS")
        quote = _create_quote(client, "GHS", "USD", 1000.00)

        payload = {
            "quote_id": quote["quote_id"],
            "collection_id": collection_id,
        }
        resp = client.post("/conversions/execute", json=payload)

        assert resp.status_code == 409
        body = resp.json()
        assert body["code"] == "COLLECTION_NOT_COMPLETED"
        assert body["details"]["current_status"] == "pending"


# -----------------------------------------------------------------------
# 6. Successful conversion execution
# -----------------------------------------------------------------------

class TestExecuteConversion:
    """POST /conversions/execute — happy path."""

    def test_successful_execution(self, client: TestClient) -> None:
        """A valid quote + completed collection produces a transfer."""
        collection_id = _create_collection(client, "GHS")
        quote = _create_quote(client, "GHS", "USD", 1000.00)

        # Simulate collection reaching completed status (25 s elapsed)
        future = datetime.now(timezone.utc) + timedelta(seconds=25)
        with patch(
            "app.services.conversions.datetime"
        ) as mock_conv_dt, patch(
            "app.services.collections.datetime"
        ) as mock_coll_dt:
            for m in (mock_conv_dt, mock_coll_dt):
                m.now.return_value = future
                m.fromisoformat = datetime.fromisoformat
                m.side_effect = lambda *a, **kw: datetime(*a, **kw)

            payload = {
                "quote_id": quote["quote_id"],
                "collection_id": collection_id,
            }
            resp = client.post("/conversions/execute", json=payload)

        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "processing"
        assert "transfer_id" in body
        assert body["quote_id"] == quote["quote_id"]
        assert body["collection_id"] == collection_id
        assert body["source_currency"] == "GHS"
        assert body["target_currency"] == "USD"


# -----------------------------------------------------------------------
# 7. Quote not found
# -----------------------------------------------------------------------

class TestQuoteNotFound:
    """POST /conversions/execute — missing quotes."""

    def test_nonexistent_quote_returns_404(
        self, client: TestClient
    ) -> None:
        """A random quote_id returns 404."""
        import uuid

        collection_id = _create_collection(client, "GHS")
        payload = {
            "quote_id": str(uuid.uuid4()),
            "collection_id": collection_id,
        }
        resp = client.post("/conversions/execute", json=payload)

        assert resp.status_code == 404
        assert resp.json()["code"] == "QUOTE_NOT_FOUND"


# -----------------------------------------------------------------------
# 8. Collection not found during execution
# -----------------------------------------------------------------------

class TestCollectionNotFoundOnExecute:
    """POST /conversions/execute — missing collection."""

    def test_nonexistent_collection_returns_404(
        self, client: TestClient
    ) -> None:
        """A random collection_id returns 404."""
        import uuid

        quote = _create_quote(client, "GHS", "USD", 1000.00)
        payload = {
            "quote_id": quote["quote_id"],
            "collection_id": str(uuid.uuid4()),
        }
        resp = client.post("/conversions/execute", json=payload)

        assert resp.status_code == 404
        assert resp.json()["code"] == "COLLECTION_NOT_FOUND"
