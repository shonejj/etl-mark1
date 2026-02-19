"""Webhooks API router — incoming webhook triggers."""

import secrets
import hashlib
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas.schemas import WebhookCreate, WebhookOut, MessageResponse
from backend.models.smtp_config import WebhookTrigger
from backend.models.pipeline import PipelineRun, PipelineRunStatus, TriggeredBy
from backend.core.security import get_current_user_id
from backend.tasks.celery_app import execute_pipeline_run

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/", response_model=WebhookOut)
async def create_webhook(
    body: WebhookCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Create an incoming webhook trigger for a pipeline."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    webhook = WebhookTrigger(
        name=body.name,
        token_hash=token_hash,
        pipeline_id=body.pipeline_id,
        is_active=True,
        created_by=user_id,
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)

    return WebhookOut(
        id=webhook.id,
        name=webhook.name,
        token=raw_token,  # Show once
        pipeline_id=webhook.pipeline_id,
        is_active=webhook.is_active,
    )


@router.post("/trigger/{token}")
async def trigger_webhook(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Incoming webhook endpoint — triggers a pipeline run."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    webhook = db.query(WebhookTrigger).filter(
        WebhookTrigger.token_hash == token_hash,
        WebhookTrigger.is_active == True,
    ).first()

    if not webhook:
        raise HTTPException(status_code=404, detail="Invalid webhook token")

    # Create run
    run = PipelineRun(
        pipeline_id=webhook.pipeline_id,
        status=PipelineRunStatus.pending,
        triggered_by=TriggeredBy.webhook,
        trigger_webhook_id=webhook.id,
    )
    db.add(run)
    webhook.last_triggered_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)

    # Dispatch
    execute_pipeline_run.delay(run.id)

    return {"message": "Pipeline triggered", "run_id": run.id}


@router.get("/")
async def list_webhooks(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """List webhooks created by the user."""
    webhooks = db.query(WebhookTrigger).filter(
        WebhookTrigger.created_by == user_id,
    ).all()
    return [
        WebhookOut(
            id=w.id, name=w.name, pipeline_id=w.pipeline_id,
            is_active=w.is_active, last_triggered_at=w.last_triggered_at,
        )
        for w in webhooks
    ]
