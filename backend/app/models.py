"""SQLAlchemy ORM models: Job, Transaction, JobSummary."""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class JobStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default=JobStatus.PENDING, index=True)
    row_count_raw = Column(Integer, default=0)
    row_count_clean = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    # Raw uploaded CSV stored so the worker can process without a shared volume.
    raw_csv = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

    transactions = relationship(
        "Transaction", back_populates="job", cascade="all, delete-orphan"
    )
    summary = relationship(
        "JobSummary",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)

    txn_id = Column(String(50), nullable=True)
    date = Column(String(10), nullable=True)  # ISO 8601 (YYYY-MM-DD)
    merchant = Column(String(120), nullable=True)
    amount = Column(Float, nullable=True)
    currency = Column(String(10), nullable=True)
    status = Column(String(20), nullable=True)
    category = Column(String(50), nullable=True)
    account_id = Column(String(50), nullable=True, index=True)
    notes = Column(Text, nullable=True)

    is_anomaly = Column(Boolean, default=False, index=True)
    anomaly_reason = Column(Text, nullable=True)

    llm_category = Column(String(50), nullable=True)
    llm_raw_response = Column(Text, nullable=True)
    llm_failed = Column(Boolean, default=False)

    job = relationship("Job", back_populates="transactions")


class JobSummary(Base):
    __tablename__ = "job_summaries"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, unique=True)

    total_spend_inr = Column(Float, default=0.0)
    total_spend_usd = Column(Float, default=0.0)
    top_merchants = Column(JSONB, default=list)
    category_breakdown = Column(JSONB, default=dict)
    anomaly_count = Column(Integer, default=0)
    narrative = Column(Text, nullable=True)
    risk_level = Column(String(10), nullable=True)

    job = relationship("Job", back_populates="summary")
