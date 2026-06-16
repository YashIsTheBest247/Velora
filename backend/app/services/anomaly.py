"""Step (b): Anomaly detection.

- Flag transactions whose amount exceeds N x the account's median (statistical outlier).
- Flag rows where currency is USD but the merchant is a domestic-only Indian brand.
"""
import pandas as pd

from app.config import settings

# Domestic-only (India) brands that should never legitimately transact in USD.
DOMESTIC_ONLY_MERCHANTS = {
    "swiggy",
    "ola",
    "irctc",
    "zomato",
    "jio recharge",
    "bookmyshow",
    "hdfc atm",
    "flipkart",
}


def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``is_anomaly`` and ``anomaly_reason`` columns to the frame."""
    df = df.copy()
    df["is_anomaly"] = False
    df["anomaly_reason"] = None

    multiplier = settings.outlier_multiplier

    # Per-account median of valid amounts.
    medians = (
        df.dropna(subset=["amount", "account_id"])
        .groupby("account_id")["amount"]
        .median()
        .to_dict()
    )

    reasons: list[list[str]] = [[] for _ in range(len(df))]

    for pos, (_, row) in enumerate(df.iterrows()):
        amount = row["amount"]
        account = row["account_id"]
        merchant = row["merchant"]
        currency = row["currency"]

        # Statistical outlier vs. the account median.
        if amount is not None and not pd.isna(amount) and account in medians:
            median = medians[account]
            if median and amount > multiplier * median:
                reasons[pos].append(
                    f"Amount {amount:.2f} exceeds {multiplier:g}x account median "
                    f"({median:.2f}) for {account}"
                )

        # USD charge on a domestic-only merchant.
        if (
            currency == "USD"
            and merchant
            and merchant.strip().lower() in DOMESTIC_ONLY_MERCHANTS
        ):
            reasons[pos].append(
                f"USD currency on domestic-only merchant '{merchant}'"
            )

    df["anomaly_reason"] = ["; ".join(r) if r else None for r in reasons]
    df["is_anomaly"] = [bool(r) for r in reasons]
    return df
