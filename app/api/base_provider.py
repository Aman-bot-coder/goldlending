"""Base class for metal rate API providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class MetalRate:
    metal_type: str          # "gold" | "silver"
    rate_per_gram: Decimal
    rate_per_10gram: Decimal
    currency: str
    source: str
    purity_basis: str        # e.g. "24K" or "999"
    fetched_at: datetime
    is_stale: bool = False

    def __post_init__(self):
        if self.rate_per_10gram == Decimal("0"):
            self.rate_per_10gram = self.rate_per_gram * Decimal("10")


class BaseRateProvider(ABC):

    name: str = "base"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    @abstractmethod
    def fetch_gold_rate(self) -> Optional[MetalRate]:
        ...

    @abstractmethod
    def fetch_silver_rate(self) -> Optional[MetalRate]:
        ...

    def fetch_all(self) -> dict[str, Optional[MetalRate]]:
        return {
            "gold": self.fetch_gold_rate(),
            "silver": self.fetch_silver_rate(),
        }
