"""Celery tasks."""
from app.celery_app import celery_app
from app.database import SessionLocal
from app.services.pipeline import run_pipeline


@celery_app.task(name="process_job")
def process_job(job_id: int) -> dict:
    """Dequeued worker entry point — runs the full pipeline for a job."""
    db = SessionLocal()
    try:
        run_pipeline(job_id, db)
        return {"job_id": job_id, "status": "done"}
    finally:
        db.close()
