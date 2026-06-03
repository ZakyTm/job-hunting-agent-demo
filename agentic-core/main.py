# agentic-core/main.py
"""
FastAPI entry point for the Job Hunting Agent.
Receives raw job posts, runs them through the LangGraph pipeline,
handles scheduled ingestion (replaces n8n cron), and
processes Telegram Bot HITL callbacks.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, Query, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

from agents.job_agent import agent
from core.logging import get_logger
from core.scheduler import setup_scheduler

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: start/stop APScheduler with the FastAPI app
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: launch scheduler. Shutdown: stop scheduler."""
    scheduler = setup_scheduler()
    scheduler.start()
    log.info("APScheduler started — Telegram ingestion scheduled")
    yield
    scheduler.shutdown(wait=False)
    log.info("APScheduler stopped")


app = FastAPI(
    title="Job Hunting Agent API",
    description="AI-powered job matching pipeline: Scanner → Matchmaker → routing → notification",
    version="0.4.0",
    lifespan=lifespan,
)


import requests as http_requests

# Supabase REST API config (no SDK needed — avoids pyiceberg build issues on Windows)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "")

def _supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def _supabase_query(table: str, select: str = "*", filters: dict = None, limit: int = 50, order: str = None):
    """Generic Supabase REST query helper."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?select={select}"
    if filters:
        for col, val in filters.items():
            url += f"&{col}=eq.{val}"
    if order:
        url += f"&order={order}"
    url += f"&limit={limit}"
    resp = http_requests.get(url, headers=_supabase_headers())
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------
class JobInput(BaseModel):
    """Payload from ingestion scripts (Telegram, Emplotic, etc.)."""
    raw_text: str
    source: str = "telegram"
    source_channel: str = "unknown"
    source_message_id: Optional[int] = None


class JobOutput(BaseModel):
    """Structured response after processing."""
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    contact_email: Optional[str] = None
    requirements: Optional[list[str]] = None
    job_type: Optional[str] = None
    location: Optional[str] = None
    match_score: Optional[int] = None
    match_reasoning: Optional[str] = None
    matched_skills: Optional[list[str]] = None
    missing_skills: Optional[list[str]] = None
    status: Optional[str] = "processed"


# ---------------------------------------------------------------------------
# Core Pipeline Endpoint
# ---------------------------------------------------------------------------
@app.post("/process-job", response_model=JobOutput)
async def process_job(data: JobInput):
    """
    Main endpoint: receives a raw job post, runs it through
    Scanner → Matchmaker → routing → saver → Telegram notification.
    """
    # --- SMART SKIP: Check if already in Supabase ---
    try:
        # Use REST API directly to check for existing raw_text
        import urllib.parse
        check_url = f"{SUPABASE_URL}/rest/v1/jobs?select=id&raw_text=eq.{urllib.parse.quote(data.raw_text[:200])}"
        check_resp = http_requests.get(check_url, headers=_supabase_headers())
        if check_resp.ok and check_resp.json():
            log.info("Duplicate job skipped", extra={"reason": "raw_text_match"})
            return JobOutput(status="skipped")
    except Exception as e:
        log.error("Duplicate check failed (ignoring)", exc_info=True)

    # --- RUN PIPELINE ---
    result = agent.invoke({
        "raw_text": data.raw_text,
        "source": data.source,
        "source_channel": data.source_channel,
        "source_message_id": data.source_message_id,
    })
    return JobOutput(**result)


# ---------------------------------------------------------------------------
# Telegram Bot Webhook — HITL callback handler
# ---------------------------------------------------------------------------
@app.post("/webhook/telegram")
async def telegram_webhook(update: dict, background_tasks: BackgroundTasks):
    """
    Receives Telegram Bot updates (callback queries from inline buttons).
    Processes Approve/Ignore actions and triggers post-approval pipeline.
    """
    callback_query = update.get("callback_query")
    if not callback_query:
        return {"status": "no_callback"}

    callback_data = callback_query.get("data", "")
    callback_id = callback_query.get("id", "")

    from core.telegram_bot import handle_telegram_callback
    result = await handle_telegram_callback(callback_data)

    # If approved, trigger post-approval pipeline in background
    if result["action"] == "approve" and result["success"]:
        background_tasks.add_task(_run_post_approval, result["job_id"])

    # Answer the callback to remove the "loading" spinner in Telegram
    try:
        from telegram import Bot
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if bot_token and callback_id:
            bot = Bot(token=bot_token)
            action_text = "✅ Approved! Generating CV, email & Q&A..." if result["action"] == "approve" else "❌ Ignored."
            await bot.answer_callback_query(callback_id, text=action_text)
    except Exception as e:
        log.error("Failed to answer Telegram callback", exc_info=True)

    return {"status": "processed", **result}


def _run_post_approval(job_id: str):
    """
    Background task: runs Tailor → Ghostwriter → Interviewer for an approved job.
    Loads job data from Supabase, runs the post-approval graph, updates the row.
    """
    try:
        from agents.post_approval_agent import run_post_approval_pipeline
        run_post_approval_pipeline(job_id)
        log.info("Post-approval pipeline completed", extra={"job_id": job_id})
    except Exception as e:
        log.error("Post-approval pipeline failed", extra={"job_id": job_id}, exc_info=True)


# ---------------------------------------------------------------------------
# Job Listing Endpoint (prep for dashboard)
# ---------------------------------------------------------------------------
@app.get("/jobs")
def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status: ready, maybe, ignored, approved"),
    min_score: Optional[int] = Query(None, ge=1, le=10, description="Minimum match score"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
):
    """List jobs from Supabase with optional filtering."""
    try:
        url = f"{SUPABASE_URL}/rest/v1/jobs?select=*&order=created_at.desc&limit={limit}"
        if status:
            url += f"&status=eq.{status}"
        if min_score:
            url += f"&match_score=gte.{min_score}"
        resp = http_requests.get(url, headers=_supabase_headers())
        resp.raise_for_status()
        data = resp.json()
        return {"jobs": data, "count": len(data)}
    except Exception as e:
        log.error("Failed to list jobs", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch jobs")


# ---------------------------------------------------------------------------
# Manual Approval Endpoint
# ---------------------------------------------------------------------------
@app.post("/jobs/{job_id}/approve")
async def approve_job(job_id: str, background_tasks: BackgroundTasks):
    """
    Manually approve a job and trigger the post-approval pipeline.
    Alternative to the Telegram Approve button.
    """
    from core.telegram_bot import update_job_status_in_supabase
    success = await update_job_status_in_supabase(job_id, "approved")

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update job status")

    background_tasks.add_task(_run_post_approval, job_id)
    return {"status": "approved", "job_id": job_id, "message": "Post-approval pipeline started in background"}


# ---------------------------------------------------------------------------
# Standard Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
def read_root():
    return {
        "message": "Job Hunting Agent is running!",
        "version": "0.4.0",
        "pipeline": "Scanner → Matchmaker → Researcher → Saver → Telegram",
        "post_approval": "Tailor → Ghostwriter → Interviewer",
        "endpoints": {
            "POST /process-job": "Send raw job text for scoring",
            "POST /webhook/telegram": "Telegram Bot callback handler",
            "GET /jobs": "List jobs with filtering",
            "POST /jobs/{id}/approve": "Manually approve a job",
            "GET /health": "Health check",
        },
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "pipeline_nodes": ["scanner", "matchmaker", "researcher", "saver"],
        "post_approval_nodes": ["tailor", "ghostwriter", "interviewer"],
    }


@app.get("/processed-ids")
def get_processed_ids(source_channel: str):
    """Returns a list of source_message_ids already processed for a channel."""
    try:
        import urllib.parse
        url = f"{SUPABASE_URL}/rest/v1/jobs?select=source_message_id&source_channel=eq.{urllib.parse.quote(source_channel)}"
        resp = http_requests.get(url, headers=_supabase_headers())
        resp.raise_for_status()
        data = resp.json()
        ids = [row["source_message_id"] for row in data if row.get("source_message_id") is not None]
        return {"processed_ids": ids}
    except Exception as e:
        log.error("Failed to fetch processed ids", exc_info=True)
        return {"processed_ids": []}
