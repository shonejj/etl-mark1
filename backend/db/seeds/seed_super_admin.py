"""Seed the super-admin user from env vars."""

from sqlalchemy.orm import Session
from backend.models.user import User
from backend.models.role import Role
from backend.core.security import hash_password
from backend.core.config import settings


def seed_super_admin(db: Session) -> None:
    """Create the super-admin user if not already present."""
    super_admin_role = db.query(Role).filter(Role.name == "super_admin").first()
    if not super_admin_role:
        print("⚠️  super_admin role not found. Run seed_roles first.")
        return

    existing = db.query(User).filter(User.email == settings.SUPER_ADMIN_EMAIL).first()
    if existing:
        print(f"ℹ️  Super admin '{settings.SUPER_ADMIN_EMAIL}' already exists, skipping.")
        return

    admin = User(
        email=settings.SUPER_ADMIN_EMAIL,
        hashed_password=hash_password(settings.SUPER_ADMIN_PASSWORD),
        full_name="Super Admin",
        is_active=True,
        is_verified=True,
        role_id=super_admin_role.id,
    )
    db.add(admin)
    db.commit()
    print(f"✅ Created super admin: {settings.SUPER_ADMIN_EMAIL}")
