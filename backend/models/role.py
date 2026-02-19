"""Role model for RBAC."""

from sqlalchemy import Column, Integer, String, Text, DateTime, func
from backend.db.base import Base


class Role(Base):
    """System role with hierarchical level and JSON permissions."""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    level = Column(Integer, nullable=False, default=20)
    permissions_json = Column(Text, nullable=True)  # JSON list of permission strings
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
