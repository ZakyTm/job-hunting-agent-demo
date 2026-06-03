# agentic-core/core/scheduler.py
"""
Native Scheduler — Replaces n8n cron workflows.
Uses APScheduler to periodically trigger Telegram ingestion.
"""
import os
import sys
import subprocess
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from core.logging import get_logger

log = get_logger(__name__)

# How often to scrape Telegram channels (in hours)
SCRAPE_INTERVAL_HOURS = int(os.environ.get("SCRAPE_INTERVAL_HOURS", "2"))


def run_telegram_ingestion():
    """
    Run the Telegram ingestion script as a subprocess.
    This is the equivalent of n8n's "Execute Command" node.
    """
    log.info("Scheduled ingestion triggered", extra={
        "pipeline_step": "scheduler",
        "interval_hours": SCRAPE_INTERVAL_HOURS,
    })

    try:
        # Run ingestion in API mode (sends jobs to FastAPI pipeline)
        result = subprocess.Popen(
            [sys.executable, "ingest/ingest_telegram.py", "--mode=api", "--limit=100", "--days=1"],
            cwd=os.path.dirname(os.path.dirname(__file__)),  # agentic-core/
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        log.info("Ingestion subprocess started", extra={
            "pid": result.pid,
            "pipeline_step": "scheduler",
        })
    except Exception as e:
        log.error("Failed to start ingestion subprocess", exc_info=True)


def setup_scheduler() -> AsyncIOScheduler:
    """
    Create and configure the APScheduler instance.
    Call scheduler.start() after FastAPI startup.

    Returns:
        Configured AsyncIOScheduler (not yet started).
    """
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        run_telegram_ingestion,
        trigger=IntervalTrigger(hours=SCRAPE_INTERVAL_HOURS),
        id="telegram_ingestion",
        name="Telegram Channel Scraper",
        replace_existing=True,
        max_instances=1,  # Don't overlap runs
    )

    log.info("Scheduler configured", extra={
        "job": "telegram_ingestion",
        "interval_hours": SCRAPE_INTERVAL_HOURS,
    })

    return scheduler
