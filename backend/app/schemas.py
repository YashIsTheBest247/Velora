"""Pydantic response/request schemas."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class JobListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    status: str
    row_count_raw: int
    row_count_clean: int
    created_at: datetime


class SummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_spend_inr: float
    total_spend_usd: float
    top_merchants: list[Any]
    category_breakdown: dict[str, Any]
    anomaly_count: int
    narrative: Optional[str]
    risk_level: Optional[str]


class JobStatusOut(BaseModel):
    id: int
    status: str
    filename: str
    row_count_raw: int
    row_count_clean: int
    created_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
    summary: Optional[SummaryOut] = None


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    txn_id: Optional[str]
    date: Optional[str]
    merchant: Optional[str]
    amount: Optional[float]
    currency: Optional[str]
    status: Optional[str]
    category: Optional[str]
    account_id: Optional[str]
    notes: Optional[str]
    is_anomaly: bool
    anomaly_reason: Optional[str]
    llm_category: Optional[str]
    llm_failed: bool


class JobResultsOut(BaseModel):
    id: int
    status: str
    filename: str
    transactions: list[TransactionOut]
    anomalies: list[TransactionOut]
    category_breakdown: dict[str, Any]
    summary: Optional[SummaryOut] = None


class UploadResponse(BaseModel):
    job_id: int
    status: str
    message: str
