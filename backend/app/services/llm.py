"""Steps (c) & (d): LLM classification + narrative summary.

Uses Gemini 1.5 Flash when ``GEMINI_API_KEY`` is set. When no key is
configured the module falls back to a deterministic heuristic so the whole
stack still runs end-to-end with `docker compose up` and zero spend.

Retry logic (step e): each LLM call is retried up to ``llm_max_retries`` times
with exponential backoff. If all retries fail the caller marks the batch as
``llm_failed`` and continues — the job is never failed because of the LLM.
"""
import json
import logging
import re

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = logging.getLogger(__name__)

VALID_CATEGORIES = [
    "Food",
    "Shopping",
    "Travel",
    "Transport",
    "Utilities",
    "Cash Withdrawal",
    "Entertainment",
    "Other",
]

# Heuristic merchant -> category map used by the fallback classifier.
_MERCHANT_CATEGORY = {
    "swiggy": "Food",
    "zomato": "Food",
    "amazon": "Shopping",
    "flipkart": "Shopping",
    "ola": "Transport",
    "irctc": "Travel",
    "makemytrip": "Travel",
    "jio recharge": "Utilities",
    "hdfc atm": "Cash Withdrawal",
    "bookmyshow": "Entertainment",
}


class LLMError(Exception):
    """Raised when an LLM call fails and should be retried."""


class QuotaError(Exception):
    """Raised on 429 / quota-exhausted. NOT retried — retrying won't help, so we
    fall back to the heuristic immediately instead of stalling on backoffs."""


# Bound each network call so a single request can't hang the worker (the SDK
# can otherwise honour a server-supplied retry_delay of tens of seconds).
_REQUEST_TIMEOUT = 30


def _classify_exception(exc: Exception) -> Exception:
    """Map a raw SDK error to QuotaError (fail fast) or LLMError (retry)."""
    msg = str(exc).lower()
    if "429" in msg or "quota" in msg or "exhaust" in msg or "rate limit" in msg:
        return QuotaError(str(exc))
    return LLMError(str(exc))


def llm_enabled() -> bool:
    return bool(settings.gemini_api_key)


def _get_model():
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(settings.gemini_model)


def _heuristic_category(merchant: str | None) -> str:
    if not merchant:
        return "Other"
    return _MERCHANT_CATEGORY.get(merchant.strip().lower(), "Other")


def _extract_json(text: str):
    """Pull the first JSON object/array out of a model response."""
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if not match:
        raise LLMError(f"No JSON found in LLM response: {text[:200]}")
    return json.loads(match.group(1))


# --------------------------------------------------------------------------- #
# Classification
# --------------------------------------------------------------------------- #
@retry(
    retry=retry_if_exception_type(LLMError),
    stop=stop_after_attempt(settings.llm_max_retries),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def _classify_call(items: list[dict]) -> dict[int, str]:
    model = _get_model()
    payload = [
        {"id": it["id"], "merchant": it["merchant"], "amount": it["amount"],
         "notes": it["notes"]}
        for it in items
    ]
    prompt = (
        "You are a financial transaction classifier. Assign each transaction "
        "exactly one category from this list: "
        f"{', '.join(VALID_CATEGORIES)}.\n"
        "Respond with ONLY a JSON object mapping each transaction id (as a "
        'string) to its category, e.g. {"12": "Food", "15": "Travel"}.\n\n'
        f"Transactions:\n{json.dumps(payload)}"
    )
    try:
        resp = model.generate_content(
            prompt, request_options={"timeout": _REQUEST_TIMEOUT}
        )
        data = _extract_json(resp.text)
    except LLMError:
        raise
    except Exception as exc:  # network / quota / parsing
        raise _classify_exception(exc) from exc

    result: dict[int, str] = {}
    for key, val in data.items():
        try:
            idx = int(key)
        except (TypeError, ValueError):
            continue
        category = val if val in VALID_CATEGORIES else "Other"
        result[idx] = category
    return result


def classify_batch(items: list[dict]) -> tuple[dict[int, str], bool]:
    """Classify a batch of transactions.

    ``items`` is a list of {"id", "merchant", "amount", "notes"}.
    Returns ``(mapping, llm_failed)`` where mapping is id -> category. On
    failure the mapping falls back to heuristics and ``llm_failed`` is True.
    """
    if not items:
        return {}, False

    if not llm_enabled():
        return {it["id"]: _heuristic_category(it["merchant"]) for it in items}, False

    try:
        return _classify_call(items), False
    except Exception as exc:
        logger.warning("LLM classification batch failed after retries: %s", exc)
        # Fallback so downstream still has a usable category.
        return (
            {it["id"]: _heuristic_category(it["merchant"]) for it in items},
            True,
        )


# --------------------------------------------------------------------------- #
# Narrative summary
# --------------------------------------------------------------------------- #
@retry(
    retry=retry_if_exception_type(LLMError),
    stop=stop_after_attempt(settings.llm_max_retries),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def _summary_call(stats: dict) -> dict:
    model = _get_model()
    prompt = (
        "You are a financial analyst. Given these aggregate statistics from a "
        "batch of transactions, produce a JSON object with EXACTLY these keys:\n"
        '  "narrative": a 2-3 sentence plain-English spending summary,\n'
        '  "risk_level": one of "low", "medium", "high".\n'
        "Base risk on the number and severity of anomalies relative to total "
        "transactions. Respond with ONLY the JSON object.\n\n"
        f"Statistics:\n{json.dumps(stats)}"
    )
    try:
        resp = model.generate_content(
            prompt, request_options={"timeout": _REQUEST_TIMEOUT}
        )
        data = _extract_json(resp.text)
    except LLMError:
        raise
    except Exception as exc:
        raise _classify_exception(exc) from exc

    narrative = str(data.get("narrative", "")).strip()
    risk = str(data.get("risk_level", "")).strip().lower()
    if risk not in {"low", "medium", "high"}:
        risk = _heuristic_risk(stats)
    if not narrative:
        narrative = _heuristic_narrative(stats)
    return {"narrative": narrative, "risk_level": risk}


def _heuristic_risk(stats: dict) -> str:
    total = max(stats.get("transaction_count", 0), 1)
    anomalies = stats.get("anomaly_count", 0)
    ratio = anomalies / total
    if anomalies == 0:
        return "low"
    if ratio >= 0.15 or anomalies >= 8:
        return "high"
    if ratio >= 0.05 or anomalies >= 3:
        return "medium"
    return "low"


def _heuristic_narrative(stats: dict) -> str:
    top = stats.get("top_merchants", [])
    top_names = ", ".join(m["merchant"] for m in top[:3]) if top else "various merchants"
    return (
        f"Processed {stats.get('transaction_count', 0)} transactions totalling "
        f"₹{stats.get('total_spend_inr', 0):,.2f} and "
        f"${stats.get('total_spend_usd', 0):,.2f}. Top merchants were {top_names}. "
        f"{stats.get('anomaly_count', 0)} transactions were flagged as anomalous."
    )


def generate_summary(stats: dict) -> tuple[dict, bool]:
    """Return ``({"narrative", "risk_level"}, llm_failed)``."""
    if not llm_enabled():
        return (
            {
                "narrative": _heuristic_narrative(stats),
                "risk_level": _heuristic_risk(stats),
            },
            False,
        )
    try:
        return _summary_call(stats), False
    except Exception as exc:
        logger.warning("LLM summary failed after retries: %s", exc)
        return (
            {
                "narrative": _heuristic_narrative(stats),
                "risk_level": _heuristic_risk(stats),
            },
            True,
        )
