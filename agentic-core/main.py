# agentic-core/main.py
"""
FastAPI entry point for the Job Hunting Agent.
Receives raw job posts and runs them through the LangGraph pipeline.
"""
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from agents.job_agent import agent

app = FastAPI(
    title="Job Hunting Agent API",
    description="AI-powered job matching pipeline: Scanner → Matchmaker → routing",
    version="0.3.0",
)


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
    status: Optional[str] = None


@app.post("/process-job", response_model=JobOutput)
async def process_job(data: JobInput):
    """
    Main endpoint: receives a raw job post, runs it through
    Scanner → Matchmaker → routing → saver.
    Returns the full structured result.
    """
    result = agent.invoke({
        "raw_text": data.raw_text,
        "source": data.source,
        "source_channel": data.source_channel,
    })
    return JobOutput(**result)


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
