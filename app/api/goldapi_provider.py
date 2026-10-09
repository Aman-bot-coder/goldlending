"""
GoldAPI.io provider — https://www.goldapi.io
Free plan provides XAU (gold) and XAG (silver) in USD.
We convert to INR using the USD/INR rate from a secondary endpoint or a stored rate.
Requires a free/paid API key from goldapi.io.
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

import requests

from app.api.base_provider import BaseRateProvider, MetalRate

logger = logging.getLogger(__name__)

BASE_URL = "https://www.goldapi.io/api"
TROY_OZ_TO_GRAM = Decimal("31.1035")


class GoldAPIProvider(BaseRateProvider):
    name = "goldapi"

    def _get_usdinr(self) -> Decimal:
        """Fetch live USD/INR rate. Falls back to 83.0 if unavailable."""
        try:
            resp = requests.get(
                "https://api.exchangerate-api.com/v4/latest/USD",
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return Decimal(str(data["rates"].get("INR", 83.0)))
        except Exception:
            return Decimal("83.0")

    def _fetch(self, symbol: str) -> Optional[dict]:
        if not self.api_key:
            return None
        try:
            resp = requests.get(
                f"{BASE_URL}/{symbol}/INR",
                headers={"x-access-token": self.api_key, "Content-Type": "application/json"},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as exc:
            logger.error("GoldAPI HTTP error for %s: %s", symbol, exc)
        except Exception as exc:
            logger.error("GoldAPI fetch error for %s: %s", symbol, exc)
        return None

    def fetch_gold_rate(self) -> Optional[MetalRate]:
        data = self._fetch("XAU")
        if not data:
            return None
        try:
            price_per_troy_oz = Decimal(str(data["price"]))
            rate_per_gram = (price_per_troy_oz / TROY_OZ_TO_GRAM).quantize(Decimal("0.01"))
            return MetalRate(
                metal_type="gold",
                rate_per_gram=rate_per_gram,
                rate_per_10gram=rate_per_gram * Decimal("10"),
                currency="INR",
                source=self.name,
                purity_basis="24K",
                fetched_at=datetime.now(),
            )
        except Exception as exc:
            logger.error("GoldAPI gold parse error: %s", exc)
            return None

    def fetch_silver_rate(self) -> Optional[MetalRate]:
        data = self._fetch("XAG")
        if not data:
            return None
        try:
            price_per_troy_oz = Decimal(str(data["price"]))
            rate_per_gram = (price_per_troy_oz / TROY_OZ_TO_GRAM).quantize(Decimal("0.01"))
            return MetalRate(
                metal_type="silver",
                rate_per_gram=rate_per_gram,
                rate_per_10gram=rate_per_gram * Decimal("10"),
                currency="INR",
                source=self.name,
                purity_basis="999",
                fetched_at=datetime.now(),
            )
        except Exception as exc:
            logger.error("GoldAPI silver parse error: %s", exc)
            return None
