"""Seed sample data for demo purposes."""

import json
from sqlalchemy.orm import Session
from backend.models.template import TransformTemplate
from backend.models.smtp_config import FeatureFlag, SystemSetting
from backend.models.user import User


def seed_sample_data(db: Session) -> None:
    """Insert sample templates, feature flags, and system settings."""

    # Get the first user (super admin) as owner
    owner = db.query(User).first()
    if not owner:
        print("⚠️  No users found. Run seed_super_admin first.")
        return

    # --- Feature Flags ---
    default_flags = [
        ("pdf_extract", True),
        ("ai_assistant", False),
        ("kafka", False),
        ("magento", False),
        ("shopify", False),
        ("salesforce", False),
        ("hubspot", False),
    ]
    for name, enabled in default_flags:
        existing = db.query(FeatureFlag).filter(FeatureFlag.name == name).first()
        if not existing:
            db.add(FeatureFlag(name=name, is_enabled=enabled, rollout_pct=100 if enabled else 0))

    # --- System Settings ---
    default_settings = [
        ("max_upload_size_mb", "100", "Maximum file upload size in MB"),
        ("concurrency", "4", "Number of concurrent pipeline executions"),
        ("default_timezone", "UTC", "Default timezone for schedules"),
        ("retention_days", "90", "Audit log retention in days"),
    ]
    for key, value, desc in default_settings:
        existing = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if not existing:
            db.add(SystemSetting(key=key, value=value, description=desc))

    # --- Sample Templates ---
    sample_templates = [
        {
            "name": "Rename and Trim Whitespace",
            "description": "Rename columns to lowercase and trim whitespace from all text columns",
            "steps_json": json.dumps([
                {"operator": "rename_column", "params": {"from_name": "Product Name", "to_name": "product_name"}},
                {"operator": "trim_whitespace", "params": {"columns": ["*"]}},
            ]),
            "category": "Data Cleaning",
            "is_public": True,
            "is_sample": True,
            "owner_id": owner.id,
        },
        {
            "name": "Type Cast and Deduplicate",
            "description": "Cast price columns to decimal and remove duplicate rows",
            "steps_json": json.dumps([
                {"operator": "cast_type", "params": {"column": "price", "target_type": "DOUBLE"}},
                {"operator": "cast_type", "params": {"column": "cost", "target_type": "DOUBLE"}},
                {"operator": "deduplicate_rows", "params": {"columns": ["sku", "name"]}},
            ]),
            "category": "Data Cleaning",
            "is_public": True,
            "is_sample": True,
            "owner_id": owner.id,
        },
    ]

    for tmpl_data in sample_templates:
        existing = db.query(TransformTemplate).filter(
            TransformTemplate.name == tmpl_data["name"],
            TransformTemplate.is_sample == True,
        ).first()
        if not existing:
            db.add(TransformTemplate(**tmpl_data))

    db.commit()
    print("✅ Seeded feature flags, system settings, and sample templates")
