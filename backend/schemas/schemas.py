"""Pydantic schemas for API request/response serialization."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ---- Auth ----
class LoginRequest(BaseModel):
    email: str = Field(..., min_length=4)
    password: str = Field(..., min_length=4)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: Optional[Dict[str, Any]] = None

class RefreshRequest(BaseModel):
    refresh_token: str

class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=4)
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=1)


# ---- User ----
class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: Optional[str] = None
    is_active: bool = True
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    role_name: Optional[str] = None
    is_active: Optional[bool] = None


# ---- Team ----
class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None

class TeamOut(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TeamMemberAdd(BaseModel):
    user_id: int
    role_in_team: str = "member"


# ---- File ----
class FileOut(BaseModel):
    id: int
    original_name: str
    format: str
    size_bytes: int
    record_count: Optional[int] = None
    version: int = 1
    quality_score: Optional[float] = None
    schema_json: Optional[str] = None
    tags_json: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class FileListResponse(BaseModel):
    files: List[FileOut]
    total: int
    page: int
    page_size: int


# ---- Pipeline ----
class PipelineCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    definition: Dict[str, Any]  # React Flow JSON
    tags: Optional[List[str]] = None

class PipelineUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    definition: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None

class PipelineOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    version: int
    is_active: bool
    tags_json: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- Pipeline Run ----
class RunOut(BaseModel):
    id: int
    pipeline_id: int
    status: str
    triggered_by: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    rows_processed: int = 0
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int = 0

    class Config:
        from_attributes = True

class NodeLogOut(BaseModel):
    id: int
    node_id: str
    node_type: str
    status: str
    rows_in: Optional[int] = None
    rows_out: Optional[int] = None
    duration_ms: Optional[int] = None
    log_text: Optional[str] = None

    class Config:
        from_attributes = True


# ---- Template ----
class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    steps: List[Dict[str, Any]]
    category: Optional[str] = None
    is_public: bool = False

class TemplateOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    steps_json: str
    version: int
    category: Optional[str] = None
    is_public: bool
    is_sample: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- Schedule ----
class ScheduleCreate(BaseModel):
    pipeline_id: int
    cron_expr: str = Field(..., min_length=5)
    timezone: str = "UTC"
    enabled: bool = True
    notify_on_failure: bool = True

class ScheduleOut(BaseModel):
    id: int
    pipeline_id: int
    cron_expr: str
    enabled: bool
    timezone: str
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- Connector ----
class ConnectorCreate(BaseModel):
    name: str
    type: str
    config: Dict[str, Any]
    is_shared: bool = False

class ConnectorOut(BaseModel):
    id: int
    name: str
    type: str
    is_active: bool
    test_status: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- Audit ----
class AuditLogOut(BaseModel):
    id: int
    actor_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- Transform preview ----
class TransformPreview(BaseModel):
    file_id: int
    steps: List[Dict[str, Any]]
    limit: int = 200

class DataPreviewResponse(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
    total_count: int = 0

class QualityScoreResponse(BaseModel):
    score: float
    total_rows: int
    column_count: int
    details: Dict[str, Any]


# ---- Connector test ----
class ConnectorTestRequest(BaseModel):
    type: str
    config: Dict[str, Any]

class ConnectorTestResponse(BaseModel):
    success: bool
    message: str


# ---- Webhook ----
class WebhookCreate(BaseModel):
    name: str
    pipeline_id: int

class WebhookOut(BaseModel):
    id: int
    name: str
    token: Optional[str] = None  # only shown once on creation
    pipeline_id: int
    is_active: bool
    last_triggered_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- Generic ----
class MessageResponse(BaseModel):
    message: str
    detail: Optional[Any] = None

class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[Any] = []
