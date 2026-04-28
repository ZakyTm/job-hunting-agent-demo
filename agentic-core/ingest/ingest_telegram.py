# agentic-core/ingest/ingest_telegram.py
"""
Telegram Ingestion Script — v2.0
Pulls job posts from subscribed channels and sends them to the FastAPI pipeline.

Modes:
  --mode=print    → Just prints job posts (default, for testing)
  --mode=api      → Sends each job post to POST http://localhost:8000/process-job

Run: python ingest/ingest_telegram.py --mode=api
"""
import os
import sys
import asyncio
import argparse
from dotenv import load_dotenv
from telethon import TelegramClient

from core.logging import get_logger

log = get_logger(__name__)

# For API mode: POST to FastAPI
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

load_dotenv()

api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")
phone_number = os.getenv("TELEGRAM_PHONE")

FASTAPI_URL = "http://localhost:8000/process-job"

# Your job channels
CHANNELS = [
    "@ITR213",
    "@rcrdz1",
    "@TechJobsOccean",
]

JOB_KEYWORDS = [
    "hiring", "job", "position", "apply", "opportunity",
    "remote", "engineer", "developer", "AI", "recrut",
    "poste", "emploi", "candidature",  # French keywords
    "مطلوب", "توظيف", "عمل",  # Arabic keywords
]


async def send_to_pipeline(raw_text: str, channel: str, msg_id: int) -> dict | None:
    """POST a job post to the FastAPI pipeline and return the result."""
    if not HAS_HTTPX:
        print("  ⚠️ httpx not installed. Run: pip install httpx")
        return None

    payload = {
        "raw_text": raw_text,
        "source": "telegram",
        "source_channel": channel,
        "source_message_id": msg_id,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(FASTAPI_URL, json=payload)
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"  ⚠️ API returned {resp.status_code}: {resp.text[:200]}")
                return None
        except httpx.ConnectError:
            print(f"  ❌ Cannot connect to {FASTAPI_URL} — is FastAPI running?")
            return None
        except Exception as e:
            print(f"  ❌ API error: {e}")
            return None


async def main(mode: str = "print", limit: int = 50, days: int = 7):
    client = TelegramClient("job_agent_session", api_id, api_hash)
    await client.start(phone=phone_number)
    print(f"✅ Connected to Telegram! (Scanning last {days} days)\n")

    from datetime import datetime, timedelta, timezone
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    total_found = 0
    total_high = 0

    for channel in CHANNELS:
        print(f"\n{'='*60}")
        print(f"📢 Channel: {channel}")
        print(f"{'='*60}")

        # Fetch processed IDs for deduplication
        processed_ids = set()
        if HAS_HTTPX and mode == "api":
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(f"{FASTAPI_URL.replace('/process-job', '/processed-ids')}?source_channel={channel}")
                    if resp.status_code == 200:
                        data = resp.json()
                        processed_ids = set(data.get("processed_ids", []))
            except Exception as e:
                log.error("Failed to fetch processed IDs", extra={"channel": channel}, exc_info=True)

        try:
            entity = await client.get_entity(channel)
            # Fetch a larger batch but stop when we hit the date limit
            messages = await client.get_messages(entity, limit=limit)

            job_count = 0
            for msg in messages:
                # Stop if message is older than cutoff
                if msg.date < cutoff_date:
                    print(f"   ⏱️ Reached date limit ({msg.date.date()}). Stopping channel.")
                    break

                if msg.id in processed_ids:
                    log.info("Skipping already processed message", extra={
                        "pipeline_step": "ingestion_dedup",
                        "source_message_id": msg.id,
                        "channel": channel
                    })
                    continue

                if msg.text:
                    text_lower = msg.text.lower()
                    if any(kw.lower() in text_lower for kw in JOB_KEYWORDS):
                        job_count += 1
                        total_found += 1

                        if mode == "print":
                            print(f"\n🟢 JOB POST FOUND (msg #{msg.id}):")
                            print(f"   Date: {msg.date}")
                            print(f"   Preview: {msg.text[:200]}...")
                            print()

                        elif mode == "api":
                            print(f"\n📤 Sending msg #{msg.id} ({msg.date.date()}) to pipeline...")
                            result = await send_to_pipeline(msg.text, channel, msg.id)
                            if result:
                                status = result.get("status", "processed")
                                if status == "skipped":
                                    print(f"   ⏭️ Already processed. Skipping LLM.")
                                    continue

                                score = result.get("match_score", 0)
                                title = result.get("job_title", "?")

                                if score >= 6:
                                    emoji = "🟢"
                                    total_high += 1
                                elif score >= 4:
                                    emoji = "🟡"
                                else:
                                    emoji = "🔴"

                                print(f"   {emoji} {title} → {score}/10")
                                print(f"   Email: {result.get('contact_email', 'N/A')}")

            if job_count == 0:
                print("   ⚪ No new job-related messages in this window")

        except Exception as e:
            print(f"   ❌ Error reading {channel}: {e}")

    await client.disconnect()

    # Summary
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY: {total_found} posts analyzed in last {days} days")
    if mode == "api":
        print(f"   🟢 High matches (6+): {total_high}")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Telegram Job Ingestion")
    parser.add_argument("--mode", choices=["print", "api"], default="print",
                        help="'print' to just display, 'api' to send to FastAPI pipeline")
    parser.add_argument("--limit", type=int, default=50,
                        help="Number of messages to fetch per channel (default: 50)")
    parser.add_argument("--days", type=int, default=7,
                        help="Only scan messages from the last X days (default: 7)")
    args = parser.parse_args()

    asyncio.run(main(mode=args.mode, limit=args.limit, days=args.days))
