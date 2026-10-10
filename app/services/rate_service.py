"""
Live metal rate service.
Fetches, caches, and persists gold/silver rates.
Falls back gracefully when API is unavailable — shows last known rate as stale.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Tuple

from app.api.base_provider import MetalRate
from app.database.connection import get_session
from app.models.metal_rate import MetalRateHistory

logger = logging.getLogger(__name__)

STALE_THRESHOLD_MINUTES = 60
MANUAL_STALE_THRESHOLD_HOURS = 24


def _get_provider():
    from app.config import get_config
    from app.api.goldapi_provider import GoldAPIProvider
    cfg = get_config()
    provider_name = cfg.rate_api_provider
    api_key = cfg.rate_api_key

    if provider_name == "goldapi":
        return GoldAPIProvider(api_key=api_key)
    # Add more providers here as needed
    return GoldAPIProvider(api_key=api_key)


class RateService:

    def save_manual_rate(self, metal_type: str, rate_per_gram: Decimal) -> None:
        """Record a rate typed in by the lender (works without internet)."""
        if metal_type not in ("gold", "silver"):
            raise ValueError("metal_type must be 'gold' or 'silver'")
        rate = Decimal(str(rate_per_gram)).quantize(Decimal("0.01"))
        if rate <= 0:
            raise ValueError("Rate must be greater than zero")
        with get_session() as session:
            session.add(MetalRateHistory(
                metal_type=metal_type,
                rate_per_gram=rate,
                rate_per_10gram=rate * Decimal("10"),
                currency="INR",
                source="manual",
                purity_basis="24K" if metal_type == "gold" else "999",
                fetched_at=datetime.now(),
                is_stale=False,
            ))

    def fetch_and_save(self) -> Tuple[Optional[MetalRate], Optional[MetalRate], str]:
        """Returns (gold_rate, silver_rate, message)."""
        from app.config import get_config
        if not get_config().rate_api_key:
            return None, None, "No API key set — enter today's rates manually."
        provider = _get_provider()
        try:
            rates = provider.fetch_all()
        except Exception as exc:
            logger.error("Rate fetch error: %s", exc)
            return None, None, f"Fetch failed: {exc}"

        gold = rates.get("gold")
        silver = rates.get("silver")
        message = ""

        with get_session() as session:
            for rate in [gold, silver]:
                if rate:
                    row = MetalRateHistory(
                        metal_type=rate.metal_type,
                        rate_per_gram=rate.rate_per_gram,
                        rate_per_10gram=rate.rate_per_10gram,
                        currency=rate.currency,
                        source=rate.source,
                        purity_basis=rate.purity_basis,
                        fetched_at=rate.fetched_at,
                        is_stale=False,
                    )
                    session.add(row)
            if gold:
                message += f"Gold: ₹{gold.rate_per_gram}/g  "
            if silver:
                message += f"Silver: ₹{silver.rate_per_gram}/g"
            if not gold and not silver:
                message = "Could not fetch live rates (offline?) — enter rates manually."

        return gold, silver, message.strip()

    def get_latest_rate(self, metal_type: str) -> Optional[dict]:
        """Returns latest rate dict, marking as stale if over threshold."""
        with get_session() as session:
            row = (
                session.query(MetalRateHistory)
                .filter(MetalRateHistory.metal_type == metal_type)
                .order_by(MetalRateHistory.fetched_at.desc())
                .first()
            )
            if not row:
                return None
            limit = (
                timedelta(hours=MANUAL_STALE_THRESHOLD_HOURS)
                if row.source == "manual"
                else timedelta(minutes=STALE_THRESHOLD_MINUTES)
            )
            is_stale = (datetime.now() - row.fetched_at) > limit
            return {
                "metal_type": row.metal_type,
                "rate_per_gram": row.rate_per_gram,
                "rate_per_10gram": row.rate_per_10gram,
                "currency": row.currency,
                "source": row.source,
                "purity_basis": row.purity_basis,
                "fetched_at": row.fetched_at,
                "is_stale": is_stale or row.is_stale,
            }

    def get_both_latest(self) -> Tuple[Optional[dict], Optional[dict]]:
        return self.get_latest_rate("gold"), self.get_latest_rate("silver")

    def get_rate_history(self, metal_type: str, limit: int = 100) -> list[dict]:
        with get_session() as session:
            rows = (
                session.query(MetalRateHistory)
                .filter(MetalRateHistory.metal_type == metal_type)
                .order_by(MetalRateHistory.fetched_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "fetched_at": r.fetched_at,
                    "rate_per_gram": r.rate_per_gram,
                    "rate_per_10gram": r.rate_per_10gram,
                    "source": r.source,
                    "is_stale": r.is_stale,
                }
                for r in rows
            ]


_rate_service: Optional[RateService] = None


def get_rate_service() -> RateService:
    global _rate_service
    if _rate_service is None:
        _rate_service = RateService()
    return _rate_service
