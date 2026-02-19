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
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Header, BackgroundTasks, Body
from pydantic import BaseModel
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


class CronRequest(BaseModel):
    """Optional body for /cron endpoint.

    - Leave body empty (or omit user_ids) → process ALL users (production behaviour).
    - Pass user_ids list → process ONLY those users (useful for local testing).
    """
    user_ids: Optional[List[str]] = None


@router.post("/cron")
async def run_daily_cron(
    x_cron_secret: str = Header(None, alias="X-Cron-Secret"),
    body: CronRequest = Body(default_factory=CronRequest),
):
    """
    Trigger daily matching cron job.
    Requires X-Cron-Secret header matching CRON_SECRET env var.

    **Production** – call with no body (or omit user_ids) to process all users:
    ```
    POST /api/strategist/cron
    X-Cron-Secret: <secret>
    ```

    **Testing** – pass specific user IDs to process only those users:
    ```
    POST /api/strategist/cron
    X-Cron-Secret: <secret>
    Content-Type: application/json

    { "user_ids": ["uuid-1", "uuid-2"] }
    ```
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

    service = get_strategist_service()

    target_user_ids = body.user_ids if body and body.user_ids else None

    if target_user_ids:
        # ── TESTING MODE: process only the specified users ──────────────────
        result = {
            "status": "success",
            "users_processed": 0,
            "users_failed": 0,
            "mode": "targeted",
            "target_user_ids": target_user_ids,
        }
        for uid in target_user_ids:
            try:
                service.process_single_user(uid)
                result["users_processed"] += 1
            except Exception as e:
                result["users_failed"] += 1
                result.setdefault("errors", {})[uid] = str(e)

        if result["users_failed"] > 0:
            result["status"] = "partial_success"
    else:
        # ── PRODUCTION MODE: process all users (original behaviour) ─────────
        result = service.run_daily_matching()
        result["mode"] = "all_users"

    return {
        "status": result.get("status", "unknown"),
        "mode": result.get("mode", "all_users"),
        "users_processed": result.get("users_processed", 0),
        "users_failed": result.get("users_failed", 0),
        "target_user_ids": result.get("target_user_ids"),
        "errors": result.get("errors"),
        "timestamp": result.get("timestamp"),
    }


@router.get("/debug/{user_id}")
async def debug_user_data(
    user_id: str,
    x_cron_secret: str = Header(None, alias="X-Cron-Secret"),
):
    """
    **TESTING ONLY** — Inspect the raw DB row and Redis cache state for a user.
    Shows generated_at, updated_at, job count, and whether Redis has a cached copy.

    Requires X-Cron-Secret header.
    """
    if not CRON_SECRET or x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Cron-Secret header")

    from services.cache_service import cache_service
    from core.db import db_manager

    supabase = db_manager.get_client()
    result = {"user_id": user_id, "db": None, "redis": None}

    # ── DB check ──────────────────────────────────────────────────────────────
    try:
        row = supabase.table("today_data").select(
            "user_id, updated_at, data_json"
        ).eq("user_id", user_id).single().execute()

        if row.data:
            data_json = row.data.get("data_json", {})
            result["db"] = {
                "found": True,
                "updated_at": row.data.get("updated_at"),
                "generated_at": data_json.get("generated_at"),
                "jobs_count": len(data_json.get("jobs", [])),
                "hackathons_count": len(data_json.get("hackathons", [])),
                "news_count": len(data_json.get("news", [])),
            }
        else:
            result["db"] = {"found": False}
    except Exception as e:
        result["db"] = {"error": str(e)}

    # ── Redis check ───────────────────────────────────────────────────────────
    try:
        cached = cache_service.get_today_data(user_id)
        if cached:
            data = cached.get("data", {})
            result["redis"] = {
                "found": True,
                "updated_at": cached.get("updated_at"),
                "generated_at": data.get("generated_at"),
                "jobs_count": len(data.get("jobs", [])),
            }
        else:
            result["redis"] = {"found": False, "note": "Cache miss — next read will go to DB"}
    except Exception as e:
        result["redis"] = {"error": str(e)}

    return result


@router.delete("/cache/{user_id}")
async def clear_user_cache(
    user_id: str,
    x_cron_secret: str = Header(None, alias="X-Cron-Secret"),
):
    """
    **TESTING ONLY** — Bust the Redis cache for a user's today_data.

    After calling this, the next GET /api/strategist/jobs (or /today) will
    re-read from the DB instead of Redis, so you'll immediately see the
    data written by the last cron run.

    Requires X-Cron-Secret header.
    """
    if not CRON_SECRET or x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Cron-Secret header")

    from services.cache_service import cache_service

    deleted = cache_service.delete_today_data(user_id)
    return {
        "status": "cleared" if deleted else "no_cache",
        "user_id": user_id,
        "message": (
            "Redis cache cleared. Next read will fetch fresh data from DB."
            if deleted else
            "No Redis cache found for this user (already fresh or Redis unavailable)."
        ),
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


# ============================================================================
# Hunter.io Recruiter Email Finder
# ============================================================================

from pydantic import BaseModel
from typing import Optional, List

class FindRecruiterRequest(BaseModel):
    company: str
    job_id: str
    job_title: str


@router.post("/find-recruiter")
async def find_recruiter_email(
    request: FindRecruiterRequest,
    user: dict = Depends(get_current_user)
):
    """
    Find recruiter/HR emails for a company using Hunter.io API.
    Also generates a personalized outreach email template.

    Request body:
    - company: Company name or domain
    - job_id: ID of the job (for tracking)
    - job_title: Title of the job (for email template)

    Returns:
    - emails: List of found emails with name, position, confidence
    - email_template: LLM-generated soft outreach email
    """
    from .hunter_service import get_hunter_service
    from supabase import create_client
    import os

    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    hunter_service = get_hunter_service()

    # Find recruiter emails
    result = await hunter_service.find_recruiter_emails(
        company=request.company,
        limit=5
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Failed to find recruiter emails")
        )

    # Get user profile for email template
    try:
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        profile_response = supabase.table("profiles").select(
            "name, skills"
        ).eq("user_id", user_id).single().execute()

        user_name = profile_response.data.get("name", "Job Seeker") if profile_response.data else "Job Seeker"
        user_skills = profile_response.data.get("skills", []) if profile_response.data else []
    except Exception as e:
        user_name = "Job Seeker"
        user_skills = []

    # Get first recruiter name for personalized email
    recruiter_name = None
    emails = result.get("emails", [])
    if emails:
        recruiter_name = emails[0].get("full_name")

    # Generate outreach email template
    email_template = await hunter_service.generate_outreach_email(
        user_name=user_name,
        user_skills=user_skills,
        job_title=request.job_title,
        company=request.company,
        recruiter_name=recruiter_name
    )

    return {
        "success": True,
        "company": request.company,
        "domain": result.get("domain"),
        "emails": emails,
        "total_found": result.get("total_found", 0),
        "recruiter_count": result.get("recruiter_count", 0),
        "email_template": email_template
    }
