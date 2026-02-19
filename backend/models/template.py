"""Transform template model."""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from backend.db.base import Base


class TransformTemplate(Base):
    """Reusable transformation template (sequence of transform steps as JSON)."""
    __tablename__ = "transform_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    steps_json = Column(Text, nullable=False)  # JSON array of transform steps
    version = Column(Integer, nullable=False, default=1)
    category = Column(String(100), nullable=True)
    is_public = Column(Boolean, default=False, nullable=False)
    is_sample = Column(Boolean, default=False, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
