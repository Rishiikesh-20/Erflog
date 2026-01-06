# backend/agents/agent_2_market/router.py

"""
Agent 2: Market Intelligence - API Router

Endpoints:
- POST /api/market/scan - User-triggered market scan (protected)
- POST /api/market/cron - Daily cron job execution (internal only)
- GET /api/market/stats - Get current market data statistics
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional
import os

from auth.dependencies import get_current_user
from .service import market_service

router = APIRouter(prefix="/api/market", tags=["Agent 2: Market Intelligence"])


# =============================================================================
# USER-TRIGGERED SCAN (Protected)
# =============================================================================

@router.post("/scan")
async def market_scan(user: dict = Depends(get_current_user)):
    """
    Run a market scan for the authenticated user.
    Returns jobs, hackathons, and news relevant to user's skills.
    """
    user_id = user["sub"]
    
    try:
        print(f"[Market Router] Running market scan for user: {user_id}")
        result = market_service.run_market_scan(user_id)
        
        return {
            "status": "success",
            "user_id": user_id,
            "data": result
        }
        
    except Exception as e:
        print(f"[Market Router] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Market scan failed: {str(e)}")


# =============================================================================
# CRON JOB ENDPOINT (Internal)
# =============================================================================

@router.post("/cron")
async def run_cron_job(x_cron_secret: Optional[str] = Header(None)):
    """
    Execute the daily market intelligence cron job.
    
    This endpoint should only be called by the cron scheduler.
    Protected by CRON_SECRET header for security.
    
    Headers:
        X-Cron-Secret: The secret key for cron job authentication
    """
    # Verify cron secret
    expected_secret = os.getenv("CRON_SECRET")
    
    if expected_secret and x_cron_secret != expected_secret:
        raise HTTPException(
            status_code=403, 
            detail="Invalid cron secret"
        )
    
    try:
        print("[Market Router] Executing daily cron job...")
        result = market_service.run_daily_scan()
        
        return {
            "status": result.get("status", "unknown"),
            "jobs_stored": result.get("jobs_stored", 0),
            "hackathons_stored": result.get("hackathons_stored", 0),
            "news_stored": result.get("news_stored", 0),
            "vectors_stored": result.get("vectors_stored", 0),
            "provider_errors": result.get("provider_errors", {}),
            "timestamp": result.get("timestamp")
        }
        
    except Exception as e:
        print(f"[Market Router] Cron job error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Cron job failed: {str(e)}"
        )


# =============================================================================
# STATISTICS ENDPOINT
# =============================================================================

@router.get("/stats")
async def get_market_stats():
    """
    Get current market data statistics.
    Returns counts of jobs, hackathons, and news in the database.
    """
    try:
        # Get job counts
        jobs_response = market_service.supabase.table("jobs").select(
            "id, type", count="exact"
        ).execute()
        
        job_count = 0
        hackathon_count = 0
        
        if jobs_response.data:
            for item in jobs_response.data:
                if item.get("type") == "job":
                    job_count += 1
                elif item.get("type") == "hackathon":
                    hackathon_count += 1
        
        # Get news count
        news_response = market_service.supabase.table("market_news").select(
            "id", count="exact"
        ).execute()
        
        news_count = len(news_response.data) if news_response.data else 0
        
        return {
            "status": "success",
            "stats": {
                "total_jobs": job_count,
                "total_hackathons": hackathon_count,
                "total_news": news_count,
                "total_items": job_count + hackathon_count + news_count
            }
        }
        
    except Exception as e:
        print(f"[Market Router] Stats error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get stats: {str(e)}"
        )