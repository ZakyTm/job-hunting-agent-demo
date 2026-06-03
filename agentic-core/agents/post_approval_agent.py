# agentic-core/agents/post_approval_agent.py
"""
Post-Approval Agent — LangGraph StateGraph for post-HITL processing.

This graph runs AFTER the user taps "Approve" on a Telegram notification.
It loads the job data from Supabase and runs:
  Tailor → Ghostwriter → Interviewer → PostSaver

Separate from the main pipeline (job_agent.py) to avoid re-running
Scanner/Matchmaker on already-processed jobs.
"""
import os
import requests
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

from agents.state import JobState
from agents.nodes.tailor import tailor_node
from agents.nodes.ghostwriter import ghostwriter_node
from agents.nodes.interviewer import interviewer_node
from agents.nodes.post_saver import post_saver_node
from core.logging import get_logger

log = get_logger(__name__)

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_KEY", "")


def _load_job_from_supabase(job_id: str) -> dict:
    """
    Fetch a job's full data from Supabase by its UUID.
    Returns a dict that can be used to initialize JobState.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Supabase not configured")

    url = f"{SUPABASE_URL}/rest/v1/jobs?id=eq.{job_id}&select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers)
    if not response.ok:
        raise RuntimeError(f"Supabase fetch failed: {response.status_code} — {response.text}")

    data = response.json()
    if not data:
        raise ValueError(f"Job {job_id} not found in Supabase")

    row = data[0]

    # Map Supabase row to JobState fields
    return {
        "job_id": row.get("id"),
        "raw_text": row.get("raw_text", ""),
        "source": row.get("source", "unknown"),
        "source_channel": row.get("source_channel"),
        "source_message_id": row.get("source_message_id"),
        "job_title": row.get("job_title"),
        "company_name": row.get("company_name"),
        "contact_email": row.get("contact_email"),
        "requirements": row.get("requirements") or [],
        "job_type": row.get("job_type"),
        "location": row.get("location"),
        "match_score": row.get("match_score"),
        "match_reasoning": row.get("match_reasoning"),
        "matched_skills": row.get("matched_skills") or [],
        "missing_skills": row.get("missing_skills") or [],
        "company_intel": row.get("company_intel"),
        "status": "approved",
    }


def build_post_approval_agent():
    """Construct and compile the post-approval LangGraph StateGraph."""
    graph = StateGraph(JobState)

    graph.add_node("tailor", tailor_node)
    graph.add_node("ghostwriter", ghostwriter_node)
    graph.add_node("interviewer", interviewer_node)
    graph.add_node("post_saver", post_saver_node)

    graph.set_entry_point("tailor")
    graph.add_edge("tailor", "ghostwriter")
    graph.add_edge("ghostwriter", "interviewer")
    graph.add_edge("interviewer", "post_saver")
    graph.add_edge("post_saver", END)

    return graph.compile()


# Module-level compiled agent
post_approval_agent = build_post_approval_agent()


def run_post_approval_pipeline(job_id: str) -> dict:
    """
    Main entry point for the post-approval pipeline.
    Called from main.py when a job is approved (via Telegram or API).

    1. Loads job data from Supabase
    2. Runs Tailor → Ghostwriter → Interviewer → PostSaver
    3. Returns the final state
    """
    log.info("Starting post-approval pipeline", extra={
        "job_id": job_id,
        "pipeline_step": "post_approval",
    })

    try:
        # Load job data from Supabase
        job_data = _load_job_from_supabase(job_id)

        log.info("Job data loaded from Supabase", extra={
            "job_id": job_id,
            "job_title": job_data.get("job_title"),
            "company": job_data.get("company_name"),
            "pipeline_step": "post_approval",
        })

        # Run the post-approval graph
        result = post_approval_agent.invoke(job_data)

        log.info("Post-approval pipeline completed", extra={
            "job_id": job_id,
            "has_cv": bool(result.get("tailored_cv_md")),
            "has_email": bool(result.get("draft_email")),
            "has_questions": bool(result.get("technical_questions")),
            "pipeline_step": "post_approval",
        })

        return result

    except Exception as e:
        log.error("Post-approval pipeline failed", extra={
            "job_id": job_id,
            "pipeline_step": "post_approval",
        }, exc_info=True)
        raise
