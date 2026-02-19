"""Auth service — JWT login, refresh, user management."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
import hashlib
import secrets

from sqlalchemy.orm import Session

from backend.models.user import User
from backend.models.role import Role
from backend.models.smtp_config import RefreshToken
from backend.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from backend.core.exceptions import AuthenticationError, ResourceNotFoundError


class AuthService:
    """Handles authentication and user management."""

    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user and return JWT tokens.

        Raises:
            AuthenticationError: If credentials are invalid.
        """
        user = db.query(User).filter(User.email == email).first()
        if not user or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        role_name = user.role.name if user.role else "viewer"

        # Create tokens
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": role_name,
            "role_level": user.role.level if user.role else 20,
        }
        access_token = create_access_token(token_data)
        refresh_token_str = create_refresh_token(token_data)

        # Store refresh token hash
        token_hash = hashlib.sha256(refresh_token_str.encode()).hexdigest()
        rt = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.fromtimestamp(decode_token(refresh_token_str)["exp"], tz=timezone.utc),
        )
        db.add(rt)

        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token_str,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": role_name,
                "avatar_url": user.avatar_url,
            },
        }

    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using a valid refresh token."""
        payload = decode_token(refresh_token)
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

        stored = db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        ).first()

        if not stored:
            raise AuthenticationError("Invalid refresh token")

        user = db.query(User).filter(User.id == int(payload["sub"])).first()
        if not user or not user.is_active:
            raise AuthenticationError("User not found or deactivated")

        role_name = user.role.name if user.role else "viewer"
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": role_name,
            "role_level": user.role.level if user.role else 20,
        }
        new_access_token = create_access_token(token_data)

        return {
            "access_token": new_access_token,
            "token_type": "bearer",
        }

    @staticmethod
    def logout(db: Session, user_id: int) -> None:
        """Revoke all refresh tokens for a user."""
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        ).update({"revoked_at": datetime.now(timezone.utc)})
        db.commit()

    @staticmethod
    def create_user(
        db: Session,
        email: str,
        password: str,
        full_name: str,
        role_name: str = "member",
    ) -> User:
        """Create a new user."""
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            from backend.core.exceptions import ResourceConflictError
            raise ResourceConflictError(f"User with email {email} already exists")

        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            raise ResourceNotFoundError(f"Role '{role_name}' not found")

        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role_id=role.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user(db: Session, user_id: int) -> User:
        """Get a user by id."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ResourceNotFoundError(f"User {user_id} not found")
        return user

    @staticmethod
    def list_users(db: Session, page: int = 1, page_size: int = 20):
        """List all users with pagination."""
        total = db.query(User).count()
        users = (
            db.query(User)
            .order_by(User.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return {"users": users, "total": total, "page": page}

    @staticmethod
    def generate_api_key(db: Session, user_id: int, name: str, scopes: list) -> str:
        """Generate a new API key for a user. Returns the raw key (shown once)."""
        import json
        from backend.models.smtp_config import ApiKey

        raw_key = f"etl_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        api_key = ApiKey(
            user_id=user_id,
            key_hash=key_hash,
            name=name,
            scopes_json=json.dumps(scopes),
        )
        db.add(api_key)
        db.commit()
        return raw_key


auth_service = AuthService()
