"""Audit log model — append-only."""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from backend.db.base import Base


class AuditLog(Base):
    """Immutable audit trail for all system mutations.

    This table is APPEND-ONLY: no UPDATE or DELETE operations should ever
    be performed on it (enforced at application level).
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_email = Column(String(255), nullable=True)
    action = Column(String(100), nullable=False, index=True)  # e.g. "pipeline.created"
    resource_type = Column(String(50), nullable=False, index=True)  # pipeline, file, user, etc.
    resource_id = Column(String(100), nullable=True)
    old_value_json = Column(Text, nullable=True)
    new_value_json = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
