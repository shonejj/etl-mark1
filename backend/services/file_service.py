"""File service — manages upload/download via MinIO and metadata in MySQL."""

import os
import hashlib
import json
import tempfile
from typing import Optional, List, Dict, Any
from datetime import datetime

from minio import Minio
from minio.error import S3Error
from sqlalchemy.orm import Session
from fastapi import UploadFile

from backend.core.config import settings
from backend.core.exceptions import StorageError, ResourceNotFoundError
from backend.models.file_meta import FileMeta, FileVersion
from backend.services.duckdb_engine import DuckDBEngine


class FileService:
    """Manages file uploads to MinIO and metadata in MySQL."""

    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.bucket = settings.MINIO_BUCKET

    def ensure_bucket(self) -> None:
        """Create the default bucket if it doesn't exist."""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    async def upload_file(
        self,
        db: Session,
        upload: UploadFile,
        owner_id: int,
        team_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> FileMeta:
        """Upload a file to MinIO and store metadata in MySQL.

        Returns:
            FileMeta ORM object.
        """
        self.ensure_bucket()

        # Read file content
        content = await upload.read()
        size_bytes = len(content)
        checksum = hashlib.md5(content).hexdigest()

        # Detect format
        filename = upload.filename or "untitled"
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        file_format = ext if ext in ("csv", "xlsx", "json", "xml", "txt", "pdf", "xls") else "csv"

        # Build MinIO object key
        team_prefix = str(team_id) if team_id else "default"
        minio_key = f"files/{team_prefix}/{checksum}/{filename}"

        # Write to temp file for MinIO upload
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Upload to MinIO
            self.client.fput_object(
                self.bucket,
                minio_key,
                tmp_path,
                content_type=upload.content_type or "application/octet-stream",
            )

            # Infer schema and record count using DuckDB
            schema_info = []
            record_count = 0
            quality_score = None
            if file_format in ("csv", "json", "xlsx", "txt"):
                try:
                    schema_info = DuckDBEngine.infer_schema(tmp_path, file_format)
                    preview = DuckDBEngine.preview_file(tmp_path, limit=1, file_format=file_format)
                    record_count = preview.get("total_count", 0)
                    quality = DuckDBEngine.data_quality_score(tmp_path, file_format)
                    quality_score = quality.get("score")
                except Exception:
                    pass  # Schema inference may fail for some formats

            # Create metadata record
            file_meta = FileMeta(
                original_name=filename,
                minio_key=minio_key,
                bucket=self.bucket,
                size_bytes=size_bytes,
                content_type=upload.content_type,
                format=file_format,
                schema_json=json.dumps(schema_info) if schema_info else None,
                tags_json=json.dumps(tags) if tags else None,
                record_count=record_count,
                version=1,
                checksum_md5=checksum,
                quality_score=quality_score,
                owner_id=owner_id,
                team_id=team_id,
            )
            db.add(file_meta)
            db.flush()

            # Create version record
            version = FileVersion(
                file_id=file_meta.id,
                version=1,
                minio_key=minio_key,
                size_bytes=size_bytes,
                record_count=record_count,
                created_by=owner_id,
            )
            db.add(version)
            db.commit()
            db.refresh(file_meta)

            return file_meta
        finally:
            os.unlink(tmp_path)

    def download_to_temp(self, minio_key: str) -> str:
        """Download a MinIO object to a temp file and return the path."""
        ext = os.path.splitext(minio_key)[1]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        tmp.close()
        try:
            self.client.fget_object(self.bucket, minio_key, tmp.name)
            return tmp.name
        except S3Error as e:
            os.unlink(tmp.name)
            raise StorageError(f"Failed to download from MinIO: {e}")

    def get_presigned_url(self, minio_key: str, expires_minutes: int = 15) -> str:
        """Generate a presigned download URL for a MinIO object."""
        from datetime import timedelta
        try:
            return self.client.presigned_get_object(
                self.bucket, minio_key, expires=timedelta(minutes=expires_minutes)
            )
        except S3Error as e:
            raise StorageError(f"Failed to generate presigned URL: {e}")

    def delete_object(self, minio_key: str) -> None:
        """Delete an object from MinIO."""
        try:
            self.client.remove_object(self.bucket, minio_key)
        except S3Error as e:
            raise StorageError(f"Failed to delete from MinIO: {e}")

    def list_files(
        self,
        db: Session,
        owner_id: Optional[int] = None,
        team_id: Optional[int] = None,
        search: Optional[str] = None,
        file_format: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """List file metadata with pagination and filters."""
        query = db.query(FileMeta).filter(FileMeta.deleted_at.is_(None))

        if owner_id:
            query = query.filter(FileMeta.owner_id == owner_id)
        if team_id:
            query = query.filter(FileMeta.team_id == team_id)
        if search:
            query = query.filter(FileMeta.original_name.ilike(f"%{search}%"))
        if file_format:
            query = query.filter(FileMeta.format == file_format)

        total = query.count()
        files = (
            query.order_by(FileMeta.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "files": files,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    def get_file(self, db: Session, file_id: int) -> FileMeta:
        """Get a single file by ID."""
        file = db.query(FileMeta).filter(
            FileMeta.id == file_id, FileMeta.deleted_at.is_(None)
        ).first()
        if not file:
            raise ResourceNotFoundError(f"File {file_id} not found")
        return file

    def soft_delete(self, db: Session, file_id: int) -> None:
        """Soft-delete a file by setting deleted_at."""
        file = self.get_file(db, file_id)
        file.deleted_at = datetime.utcnow()
        db.commit()


# Singleton instance
file_service = FileService()
