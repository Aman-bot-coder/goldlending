"""User and authentication models."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Integer, String, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("admin", "lender", "viewer", name="user_role"),
        nullable=False, default="lender"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    # Relationships
    login_history: Mapped[List["LoginHistory"]] = relationship(
        "LoginHistory", back_populates="user", foreign_keys="LoginHistory.user_id"
    )

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_locked(self) -> bool:
        if self.locked_until and self.locked_until > datetime.now():
            return True
        return False


class LoginHistory(Base):
    __tablename__ = "login_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    login_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    logout_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="login_history", foreign_keys=[user_id]
    )
