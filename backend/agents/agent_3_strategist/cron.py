# backend/agents/agent_3_strategist/cron.py

"""
Agent 3: Strategist - Cron Job Entry Point

Run this script daily to update all users' personalized data.
This is the ONLY time processing happens - after cron completion,
no further processing takes place until the next cron run.

The workflow:
1. Fetch all users from profiles table
2. For each user:
   - Get top 10 jobs, hackathons, news from Pinecone
   - For jobs with match < 80%: Generate learning roadmaps
   - For ALL jobs: Generate default application text
   - Store everything in today_data table (upsert)

Can be triggered via:
- Cron job: python -m agents.agent_3_strategist.cron
- FastAPI endpoint (admin only)
- Manual execution
"""

import asyncio
import logging
from datetime import datetime
from .service import get_strategist_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [Agent3Cron] - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Agent3Cron")


def run_daily_matching():
    """
    Synchronous wrapper for daily matching.
    Called by cron schedulers.
    
    This function:
    1. Processes all users in the system
    2. Generates roadmaps for jobs with match < 80%
    3. Generates application text for all jobs
    4. Stores everything in today_data table
    
    After this runs, no further processing needed until next cron run.
    """
    logger.info("=" * 70)
    logger.info("🚀 Agent 3 Cron Started")
    logger.info(f"📅 Timestamp: {datetime.now().isoformat()}")
    logger.info("=" * 70)
    logger.info("")
    logger.info("📋 Workflow:")
    logger.info("   1. Fetch top 10 jobs per user (vector similarity)")
    logger.info("   2. Jobs with match < 80% → Generate roadmap")
    logger.info("   3. ALL jobs → Generate application text")
    logger.info("   4. Store in today_data table")
    logger.info("")
    
    try:
        service = get_strategist_service()
        result = service.run_daily_matching()
        
        logger.info("")
        logger.info("=" * 70)
        logger.info(f"✅ Cron Complete: {result.get('status', 'unknown')}")
        logger.info(f"   Users Processed: {result.get('users_processed', 0)}")
        logger.info(f"   Users Failed: {result.get('users_failed', 0)}")
        logger.info("=" * 70)
        
        return result
    except Exception as e:
        logger.error(f"❌ Cron Failed: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "failed", "error": str(e)}


async def run_daily_matching_async():
    """
    Async wrapper for daily matching.
    Can be called from async contexts (e.g., FastAPI endpoints).
    """
    import concurrent.futures
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, run_daily_matching)
    return result


if __name__ == "__main__":
    # Direct execution
    result = run_daily_matching()
    print(f"\n📊 Final Result: {result}")
