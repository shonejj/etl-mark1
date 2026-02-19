"""File metadata model for MinIO-stored files."""

from sqlalchemy import Column, Integer, String, Text, BigInteger, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from backend.db.base import Base


class FileMeta(Base):
    """Metadata for uploaded files stored in MinIO."""
    __tablename__ = "file_meta"

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_name = Column(String(500), nullable=False)
    minio_key = Column(String(1000), nullable=False)
    bucket = Column(String(255), nullable=False)
    size_bytes = Column(BigInteger, nullable=False, default=0)
    content_type = Column(String(100), nullable=True)
    format = Column(String(20), nullable=False)  # csv, xlsx, json, xml, txt, pdf
    schema_json = Column(Text, nullable=True)  # JSON column info
    tags_json = Column(Text, nullable=True)
    record_count = Column(Integer, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    checksum_md5 = Column(String(32), nullable=True)
    quality_score = Column(Float, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime, nullable=True)  # soft delete

    owner = relationship("User", lazy="joined")
    versions = relationship("FileVersion", back_populates="file", lazy="selectin")


class FileVersion(Base):
    """Version history for a file."""
    __tablename__ = "file_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("file_meta.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    minio_key = Column(String(1000), nullable=False)
    size_bytes = Column(BigInteger, nullable=False, default=0)
    record_count = Column(Integer, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    file = relationship("FileMeta", back_populates="versions")
