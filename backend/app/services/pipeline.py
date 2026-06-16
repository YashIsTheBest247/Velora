"""Orchestrates the full processing pipeline for a single job."""
import io
import logging
from collections import defaultdict
from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Job, JobStatus, JobSummary, Transaction
from app.services import llm
from app.services.anomaly import detect_anomalies
from app.services.cleaning import clean_dataframe

logger = logging.getLogger(__name__)


def _compute_stats(df: pd.DataFrame, effective_category) -> dict:
    """Aggregate spend, top merchants, anomalies and category breakdown."""
    valid = df.dropna(subset=["amount"])

    total_inr = float(valid.loc[valid["currency"] == "INR", "amount"].sum())
    total_usd = float(valid.loc[valid["currency"] == "USD", "amount"].sum())

    merchant_totals = (
        valid.dropna(subset=["merchant"]).groupby("merchant")["amount"].sum()
    )
    top_merchants = [
        {"merchant": m, "total": round(float(t), 2)}
        for m, t in merchant_totals.sort_values(ascending=False).head(3).items()
    ]

    category_breakdown: dict[str, float] = defaultdict(float)
    for cat, amt in zip(effective_category, df["amount"]):
        if amt is not None and not pd.isna(amt):
            category_breakdown[cat] += float(amt)
    category_breakdown = {k: round(v, 2) for k, v in category_breakdown.items()}

    anomaly_count = int(df["is_anomaly"].sum())

    return {
        "transaction_count": len(df),
        "total_spend_inr": round(total_inr, 2),
        "total_spend_usd": round(total_usd, 2),
        "top_merchants": top_merchants,
        "category_breakdown": category_breakdown,
        "anomaly_count": anomaly_count,
    }


def run_pipeline(job_id: int, db: Session) -> None:
    """Execute steps (a)-(e) for the given job and persist all results."""
    job = db.query(Job).get(job_id)
    if job is None:
        logger.error("Job %s not found", job_id)
        return

    try:
        job.status = JobStatus.PROCESSING
        db.commit()

        # --- (a) Cleaning -------------------------------------------------- #
        df = pd.read_csv(io.StringIO(job.raw_csv), dtype=str, keep_default_na=False)
        df, row_count_raw = clean_dataframe(df)
        job.row_count_raw = row_count_raw
        job.row_count_clean = len(df)
        db.commit()

        # --- (b) Anomaly detection ---------------------------------------- #
        df = detect_anomalies(df)

        # --- (c) LLM classification (batched, only blank categories) ------ #
        df = df.reset_index(drop=True)
        df["llm_category"] = None
        df["llm_failed"] = False

        to_classify = df[df["needs_classification"]]
        items = [
            {
                "id": int(idx),
                "merchant": row["merchant"],
                "amount": row["amount"],
                "notes": row["notes"],
            }
            for idx, row in to_classify.iterrows()
        ]

        batch_size = settings.llm_batch_size
        for start in range(0, len(items), batch_size):
            batch = items[start : start + batch_size]
            mapping, failed = llm.classify_batch(batch)
            for idx, category in mapping.items():
                df.at[idx, "llm_category"] = category
                df.at[idx, "llm_failed"] = failed

        # Effective category = LLM result where we classified, else original.
        effective_category = df.apply(
            lambda r: r["llm_category"]
            if r["needs_classification"] and r["llm_category"]
            else r["category"],
            axis=1,
        )
        df["category"] = effective_category

        # --- Persist transactions ----------------------------------------- #
        db.query(Transaction).filter(Transaction.job_id == job_id).delete()
        for idx, row in df.iterrows():
            db.add(
                Transaction(
                    job_id=job_id,
                    txn_id=row["txn_id"],
                    date=row["date"],
                    merchant=row["merchant"],
                    amount=None if pd.isna(row["amount"]) else float(row["amount"]),
                    currency=row["currency"],
                    status=row["status"],
                    category=row["category"],
                    account_id=row["account_id"],
                    notes=row["notes"],
                    is_anomaly=bool(row["is_anomaly"]),
                    anomaly_reason=row["anomaly_reason"],
                    llm_category=row["llm_category"],
                    llm_failed=bool(row["llm_failed"]),
                )
            )
        db.commit()

        # --- (d) LLM narrative summary ------------------------------------ #
        stats = _compute_stats(df, effective_category)
        summary_out, _ = llm.generate_summary(stats)

        summary = JobSummary(
            job_id=job_id,
            total_spend_inr=stats["total_spend_inr"],
            total_spend_usd=stats["total_spend_usd"],
            top_merchants=stats["top_merchants"],
            category_breakdown=stats["category_breakdown"],
            anomaly_count=stats["anomaly_count"],
            narrative=summary_out["narrative"],
            risk_level=summary_out["risk_level"],
        )
        db.add(summary)

        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        db.commit()
        logger.info("Job %s completed: %s clean rows", job_id, len(df))

    except Exception as exc:  # noqa: BLE001 — pipeline must surface as failed job
        logger.exception("Job %s failed", job_id)
        db.rollback()
        job = db.query(Job).get(job_id)
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)[:1000]
            db.commit()
