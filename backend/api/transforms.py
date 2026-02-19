"""Transform preview API router — apply transforms via DuckDB."""

import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas.schemas import TransformPreview, DataPreviewResponse
from backend.services.file_service import file_service
from backend.services.duckdb_engine import DuckDBEngine
from backend.core.security import get_current_user_id

router = APIRouter(prefix="/transforms", tags=["transforms"])


@router.post("/preview", response_model=DataPreviewResponse)
async def preview_transform(
    body: TransformPreview,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Apply transform steps to a file and return preview.

    This does NOT modify the original file. It's a read-only preview.
    """
    file = file_service.get_file(db, body.file_id)
    tmp_path = file_service.download_to_temp(file.minio_key)

    try:
        result = DuckDBEngine.apply_transforms(
            tmp_path, file.format, body.steps, body.limit,
        )
        return DataPreviewResponse(**result)
    finally:
        os.unlink(tmp_path)


@router.post("/sql")
async def execute_sql(
    sql: str,
    file_id: int,
    limit: int = 1000,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Execute raw SQL against a file via DuckDB."""
    file = file_service.get_file(db, file_id)
    tmp_path = file_service.download_to_temp(file.minio_key)

    try:
        safe_sql = sql.replace("{{input}}", "_data")
        result = DuckDBEngine.execute_sql(
            safe_sql,
            sources={"_data": tmp_path},
            limit=limit,
        )
        return result
    finally:
        os.unlink(tmp_path)
