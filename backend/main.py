"""
Career Flow AI - Main Application Entry Point
FastAPI Server for Agentic AI Backend

This file is intentionally minimal - all business logic lives in agent routers.
"""

import os
import logging
from dotenv import load_dotenv

# 1. Load env FIRST
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Main")

from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Auth dependencies
from auth.dependencies import get_current_user

# =============================================================================
# Import ALL Agent Routers
# =============================================================================
from agents.agent_1_perception.router import router as agent1_router
from agents.agent_2_market.router import router as agent2_router
from agents.agent_3_strategist.router import router as agent3_router
from agents.agent_3_strategist.saved_jobs_router import router as saved_jobs_router
from agents.agent_4_operative import agent4_router, operative_router
from agents.agent_5_mock_interview.router import router as agent5_router
from agents.agent_6_leetcode import agent6_router


# =============================================================================
# FastAPI App
# =============================================================================
app = FastAPI(
    title="Career Flow AI API",
    description="AI-powered career automation system with 5 specialized agents",
    version="2.0.0"
)

# =============================================================================
# Middleware
# =============================================================================

# CORS Configuration - Allow both local development and production URLs
allowed_origins = [
    # Local development
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    # Production URLs - Add your actual URLs here after deployment
    "https://erflog.vercel.app",
    "https://www.erflog.vercel.app",
    # Cloud Run URLs will be added dynamically via environment variable
]

# Add Cloud Run URL from environment if available
import os
cloud_run_url = os.getenv("CLOUD_RUN_URL")
if cloud_run_url:
    allowed_origins.append(cloud_run_url)

# Add frontend URL from environment if available
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Mount ALL Agent Routers
# =============================================================================
app.include_router(agent1_router)   # /api/perception/*
app.include_router(agent2_router)   # /api/market/*
app.include_router(agent3_router)   # /api/strategist/*
app.include_router(saved_jobs_router)  # /api/saved-jobs/*
app.include_router(agent4_router)   # /agent4/*
app.include_router(operative_router)
app.include_router(agent5_router)   # /api/interview/*
app.include_router(agent6_router)   # /api/leetcode/*


@app.get("/")
async def root():
    """Root endpoint with API overview"""
    return {
        "status": "online",
        "version": "2.0.0",
        "agents": {
            "agent1_perception": "/api/perception",
            "agent2_market": "/api/market",
            "agent3_strategist": "/api/strategist",
            "agent4_operative": "/agent4",
            "agent5_interview": "/api/interview",
            "agent6_leetcode": "/api/leetcode"
        },
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "message": "Career Flow AI Backend is running"
        }
    )


@app.get("/api/me")
async def get_me(user=Depends(get_current_user)):
    """Get current authenticated user info"""
    return {
        "user_id": user["sub"],
        "email": user.get("email"),
        "provider": user.get("app_metadata", {}).get("provider")
    }


# =============================================================================
# Jobs API - Individual Job Details
# =============================================================================
from supabase import create_client

def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)


@app.get("/api/jobs/{job_id}")
async def get_job_details(job_id: str):
    """Get individual job details by ID"""
    supabase = get_supabase()
    if not supabase:
        return JSONResponse(
            status_code=500,
            content={"error": "Database not configured"}
        )
    
    try:
        # Try to find in jobs table first
        result = supabase.table("jobs").select("*").eq("id", int(job_id)).execute()
        
        if result.data and len(result.data) > 0:
            job = result.data[0]
            return {
                "id": job.get("id"),
                "title": job.get("title", "Job Position"),
                "company": job.get("company", "Company"),
                "location": job.get("location"),
                "description": job.get("description"),
                "link": job.get("link"),
                "score": job.get("score"),
                "type": job.get("type", "job")
            }
        
        # If not found in jobs, try saved_jobs with original_job_id
        saved_result = supabase.table("saved_jobs").select("*").eq("original_job_id", job_id).execute()
        
        if saved_result.data and len(saved_result.data) > 0:
            job = saved_result.data[0]
            return {
                "id": job.get("original_job_id"),
                "title": job.get("title", "Job Position"),
                "company": job.get("company", "Company"),
                "description": job.get("description"),
                "link": job.get("link"),
                "score": job.get("score")
            }
        
        # Not found
        return JSONResponse(
            status_code=404,
            content={"error": f"Job {job_id} not found"}
        )
        
    except Exception as e:
        logger.error(f"Error fetching job {job_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# =============================================================================
# Entry Point
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)