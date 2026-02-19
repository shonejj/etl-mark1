"""Pipeline service — CRUD, clone, export for pipeline definitions."""

import json
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from backend.models.pipeline import Pipeline
from backend.core.exceptions import ResourceNotFoundError


class PipelineService:
    """Manages pipeline definitions (visual DAG JSON)."""

    @staticmethod
    def create(
        db: Session,
        name: str,
        definition: Dict[str, Any],
        owner_id: int,
        description: Optional[str] = None,
        team_id: Optional[int] = None,
        tags: Optional[list] = None,
    ) -> Pipeline:
        """Create a new pipeline."""
        pipeline = Pipeline(
            name=name,
            description=description,
            definition_json=json.dumps(definition),
            tags_json=json.dumps(tags) if tags else None,
            owner_id=owner_id,
            team_id=team_id,
        )
        db.add(pipeline)
        db.commit()
        db.refresh(pipeline)
        return pipeline

    @staticmethod
    def get(db: Session, pipeline_id: int) -> Pipeline:
        """Get a pipeline by id."""
        pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        if not pipeline:
            raise ResourceNotFoundError(f"Pipeline {pipeline_id} not found")
        return pipeline

    @staticmethod
    def list_pipelines(
        db: Session,
        owner_id: Optional[int] = None,
        team_id: Optional[int] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """List pipelines with filters."""
        query = db.query(Pipeline).filter(Pipeline.is_active == True)

        if owner_id:
            query = query.filter(Pipeline.owner_id == owner_id)
        if team_id:
            query = query.filter(Pipeline.team_id == team_id)
        if search:
            query = query.filter(Pipeline.name.ilike(f"%{search}%"))

        total = query.count()
        pipelines = (
            query.order_by(Pipeline.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {"pipelines": pipelines, "total": total, "page": page}

    @staticmethod
    def update(db: Session, pipeline_id: int, **kwargs) -> Pipeline:
        """Update a pipeline's fields and bump version."""
        pipeline = PipelineService.get(db, pipeline_id)
        if "definition" in kwargs:
            kwargs["definition_json"] = json.dumps(kwargs.pop("definition"))
        if "tags" in kwargs:
            kwargs["tags_json"] = json.dumps(kwargs.pop("tags"))
        for key, value in kwargs.items():
            if hasattr(pipeline, key):
                setattr(pipeline, key, value)
        pipeline.version += 1
        db.commit()
        db.refresh(pipeline)
        return pipeline

    @staticmethod
    def delete(db: Session, pipeline_id: int) -> None:
        """Soft-delete a pipeline."""
        pipeline = PipelineService.get(db, pipeline_id)
        pipeline.is_active = False
        db.commit()

    @staticmethod
    def clone(db: Session, pipeline_id: int, owner_id: int) -> Pipeline:
        """Clone a pipeline for a new owner."""
        source = PipelineService.get(db, pipeline_id)
        clone = Pipeline(
            name=f"Copy of {source.name}",
            description=source.description,
            definition_json=source.definition_json,
            tags_json=source.tags_json,
            owner_id=owner_id,
            team_id=source.team_id,
        )
        db.add(clone)
        db.commit()
        db.refresh(clone)
        return clone

    @staticmethod
    def export_json(db: Session, pipeline_id: int) -> Dict[str, Any]:
        """Export a pipeline as a plain JSON dict."""
        pipeline = PipelineService.get(db, pipeline_id)
        return {
            "id": pipeline.id,
            "name": pipeline.name,
            "description": pipeline.description,
            "version": pipeline.version,
            "definition": json.loads(pipeline.definition_json),
            "tags": json.loads(pipeline.tags_json) if pipeline.tags_json else [],
        }


pipeline_service = PipelineService()
