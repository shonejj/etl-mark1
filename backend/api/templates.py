"""Templates API router."""

import json
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas.schemas import TemplateCreate, TemplateOut, MessageResponse
from backend.services.template_service import template_service
from backend.core.security import get_current_user_id

router = APIRouter(prefix="/templates", tags=["templates"])


@router.post("/", response_model=TemplateOut)
async def create_template(
    body: TemplateCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Create a new transform template."""
    return template_service.create(
        db, body.name, body.steps, user_id,
        body.description, body.category, is_public=body.is_public,
    )


@router.get("/")
async def list_templates(
    search: Optional[str] = Query(None),
    team_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """List templates."""
    return template_service.list_templates(db, user_id, team_id, search, page=page, page_size=page_size)


@router.get("/{template_id}", response_model=TemplateOut)
async def get_template(template_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Get a template."""
    return template_service.get(db, template_id)


@router.put("/{template_id}", response_model=TemplateOut)
async def update_template(
    template_id: int,
    body: TemplateCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Update a template."""
    return template_service.update(
        db, template_id, name=body.name, steps=body.steps,
        description=body.description, category=body.category,
    )


@router.delete("/{template_id}", response_model=MessageResponse)
async def delete_template(template_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Delete a template."""
    template_service.delete(db, template_id)
    return MessageResponse(message="Template deleted")


@router.post("/{template_id}/clone", response_model=TemplateOut)
async def clone_template(template_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Clone a template."""
    return template_service.clone(db, template_id, user_id)
