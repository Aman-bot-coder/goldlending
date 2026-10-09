"""Collateral item model."""
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class CollateralItem(Base, TimestampMixin):
    __tablename__ = "collateral_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("loans.id"), nullable=False, index=True
    )
    metal_type: Mapped[str] = mapped_column(
        Enum("gold", "silver", name="metal_type_enum"), nullable=False
    )
    item_category: Mapped[str] = mapped_column(
        Enum(
            "ring", "chain", "necklace", "bracelet",
            "coin", "bar", "utensils", "other",
            name="item_category_enum",
        ),
        nullable=False, default="other",
    )
    gross_weight: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    stone_weight: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=Decimal("0"), nullable=False)
    net_weight: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    purity: Mapped[str] = mapped_column(String(10), nullable=False)   # e.g. "22K", "999"
    purity_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)
    assayed_purity: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Rates used at valuation time
    market_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    valuation_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    valuation_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Calculated fields
    pure_metal_weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    indicative_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    # Description
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photo_paths: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    tag_number: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True, index=True)
    storage_location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    appraiser_remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Release
    is_released: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    release_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    release_authorized_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    loan: Mapped["Loan"] = relationship("Loan", back_populates="collateral_items")  # type: ignore

    def __repr__(self) -> str:
        return f"<CollateralItem {self.tag_number or self.id} {self.metal_type} {self.gross_weight}g>"
