"""Template service — save, apply, version transform templates."""

import json
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from backend.models.template import TransformTemplate
from backend.core.exceptions import ResourceNotFoundError


class TemplateService:
    """Manages reusable transformation templates."""

    @staticmethod
    def create(
        db: Session,
        name: str,
        steps: List[Dict[str, Any]],
        owner_id: int,
        description: Optional[str] = None,
        category: Optional[str] = None,
        team_id: Optional[int] = None,
        is_public: bool = False,
    ) -> TransformTemplate:
        """Create a new transform template."""
        template = TransformTemplate(
            name=name,
            description=description,
            steps_json=json.dumps(steps),
            category=category,
            is_public=is_public,
            owner_id=owner_id,
            team_id=team_id,
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def get(db: Session, template_id: int) -> TransformTemplate:
        """Get a template by id."""
        template = db.query(TransformTemplate).filter(TransformTemplate.id == template_id).first()
        if not template:
            raise ResourceNotFoundError(f"Template {template_id} not found")
        return template

    @staticmethod
    def list_templates(
        db: Session,
        owner_id: Optional[int] = None,
        team_id: Optional[int] = None,
        search: Optional[str] = None,
        include_public: bool = True,
        include_samples: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """List templates with filters and pagination."""
        query = db.query(TransformTemplate)

        if owner_id and not include_public:
            query = query.filter(TransformTemplate.owner_id == owner_id)
        elif owner_id:
            query = query.filter(
                (TransformTemplate.owner_id == owner_id) |
                (TransformTemplate.is_public == True) |
                (TransformTemplate.is_sample == True)
            )

        if team_id:
            query = query.filter(
                (TransformTemplate.team_id == team_id) |
                (TransformTemplate.is_public == True)
            )

        if search:
            query = query.filter(TransformTemplate.name.ilike(f"%{search}%"))

        total = query.count()
        templates = (
            query.order_by(TransformTemplate.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "templates": templates,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    def update(
        db: Session,
        template_id: int,
        **kwargs,
    ) -> TransformTemplate:
        """Update a template's fields."""
        template = TemplateService.get(db, template_id)
        if "steps" in kwargs:
            kwargs["steps_json"] = json.dumps(kwargs.pop("steps"))
        for key, value in kwargs.items():
            if hasattr(template, key):
                setattr(template, key, value)
        template.version += 1
        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def delete(db: Session, template_id: int) -> None:
        """Delete a template."""
        template = TemplateService.get(db, template_id)
        db.delete(template)
        db.commit()

    @staticmethod
    def clone(db: Session, template_id: int, owner_id: int) -> TransformTemplate:
        """Clone a template for a new owner."""
        source = TemplateService.get(db, template_id)
        clone = TransformTemplate(
            name=f"Copy of {source.name}",
            description=source.description,
            steps_json=source.steps_json,
            category=source.category,
            is_public=False,
            is_sample=False,
            owner_id=owner_id,
            team_id=source.team_id,
        )
        db.add(clone)
        db.commit()
        db.refresh(clone)
        return clone


template_service = TemplateService()
