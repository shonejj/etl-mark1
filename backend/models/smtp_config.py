"""SMTP, API key, webhook trigger, feature flag, and system settings models."""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, func
from backend.db.base import Base


class SmtpConfig(Base):
    """SMTP email configuration."""
    __tablename__ = "smtp_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False, default=587)
    username = Column(String(255), nullable=True)
    password_encrypted = Column(String(500), nullable=True)
    use_tls = Column(Boolean, default=True, nullable=False)
    from_email = Column(String(255), nullable=False)
    from_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    test_status = Column(String(20), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class ApiKey(Base):
    """API key for machine-to-machine access."""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key_hash = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    scopes_json = Column(Text, nullable=True)  # JSON list of scopes
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class RefreshToken(Base):
    """Stored refresh token for JWT auth flow."""
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class WebhookTrigger(Base):
    """Incoming webhook trigger linked to a pipeline."""
    __tablename__ = "webhook_triggers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    pipeline_id = Column(Integer, ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    payload_schema_json = Column(Text, nullable=True)
    last_triggered_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class FeatureFlag(Base):
    """Feature flag for gating incomplete features."""
    __tablename__ = "feature_flags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    is_enabled = Column(Boolean, default=False, nullable=False)
    rollout_pct = Column(Integer, default=0)  # 0-100
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class SystemSetting(Base):
    """Key-value system settings."""
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    description = Column(String(500), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
