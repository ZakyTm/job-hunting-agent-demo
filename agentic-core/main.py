# agentic-core/main.py
"""
FastAPI entry point for the Job Hunting Agent.
Receives raw job posts and runs them through the LangGraph pipeline.
"""
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from agents.job_agent import agent
import subprocess
import os
import sys

app = FastAPI(
    title="Job Hunting Agent API",
    description="AI-powered job matching pipeline: Scanner → Matchmaker → routing",
    version="0.3.0",
)


from supabase import create_client, Client

# Initialize Supabase for duplicate checks
URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(URL, KEY)


class JobInput(BaseModel):
    """Payload from ingestion scripts (Telegram, Emplotic, etc.)."""
    raw_text: str
    source: str = "telegram"
    source_channel: str = "unknown"


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


@app.post("/process-job", response_model=JobOutput)
async def process_job(data: JobInput):
    """
    Main endpoint: receives a raw job post, runs it through
    Scanner → Matchmaker → routing → saver.
    """
    # --- SMART SKIP: Check if already in Supabase ---
    try:
        # Check for duplicate raw_text
        existing = supabase.table("jobs").select("id").eq("raw_text", data.raw_text).execute()
        if existing.data and len(existing.data) > 0:
            return JobOutput(status="skipped")
    except Exception as e:
        print(f"⚠️ Duplicate check failed (ignoring): {e}")

    # --- RUN PIPELINE ---
    result = agent.invoke({
        "raw_text": data.raw_text,
        "source": data.source,
        "source_channel": data.source_channel,
    })
    return JobOutput(**result)


@app.post("/trigger-ingestion")
def trigger_ingestion(background_tasks: BackgroundTasks):
    """
    Called by n8n to start the Telegram ingestion script.
    """
    def run_scraper():
        print("\n🚀 Starting background ingestion via n8n trigger...")
        # Use the new --days=7 and --limit=50 flags
        subprocess.Popen(
            [sys.executable, "ingest/ingest_telegram.py", "--mode=api", "--limit=100", "--days=7"],
            cwd=os.path.dirname(__file__)
        )
        
    background_tasks.add_task(run_scraper)
    return {"status": "ok"}


@app.get("/")
def read_root():
    return {
        "message": "Job Hunting Agent is running!",
        "version": "0.3.0",
        "pipeline": "Scanner → Matchmaker → routing → saver",
        "endpoints": {
            "POST /process-job": "Send raw job text for scoring",
            "GET /health": "Health check",
        },
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "pipeline_nodes": ["scanner", "matchmaker", "saver"]}
