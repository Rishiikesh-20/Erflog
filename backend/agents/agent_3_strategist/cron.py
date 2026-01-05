# backend/agents/agent_3_strategist/cron.py

"""
Agent 3: Strategist - Cron Job Entry Point

Run this script daily to update all users' personalized data.
Can be triggered via:
- Cron job: python -m agents.agent_3_strategist.cron
- FastAPI endpoint (admin only)
- Manual execution
"""

import asyncio
import logging
from datetime import datetime
from .service import get_strategist_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Agent3Cron")


def run_daily_matching():
    """
    Synchronous wrapper for daily matching.
    Called by cron schedulers.
    """
    logger.info(f"🚀 Agent 3 Cron Started at {datetime.now().isoformat()}")
    
    try:
        service = get_strategist_service()
        result = service.run_daily_matching()
        
        logger.info(f"✅ Cron Complete: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Cron Failed: {e}")
        return {"status": "failed", "error": str(e)}


async def run_daily_matching_async():
    """
    Async wrapper for daily matching.
    Can be called from async contexts.
    """
    # Run in thread pool to not block
    import concurrent.futures
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, run_daily_matching)
    return result


if __name__ == "__main__":
    # Direct execution
    result = run_daily_matching()
    print(f"Result: {result}")
