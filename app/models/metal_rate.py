"""Metal rate history model."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class MetalRateHistory(Base):
    __tablename__ = "metal_rate_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metal_type: Mapped[str] = mapped_column(
        Enum("gold", "silver", name="mrh_metal_type"), nullable=False, index=True
    )
    rate_per_gram: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    rate_per_10gram: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    purity_basis: Mapped[str] = mapped_column(String(20), default="24K/999", nullable=False)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<MetalRate {self.metal_type} ₹{self.rate_per_gram}/g @ {self.fetched_at}>"
