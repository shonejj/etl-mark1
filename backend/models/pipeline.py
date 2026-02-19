"""Pipeline model and related run/log models."""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, BigInteger,
    ForeignKey, Enum, func
)
from sqlalchemy.orm import relationship
from backend.db.base import Base
import enum


class PipelineRunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"


class TriggeredBy(str, enum.Enum):
    manual = "manual"
    schedule = "schedule"
    event = "event"
    webhook = "webhook"


class Pipeline(Base):
    """Visual pipeline definition (JSON-serialized DAG)."""
    __tablename__ = "pipelines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    definition_json = Column(Text, nullable=False)  # Full pipeline DAG definition
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, default=True, nullable=False)
    tags_json = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    runs = relationship("PipelineRun", back_populates="pipeline", lazy="dynamic")
    owner = relationship("User", lazy="joined")


class PipelineRun(Base):
    """Record of a single pipeline execution."""
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(Integer, ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(PipelineRunStatus), default=PipelineRunStatus.pending, nullable=False)
    triggered_by = Column(Enum(TriggeredBy), default=TriggeredBy.manual, nullable=False)
    trigger_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    trigger_webhook_id = Column(Integer, nullable=True)
    celery_task_id = Column(String(255), nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    rows_processed = Column(BigInteger, default=0)
    duration_ms = Column(BigInteger, nullable=True)
    retry_count = Column(Integer, default=0)

    pipeline = relationship("Pipeline", back_populates="runs")
    node_logs = relationship("NodeRunLog", back_populates="run", lazy="selectin")


class NodeRunLog(Base):
    """Per-node execution log within a pipeline run."""
    __tablename__ = "node_run_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String(100), nullable=False)  # Visual node ID from React Flow
    node_type = Column(String(50), nullable=False)
    attempt_no = Column(Integer, default=1, nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending/running/success/failed
    log_text = Column(Text, nullable=True)
    rows_in = Column(BigInteger, nullable=True)
    rows_out = Column(BigInteger, nullable=True)
    duration_ms = Column(BigInteger, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    metadata_json = Column(Text, nullable=True)

    run = relationship("PipelineRun", back_populates="node_logs")
