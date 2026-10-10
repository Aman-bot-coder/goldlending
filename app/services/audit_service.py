"""Audit logging service."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional, List

from app.database.connection import get_session
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


class AuditService:

    def log(
        self,
        action: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        entity_ref: Optional[str] = None,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
        ip_address: Optional[str] = None,
        extra: Optional[str] = None,
    ) -> None:
        try:
            # Own session so an audit write never commits/closes a caller's transaction.
            from sqlalchemy.orm import Session
            from app.database.connection import get_engine
            with Session(get_engine()) as session, session.begin():
                log = AuditLog(
                    user_id=user_id,
                    username=username,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_ref=entity_ref,
                    old_value=json.dumps(old_value, default=str) if old_value else None,
                    new_value=json.dumps(new_value, default=str) if new_value else None,
                    ip_address=ip_address,
                    extra=extra,
                )
                session.add(log)
        except Exception as exc:
            logger.error("Audit log failed: %s", exc)

    def get_logs(
        self,
        action_filter: str = "",
        entity_type: str = "",
        username: str = "",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[dict]:
        with get_session() as session:
            q = session.query(AuditLog)
            if action_filter:
                q = q.filter(AuditLog.action.ilike(f"%{action_filter}%"))
            if entity_type:
                q = q.filter(AuditLog.entity_type == entity_type)
            if username:
                q = q.filter(AuditLog.username.ilike(f"%{username}%"))
            if from_date:
                q = q.filter(AuditLog.created_at >= from_date)
            if to_date:
                q = q.filter(AuditLog.created_at <= to_date)
            rows = q.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset).all()
            return [
                {
                    "id": r.id,
                    "username": r.username,
                    "action": r.action,
                    "entity_type": r.entity_type,
                    "entity_id": r.entity_id,
                    "entity_ref": r.entity_ref,
                    "old_value": r.old_value,
                    "new_value": r.new_value,
                    "ip_address": r.ip_address,
                    "created_at": r.created_at,
                }
                for r in rows
            ]


_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service


def audit(
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    entity_ref: Optional[str] = None,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    extra: Optional[str] = None,
    username: Optional[str] = None,
    user_id: Optional[int] = None,
) -> None:
    """Record an action by the currently signed-in user. Never raises."""
    from app.ui.session_state import session as app_session
    get_audit_service().log(
        action,
        user_id=user_id if user_id is not None else app_session.user_id,
        username=username or app_session.username,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_ref=entity_ref,
        old_value=old_value,
        new_value=new_value,
        extra=extra,
    )
