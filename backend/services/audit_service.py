"""Audit service — append-only audit trail for all mutations."""

import json
from typing import Optional, Any
from sqlalchemy.orm import Session
from fastapi import Request

from backend.models.audit_log import AuditLog


class AuditService:
    """Records immutable audit log entries for system events."""

    @staticmethod
    def log(
        db: Session,
        actor_id: Optional[int],
        actor_email: Optional[str],
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        team_id: Optional[int] = None,
    ) -> AuditLog:
        """Write a single audit log record.

        Args:
            action: e.g. "user.login", "pipeline.created", "file.deleted"
            resource_type: pipeline, file, user, team, connector, template, schedule, system

        This method commits immediately to ensure audit is never lost.
        """
        entry = AuditLog(
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            old_value_json=json.dumps(old_value, default=str) if old_value else None,
            new_value_json=json.dumps(new_value, default=str) if new_value else None,
            ip_address=ip_address,
            user_agent=user_agent,
            team_id=team_id,
        )
        db.add(entry)
        db.commit()
        return entry

    @staticmethod
    def log_from_request(
        db: Session,
        request: Request,
        actor_id: Optional[int],
        actor_email: Optional[str],
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        team_id: Optional[int] = None,
    ) -> AuditLog:
        """Write audit log extracting IP and user-agent from the request."""
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent", "")[:500]
        return AuditService.log(
            db=db,
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip,
            user_agent=ua,
            team_id=team_id,
        )

    @staticmethod
    def query_logs(
        db: Session,
        actor_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        team_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
    ):
        """Query audit logs with filters and pagination."""
        query = db.query(AuditLog)

        if actor_id:
            query = query.filter(AuditLog.actor_id == actor_id)
        if action:
            query = query.filter(AuditLog.action.ilike(f"%{action}%"))
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if team_id:
            query = query.filter(AuditLog.team_id == team_id)

        total = query.count()
        logs = (
            query.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "logs": logs,
            "total": total,
            "page": page,
            "page_size": page_size,
        }


audit_service = AuditService()
