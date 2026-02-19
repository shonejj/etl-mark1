"""Connector configuration model."""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from backend.db.base import Base


class ConnectorConfig(Base):
    """Configuration for a data connector (input/output)."""
    __tablename__ = "connector_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # csv, json, postgres, mysql, http, ftp, minio, etc.
    config_encrypted = Column(Text, nullable=False)  # AES-encrypted JSON config
    is_active = Column(Boolean, default=True, nullable=False)
    is_shared = Column(Boolean, default=False, nullable=False)
    last_tested_at = Column(DateTime, nullable=True)
    test_status = Column(String(20), nullable=True)  # success, failed, untested
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
