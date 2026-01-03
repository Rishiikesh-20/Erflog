# backend/agents/agent_1_perception/router.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from auth.dependencies import get_current_user
from .service import agent1_service
from .schemas import (
    ProfileResponse, 
    GithubSyncResponse, 
    OnboardingRequest, 
    OnboardingResponse,
    WatchdogCheckRequest
)

router = APIRouter(prefix="/api/perception", tags=["Agent 1: Perception"])


@router.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...), 
    user: dict = Depends(get_current_user)  # JWT Auth - extracts user from token
):
    """
    HTTP Trigger for Resume Processing (Protected)
    
    Requires: Authorization header with valid Supabase JWT
    The user_id is automatically extracted from the JWT token.
    """
    # Extract user_id from JWT payload
    user_id = user["sub"]
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files allowed")
    
    try:
        # Call the Decoupled Service with authenticated user_id
        result = await agent1_service.process_resume_upload(file, user_id)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/sync-github", response_model=dict)
async def sync_github(user: dict = Depends(get_current_user)):
    """
    HTTP Trigger for GitHub Sync (Protected)
    
    Requires: Authorization header with valid Supabase JWT
    
    NOTE: No longer requires github_url in request body.
    The service will look up the user's stored github_url from the database.
    User must complete onboarding first to set their GitHub URL.
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


@router.patch("/onboarding", response_model=OnboardingResponse)
async def update_onboarding(
    request: OnboardingRequest,
    user: dict = Depends(get_current_user)
):
    """
    Update user profile with onboarding information (Protected)
    
    Allows users to set:
    - github_url: Their GitHub profile URL
    - linkedin_url: Their LinkedIn profile URL  
    - target_roles: List of job roles they're interested in
    
    All fields are optional - only provided fields will be updated.
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


@router.post("/watchdog/check")
async def watchdog_check(
    request: WatchdogCheckRequest,
    user: dict = Depends(get_current_user)
):
    """
    Poll for new GitHub activity (Protected)
    
    Used by frontend to check for new commits/activity.
    Returns analysis if new activity is detected.
    """
    user_id = user["sub"]
    
    try:
        result = await agent1_service.check_github_activity(
            user_id=user_id,
            last_known_sha=request.last_known_sha
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
