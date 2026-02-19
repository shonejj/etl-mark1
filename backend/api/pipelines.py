"""Pipelines API router — CRUD, run, clone, export."""

import json
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas.schemas import (
    PipelineCreate, PipelineUpdate, PipelineOut,
    RunOut, NodeLogOut, MessageResponse,
)
from backend.services.pipeline_service import pipeline_service
from backend.services.audit_service import audit_service
from backend.models.pipeline import PipelineRun, PipelineRunStatus, TriggeredBy, NodeRunLog
from backend.core.security import get_current_user_id
from backend.tasks.celery_app import execute_pipeline_run

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


@router.post("/", response_model=PipelineOut)
async def create_pipeline(
    body: PipelineCreate,
    request: Request,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Create a new pipeline."""
    pipeline = pipeline_service.create(
        db, body.name, body.definition, user_id,
        body.description, tags=body.tags,
    )
    audit_service.log_from_request(
        db, request, user_id, None, "pipeline.created",
        "pipeline", str(pipeline.id),
    )
    return pipeline


@router.get("/")
async def list_pipelines(
    search: Optional[str] = Query(None),
    team_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """List pipelines."""
    return pipeline_service.list_pipelines(db, user_id, team_id, search, page, page_size)


@router.get("/{pipeline_id}", response_model=PipelineOut)
async def get_pipeline(pipeline_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Get single pipeline."""
    return pipeline_service.get(db, pipeline_id)


@router.get("/{pipeline_id}/definition")
async def get_pipeline_definition(pipeline_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Get pipeline JSON definition (nodes + edges)."""
    pipeline = pipeline_service.get(db, pipeline_id)
    return json.loads(pipeline.definition_json)


@router.put("/{pipeline_id}", response_model=PipelineOut)
async def update_pipeline(
    pipeline_id: int,
    body: PipelineUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Update a pipeline."""
    kwargs = body.model_dump(exclude_unset=True)
    return pipeline_service.update(db, pipeline_id, **kwargs)


@router.delete("/{pipeline_id}", response_model=MessageResponse)
async def delete_pipeline(
    pipeline_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Soft-delete a pipeline."""
    pipeline_service.delete(db, pipeline_id)
    return MessageResponse(message="Pipeline deleted")


@router.post("/{pipeline_id}/clone", response_model=PipelineOut)
async def clone_pipeline(
    pipeline_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Clone a pipeline."""
    return pipeline_service.clone(db, pipeline_id, user_id)


@router.get("/{pipeline_id}/export")
async def export_pipeline(pipeline_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Export pipeline as JSON."""
    return pipeline_service.export_json(db, pipeline_id)


# ---- Run Endpoints ----

@router.post("/{pipeline_id}/run", response_model=RunOut)
async def run_pipeline(
    pipeline_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Trigger a pipeline run (async via Celery)."""
    pipeline = pipeline_service.get(db, pipeline_id)

    run = PipelineRun(
        pipeline_id=pipeline_id,
        status=PipelineRunStatus.pending,
        triggered_by=TriggeredBy.manual,
        trigger_user_id=user_id,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Dispatch to Celery
    task = execute_pipeline_run.delay(run.id)
    run.celery_task_id = task.id
    db.commit()

    audit_service.log_from_request(
        db, request, user_id, None, "pipeline.run_started",
        "pipeline", str(pipeline_id), new_value={"run_id": run.id},
    )

    return run


@router.get("/{pipeline_id}/runs")
async def list_runs(
    pipeline_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """List runs for a pipeline."""
    query = db.query(PipelineRun).filter(PipelineRun.pipeline_id == pipeline_id)
    total = query.count()
    runs = (
        query.order_by(PipelineRun.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"runs": [RunOut.model_validate(r) for r in runs], "total": total, "page": page}


@router.get("/runs/{run_id}")
async def get_run(run_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Get a single run with node logs."""
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    node_logs = [NodeLogOut.model_validate(n) for n in run.node_logs]
    return {
        "run": RunOut.model_validate(run),
        "node_logs": node_logs,
    }
