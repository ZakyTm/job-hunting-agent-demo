# agentic-core/core/telegram_bot.py
"""
Telegram Bot — Notifications + HITL (Human-In-The-Loop).
Replaces n8n webhook notifications with native Telegram Bot API.

Setup:
  1. Message @BotFather on Telegram → /newbot → get token
  2. Add TELEGRAM_BOT_TOKEN to .env
  3. Send /start to your bot, then add your user ID as TELEGRAM_CHAT_ID in .env
     (Get your ID by messaging @userinfobot)
"""
import os
import asyncio
from dotenv import load_dotenv
from core.logging import get_logger

log = get_logger(__name__)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


async def notify_new_match(job_data: dict) -> bool:
    """
    Send a rich notification to the user's Telegram chat for a high-scoring job.
    Includes inline Approve/Ignore buttons for HITL.

    Args:
        job_data: dict with keys: job_id, job_title, company_name, match_score,
                  match_reasoning, matched_skills, company_intel, contact_email

    Returns:
        True if message was sent successfully, False otherwise.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("Telegram bot not configured (missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID)")
        return False

    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot

        bot = Bot(token=TELEGRAM_BOT_TOKEN)

        job_id = job_data.get("job_id", "unknown")
        title = job_data.get("job_title", "Unknown Position")
        company = job_data.get("company_name", "Unknown Company")
        score = job_data.get("match_score", 0)
        reasoning = job_data.get("match_reasoning", "No reasoning available.")
        matched = job_data.get("matched_skills", [])
        email = job_data.get("contact_email", "N/A")
        company_intel = job_data.get("company_intel") or {}

        # Build the notification message
        matched_str = ", ".join(matched[:5]) if matched else "N/A"
        talking_point = company_intel.get("talking_point", "")
        tech_stack = ", ".join(company_intel.get("tech_stack", [])[:4])

        message = (
            f"🟢 *NEW MATCH: {_escape_md(title)}*\n"
            f"🏢 {_escape_md(company)} — Score: *{score}/10*\n"
            f"\n"
            f"📋 *Reasoning:* {_escape_md(reasoning[:300])}\n"
            f"\n"
            f"✅ *Matched Skills:* {_escape_md(matched_str)}\n"
            f"📧 *Contact:* {_escape_md(email)}\n"
        )

        if talking_point:
            message += f"\n💡 *Intel:* {_escape_md(talking_point[:200])}\n"
        if tech_stack:
            message += f"🔧 *Stack:* {_escape_md(tech_stack)}\n"

        # Inline keyboard: Approve / Ignore
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve:{job_id}"),
                InlineKeyboardButton("❌ Ignore", callback_data=f"ignore:{job_id}"),
            ]
        ])

        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

        log.info("Telegram notification sent", extra={
            "job_id": job_id,
            "job_title": title,
            "score": score,
        })
        return True

    except Exception as e:
        log.error("Failed to send Telegram notification", exc_info=True)
        return False


async def update_job_status_in_supabase(job_id: str, new_status: str) -> bool:
    """
    Update the status of a job in Supabase.

    Args:
        job_id: The UUID of the job row.
        new_status: 'approved' or 'ignored_by_user'.
    """
    import requests

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_KEY", "")

    if not supabase_url or not supabase_key:
        log.error("Cannot update Supabase — missing credentials")
        return False

    try:
        url = f"{supabase_url}/rest/v1/jobs?id=eq.{job_id}"
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        response = requests.patch(url, headers=headers, json={"status": new_status})

        if response.ok:
            log.info("Supabase status updated", extra={"job_id": job_id, "status": new_status})
            return True
        else:
            log.error("Supabase update failed", extra={
                "job_id": job_id,
                "status_code": response.status_code,
                "text": response.text,
            })
            return False
    except Exception as e:
        log.error("Supabase update error", exc_info=True)
        return False


async def handle_telegram_callback(callback_data: str) -> dict:
    """
    Process an inline keyboard callback from Telegram.

    Args:
        callback_data: String like 'approve:uuid' or 'ignore:uuid'

    Returns:
        dict with 'action', 'job_id', and 'success' keys.
    """
    parts = callback_data.split(":", 1)
    if len(parts) != 2:
        return {"action": "unknown", "job_id": None, "success": False}

    action, job_id = parts

    if action == "approve":
        success = await update_job_status_in_supabase(job_id, "approved")
        return {"action": "approve", "job_id": job_id, "success": success}

    elif action == "ignore":
        success = await update_job_status_in_supabase(job_id, "ignored_by_user")
        return {"action": "ignore", "job_id": job_id, "success": success}

    return {"action": action, "job_id": job_id, "success": False}


def _escape_md(text: str) -> str:
    """Escape special Markdown characters for Telegram."""
    if not text:
        return ""
    # In Markdown mode, only _ * [ ] need escaping
    for char in ["_", "*", "[", "]", "`"]:
        text = text.replace(char, f"\\{char}")
    return text
