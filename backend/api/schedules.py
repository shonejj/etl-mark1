"""Schedules API router."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas.schemas import ScheduleCreate, ScheduleOut, MessageResponse
from backend.models.schedule import Schedule
from backend.core.security import get_current_user_id

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.post("/", response_model=ScheduleOut)
async def create_schedule(
    body: ScheduleCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Create a new schedule for a pipeline."""
    schedule = Schedule(
        pipeline_id=body.pipeline_id,
        cron_expr=body.cron_expr,
        enabled=body.enabled,
        timezone=body.timezone,
        notify_on_failure=body.notify_on_failure,
        created_by=user_id,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


@router.get("/")
async def list_schedules(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """List all schedules."""
    schedules = db.query(Schedule).all()
    return [ScheduleOut.model_validate(s) for s in schedules]


@router.put("/{schedule_id}/toggle", response_model=ScheduleOut)
async def toggle_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Toggle a schedule on/off."""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if schedule:
        schedule.enabled = not schedule.enabled
        db.commit()
        db.refresh(schedule)
    return schedule


@router.delete("/{schedule_id}", response_model=MessageResponse)
async def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Delete a schedule."""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if schedule:
        db.delete(schedule)
        db.commit()
    return MessageResponse(message="Schedule deleted")
