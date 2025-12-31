"""
Career Flow AI - Main Application Entry Point
FastAPI Server for Agentic AI Backend with Multi-Agent Workflow
"""

import os
import uuid
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Load env FIRST before any other imports
load_dotenv()

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

# Import routers
from agents.agent_4_operative import agent4_router

# Import Agent Nodes
from agents.agent_1_perception.graph import perception_node
from agents.agent_2_market.graph import market_scan_node
from agents.agent_3_strategist.graph import search_jobs as strategist_search_jobs, process_career_strategy
from agents.agent_6_interviewer.graph import run_interview_turn

# Import state
from core.state import AgentState

app = FastAPI(
    title="Career Flow AI API",
    description="AI-powered career automation system with Multi-Agent Workflow",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agent4_router)

# -----------------------------------------------------------------------------
# Global Session Store
# -----------------------------------------------------------------------------
SESSIONS: Dict[str, AgentState] = {}

# -----------------------------------------------------------------------------
# Pydantic Models
# -----------------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    query: Optional[str] = None
    context: Optional[dict] = None

class SearchRequest(BaseModel):
    query: str

class KitRequest(BaseModel):
    user_name: str
    job_title: str
    job_company: str

class SessionRequest(BaseModel):
    session_id: str

class MarketScanRequest(BaseModel):
    session_id: str

class StrategyRequest(BaseModel):
    session_id: str

class ApplicationRequest(BaseModel):
    session_id: str
    job_description: Optional[str] = None

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def get_session(session_id: str) -> AgentState:
    """Retrieve session state or raise 404."""
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return SESSIONS[session_id]


def initialize_state() -> AgentState:
    """Create a fresh AgentState with default values."""
    return AgentState(
        resume_text=None,
        skills=[],
        user_id=None,
        context={},
        results={}
    )

# -----------------------------------------------------------------------------
# EXISTING ENDPOINTS (PRESERVED)
# -----------------------------------------------------------------------------

# --- Pydantic Models ---
class AnalyzeRequest(BaseModel):
    user_input: str
    context: Optional[dict] = {}

class SearchRequest(BaseModel):
    query: str

class KitRequest(BaseModel):
    user_name: str
    job_title: str
    job_company: str

class InterviewRequest(BaseModel):
    session_id: str
    user_message: str = ""  # Empty for first turn (start interview)
    job_context: str        # Job title/description


@app.get("/")
async def root():
    return {
        "message": "Career Flow AI API Online",
        "version": "2.0.0",
        "agents_active": 6,
        "endpoints": {
            "workflow": ["/api/init", "/api/upload-resume", "/api/market-scan", "/api/generate-strategy", "/api/generate-application"],
            "interview": "/api/interview/chat",
            "legacy": ["/api/match", "/api/generate-kit"],
            "agent4": "/agent4"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "message": "Career Flow AI Backend is running",
            "active_sessions": len(SESSIONS)
        }
    )


@app.post("/analyze")
async def analyze_career(request: AnalyzeRequest):
    """Legacy analyze endpoint"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": "Analysis request received",
            "data": {}
        }
    )


@app.post("/api/match")
async def match_agent(request: SearchRequest):
    """
    Match agent endpoint - uses Agent 3 Strategist for semantic job matching.
    Uses process_career_strategy which handles Tiers and generates Roadmaps.
    """
    if not request.query:
        raise HTTPException(status_code=400, detail="Query text is required")
    
    try:
        # Use Agent 3's full orchestrator (search + tier classification + roadmap generation)
        result = process_career_strategy(request.query)
        
        return {
            "status": "success",
            "count": result.get("matches_found", 0),
            "matches": result.get("strategy_report", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Match agent error: {str(e)}")


@app.post("/api/generate-kit")
async def generate_kit_endpoint(request: KitRequest):
    """
    Generate deployment kit endpoint.
    Uses Agent 4 for resume/application generation.
    """
    try:
        # Use Agent 4's service for kit generation
        from agents.agent_4_operative import agent4_service
        
        result = agent4_service.generate_resume(
            user_profile={"name": request.user_name},
            job_description=f"Position: {request.job_title} at {request.job_company}"
        )
        
        if result.get("pdf_path"):
            return FileResponse(
                path=result["pdf_path"],
                filename=os.path.basename(result["pdf_path"]),
                media_type='application/pdf'
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Kit generated",
                "data": result
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kit generation error: {str(e)}")


# -----------------------------------------------------------------------------
# NEW AGENT WORKFLOW ENDPOINTS
# -----------------------------------------------------------------------------

@app.post("/api/init")
async def init_session():
    """
    Initialize a new session for the agent workflow.
    
    Returns:
        session_id: Unique identifier for the user session
    """
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = initialize_state()
    
    print(f"[Orchestrator] New session initialized: {session_id}")
    
    return {
        "status": "success",
        "session_id": session_id,
        "message": "Session initialized. Upload a resume to begin."
    }


@app.post("/api/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    session_id: str = Form(...)
):
    """
    Upload a resume PDF and run Agent 1 (Perception).
    
    Args:
        file: Resume PDF file
        session_id: Session identifier
        
    Returns:
        Extracted profile data (name, skills, summary)
    """
    # Validate session
    state = get_session(session_id)
    
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    # Save PDF to temporary location
    try:
        temp_dir = Path(tempfile.gettempdir()) / "career_flow_uploads"
        temp_dir.mkdir(exist_ok=True)
        
        pdf_filename = f"{session_id}_{file.filename}"
        pdf_path = temp_dir / pdf_filename
        
        with open(pdf_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        print(f"[Orchestrator] Resume saved: {pdf_path}")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Update state with PDF path
    state["context"]["pdf_path"] = str(pdf_path)
    
    # Run Agent 1: Perception
    try:
        print(f"[Orchestrator] Running Agent 1 (Perception) for session: {session_id}")
        updated_state = perception_node(state)
        
        # Merge updated state back into session
        SESSIONS[session_id].update(updated_state)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Perception Agent failed: {str(e)}")
    
    # Extract response data
    perception_results = SESSIONS[session_id].get("results", {}).get("perception", {})
    
    return {
        "status": "success",
        "session_id": session_id,
        "profile": {
            "name": perception_results.get("name"),
            "email": perception_results.get("email"),
            "skills": SESSIONS[session_id].get("skills", []),
            "experience_summary": perception_results.get("experience_summary"),
            "education": perception_results.get("education"),
            "user_id": SESSIONS[session_id].get("user_id")
        }
    }


@app.post("/api/market-scan")
async def market_scan(request: MarketScanRequest):
    """
    Run Agent 2 (Market Sentinel) to find job matches.
    
    Args:
        request: JSON body with session_id
        
    Returns:
        List of job matches with full descriptions
    """
    session_id = request.session_id
    
    # Validate session
    state = get_session(session_id)
    
    # Run Agent 2: Market Sentinel
    try:
        print(f"[Orchestrator] Running Agent 2 (Market) for session: {session_id}")
        updated_state = market_scan_node(state)
        
        # Merge updated state back into session
        SESSIONS[session_id].update(updated_state)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Market Agent failed: {str(e)}")
    
    # Extract job matches from results
    market_results = SESSIONS[session_id].get("results", {}).get("market", {})
    job_matches = market_results.get("job_matches", [])
    
    return {
        "status": "success",
        "session_id": session_id,
        "job_matches": job_matches,
        "total_matches": len(job_matches)
    }


@app.post("/api/generate-strategy")
async def generate_strategy(request: StrategyRequest):
    """
    Run Agent 3 (Strategist) for semantic job matching.
    Uses the user's skills/resume to find best-fit jobs via vector search.
    
    Args:
        request: JSON body with session_id
        
    Returns:
        Strategy analysis with matched jobs and recommendations
    """
    session_id = request.session_id
    
    # Validate session
    state = get_session(session_id)
    
    # Get user skills/summary for matching
    skills = state.get("skills", [])
    perception_results = state.get("results", {}).get("perception", {})
    experience_summary = perception_results.get("experience_summary", "")
    
    # Build query from user profile
    query_text = f"{' '.join(skills)} {experience_summary}"
    
    if not query_text.strip():
        raise HTTPException(status_code=400, detail="No profile data available. Upload a resume first.")
    
    # Run Agent 3: Strategist (semantic search)
    try:
        print(f"[Orchestrator] Running Agent 3 (Strategist) for session: {session_id}")
        matched_jobs = strategist_search_jobs(query_text, top_k=5)
        
        # Store results in session
        if "results" not in SESSIONS[session_id]:
            SESSIONS[session_id]["results"] = {}
        
        SESSIONS[session_id]["results"]["strategist"] = {
            "matched_jobs": matched_jobs,
            "query_used": query_text[:200],
            "total_matches": len(matched_jobs)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Strategist Agent failed: {str(e)}")
    
    return {
        "status": "success",
        "session_id": session_id,
        "strategy": {
            "matched_jobs": matched_jobs,
            "total_matches": len(matched_jobs),
            "recommendations": [
                f"Apply to high-match jobs (score > 0.80)",
                f"Consider upskilling for jobs with score 0.60-0.80",
                f"Top match: {matched_jobs[0]['title'] if matched_jobs else 'N/A'}"
            ]
        }
    }


@app.post("/api/generate-application")
async def generate_application(request: ApplicationRequest):
    """
    Run Agent 4 (Operative) to generate tailored resume and recruiter outreach.
    
    Args:
        request: JSON body with session_id and optionally job_description
        
    Returns:
        Tailored resume (PDF path) and recruiter email
    """
    session_id = request.session_id
    
    # Validate session
    state = get_session(session_id)
    
    # Get job description from request or from strategist results
    job_description = request.job_description
    if not job_description:
        strategist_results = state.get("results", {}).get("strategist", {})
        matched_jobs = strategist_results.get("matched_jobs", [])
        if matched_jobs:
            job_description = matched_jobs[0].get("description", "")
    
    if not job_description:
        # Try market results as fallback
        market_results = state.get("results", {}).get("market", {})
        job_matches = market_results.get("job_matches", [])
        if job_matches:
            job_description = job_matches[0].get("description", job_matches[0].get("summary", ""))
    
    if not job_description:
        raise HTTPException(status_code=400, detail="job_description is required (none found in session)")
    
    # Build user profile from perception results
    perception_results = state.get("results", {}).get("perception", {})
    user_profile = {
        "name": perception_results.get("name"),
        "email": perception_results.get("email"),
        "skills": state.get("skills", []),
        "experience_summary": perception_results.get("experience_summary"),
        "education": perception_results.get("education"),
        "resume": perception_results.get("resume_json", {})
    }
    
    # Run Agent 4: Operative
    try:
        print(f"[Orchestrator] Running Agent 4 (Operative) for session: {session_id}")
        from agents.agent_4_operative.graph import run_agent4
        
        operative_result = run_agent4(job_description, user_profile)
        
        # Store operative results in session
        if "results" not in SESSIONS[session_id]:
            SESSIONS[session_id]["results"] = {}
        SESSIONS[session_id]["results"]["operative"] = operative_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Operative Agent failed: {str(e)}")
    
    return {
        "status": "success",
        "session_id": session_id,
        "application": {
            "pdf_path": operative_result.get("pdf_path"),
            "pdf_url": operative_result.get("pdf_url"),  # Supabase storage URL
            "recruiter_email": operative_result.get("recruiter_email"),
            "application_status": operative_result.get("application_status"),
            "rewritten_content": operative_result.get("rewritten_content")
        }
    }


# -----------------------------------------------------------------------------
# AGENT 6: INTERVIEW CHAT ENDPOINT
# -----------------------------------------------------------------------------

@app.post("/api/interview/chat")
async def interview_chat(request: InterviewRequest):
    """
    🎤 AGENT 6 ENDPOINT: The Interviewer
    Conversational interview powered by LangGraph + Gemini.
    
    - Send empty `user_message` to start the interview.
    - Send user's answer to continue the conversation.
    - Each session_id maintains separate conversation state.
    """
    if not request.session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    if not request.job_context:
        raise HTTPException(status_code=400, detail="job_context is required")
    
    try:
        result = run_interview_turn(
            session_id=request.session_id,
            user_message=request.user_message,
            job_context=request.job_context
        )
        
        return {
            "status": "success",
            "response": result["response"],
            "stage": result["stage"],
            "message_count": result["message_count"]
        }
    except Exception as e:
        print(f"❌ Interview Error: {e}")
        raise HTTPException(status_code=500, detail=f"Interview agent error: {str(e)}")


# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")