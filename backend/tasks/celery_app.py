"""Celery app and tasks for async pipeline execution."""

from celery import Celery
from backend.core.config import settings

celery_app = Celery(
    "etl_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_concurrency=settings.CONCURRENCY,
    task_soft_time_limit=600,  # 10 min soft limit
    task_time_limit=900,  # 15 min hard limit
)


@celery_app.task(bind=True, name="execute_pipeline_run")
def execute_pipeline_run(self, run_id: int) -> dict:
    """Execute a pipeline run as a Celery task.

    This is the main entry point for async pipeline execution.
    """
    from backend.db.session import SessionLocal
    from backend.executor.engine import PipelineExecutor
    from backend.services.cache_service import cache_service
    import json

    db = SessionLocal()
    try:
        executor = PipelineExecutor(db)
        result = executor.execute(run_id)

        # Publish completion event via Redis
        cache_service.publish(
            f"pipeline_run:{run_id}",
            json.dumps({"run_id": run_id, "status": result["status"]}),
        )

        return result
    except Exception as e:
        # Publish failure event
        cache_service.publish(
            f"pipeline_run:{run_id}",
            json.dumps({"run_id": run_id, "status": "failed", "error": str(e)}),
        )
        raise
    finally:
        db.close()
