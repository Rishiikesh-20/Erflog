# backend/agents/agent_3_strategist/router.py

"""
Agent 3: Strategist - API Endpoints

Provides endpoints for:
- GET /api/strategist/today - Get user's personalized today_data
- GET /api/strategist/jobs - Get all 10 matched jobs
- GET /api/strategist/hackathons - Get all 10 matched hackathons
- GET /api/strategist/dashboard - Get dashboard summary (5 jobs, 2 hackathons, 2 news)
- POST /api/strategist/refresh - Trigger manual refresh for a user
- POST /api/strategist/cron - Trigger daily cron (requires CRON_SECRET)
"""

import os
from fastapi import APIRouter, HTTPException, Depends, Header, BackgroundTasks
from auth.dependencies import get_current_user
from .service import get_strategist_service

router = APIRouter(prefix="/api/strategist", tags=["Agent 3: Strategist"])

# Cron secret for secure cron endpoint
CRON_SECRET = os.getenv("CRON_SECRET")


@router.get("/today")
async def get_today_data(user: dict = Depends(get_current_user)):
    """
    Get the current user's complete today_data.
    Contains all matched jobs, hackathons, and news.
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")
    
    service = get_strategist_service()
    data = service.get_user_today_data(user_id)
    
    if not data:
        # No data yet - generate on-demand
        result = service.process_single_user(user_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return {
            "status": "success",
            "data": result,
            "fresh": True
        }
    
    return {
        "status": "success",
        "data": data["data"],
        "updated_at": data["updated_at"],
        "fresh": False
    }


@router.get("/jobs")
async def get_today_jobs(user: dict = Depends(get_current_user)):
    """
    Get all 10 matched jobs for the current user.
    Each job includes:
    - Basic info (title, company, score, etc.)
    - roadmap: Learning roadmap (only for jobs with match < 80%)
    - application_text: Pre-generated application text
    - needs_improvement: Boolean indicating if roadmap was generated
    
    Used by the Jobs page.
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")
    
    service = get_strategist_service()
    data = service.get_user_today_data(user_id)
    
    if not data:
        # Generate on-demand
        result = service.process_single_user(user_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        jobs = result.get("jobs", [])
    else:
        jobs = data["data"].get("jobs", [])
    
    return {
        "status": "success",
        "jobs": jobs,
        "count": len(jobs),
        "stats": {
            "high_match": sum(1 for j in jobs if not j.get("needs_improvement")),
            "needs_improvement": sum(1 for j in jobs if j.get("needs_improvement")),
            "with_roadmap": sum(1 for j in jobs if j.get("roadmap"))
        }
    }


@router.get("/jobs/{job_id}/roadmap")
async def get_job_roadmap(job_id: str, user: dict = Depends(get_current_user)):
    """
    Get the learning roadmap for a specific job.
    Returns the roadmap graph with nodes, edges, and resources.
    
    Only available for jobs with match < 80%.
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")
    
    service = get_strategist_service()
    data = service.get_user_today_data(user_id)
    
    if not data:
        raise HTTPException(status_code=404, detail="No data found. Please refresh first.")
    
    jobs = data["data"].get("jobs", [])
    
    # Find the job
    job = next((j for j in jobs if str(j.get("id")) == str(job_id)), None)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    roadmap = job.get("roadmap")
    
    if not roadmap:
        return {
            "status": "success",
            "message": "No roadmap needed - high match (>= 80%)",
            "job": {
                "id": job.get("id"),
                "title": job.get("title"),
                "company": job.get("company"),
                "score": job.get("score")
            },
            "roadmap": None
        }
    
    return {
        "status": "success",
        "job": {
            "id": job.get("id"),
            "title": job.get("title"),
            "company": job.get("company"),
            "score": job.get("score")
        },
        "roadmap": roadmap
    }


@router.get("/jobs/{job_id}/application")
async def get_job_application_text(job_id: str, user: dict = Depends(get_current_user)):
    """
    Get pre-generated application text for a specific job.
    Returns copy-paste ready responses for common application questions.
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")
    
    service = get_strategist_service()
    data = service.get_user_today_data(user_id)
    
    if not data:
        raise HTTPException(status_code=404, detail="No data found. Please refresh first.")
    
    jobs = data["data"].get("jobs", [])
    
    # Find the job
    job = next((j for j in jobs if str(j.get("id")) == str(job_id)), None)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    application_text = job.get("application_text", {})
    
    return {
        "status": "success",
        "job": {
            "id": job.get("id"),
            "title": job.get("title"),
            "company": job.get("company"),
            "score": job.get("score")
        },
        "application_text": application_text
    }


@router.get("/hackathons")
async def get_today_hackathons(user: dict = Depends(get_current_user)):
    """
    Get all 10 matched hackathons for the current user.
    Used by the Hackathons page.
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")
    
    service = get_strategist_service()
    data = service.get_user_today_data(user_id)
    
    if not data:
        # Generate on-demand
        result = service.process_single_user(user_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        hackathons = result.get("hackathons", [])
    else:
        hackathons = data["data"].get("hackathons", [])
    
    return {
        "status": "success",
        "hackathons": hackathons,
        "count": len(hackathons)
    }


@router.get("/dashboard")
async def get_dashboard_data(user: dict = Depends(get_current_user)):
    """
    Get dashboard summary data.
    Returns: top 5 jobs, top 2 hackathons, top 2 news.
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")
    
    service = get_strategist_service()
    data = service.get_user_today_data(user_id)
    
    if not data:
        # Generate on-demand
        result = service.process_single_user(user_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        all_data = result
    else:
        all_data = data["data"]
    
    # Slice for dashboard
    return {
        "status": "success",
        "jobs": all_data.get("jobs", [])[:5],
        "hackathons": all_data.get("hackathons", [])[:2],
        "news": all_data.get("news", [])[:2],
        "updated_at": data["updated_at"] if data else all_data.get("generated_at")
    }


@router.post("/refresh")
async def refresh_user_data(user: dict = Depends(get_current_user)):
    """
    Manually trigger a refresh of user's today_data.
    Replaces existing data with fresh matches.
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")
    
    service = get_strategist_service()
    result = service.process_single_user(user_id)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return {
        "status": "success",
        "message": "Data refreshed successfully",
        "stats": result.get("stats", {})
    }


@router.post("/cron")
async def run_daily_cron(
    x_cron_secret: str = Header(None, alias="X-Cron-Secret")
):
    """
    Trigger daily matching cron job for all users.
    Requires X-Cron-Secret header matching CRON_SECRET env var.
    
    This endpoint should be called by external cron service (e.g., Vercel Cron, Railway Cron).
    """
    # Validate cron secret
    if not CRON_SECRET:
        raise HTTPException(
            status_code=500, 
            detail="CRON_SECRET not configured on server"
        )
    
    if x_cron_secret != CRON_SECRET:
        raise HTTPException(
            status_code=401, 
            detail="Invalid or missing X-Cron-Secret header"
        )
    
    # Run the daily matching
    service = get_strategist_service()
    result = service.run_daily_matching()
    
    return {
        "status": result.get("status", "unknown"),
        "users_processed": result.get("users_processed", 0),
        "users_failed": result.get("users_failed", 0),
        "timestamp": result.get("timestamp")
    }


@router.post("/cold-start")
async def trigger_cold_start(
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """
    Trigger cold start processing for a newly onboarded user.
    Runs the full Strategist pipeline (jobs, hackathons, news, roadmaps) for this user only.
    
    This endpoint is called after onboarding completion to immediately populate
    the user's personalized data instead of waiting for the 2AM cron job.
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")
    
    service = get_strategist_service()
    
    # Run in background so user doesn't have to wait for full processing
    background_tasks.add_task(service.process_single_user, user_id)
    
    return {
        "status": "processing",
        "message": "Generating your personalized data. This may take 30-60 seconds.",
        "user_id": user_id
    }


@router.post("/cron/notifications")
async def run_daily_notifications(
    x_cron_secret: str = Header(None, alias="X-Cron-Secret")
):
    """
    Trigger daily email notification cron job for all users.
    Sends personalized digest emails with top jobs, hackathons, and news.
    
    Requires X-Cron-Secret header matching CRON_SECRET env var.
    """
    from .notifications import get_notification_service
    
    # Validate cron secret
    if not CRON_SECRET:
        raise HTTPException(
            status_code=500, 
            detail="CRON_SECRET not configured on server"
        )
    
    if x_cron_secret != CRON_SECRET:
        raise HTTPException(
            status_code=401, 
            detail="Invalid or missing X-Cron-Secret header"
        )
    
    # Run the daily notifications
    notification_service = get_notification_service()
    result = notification_service.run_daily_notifications()
    
    return {
        "status": result.get("status", "unknown"),
        "emails_sent": result.get("emails_sent", 0),
        "emails_failed": result.get("emails_failed", 0),
        "emails_skipped": result.get("emails_skipped", 0),
        "timestamp": result.get("timestamp")
    }
