"""Global session state — current user, token, timeout tracking."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional


class SessionState:
    def __init__(self):
        self._user_id: Optional[int] = None
        self._username: Optional[str] = None
        self._full_name: Optional[str] = None
        self._role: Optional[str] = None
        self._last_activity: Optional[datetime] = None
        self._timeout_minutes: int = 30

    def login(self, user_id: int, username: str, full_name: str, role: str, timeout_minutes: int = 30):
        self._user_id = user_id
        self._username = username
        self._full_name = full_name
        self._role = role
        self._timeout_minutes = timeout_minutes
        self._last_activity = datetime.now()

    def logout(self):
        self._user_id = None
        self._username = None
        self._full_name = None
        self._role = None
        self._last_activity = None

    def touch(self):
        if self._user_id:
            self._last_activity = datetime.now()

    def is_logged_in(self) -> bool:
        return self._user_id is not None

    def is_timed_out(self) -> bool:
        if not self._last_activity:
            return False
        return datetime.now() - self._last_activity > timedelta(minutes=self._timeout_minutes)

    @property
    def user_id(self) -> Optional[int]:
        return self._user_id

    @property
    def username(self) -> Optional[str]:
        return self._username

    @property
    def full_name(self) -> Optional[str]:
        return self._full_name

    @property
    def role(self) -> Optional[str]:
        return self._role

    @property
    def is_admin(self) -> bool:
        return self._role == "admin"

    def can(self, permission: str) -> bool:
        perms = {
            "admin": {
                "manage_users", "approve_loans", "reset_password",
                "view_audit_logs", "manage_settings", "backup_restore",
                "create_loans", "collect_payments", "view_reports",
                "release_collateral",
            },
            "lender": {
                "create_loans", "collect_payments", "view_reports",
            },
            "viewer": {
                "view_reports",
            },
        }
        role_perms = perms.get(self._role or "viewer", set())
        return permission in role_perms


# Global singleton
session = SessionState()
