"""FastAPI application entry point."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import jobs

logging.basicConfig(level=logging.INFO)

# Create tables on startup (small schema, no migration tool needed here).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI-Powered Transaction Processing Pipeline",
    version="1.0.0",
    description=(
        "Upload a CSV of raw transactions, process it asynchronously through a "
        "Celery/Redis job queue, classify + flag anomalies with an LLM, and "
        "retrieve a structured summary report via polling."
    ),
)

_origins = (
    ["*"]
    if settings.cors_origins.strip() == "*"
    else [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
