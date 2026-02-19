"""Connectors API router."""

import json
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet

from backend.db.session import get_db
from backend.schemas.schemas import ConnectorCreate, ConnectorOut, ConnectorTestRequest, ConnectorTestResponse, MessageResponse
from backend.models.connector import ConnectorConfig
from backend.connectors.builtin import get_connector
from backend.core.security import get_current_user_id, require_member

router = APIRouter(prefix="/connectors", tags=["connectors"])

# Simple encryption key (in production, load from env/vault)
_FERNET_KEY = Fernet.generate_key()
_fernet = Fernet(_FERNET_KEY)


@router.post("/", response_model=ConnectorOut)
async def create_connector(
    body: ConnectorCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Create a new connector configuration."""
    encrypted = _fernet.encrypt(json.dumps(body.config).encode()).decode()
    connector = ConnectorConfig(
        name=body.name,
        type=body.type,
        config_encrypted=encrypted,
        is_shared=body.is_shared,
        owner_id=user_id,
        test_status="untested",
    )
    db.add(connector)
    db.commit()
    db.refresh(connector)
    return connector


@router.get("/")
async def list_connectors(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """List connectors owned by or shared with the user."""
    connectors = db.query(ConnectorConfig).filter(
        (ConnectorConfig.owner_id == user_id) | (ConnectorConfig.is_shared == True)
    ).all()
    return [ConnectorOut.model_validate(c) for c in connectors]


@router.post("/test", response_model=ConnectorTestResponse)
async def test_connector(body: ConnectorTestRequest):
    """Test a connector configuration."""
    try:
        connector = get_connector(body.type)
        connector.connect(body.config)
        success = connector.test_connection()
        return ConnectorTestResponse(
            success=success,
            message="Connection successful" if success else "Connection failed",
        )
    except Exception as e:
        return ConnectorTestResponse(success=False, message=str(e))


@router.delete("/{connector_id}", response_model=MessageResponse)
async def delete_connector(
    connector_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Delete a connector."""
    connector = db.query(ConnectorConfig).filter(
        ConnectorConfig.id == connector_id,
        ConnectorConfig.owner_id == user_id,
    ).first()
    if connector:
        db.delete(connector)
        db.commit()
    return MessageResponse(message="Connector deleted")
