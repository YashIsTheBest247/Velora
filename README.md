# Velora: AI-Powered Transaction Processing Pipeline

A backend service that ingests a messy CSV of financial transactions, processes
it **asynchronously** through a job queue, uses an **LLM** to classify transactions and flag anomalies, and exposes a structured summary report via a
**polling API** 

> **One command to run everything:** `docker compose up --build`

---

## Stack

| Layer            | Choice                                             |
| ---------------- | -------------------------------------------------- |
| API framework    | **FastAPI** (Python 3.12)                          |
| Database         | **PostgreSQL 16** (SQLAlchemy ORM)                 |
| Job queue        | **Celery + Redis**                                 |
| LLM              | **Gemini 1.5 Flash** (free tier) — graceful fallback when no key |
| Frontend         | **React 18 + Vite**, served by nginx               |
| Containerisation | **Docker + Docker Compose**                        |

The system runs **end-to-end with no LLM key**: if `GEMINI_API_KEY` is unset,
classification and the narrative summary use a deterministic heuristic so the
whole stack still works on `docker compose up` with zero spend. Set a key to use
the real LLM.

---

## Architecture

```
                        ┌───────────────────────────────────────────────┐
   Browser              │                  Docker network               │
  ┌────────┐  /api/*    │  ┌──────────┐  enqueue   ┌─────────┐          │
  │ React  │──────────► │  │ FastAPI  │ ─────────► │  Redis  │          │
  │  (nginx│ ◄──────────│  │   API    │            │ (broker)│          │
  │ :3000) │   JSON     │  └────┬─────┘            └────┬────┘          │
  └────────┘            │       │ write                 │ dequeue       │
                        │       ▼                       ▼               │
                        │  ┌──────────┐           ┌───────────┐         │
                        │  │ Postgres │ ◄──────── │  Celery   │ ──► LLM │
                        │  │  :5432   │  persist  │  worker   │ (Gemini)│
                        │  └──────────┘           └───────────┘         │
                        └───────────────────────────────────────────────┘
```

**Request lifecycle (upload):** `POST /api/jobs/upload` → API validates the CSV,
writes a `Job(status=pending)` row (raw CSV stored in the row), enqueues
`process_job(job_id)` on Redis, and returns `job_id` immediately. The Celery
worker dequeues, runs the pipeline (clean → detect anomalies → LLM classify →
LLM summarise), persists `Transaction` + `JobSummary` rows, and flips the job to
`completed`. The client polls `GET /api/jobs/{id}/status` until done, then reads
`GET /api/jobs/{id}/results`.

### Processing pipeline (worker)

1. **Clean** — dates → ISO 8601, strip `$` from amounts, uppercase `status`,
   normalise currency casing, fill blank categories with `Uncategorised`, remove
   exact duplicate rows.
2. **Anomaly detection** — flag amounts `> 3× the account's median`; flag `USD`
   charges on domestic-only merchants (Swiggy, Ola, IRCTC, Zomato, …).
3. **LLM classification** — only for rows with a blank category, sent in
   **batches** (not one call per row).
4. **LLM narrative summary** — a single call producing total spend by currency,
   top 3 merchants, anomaly count, a 2–3 sentence narrative, and `risk_level`.
5. **Retry logic** — each LLM call retries up to 3× with exponential backoff; on
   total failure the batch is marked `llm_failed` and the job continues (never
   fails the whole job).

### Data model

- **Job** — `id, filename, status, row_count_raw, row_count_clean, created_at, completed_at, error_message, raw_csv`
- **Transaction** — `id, job_id, txn_id, date, merchant, amount, currency, status, category, account_id, notes, is_anomaly, anomaly_reason, llm_category, llm_failed`
- **JobSummary** — `id, job_id, total_spend_inr, total_spend_usd, top_merchants, category_breakdown, anomaly_count, narrative, risk_level`

---

## Running it

### Prerequisites
- Docker + Docker Compose

### Start

```bash
# from the repo root
docker compose up --build
```

| Service   | URL                                |
| --------- | ---------------------------------- |
| Frontend  | http://localhost:3000              |
| API       | http://localhost:8000              |
| API docs  | http://localhost:8000/docs         |

### Use the real LLM

```bash
# Linux/macOS
export GEMINI_API_KEY=your_key_here
docker compose up --build

# Windows PowerShell
$env:GEMINI_API_KEY="your_key_here"; docker compose up --build
```

A sample file is provided at [`sample_data/transactions.csv`](sample_data/transactions.csv).

---

## API endpoints & example curl requests

### Upload a CSV
```bash
curl -X POST http://localhost:8000/jobs/upload \
  -F "file=@sample_data/transactions.csv"
# -> {"job_id": 1, "status": "pending", "message": "File accepted and queued for processing."}
```

### Poll job status
```bash
curl http://localhost:8000/jobs/1/status
# -> {"id":1,"status":"completed","row_count_raw":95,"row_count_clean":85,
#     "summary":{"total_spend_inr":...,"anomaly_count":10,"risk_level":"high",...}}
```

### Get full results
```bash
curl http://localhost:8000/jobs/1/results
# -> { transactions:[...], anomalies:[...], category_breakdown:{...}, summary:{...} }
```

### List jobs (with optional status filter)
```bash
curl http://localhost:8000/jobs
curl "http://localhost:8000/jobs?status=completed"
```

> The frontend calls these same endpoints via the `/api` prefix (nginx proxies
> `/api/*` → `api:8000`).

---

## What the sample data exercises

Running the included `transactions.csv` (95 rows) yields:
- **85 clean rows** after removing 10 exact duplicates
- **13 rows** with blank categories sent to the LLM (batched)
- **10 anomalies**: 5 USD-on-domestic-merchant (Zomato) + 5 statistical outliers
  (the `TXN200x` rows that are ~20× a normal amount)
- Mixed date formats (`DD-MM-YYYY`, `YYYY/MM/DD`, `YYYY-MM-DD`) all normalised to
  ISO 8601, and `$`-prefixed amounts cleaned.

---

## Scaling notes (100× traffic)

**Where it breaks first**
- **Raw CSV stored in the `jobs` row** — fine for ~90-row files, but at scale
  this bloats Postgres and inflates row reads. Move raw files to object storage
  (S3) and store only a key.
- **Synchronous LLM calls inside the worker** — the dominant latency. Batch
  sizes and provider rate limits become the bottleneck.
- **DB connection pool** — a fixed `pool_size` (10) saturates under many
  concurrent workers/API replicas.
- **`pandas` loads the whole file in memory** — large uploads pressure worker RAM.

**Next iteration**
- Horizontally scale API (stateless) behind a load balancer; scale Celery
  workers independently and route LLM-heavy work to a dedicated queue.
- Stream/chunk CSV parsing and bulk-insert transactions (`COPY`) instead of
  per-row inserts.
- Add a caching/dedupe layer for LLM classification (same merchant → same
  category) to cut LLM volume.
- Use PgBouncer for connection pooling; add read replicas for the results API.
- Add observability (structured logs, metrics, dead-letter queue for poison jobs).

---

## Local development (without Docker)

```bash
# Backend (needs a local Postgres + Redis)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
celery -A app.celery_app.celery_app worker --loglevel=info

# Frontend
cd frontend
npm install
npm run dev   # proxies /api -> http://localhost:8000
```
