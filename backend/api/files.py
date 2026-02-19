"""Files API router — upload, list, preview, download, delete."""

import json
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException, Request
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas.schemas import FileOut, FileListResponse, DataPreviewResponse, QualityScoreResponse, MessageResponse
from backend.services.file_service import file_service
from backend.services.duckdb_engine import DuckDBEngine
from backend.services.audit_service import audit_service
from backend.services.cache_service import cache_service
from backend.core.security import get_current_user_id
from backend.core.exceptions import ResourceNotFoundError

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=FileOut)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    team_id: Optional[int] = Query(None),
    tags: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Upload a file to MinIO."""
    tag_list = json.loads(tags) if tags else None
    result = await file_service.upload_file(db, file, user_id, team_id, tag_list)
    audit_service.log_from_request(
        db, request, user_id, None, "file.uploaded",
        "file", str(result.id), new_value={"name": result.original_name},
    )
    return result


@router.get("/", response_model=FileListResponse)
async def list_files(
    search: Optional[str] = Query(None),
    file_format: Optional[str] = Query(None),
    team_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """List files with filters and pagination."""
    result = file_service.list_files(db, user_id, team_id, search, file_format, page, page_size)
    return FileListResponse(
        files=[FileOut.model_validate(f) for f in result["files"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get("/{file_id}", response_model=FileOut)
async def get_file(file_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Get file metadata."""
    try:
        return file_service.get_file(db, file_id)
    except ResourceNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


@router.get("/{file_id}/preview", response_model=DataPreviewResponse)
async def preview_file(
    file_id: int,
    limit: int = Query(200, ge=1, le=5000),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Preview file data via DuckDB."""
    cache_key = f"preview:{file_id}:{limit}"
    cached = cache_service.get_json(cache_key)
    if cached:
        return DataPreviewResponse(**cached)

    file = file_service.get_file(db, file_id)
    tmp_path = file_service.download_to_temp(file.minio_key)

    try:
        result = DuckDBEngine.preview_file(tmp_path, limit, file.format)
        cache_service.set_json(cache_key, result, ttl_seconds=300)
        return DataPreviewResponse(**result)
    finally:
        import os
        os.unlink(tmp_path)


@router.get("/{file_id}/schema")
async def get_schema(file_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Get inferred schema of a file."""
    file = file_service.get_file(db, file_id)
    if file.schema_json:
        return json.loads(file.schema_json)
    return []


@router.get("/{file_id}/quality", response_model=QualityScoreResponse)
async def get_quality(file_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Get data quality score for a file."""
    file = file_service.get_file(db, file_id)
    tmp_path = file_service.download_to_temp(file.minio_key)
    try:
        result = DuckDBEngine.data_quality_score(tmp_path, file.format)
        return QualityScoreResponse(**result)
    finally:
        import os
        os.unlink(tmp_path)


@router.get("/{file_id}/download")
async def download_file(file_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Get a presigned download URL."""
    file = file_service.get_file(db, file_id)
    url = file_service.get_presigned_url(file.minio_key)
    return {"url": url, "filename": file.original_name}


@router.delete("/{file_id}", response_model=MessageResponse)
async def delete_file(
    file_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Soft-delete a file."""
    file_service.soft_delete(db, file_id)
    audit_service.log_from_request(
        db, request, user_id, None, "file.deleted", "file", str(file_id),
    )
    return MessageResponse(message="File deleted")
