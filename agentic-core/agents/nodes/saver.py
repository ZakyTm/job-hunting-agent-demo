# agentic-core/agents/nodes/saver.py
import os
import asyncio
import requests
from dotenv import load_dotenv

from core.logging import get_logger

log = get_logger(__name__)

load_dotenv()

# We need these to be set in .env
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
# Backend uses service_role to bypass RLS
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
# Fallback to anon key for backward compatibility
SUPABASE_KEY = SUPABASE_SERVICE_KEY or os.environ.get("SUPABASE_KEY", "")
# The user's UUID so they own the jobs
SUPABASE_USER_ID = os.environ.get("SUPABASE_USER_ID", None)


def saver_node(state) -> dict:
    """
    Saves the processed job to Supabase and determines status.
    If match score >= 7, sends a Telegram notification with Approve/Ignore buttons.
    """
    state_dict = state.model_dump() if hasattr(state, "model_dump") else (state.dict() if hasattr(state, "dict") else state)
    score = state_dict.get("match_score", 0)
    
    # Set status
    if score >= 7:
        status = "ready"
    elif score >= 5:
        status = "maybe"
    else:
        status = "ignored"
        
    updates = {"status": status}
    
    log.info("Saving job to Supabase", extra={
        "pipeline_step": "saver",
        "job_id": state_dict.get("job_id"),
        "job_title": state_dict.get("job_title"),
        "score": score,
        "status": status
    })
    
    # 1. Save to Supabase (using standard REST API)
    saved_id = None
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            url = f"{SUPABASE_URL}/rest/v1/jobs"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            }
            
            job_data = {
                "source": state_dict.get("source", "unknown"),
                "source_channel": state_dict.get("source_channel"),
                "job_title": state_dict.get("job_title"),
                "company_name": state_dict.get("company_name"),
                "contact_email": state_dict.get("contact_email"),
                "requirements": state_dict.get("requirements", []),
                "match_score": score,
                "match_reasoning": state_dict.get("match_reasoning"),
                "matched_skills": state_dict.get("matched_skills", []),
                "missing_skills": state_dict.get("missing_skills", []),
                "reasoning_trace": state_dict.get("reasoning_trace"),
                "company_intel": state_dict.get("company_intel"),
                "source_message_id": state_dict.get("source_message_id"),
                "status": status,
                "raw_text": state_dict.get("raw_text")
            }
            if SUPABASE_USER_ID:
                job_data["user_id"] = SUPABASE_USER_ID
            
            response = requests.post(url, headers=headers, json=job_data)
            
            if response.ok and response.json():
                saved_id = response.json()[0].get("id")
                updates["job_id"] = saved_id
                log.info("Saved to Supabase", extra={"job_id": saved_id, "pipeline_step": "saver"})
            else:
                log.error("Failed to save to Supabase", extra={"status_code": response.status_code, "text": response.text, "pipeline_step": "saver"})
        except Exception as e:
            log.error("Supabase error", extra={"pipeline_step": "saver"}, exc_info=True)
    else:
        log.warning("Skipped Supabase insert (missing credentials in .env)", extra={"pipeline_step": "saver"})

    # 2. Send Telegram notification for high matches (replaces n8n webhook)
    if status == "ready" and saved_id:
        try:
            from core.telegram_bot import notify_new_match

            notification_data = {
                "job_id": saved_id,
                "job_title": state_dict.get("job_title"),
                "company_name": state_dict.get("company_name"),
                "match_score": score,
                "match_reasoning": state_dict.get("match_reasoning"),
                "matched_skills": state_dict.get("matched_skills", []),
                "contact_email": state_dict.get("contact_email"),
                "company_intel": state_dict.get("company_intel"),
                "source_channel": state_dict.get("source_channel"),
            }

            # Run async notification in sync context
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # We're inside an async context — schedule as a task
                asyncio.ensure_future(notify_new_match(notification_data))
            else:
                # We're in a sync context — create a new event loop
                asyncio.run(notify_new_match(notification_data))

            log.info("Telegram notification dispatched", extra={"pipeline_step": "saver", "job_id": saved_id})

        except Exception as e:
            # Non-fatal: job is saved even if notification fails
            log.error("Telegram notification failed (job still saved)", extra={"pipeline_step": "saver"}, exc_info=True)

    return updates

