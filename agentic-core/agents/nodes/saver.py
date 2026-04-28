# agentic-core/agents/nodes/saver.py
import os
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

# Webhook for n8n notifications
# N8N_MODE can be 'prod' or 'test'. 
# In 'test' mode, we use the /webhook-test/ path so you can see it in the n8n editor.
N8N_MODE = os.environ.get("N8N_MODE", "prod").lower()
N8N_BASE_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/job-ready")

def get_n8n_url(url: str, mode: str) -> str:
    """
    Adjusts the n8n URL based on the mode.
    n8n v2 uses /webhook-test/ for manual test executions.
    """
    if mode == "test" and "/webhook/" in url:
        return url.replace("/webhook/", "/webhook-test/")
    return url

def saver_node(state: dict) -> dict:
    """
    Saves the processed job to Supabase and determines status.
    If match score >= 7, triggers an n8n webhook for desktop notification.
    """
    score = state.get("match_score", 0)
    
    # Set status
    if score >= 7:
        status = "ready"
    elif score >= 5:
        status = "maybe"
    else:
        status = "ignored"
        
    state["status"] = status
    
    log.info("Saving job to Supabase", extra={
        "pipeline_step": "saver",
        "job_id": state.get("job_id"),
        "job_title": state.get("job_title"),
        "score": score,
        "status": status
    })
    
    # 1. Save to Supabase (using standard REST API to avoid package build errors)
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
                "source": state.get("source", "unknown"),
                "source_channel": state.get("source_channel"),
                "job_title": state.get("job_title"),
                "company_name": state.get("company_name"),
                "contact_email": state.get("contact_email"),
                "requirements": state.get("requirements", []),
                "match_score": score,
                "match_reasoning": state.get("match_reasoning"),
                "matched_skills": state.get("matched_skills", []),
                "missing_skills": state.get("missing_skills", []),
                "reasoning_trace": state.get("reasoning_trace"),
                "company_intel": state.get("company_intel"),
                "source_message_id": state.get("source_message_id"),
                "status": status,
                "raw_text": state.get("raw_text")
            }
            if SUPABASE_USER_ID:
                job_data["user_id"] = SUPABASE_USER_ID
            
            response = requests.post(url, headers=headers, json=job_data)
            
            if response.ok and response.json():
                state["job_id"] = response.json()[0].get("id")
                log.info("Saved to Supabase", extra={"job_id": state["job_id"], "pipeline_step": "saver"})
            else:
                log.error("Failed to save to Supabase", extra={"status_code": response.status_code, "text": response.text, "pipeline_step": "saver"})
        except Exception as e:
            log.error("Supabase error", extra={"pipeline_step": "saver"}, exc_info=True)
    else:
        log.warning("Skipped Supabase insert (missing credentials in .env)", extra={"pipeline_step": "saver"})

    # 2. Trigger n8n webhook for high matches
    if status == "ready":
        try:
            target_url = get_n8n_url(N8N_BASE_WEBHOOK_URL, N8N_MODE)
            log.info("Triggering n8n notification", extra={"url": target_url, "mode": N8N_MODE, "pipeline_step": "saver"})
            
            payload = {
                "job_title": state.get("job_title"),
                "company_name": state.get("company_name"),
                "match_score": score,
                "match_reasoning": state.get("match_reasoning")
            }
            res = requests.post(target_url, json=payload, timeout=5)
            if res.ok:
                log.info("Notification webhook triggered", extra={"pipeline_step": "saver"})
            else:
                log.warning("Webhook failed", extra={"status_code": res.status_code, "pipeline_step": "saver"})
        except Exception as e:
            log.error("Webhook error", extra={"pipeline_step": "saver"}, exc_info=True)

    return state
