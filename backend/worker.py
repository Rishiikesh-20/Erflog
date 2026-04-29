"""
ARQ Worker — Async background job queue for Career Flow AI.

Replaces fragile cron jobs with a robust, Redis-backed async queue.

Usage:
    # Start the worker (from the backend/ directory):
    arq worker.WorkerSettings

    # Or programmatically enqueue a task:
    from worker import enqueue_market_scan
    await enqueue_market_scan()

Scheduled jobs:
    - Agent 2 (Market Intelligence): daily at 02:00 UTC
    - Agent 3 (Strategist):          daily at 03:00 UTC  (after Agent 2)
"""

import os
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

from arq import cron
from arq.connections import RedisSettings, create_pool

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [ARQ Worker] - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ARQWorker")

# =============================================================================
# REDIS CONFIGURATION
# =============================================================================

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


def get_redis_settings() -> RedisSettings:
    """Parse REDIS_URL into ARQ RedisSettings."""
    if REDIS_URL.startswith("redis://"):
        parsed = urlparse(REDIS_URL)
        database = 0
        if parsed.path and parsed.path != "/":
            try:
                database = int(parsed.path.lstrip("/"))
            except ValueError:
                database = 0
        return RedisSettings(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            database=database,
            username=parsed.username,
            password=parsed.password,
            ssl=parsed.scheme == "rediss",
        )
    return RedisSettings()


# =============================================================================
# TASK FUNCTIONS
# =============================================================================

async def run_market_scan(ctx: dict) -> dict:
    """
    Agent 2: Market Intelligence — daily scan.

    Collects jobs, hackathons, and news from all providers and stores
    them in Supabase + Pinecone.
    """
    logger.info("=" * 60)
    logger.info("🚀 Agent 2: Market Intelligence — Starting daily scan")
    logger.info(f"📅 {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    try:
        from agents.agent_2_market.service import MarketIntelligenceService

        service = MarketIntelligenceService()
        result = service.run_daily_scan()

        logger.info(f"✅ Market scan complete — status: {result.get('status')}")
        logger.info(f"   Jobs: {result.get('jobs_stored', 0)}  |  "
                     f"Hackathons: {result.get('hackathons_stored', 0)}  |  "
                     f"News: {result.get('news_stored', 0)}")
        return result

    except Exception as e:
        logger.error(f"❌ Market scan failed: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "failed", "error": str(e)}


async def run_strategist_matching(ctx: dict) -> dict:
    """
    Agent 3: Strategist — daily matching.

    For every user: fetches top jobs via Pinecone, generates roadmaps,
    generates application text, and stores results in today_data.
    """
    logger.info("=" * 60)
    logger.info("🚀 Agent 3: Strategist — Starting daily matching")
    logger.info(f"📅 {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    try:
        from agents.agent_3_strategist.service import get_strategist_service

        service = get_strategist_service()
        result = service.run_daily_matching()

        logger.info(f"✅ Strategist matching complete — status: {result.get('status')}")
        logger.info(f"   Users processed: {result.get('users_processed', 0)}  |  "
                     f"Users failed: {result.get('users_failed', 0)}")
        return result

    except Exception as e:
        logger.error(f"❌ Strategist matching failed: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "failed", "error": str(e)}


# =============================================================================
# ON-DEMAND ENQUEUE HELPERS  (call from FastAPI endpoints)
# =============================================================================

async def enqueue_market_scan():
    """Enqueue a market scan job to run immediately."""
    pool = await create_pool(get_redis_settings())
    job = await pool.enqueue_job("run_market_scan")
    logger.info(f"📤 Enqueued market scan: {job.job_id}")
    return job.job_id


async def enqueue_strategist_matching():
    """Enqueue a strategist matching job to run immediately."""
    pool = await create_pool(get_redis_settings())
    job = await pool.enqueue_job("run_strategist_matching")
    logger.info(f"📤 Enqueued strategist matching: {job.job_id}")
    return job.job_id


# =============================================================================
# WORKER SETTINGS  (arq picks this up automatically)
# =============================================================================

class WorkerSettings:
    """ARQ worker configuration.

    Start with:  ``arq worker.WorkerSettings``
    """

    # Task functions available for on-demand enqueue
    functions = [run_market_scan, run_strategist_matching]

    # Scheduled cron jobs
    cron_jobs = [
        # Agent 2: Market scan every day at 02:00 UTC
        cron(run_market_scan, hour=2, minute=0),

        # Agent 3: Strategist matching every day at 03:00 UTC
        # Runs after Agent 2 so the freshest jobs are available
        cron(run_strategist_matching, hour=3, minute=0),
    ]

    # Redis connection
    redis_settings = get_redis_settings()

    # Worker tuning
    max_jobs = 5
    job_timeout = 600  # 10 min per job
    keep_result = 3600  # keep results for 1 hour
