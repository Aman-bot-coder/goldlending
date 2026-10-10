"""
Authentication and user management service.
Handles login, session management, password operations, and user CRUD.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.database.connection import get_session
from app.services.audit_service import audit
from app.models.user import User, LoginHistory
from app.utils.security import (
    hash_password, verify_password, needs_rehash,
    generate_temp_password, generate_session_token,
)

logger = logging.getLogger(__name__)

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 30
SESSION_TIMEOUT_MINUTES = 30


class AuthService:
    """Stateless service — pass session where needed, or uses context manager."""

    # ------------------------------------------------------------------ login

    def login(self, username: str, password: str, ip_address: str = "") -> Tuple[bool, str, Optional[User]]:
        """
        Returns (success, message, user_object).
        Logs the attempt to login_history.
        """
        with get_session() as session:
            user = (
                session.query(User)
                .filter(
                    (User.username == username.strip()) | (User.email == username.strip())
                )
                .first()
            )

            failure_reason: Optional[str] = None

            if user is None:
                failure_reason = "User not found"
                self._log_attempt(session, None, username, ip_address, False, failure_reason)
                return False, "Invalid credentials", None

            if not user.is_active:
                failure_reason = "Account disabled"
                self._log_attempt(session, user.id, username, ip_address, False, failure_reason)
                return False, "Account is disabled. Contact administrator.", None

            if user.is_locked:
                mins_left = int((user.locked_until - datetime.now()).total_seconds() / 60)
                failure_reason = "Account locked"
                self._log_attempt(session, user.id, username, ip_address, False, failure_reason)
                return False, f"Account locked for {mins_left} more minute(s). Try later.", None

            if not verify_password(password, user.password_hash):
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                    user.locked_until = datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)
                    logger.warning("User %s locked after %d failed attempts", username, MAX_FAILED_ATTEMPTS)
                    failure_reason = "Too many failed attempts - account locked"
                    self._log_attempt(session, user.id, username, ip_address, False, failure_reason)
                    return False, f"Too many failed attempts. Account locked for {LOCKOUT_MINUTES} minutes.", None
                failure_reason = "Wrong password"
                self._log_attempt(session, user.id, username, ip_address, False, failure_reason)
                remaining = MAX_FAILED_ATTEMPTS - user.failed_login_attempts
                return False, f"Invalid credentials. {remaining} attempt(s) remaining.", None

            # Success
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login = datetime.now()

            if needs_rehash(user.password_hash):
                user.password_hash = hash_password(password)

            self._log_attempt(session, user.id, username, ip_address, True, None)
            session.flush()

            # Detach so we can return without keeping session open
            session.expunge(user)
            from sqlalchemy.orm import make_transient
            make_transient(user)

        audit("LOGIN", "user", user.id, user.username, username=user.username, user_id=user.id)
        return True, "Login successful", user

    def _log_attempt(
        self, session: Session, user_id: Optional[int], username: str,
        ip: str, success: bool, reason: Optional[str]
    ) -> None:
        log = LoginHistory(
            user_id=user_id,
            username=username,
            ip_address=ip,
            success=success,
            failure_reason=reason,
        )
        session.add(log)

    # ---------------------------------------------------------------- password

    def change_password(self, user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
        from app.utils.validators import validate_password
        err = validate_password(new_password)
        if err:
            return False, err

        with get_session() as session:
            user = session.get(User, user_id)
            if not user:
                return False, "User not found"
            if not verify_password(old_password, user.password_hash):
                return False, "Current password is incorrect"
            user.password_hash = hash_password(new_password)
            user.must_change_password = False
        audit("PASSWORD_CHANGED", "user", user_id, user_id=user_id)
        return True, "Password changed successfully"

    def admin_reset_password(self, admin_id: int, target_user_id: int) -> Tuple[bool, str, str]:
        with get_session() as session:
            admin = session.get(User, admin_id)
            if not admin or not admin.is_admin:
                return False, "Unauthorized", ""
            target = session.get(User, target_user_id)
            if not target:
                return False, "User not found", ""
            temp_pw = generate_temp_password()
            target.password_hash = hash_password(temp_pw)
            target.must_change_password = True
        audit("PASSWORD_RESET", "user", target_user_id, user_id=admin_id)
        return True, "Password reset. User must change on next login.", temp_pw

    # ------------------------------------------------------------------ users

    def create_user(
        self, admin_id: int, username: str, email: str, full_name: str,
        role: str, phone: str = ""
    ) -> Tuple[bool, str, Optional[User]]:
        from app.utils.validators import validate_username, validate_email
        err = validate_username(username)
        if err:
            return False, err, None
        err = validate_email(email)
        if err:
            return False, err, None

        with get_session() as session:
            admin = session.get(User, admin_id)
            if not admin or not admin.is_admin:
                return False, "Unauthorized", None

            existing = (
                session.query(User)
                .filter((User.username == username) | (User.email == email))
                .first()
            )
            if existing:
                return False, "Username or email already exists", None

            temp_pw = generate_temp_password()
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                password_hash=hash_password(temp_pw),
                role=role,
                phone=phone,
                must_change_password=True,
                created_by=admin_id,
            )
            session.add(user)
            session.flush()
            session.expunge(user)
            from sqlalchemy.orm import make_transient
            make_transient(user)

        audit("USER_CREATED", "user", user.id, user.username, new_value={"role": role}, user_id=admin_id)
        return True, f"User created. Temporary password: {temp_pw}", user

    def update_user(self, admin_id: int, user_id: int, **kwargs) -> Tuple[bool, str]:
        with get_session() as session:
            admin = session.get(User, admin_id)
            if not admin or not admin.is_admin:
                return False, "Unauthorized"
            user = session.get(User, user_id)
            if not user:
                return False, "User not found"
            allowed = {"full_name", "email", "phone", "role", "is_active"}
            for key, val in kwargs.items():
                if key in allowed:
                    setattr(user, key, val)
        audit("USER_UPDATED", "user", user_id, new_value=kwargs, user_id=admin_id)
        return True, "User updated"

    def list_users(self) -> list[dict]:
        with get_session() as session:
            users = session.query(User).order_by(User.username).all()
            return [
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "full_name": u.full_name,
                    "role": u.role,
                    "is_active": u.is_active,
                    "last_login": u.last_login,
                    "created_at": u.created_at,
                }
                for u in users
            ]

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        with get_session() as session:
            u = session.get(User, user_id)
            if not u:
                return None
            return {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "phone": u.phone,
                "last_login": u.last_login,
                "must_change_password": u.must_change_password,
            }


# Module-level singleton
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
