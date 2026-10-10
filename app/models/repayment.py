"""Repayment and interest accrual models."""
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Repayment(Base, TimestampMixin):
    __tablename__ = "repayments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("loans.id"), nullable=False, index=True
    )
    receipt_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    principal_paid: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"), nullable=False)
    interest_paid: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"), nullable=False)
    fee_paid: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"), nullable=False)
    penalty_paid: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"), nullable=False)
    total_paid: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    payment_mode: Mapped[str] = mapped_column(
        Enum("cash", "bank_transfer", "upi", "cheque", "other", name="rep_payment_mode"),
        default="cash", nullable=False,
    )
    transaction_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    balance_principal_after: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    balance_interest_after: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    total_outstanding_after: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    # Reversal support (never delete financial records)
    is_reversed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reversal_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reversed_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    reversed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    loan: Mapped["Loan"] = relationship("Loan", back_populates="repayments")  # type: ignore

    def __repr__(self) -> str:
        return f"<Repayment {self.receipt_number} ₹{self.total_paid}>"


class InterestAccrual(Base):
    __tablename__ = "interest_accruals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("loans.id"), nullable=False, index=True
    )
    accrual_date: Mapped[date] = mapped_column(Date, nullable=False)
    days_accrued: Mapped[int] = mapped_column(Integer, nullable=False)
    principal_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    interest_accrued: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    cumulative_interest: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, server_default=func.now(), nullable=False
    )
