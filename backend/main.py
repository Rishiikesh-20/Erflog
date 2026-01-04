"""
Career Flow AI - Main Application Entry Point
FastAPI Server for Agentic AI Backend with Multi-Agent Workflow
"""

import os
import uuid
from typing import Optional, Dict
from dotenv import load_dotenv

# 1. Load env FIRST
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 2. Auth & DB
from auth.dependencies import get_current_user
from core.state import AgentState
from core.db import db_manager

# 3. Agent Routers
from agents.agent_1_perception.router import router as agent1_router 
from agents.agent_2_market.router import router as agent2_router

app = FastAPI(
    title="Career Flow AI API",
    description="AI-powered career automation system",
    version="2.0.0"
)

# -----------------------------------------------------------------------------
# Middleware
# -----------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Mount Routers
# -----------------------------------------------------------------------------
app.include_router(agent1_router)  # /api/perception/*
app.include_router(agent2_router)  # /api/market/*

# -----------------------------------------------------------------------------
# Global State
# -----------------------------------------------------------------------------
SESSIONS: Dict[str, AgentState] = {}

def initialize_state() -> AgentState:
    return AgentState(resume_text=None, skills=[], user_id=None, context={}, results={})

# -----------------------------------------------------------------------------
# Core Endpoints
# -----------------------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "status": "online",
        "version": "2.0.0",
        "active_agents": ["Perception", "Market"]
    }

@app.get("/api/me")
async def get_me(user=Depends(get_current_user)):
    return {
        "user_id": user["sub"],
        "email": user.get("email"),
        "provider": user.get("app_metadata", {}).get("provider")
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "active_sessions": len(SESSIONS)}

@app.post("/api/init")
async def init_session():
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = initialize_state()
    return {"status": "success", "session_id": session_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)