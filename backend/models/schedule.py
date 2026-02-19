"""Schedule and ScheduledLog models."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from backend.db.base import Base


class Schedule(Base):
    """Cron-based schedule for recurring pipeline execution."""
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(Integer, ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False)
    cron_expr = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    last_run_status = Column(String(20), nullable=True)
    failure_count = Column(Integer, default=0)
    notify_on_failure = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    pipeline = relationship("Pipeline", lazy="joined")
    logs = relationship("ScheduledLog", back_populates="schedule", lazy="dynamic")


class ScheduledLog(Base):
    """Log of each scheduled pipeline trigger."""
    __tablename__ = "scheduled_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)
    triggered_at = Column(DateTime, server_default=func.now(), nullable=False)
    status = Column(String(20), default="triggered", nullable=False)

    schedule = relationship("Schedule", back_populates="logs")
