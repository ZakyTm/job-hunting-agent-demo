# agentic-core/agents/nodes/saver.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# We need these to be set in .env
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# Webhook for n8n notifications
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/job-ready")


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
    
    print(f"\n--- Saving job to Supabase ---")
    print(f"Title: {state.get('job_title')}")
    print(f"Score: {score}/10 -> {status.upper()}")
    
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
                "status": status,
                "raw_text": state.get("raw_text")
            }
            
            response = requests.post(url, headers=headers, json=job_data)
            
            if response.ok and response.json():
                state["job_id"] = response.json()[0].get("id")
                print(f"✅ Saved to Supabase! ID: {state['job_id']}")
            else:
                print(f"⚠️ Failed to save to Supabase: {response.status_code} {response.text}")
        except Exception as e:
            print(f"❌ Supabase error: {e}")
    else:
        print("⚠️ Skipped Supabase insert (missing credentials in .env)")

    # 2. Trigger n8n webhook for high matches
    if status == "ready":
        try:
            print(f"🔔 Triggering n8n notification webhook...")
            # We send minimal data to n8n just to trigger the toast
            payload = {
                "job_title": state.get("job_title"),
                "company_name": state.get("company_name"),
                "match_score": score,
                "match_reasoning": state.get("match_reasoning")
            }
            res = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=5)
            if res.ok:
                print(f"✅ Notification webhook triggered")
            else:
                print(f"⚠️ Webhook failed with status: {res.status_code}")
        except Exception as e:
            print(f"❌ Webhook error: {e}")

    return state
