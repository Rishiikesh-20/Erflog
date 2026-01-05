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
from agents.agent_4_operative.router import agent4_router
from agents.agent_5_mock_interview.router import router as agent5_router

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
app.include_router(agent5_router)   # /api/interview/*

# =============================================================================
# Core Endpoints (Health, Root, Auth)
# =============================================================================

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
            "agent5_interview": "/api/interview"
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
# Entry Point
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)