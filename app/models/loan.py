"""Loan and loan lifecycle models."""
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Integer,
    Numeric, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

LOAN_STATUSES = (
    "draft",
    "pending_approval",
    "approved",
    "disbursed",
    "active",
    "partially_repaid",
    "overdue",
    "closed",
    "renewed",
    "auction_review",
)


class Loan(Base, TimestampMixin):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loan_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        Enum(*LOAN_STATUSES, name="loan_status_enum"),
        default="draft", nullable=False, index=True,
    )
    # Amounts
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    approved_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    disbursed_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    outstanding_principal: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    outstanding_interest: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    total_outstanding: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    # Interest
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    interest_method: Mapped[str] = mapped_column(
        Enum("simple", "reducing_balance", name="interest_method_enum"),
        default="simple", nullable=False,
    )
    # Tenure
    tenure_days: Mapped[int] = mapped_column(Integer, nullable=False)
    disbursement_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    maturity_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # LTV & valuation
    ltv_percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    total_collateral_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    # Charges
    processing_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    other_charges: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    # Payment
    payment_mode: Mapped[str] = mapped_column(
        Enum("cash", "bank_transfer", "upi", "cheque", "other", name="payment_mode_enum"),
        default="cash", nullable=False,
    )
    # Approval
    approved_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Renewal
    renewal_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parent_loan_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("loans.id"), nullable=True
    )
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="loans")  # type: ignore
    collateral_items: Mapped[List["CollateralItem"]] = relationship(  # type: ignore
        "CollateralItem", back_populates="loan", cascade="all, delete-orphan"
    )
    repayments: Mapped[List["Repayment"]] = relationship(  # type: ignore
        "Repayment", back_populates="loan", order_by="Repayment.payment_date"
    )
    status_history: Mapped[List["LoanStatusHistory"]] = relationship(
        "LoanStatusHistory", back_populates="loan", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Loan {self.loan_number} {self.status}>"


class LoanStatusHistory(Base):
    __tablename__ = "loan_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("loans.id"), nullable=False, index=True
    )
    from_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    loan: Mapped["Loan"] = relationship("Loan", back_populates="status_history")
