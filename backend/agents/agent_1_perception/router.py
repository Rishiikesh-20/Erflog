# backend/agents/agent_1_perception/router.py
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from auth.dependencies import get_current_user
from .service import agent1_service
from .schemas import (
    ProfileResponse, 
    GithubSyncResponse, 
    OnboardingRequest, 
    OnboardingResponse,
    WatchdogCheckRequest,
    QuizRequest,
    QuizResponse,
    QuizSubmission,
    QuizResult,
    # New onboarding schemas
    OnboardingCompleteRequest,
    OnboardingStatusResponse,
    OnboardingQuizSubmission,
    OnboardingQuizResponse,
    DashboardInsightsResponse
)
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/perception", tags=["Agent 1: Perception"])


# =============================================================================
# RESUME UPLOAD
# =============================================================================

@router.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...), 
    user: dict = Depends(get_current_user)
):
    """
    Upload and process resume (Protected)
    
    Extracts skills with metadata and stores in both:
    - skills: Legacy string array for backward compatibility
    - skills_metadata: Rich skill profiles with source and verification status
    """
    user_id = user["sub"]
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files allowed")
    
    try:
        result = await agent1_service.process_resume_upload(file, user_id)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(500, str(e))


# =============================================================================
# GITHUB SYNC
# =============================================================================

@router.post("/sync-github", response_model=dict)
async def sync_github(user: dict = Depends(get_current_user)):
    """
    Trigger GitHub sync (Protected)
    
    Scans user's GitHub activity and updates skills_metadata:
    - New skills: source="github", verification_status="pending"
    - Existing skills: Updates evidence and last_seen timestamp
    """
    user_id = user["sub"]
    
    try:
        result = await agent1_service.run_github_watchdog(user_id)
        
        if result is None:
            raise HTTPException(
                status_code=400, 
                detail="GitHub sync failed. Please ensure you have completed onboarding with a valid GitHub URL."
            )
        
        return {"status": "success", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# =============================================================================
# ONBOARDING
# =============================================================================

@router.patch("/onboarding", response_model=OnboardingResponse)
async def update_onboarding(
    request: OnboardingRequest,
    user: dict = Depends(get_current_user)
):
    """
    Update user profile with onboarding information (Protected)
    
    Set github_url, linkedin_url, and target_roles.
    """
    user_id = user["sub"]
    
    try:
        result = await agent1_service.update_user_onboarding(
            user_id=user_id,
            github_url=request.github_url,
            linkedin_url=request.linkedin_url,
            target_roles=request.target_roles
        )
        return result
    except Exception as e:
        raise HTTPException(500, str(e))


# =============================================================================
# WATCHDOG POLLING
# =============================================================================

@router.get("/watchdog/check")
async def watchdog_check(
    session_id: Optional[str] = None,
    last_sha: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Poll for new GitHub activity (Protected)
    
    Efficient check using commit SHA comparison.
    Returns full analysis if new activity detected.
    
    Query params:
        - session_id: Optional session identifier (not used currently)
        - last_sha: Last known commit SHA
    """
    user_id = user["sub"]
    
    try:
        result = await agent1_service.check_github_activity(
            user_id=user_id,
            last_known_sha=last_sha
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# =============================================================================
# SKILL VERIFICATION: Quiz Endpoints
# =============================================================================

@router.post("/verify/quiz")
async def generate_verification_quiz(
    request: QuizRequest,
    user: dict = Depends(get_current_user)
):
    """
    Generate a skill verification quiz question (Protected)
    
    Creates a multiple-choice question to verify the user's knowledge
    of a specific skill. Returns quiz_id, question, and options.
    
    NOTE: In this stateless implementation, correct_index is included
    in the response. In production, store server-side and validate.
    """
    user_id = user["sub"]
    
    try:
        result = await agent1_service.generate_quiz(
            user_id=user_id,
            skill_name=request.skill_name,
            level=request.level or "intermediate"
        )
        
        if not result:
            raise HTTPException(500, "Failed to generate quiz")
        
        return {
            "status": "success",
            "quiz": {
                "quiz_id": result["quiz_id"],
                "skill_name": result["skill_name"],
                "question": result["question"],
                "options": result["options"],
                # Include correct_index for stateless verification
                # In production, this would be stored server-side
                "correct_index": result["correct_index"],
                "explanation": result.get("explanation", "")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/verify/submit", response_model=dict)
async def submit_quiz_answer(
    request: QuizSubmission,
    user: dict = Depends(get_current_user)
):
    """
    Submit quiz answer and update skill verification status (Protected)
    
    Compares user's answer with expected correct answer.
    If correct: Updates skills_metadata[skill].verification_status = "verified"
    If incorrect: Status remains unchanged (pending)
    
    Request body:
    - quiz_id: The quiz ID from generate_verification_quiz
    - skill_name: The skill being verified
    - answer_index: User's selected answer (0-3)
    - expected_correct_index: The correct answer index (for stateless verification)
    """
    user_id = user["sub"]
    
    try:
        # Stateless verification: compare answer_index with expected_correct_index
        # In production, you would look up the correct answer from a database
        passed = request.answer_index == request.expected_correct_index
        
        result = await agent1_service.verify_quiz_attempt(
            user_id=user_id,
            skill_name=request.skill_name,
            passed=passed
        )
        
        return {
            "status": "success",
            "result": {
                "correct": result["correct"],
                "new_status": result["new_status"],
                "message": result["message"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# =============================================================================
# PROFILE RETRIEVAL (Optional utility endpoint)
# =============================================================================

@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    """
    Get current user's profile with skills metadata (Protected)
    Returns null profile data if user hasn't completed onboarding yet.
    """
    user_id = user["sub"]
    
    try:
        response = agent1_service.supabase.table("profiles").select("*").eq("user_id", user_id).execute()
        
        if not response.data:
            # New user - return empty profile structure
            return {
                "status": "success",
                "profile": {
                    "user_id": user_id,
                    "name": user.get("user_metadata", {}).get("full_name") or user.get("email"),
                    "email": user.get("email"),
                    "resume_url": None,
                    "skills": [],
                    "skills_metadata": {},
                    "experience_summary": None,
                    "needs_onboarding": True
                }
            }
        
        profile = response.data[0]
        
        return {
            "status": "success",
            "profile": {
                "user_id": profile.get("user_id"),
                "name": profile.get("name"),
                "email": profile.get("email"),
                "resume_url": profile.get("resume_url"),
                "skills": profile.get("skills", []),
                "skills_metadata": profile.get("skills_metadata", {}),
                "experience_summary": profile.get("experience_summary"),
                "needs_onboarding": False
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# =============================================================================
# NEW ONBOARDING FLOW ENDPOINTS
# =============================================================================

@router.get("/onboarding/status")
async def get_onboarding_status(user: dict = Depends(get_current_user)):
    """
    Check if user needs to complete onboarding (Protected)
    
    Returns:
    - needs_onboarding: True if user hasn't completed onboarding
    - onboarding_step: Which step they're on (1-4)
    - profile_complete: Whether basic profile info is filled
    - has_resume: Whether resume was uploaded
    - has_quiz_completed: Whether quiz was completed
    """
    user_id = user["sub"]
    
    try:
        result = await agent1_service.check_onboarding_status(user_id)
        return {"status": "success", **result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/onboarding/complete")
async def complete_onboarding(
    request: OnboardingCompleteRequest,
    user: dict = Depends(get_current_user)
):
    """
    Complete onboarding profile setup (Protected)
    
    Save user profile data including skills, target roles, education.
    After this, user should complete the quiz.
    """
    user_id = user["sub"]
    
    try:
        # Convert education items to dicts
        education_dicts = [
            {
                "institution": edu.institution,
                "degree": edu.degree,
                "course": edu.course,
                "year": edu.year
            }
            for edu in request.education
        ]
        
        result = await agent1_service.complete_onboarding(
            user_id=user_id,
            name=request.name,
            email=request.email,
            skills=request.skills,
            target_roles=request.target_roles,
            education=education_dicts,
            experience_summary=request.experience_summary,
            github_url=request.github_url,
            linkedin_url=request.linkedin_url,
            leetcode_url=request.leetcode_url,
            has_resume=request.has_resume
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


class GenerateQuizRequest(BaseModel):
    """Request body for generating onboarding quiz"""
    skills: Optional[List[str]] = None
    target_roles: Optional[List[str]] = None


@router.post("/onboarding/quiz/generate")
async def generate_onboarding_quiz(
    request: GenerateQuizRequest,
    user: dict = Depends(get_current_user)
):
    """
    Generate 5 MCQ questions for onboarding quiz (Protected)
    
    Questions are based on user's skills and target roles.
    Returns questions with correct_index for stateless verification.
    """
    user_id = user["sub"]
    
    try:
        result = await agent1_service.generate_onboarding_quiz(
            user_id=user_id,
            skills=request.skills or [],
            target_roles=request.target_roles or []
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/onboarding/quiz/submit")
async def submit_onboarding_quiz(
    request: OnboardingQuizSubmission,
    user: dict = Depends(get_current_user)
):
    """
    Submit onboarding quiz answers (Protected)
    
    Marks onboarding as complete and calculates score.
    """
    user_id = user["sub"]
    
    try:
        # Convert answers to dicts
        answers_dicts = [
            {
                "question_id": a.question_id,
                "selected_index": a.selected_index,
                "correct_index": a.correct_index
            }
            for a in request.answers
        ]
        
        result = await agent1_service.submit_onboarding_quiz(
            user_id=user_id,
            answers=answers_dicts
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# =============================================================================
# DASHBOARD INSIGHTS ENDPOINT
# =============================================================================

@router.get("/dashboard")
async def get_dashboard_insights(user: dict = Depends(get_current_user)):
    """
    Get dashboard insights for authenticated users (Protected)
    
    Returns:
    - user_name: User's display name
    - profile_strength: 0-100 completion score
    - top_jobs: Top 3 job matches for today
    - hot_skills: Trending skills to learn
    - github_insights: Analysis of recent GitHub activity
    - news_cards: Industry news and insights
    - agent_status: Current AI agent status
    """
    user_id = user["sub"]
    
    try:
        result = await agent1_service.get_dashboard_insights(user_id)
        return {"status": "success", **result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# =============================================================================
# SETTINGS ENDPOINTS
# =============================================================================

class ProfileUpdateRequest(BaseModel):
    """Request body for updating profile fields"""
    name: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None


@router.get("/settings/profile")
async def get_settings_profile(user: dict = Depends(get_current_user)):
    """
    Get full profile for Settings page (Protected)
    
    Returns all profile fields including both resume URLs.
    """
    user_id = user["sub"]
    
    try:
        result = await agent1_service.get_full_profile(user_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.patch("/settings/profile")
async def update_settings_profile(
    request: ProfileUpdateRequest,
    user: dict = Depends(get_current_user)
):
    """
    Update profile fields from Settings page (Protected)
    
    Updates name, github_url, and/or linkedin_url.
    """
    user_id = user["sub"]
    
    try:
        result = await agent1_service.update_profile_fields(
            user_id=user_id,
            name=request.name,
            github_url=request.github_url,
            linkedin_url=request.linkedin_url
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.put("/settings/resume")
async def update_primary_resume(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """
    Upload new primary resume (Protected)
    
    Replaces the existing primary resume:
    - Deletes old resume from S3
    - Uploads new resume
    - Re-processes profile data
    """
    user_id = user["sub"]
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files allowed")
    
    try:
        result = await agent1_service.update_primary_resume(file, user_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/settings/calculate-ats")
async def calculate_ats_on_demand(user: dict = Depends(get_current_user)):
    """
    Calculate ATS score on demand (Protected)
    
    Called when Settings page loads and ATS_SCORE is NULL.
    Fetches resume_text from profile, calculates ATS score, and saves it.
    """
    user_id = user["sub"]
    
    try:
        result = await agent1_service.calculate_ats_on_demand(user_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
