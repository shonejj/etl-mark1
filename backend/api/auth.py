"""Auth API router — login, register, refresh, logout, me."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas.schemas import (
    LoginRequest, RegisterRequest, RefreshRequest,
    TokenResponse, UserOut, MessageResponse,
)
from backend.services.auth_service import auth_service
from backend.services.audit_service import audit_service
from backend.core.security import get_current_user_id
from backend.core.exceptions import AuthenticationError, ResourceConflictError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticate and return JWT tokens."""
    try:
        result = auth_service.authenticate(db, body.email, body.password)
        audit_service.log_from_request(
            db, request,
            actor_id=result["user"]["id"],
            actor_email=body.email,
            action="user.login",
            resource_type="user",
            resource_id=str(result["user"]["id"]),
        )
        return result
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/register", response_model=UserOut)
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    try:
        user = auth_service.create_user(
            db, body.email, body.password, body.full_name, "member"
        )
        return UserOut(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.name if user.role else "member",
            is_active=user.is_active,
            created_at=user.created_at,
        )
    except ResourceConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    """Refresh access token."""
    try:
        return auth_service.refresh_access_token(db, body.refresh_token)
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout", response_model=MessageResponse)
async def logout(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Revoke all refresh tokens."""
    auth_service.logout(db, user_id)
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserOut)
async def get_me(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get current user profile."""
    user = auth_service.get_user(db, user_id)
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.name if user.role else "member",
        is_active=user.is_active,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
    )
