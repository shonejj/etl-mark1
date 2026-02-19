"""Seed default roles into the database."""

import json
from sqlalchemy.orm import Session
from backend.models.role import Role


def seed_roles(db: Session) -> None:
    """Insert default roles if they don't already exist."""
    roles_data = [
        {
            "name": "super_admin",
            "level": 100,
            "description": "Full system access, manage everything",
            "permissions_json": json.dumps([
                "system.manage", "users.manage", "teams.manage", "audit.view_all",
                "pipelines.manage_all", "connectors.manage_all", "templates.manage_all",
                "schedules.manage_all", "files.manage_all", "settings.manage",
            ]),
        },
        {
            "name": "admin",
            "level": 80,
            "description": "Manage users, teams, and all resources",
            "permissions_json": json.dumps([
                "users.manage", "teams.manage", "audit.view_team",
                "pipelines.manage_all", "connectors.manage_all", "templates.manage_all",
                "schedules.manage_all", "files.manage_all",
            ]),
        },
        {
            "name": "team_lead",
            "level": 60,
            "description": "Manage team pipelines, templates, invite members",
            "permissions_json": json.dumps([
                "teams.invite", "pipelines.manage_team", "connectors.manage_team",
                "templates.manage_team", "schedules.manage_team", "files.manage_team",
            ]),
        },
        {
            "name": "member",
            "level": 40,
            "description": "Create and run pipelines within team",
            "permissions_json": json.dumps([
                "pipelines.create", "pipelines.run", "templates.create",
                "files.upload", "files.transform",
            ]),
        },
        {
            "name": "viewer",
            "level": 20,
            "description": "Read-only access to team resources",
            "permissions_json": json.dumps([
                "pipelines.view", "templates.view", "files.view", "runs.view",
            ]),
        },
    ]

    for role_data in roles_data:
        existing = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing:
            db.add(Role(**role_data))

    db.commit()
    print(f"✅ Seeded {len(roles_data)} roles")
