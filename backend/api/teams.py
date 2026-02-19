"""Teams API router."""

import re
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas.schemas import TeamCreate, TeamOut, TeamMemberAdd, MessageResponse
from backend.models.team import Team, TeamMember, TeamRoleEnum
from backend.core.security import get_current_user_id

router = APIRouter(prefix="/teams", tags=["teams"])


@router.post("/", response_model=TeamOut)
async def create_team(
    body: TeamCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Create a new team."""
    slug = re.sub(r"[^a-z0-9]+", "-", body.name.lower()).strip("-")
    team = Team(
        name=body.name,
        slug=slug,
        description=body.description,
        created_by=user_id,
    )
    db.add(team)
    db.flush()

    # Auto-add creator as lead
    member = TeamMember(
        team_id=team.id,
        user_id=user_id,
        role_in_team=TeamRoleEnum.lead,
    )
    db.add(member)
    db.commit()
    db.refresh(team)
    return team


@router.get("/")
async def list_teams(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """List teams the user belongs to."""
    memberships = db.query(TeamMember).filter(TeamMember.user_id == user_id).all()
    team_ids = [m.team_id for m in memberships]
    teams = db.query(Team).filter(Team.id.in_(team_ids)).all() if team_ids else []
    return [TeamOut.model_validate(t) for t in teams]


@router.post("/{team_id}/members", response_model=MessageResponse)
async def add_member(
    team_id: int,
    body: TeamMemberAdd,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Add a member to a team."""
    member = TeamMember(
        team_id=team_id,
        user_id=body.user_id,
        role_in_team=TeamRoleEnum(body.role_in_team),
        invited_by=user_id,
    )
    db.add(member)
    db.commit()
    return MessageResponse(message="Member added")


@router.get("/{team_id}/members")
async def list_members(
    team_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """List team members."""
    members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
    return [
        {
            "user_id": m.user_id,
            "role_in_team": m.role_in_team.value,
            "joined_at": m.joined_at,
        }
        for m in members
    ]
