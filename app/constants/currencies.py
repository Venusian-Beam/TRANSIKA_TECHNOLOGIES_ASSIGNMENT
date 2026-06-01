"""
Currency constants and FX rate definitions.

All supported currencies and FX corridors are defined here as the single
source of truth. Rates are hardcoded mid-market approximations — in a
production system these would be sourced from a live feed.

Security note: Centralising currency validation here prevents untrusted
input from propagating into downstream calculations. Any new corridor
must be explicitly registered.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class Currency(StrEnum):
    """ISO 4217 currency codes supported by the platform."""

    GHS = "GHS"
    NGN = "NGN"
    KES = "KES"
    ZAR = "ZAR"
    USD = "USD"


# ---------------------------------------------------------------------------
# FX corridors: (source_currency, target_currency) → mid-market rate
#
# The rate represents how many units of target currency you receive for
# one unit of source currency.  At least four corridors are required by
# the specification.
# ---------------------------------------------------------------------------
FX_RATES: Final[dict[tuple[str, str], float]] = {
    # African → USD conversions
    ("GHS", "USD"): 0.067,   # 1 GHS ≈ 0.067 USD
    ("NGN", "USD"): 0.00063, # 1 NGN ≈ 0.00063 USD
    ("KES", "USD"): 0.0065,  # 1 KES ≈ 0.0065 USD
    ("ZAR", "USD"): 0.053,   # 1 ZAR ≈ 0.053 USD
    # USD → African conversions (inverse)
    ("USD", "GHS"): 14.93,
    ("USD", "NGN"): 1587.30,
    ("USD", "KES"): 153.85,
    ("USD", "ZAR"): 18.87,
    # Cross-currency African corridors
    ("GHS", "NGN"): 106.27,
    ("NGN", "GHS"): 0.0094,
    ("KES", "ZAR"): 8.15,
    ("ZAR", "KES"): 0.1227,
}

# ---------------------------------------------------------------------------
# Fee schedule
# ---------------------------------------------------------------------------
FEE_PERCENTAGE: Final[float] = 0.012     # 1.2 %
FEE_MINIMUM_USD: Final[float] = 0.50     # USD 0.50 floor

# ---------------------------------------------------------------------------
# Timing thresholds (seconds) for collection status transitions
# ---------------------------------------------------------------------------
COLLECTION_PROCESSING_DELAY: Final[int] = 10
COLLECTION_COMPLETED_DELAY: Final[int] = 20

# ---------------------------------------------------------------------------
# Quote expiry window
# ---------------------------------------------------------------------------
QUOTE_EXPIRY_SECONDS: Final[int] = 60
