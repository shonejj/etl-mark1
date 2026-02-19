"""Admin / Audit API router."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas.schemas import AuditLogOut, UserOut, UserUpdateRequest, MessageResponse
from backend.services.audit_service import audit_service
from backend.services.auth_service import auth_service
from backend.models.user import User
from backend.models.role import Role
from backend.core.security import require_admin, require_super_admin, get_current_user_id

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
async def admin_list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    payload: dict = Depends(require_admin),
):
    """List all users (admin only)."""
    result = auth_service.list_users(db, page, page_size)
    return {
        "users": [
            UserOut(
                id=u.id, email=u.email, full_name=u.full_name,
                role=u.role.name if u.role else None,
                is_active=u.is_active, created_at=u.created_at,
            )
            for u in result["users"]
        ],
        "total": result["total"],
        "page": result["page"],
    }


@router.put("/users/{user_id}", response_model=MessageResponse)
async def admin_update_user(
    user_id: int,
    body: UserUpdateRequest,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_admin),
):
    """Update a user's role, name, or status (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")

    if body.full_name:
        user.full_name = body.full_name
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.role_name:
        role = db.query(Role).filter(Role.name == body.role_name).first()
        if role:
            user.role_id = role.id
    db.commit()
    return MessageResponse(message="User updated")


@router.get("/audit")
async def get_audit_logs(
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    actor_id: Optional[int] = Query(None),
    team_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    payload: dict = Depends(require_admin),
):
    """Query audit logs (admin only)."""
    result = audit_service.query_logs(
        db, actor_id, action, resource_type, team_id, page, page_size,
    )
    return {
        "logs": [
            AuditLogOut.model_validate(log)
            for log in result["logs"]
        ],
        "total": result["total"],
        "page": result["page"],
    }


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """System health check — DB and Redis."""
    from backend.services.cache_service import cache_service

    db_ok = False
    redis_ok = False
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    redis_ok = cache_service.health_check()

    return {
        "mysql": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
        "status": "healthy" if db_ok else "degraded",
    }


@router.get("/stats")
async def system_stats(
    db: Session = Depends(get_db),
    payload: dict = Depends(require_admin),
):
    """Get system-level statistics."""
    from backend.models.pipeline import Pipeline, PipelineRun
    from backend.models.file_meta import FileMeta
    from backend.models.template import TransformTemplate
    from backend.models.audit_log import AuditLog

    return {
        "total_users": db.query(User).count(),
        "total_pipelines": db.query(Pipeline).filter(Pipeline.is_active == True).count(),
        "total_runs": db.query(PipelineRun).count(),
        "total_files": db.query(FileMeta).filter(FileMeta.deleted_at.is_(None)).count(),
        "total_templates": db.query(TransformTemplate).count(),
        "total_audit_events": db.query(AuditLog).count(),
    }
