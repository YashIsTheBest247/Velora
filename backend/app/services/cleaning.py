"""Step (a): Data cleaning / normalisation.

- Normalise dates to ISO 8601 (YYYY-MM-DD)
- Strip currency symbols from amounts
- Uppercase status values
- Normalise currency casing
- Fill missing categories with 'Uncategorised' (and flag for LLM classification)
- Remove exact duplicate rows
"""
from datetime import datetime
from typing import Optional

import pandas as pd

DATE_FORMATS = [
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
]

EXPECTED_COLUMNS = [
    "txn_id",
    "date",
    "merchant",
    "amount",
    "currency",
    "status",
    "category",
    "account_id",
    "notes",
]


def parse_date(value) -> Optional[str]:
    """Return an ISO-8601 date string, or None if unparseable."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    raw = str(value).strip()
    if not raw:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Last resort: let pandas attempt to infer.
    try:
        return pd.to_datetime(raw, dayfirst=True).strftime("%Y-%m-%d")
    except Exception:
        return None


def parse_amount(value) -> Optional[float]:
    """Strip currency symbols / thousands separators and return a float."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    raw = str(value).strip().replace("$", "").replace("₹", "").replace(",", "")
    if not raw:
        return None
    try:
        return round(float(raw), 2)
    except ValueError:
        return None


def _clean_str(value) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    return s or None


def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Clean a raw transactions DataFrame.

    Returns the cleaned DataFrame plus the raw row count (pre-dedup).
    The cleaned frame gains a boolean ``needs_classification`` column.
    """
    # Ensure all expected columns exist.
    for col in EXPECTED_COLUMNS:
        if col not in df.columns:
            df[col] = None

    df = df[EXPECTED_COLUMNS].copy()
    row_count_raw = len(df)

    # Remove exact duplicate rows (all columns identical).
    df = df.drop_duplicates(keep="first").reset_index(drop=True)

    df["txn_id"] = df["txn_id"].map(_clean_str)
    df["merchant"] = df["merchant"].map(_clean_str)
    df["account_id"] = df["account_id"].map(_clean_str)
    df["notes"] = df["notes"].map(_clean_str)

    df["date"] = df["date"].map(parse_date)
    df["amount"] = df["amount"].map(parse_amount)

    df["status"] = df["status"].map(
        lambda v: _clean_str(v).upper() if _clean_str(v) else None
    )
    df["currency"] = df["currency"].map(
        lambda v: _clean_str(v).upper() if _clean_str(v) else None
    )

    # Track which rows had no category, then fill with 'Uncategorised'.
    category_clean = df["category"].map(_clean_str)
    df["needs_classification"] = category_clean.isna()
    df["category"] = category_clean.fillna("Uncategorised")

    return df, row_count_raw
