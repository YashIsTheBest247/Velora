"""Job-related API endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, JobStatus, Transaction
from app.schemas import (
    JobListItem,
    JobResultsOut,
    JobStatusOut,
    SummaryOut,
    TransactionOut,
    UploadResponse,
)
from app.tasks import process_job

router = APIRouter(prefix="/jobs", tags=["jobs"])

VALID_STATUSES = {
    JobStatus.PENDING,
    JobStatus.PROCESSING,
    JobStatus.COMPLETED,
    JobStatus.FAILED,
}


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Accept a CSV upload, create a pending Job, enqueue processing."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="A .csv file is required.")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 text.")

    first_line = text.splitlines()[0] if text.splitlines() else ""
    if "," not in first_line:
        raise HTTPException(status_code=400, detail="CSV header could not be parsed.")

    job = Job(
        filename=file.filename,
        status=JobStatus.PENDING,
        raw_csv=text,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    process_job.delay(job.id)

    return UploadResponse(
        job_id=job.id,
        status=job.status,
        message="File accepted and queued for processing.",
    )


@router.get("/{job_id}/status", response_model=JobStatusOut)
def get_status(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    summary = None
    if job.status == JobStatus.COMPLETED and job.summary:
        summary = SummaryOut.model_validate(job.summary)

    return JobStatusOut(
        id=job.id,
        status=job.status,
        filename=job.filename,
        row_count_raw=job.row_count_raw,
        row_count_clean=job.row_count_clean,
        created_at=job.created_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        summary=summary,
    )


@router.get("/{job_id}/results", response_model=JobResultsOut)
def get_results(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=f"Job is '{job.status}'. Results are available once completed.",
        )

    txns = (
        db.query(Transaction)
        .filter(Transaction.job_id == job_id)
        .order_by(Transaction.id)
        .all()
    )
    transactions = [TransactionOut.model_validate(t) for t in txns]
    anomalies = [t for t in transactions if t.is_anomaly]

    summary = SummaryOut.model_validate(job.summary) if job.summary else None
    breakdown = job.summary.category_breakdown if job.summary else {}

    return JobResultsOut(
        id=job.id,
        status=job.status,
        filename=job.filename,
        transactions=transactions,
        anomalies=anomalies,
        category_breakdown=breakdown,
        summary=summary,
    )


@router.get("", response_model=list[JobListItem])
def list_jobs(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Job)
    if status:
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status filter.")
        query = query.filter(Job.status == status)
    jobs = query.order_by(Job.created_at.desc()).all()
    return [JobListItem.model_validate(j) for j in jobs]
