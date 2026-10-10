"""Customer and KYC models."""
from __future__ import annotations

from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    father_spouse_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    mobile: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    alt_mobile: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    photo_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # KYC
    kyc_type: Mapped[Optional[str]] = mapped_column(
        Enum(
            "aadhaar", "pan", "voter_id", "passport",
            "driving_licence", "other", name="kyc_type_enum"
        ),
        nullable=True,
    )
    # Stored encrypted — never plain text
    kyc_ref_encrypted: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    kyc_consent_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    kyc_status: Mapped[str] = mapped_column(
        Enum("pending", "verified", "rejected", name="kyc_status_enum"),
        default="pending", nullable=False,
    )
    kyc_verified_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    kyc_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    kyc_rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    # Relationships
    kyc_documents: Mapped[List["KYCDocument"]] = relationship(
        "KYCDocument", back_populates="customer", cascade="all, delete-orphan"
    )
    loans: Mapped[List["Loan"]] = relationship(  # type: ignore[name-defined]
        "Loan", back_populates="customer"
    )

    def __repr__(self) -> str:
        return f"<Customer {self.customer_id} {self.full_name}>"


class KYCDocument(Base, TimestampMixin):
    __tablename__ = "kyc_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=False, index=True
    )
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    doc_ref_encrypted: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, server_default=func.now())
    uploaded_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    customer: Mapped["Customer"] = relationship("Customer", back_populates="kyc_documents")
