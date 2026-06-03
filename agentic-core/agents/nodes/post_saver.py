# agentic-core/agents/nodes/post_saver.py
"""
Post-Approval Saver — Updates the existing Supabase job row with
Tailor, Ghostwriter, and Interviewer outputs.

Unlike saver.py which INSERT a new row, this node PATCHes an existing one.
"""
import os
import requests
from dotenv import load_dotenv

from core.logging import get_logger

log = get_logger(__name__)

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_KEY", "")


def post_saver_node(state) -> dict:
    """
    Updates the existing Supabase row with post-approval pipeline outputs.
    """
    state_dict = state if isinstance(state, dict) else (state.model_dump() if hasattr(state, "model_dump") else state)

    job_id = state_dict.get("job_id")
    if not job_id:
        log.error("No job_id in state — cannot update Supabase", extra={"pipeline_step": "post_saver"})
        return {"error": "Missing job_id"}

    if not SUPABASE_URL or not SUPABASE_KEY:
        log.warning("Supabase not configured, skipping post-save", extra={"pipeline_step": "post_saver"})
        return {}

    update_data = {
        "status": "completed",
        "tailored_cv_md": state_dict.get("tailored_cv_md"),
        "tailored_cv_path": state_dict.get("tailored_cv_path"),
        "tailored_cv_diff": state_dict.get("tailored_cv_diff"),
        "draft_email": state_dict.get("draft_email"),
        "email_subject": state_dict.get("email_subject"),
        "technical_questions": state_dict.get("technical_questions"),
        "behavioral_questions": state_dict.get("behavioral_questions"),
        "questions_to_ask": state_dict.get("questions_to_ask"),
        "skill_gap_answers": state_dict.get("skill_gap_answers"),
    }

    # Remove None values to avoid overwriting with null
    update_data = {k: v for k, v in update_data.items() if v is not None}

    try:
        url = f"{SUPABASE_URL}/rest/v1/jobs?id=eq.{job_id}"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

        response = requests.patch(url, headers=headers, json=update_data)

        if response.ok:
            log.info("Post-approval results saved to Supabase", extra={
                "pipeline_step": "post_saver",
                "job_id": job_id,
                "fields_updated": list(update_data.keys()),
            })
            return {"status": "completed"}
        else:
            log.error("Post-save Supabase update failed", extra={
                "pipeline_step": "post_saver",
                "job_id": job_id,
                "status_code": response.status_code,
                "text": response.text,
            })
            return {"error": f"Supabase update failed: {response.status_code}"}

    except Exception as e:
        log.error("Post-save error", extra={"pipeline_step": "post_saver"}, exc_info=True)
        return {"error": f"Post-save error: {str(e)}"}
