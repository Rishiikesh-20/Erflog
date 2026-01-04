from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime

from .schemas import (
    GenerateResumeRequest,
    GenerateResumeByProfileIdRequest,
    AnalyzeRejectionRequest,
    GenerateApplicationResponsesRequest,
    GenerateResumeResponse,
    AnalyzeRejectionResponse,
    GenerateApplicationResponsesResponse,
    HealthResponse,
    ErrorResponse,
    AtsRequest,
    AtsScoreResponse,
    AutoApplyRequest,
    AutoApplyResponse
)
from .service import agent4_service
from .tools import calculate_ats_score, run_auto_apply, analyze_rejection


agent4_router = APIRouter(
    prefix="/agent4",
    tags=["Agent 4 - Application Operative"]
)

# Secondary router for /api/operative prefix
operative_router = APIRouter(
    prefix="/api/operative",
    tags=["Agent 4 - Operative APIs"]
)


@agent4_router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for Agent 4."""
    return HealthResponse(
        status="healthy",
        agent="Agent 4 - Application Operative",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )


@agent4_router.post(
    "/generate-resume",
    response_model=GenerateResumeResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def generate_resume(request: GenerateResumeRequest):
    """
    Generate an ATS-optimized resume for a user targeting a specific job.
    
    - Fetches user profile from Supabase using user_id (UUID)
    - Sends profile + job description to Gemini for optimization
    - Generates a PDF resume
    - Returns optimized resume data and PDF path
    """
    try:
        result = agent4_service.generate_resume(
            user_id=request.user_id,
            job_description=request.job_description,
            job_id=request.job_id
        )
        return GenerateResumeResponse(**result)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@agent4_router.post(
    "/generate-resume-by-profile",
    response_model=GenerateResumeResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def generate_resume_by_profile_id(request: GenerateResumeByProfileIdRequest):
    """
    Generate resume using profile ID instead of UUID.
    Convenience endpoint for simpler integrations.
    """
    try:
        result = agent4_service.generate_resume_by_profile_id(
            profile_id=request.profile_id,
            job_description=request.job_description
        )
        return GenerateResumeResponse(**result)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@agent4_router.post(
    "/analyze-rejection",
    response_model=AnalyzeRejectionResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def analyze_rejection_endpoint(request: AnalyzeRejectionRequest):
    """
    Analyze why a resume was rejected using Agent 4's analytical tool.
    
    - Identifies skill gaps and mismatches
    - Returns actionable recommendations
    """
    try:
        # Call the new async tool directly
        result = await analyze_rejection(
            user_id=str(request.user_id), # Ensure UUID is converted to string
            job_description=request.job_description,
            rejection_input=request.rejection_reason # Map 'reason' from schema to 'input' arg
        )
        
        # Check if tool returned an internal error dict
        if "error" in result:
             raise HTTPException(status_code=404, detail=result["error"])

        return AnalyzeRejectionResponse(**result)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@agent4_router.post(
    "/generate-responses",
    response_model=GenerateApplicationResponsesResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def generate_application_responses(request: GenerateApplicationResponsesRequest):
    """
    Generate copy-paste ready responses for common job application questions.
    
    Generates personalized answers for:
    - Why do you want to join this company?
    - Tell us about yourself
    - Relevant skills and technical expertise
    - Work experience and key achievements
    - Why are you a good fit for this role?
    - Problem-solving or challenges faced
    - Additional information
    - Availability, location, or other logistics
    """
    try:
        result = agent4_service.generate_responses(
            user_id=request.user_id,
            job_description=request.job_description,
            company_name=request.company_name,
            job_title=request.job_title,
            additional_context=request.additional_context
        )
        return GenerateApplicationResponsesResponse(**result)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# =============================================================================
# ATS SCORING & AUTO-APPLY ENDPOINTS
# =============================================================================

@agent4_router.post(
    "/ats-score",
    response_model=AtsScoreResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def ats_score_endpoint(request: AtsRequest):
    """
    Calculate ATS (Applicant Tracking System) compatibility score for a resume.
    
    - Analyzes resume text for ATS-friendly formatting
    - Identifies missing keywords and skills
    - Returns a score from 0-100 with recommendations
    """
    try:
        result = await calculate_ats_score(resume_text=request.resume_text)
        return AtsScoreResponse(
            success=True,
            score=result["score"],
            missing_keywords=result["missing_keywords"],
            summary=result["summary"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ATS analysis failed: {str(e)}")


@agent4_router.post(
    "/auto-apply",
    response_model=AutoApplyResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def auto_apply_endpoint(request: AutoApplyRequest):
    """
    Auto-fill a job application form using browser automation.
    
    - Opens the job URL in a visible browser
    - Clicks the Apply button
    - Fills form fields with provided user data
    - Does NOT upload files or submit the form
    - User should review and submit manually
    """
    try:
        result = await run_auto_apply(
            job_url=request.job_url,
            user_data=request.user_data
        )
        return AutoApplyResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-apply failed: {str(e)}")


# =============================================================================
# OPERATIVE ROUTER ENDPOINTS (Alternative prefix: /api/operative)
# =============================================================================

@operative_router.post(
    "/ats-score",
    response_model=AtsScoreResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def operative_ats_score(request: AtsRequest):
    """
    Calculate ATS compatibility score for a resume.
    Alternative endpoint with /api/operative prefix.
    """
    try:
        result = await calculate_ats_score(resume_text=request.resume_text)
        return AtsScoreResponse(
            success=True,
            score=result["score"],
            missing_keywords=result["missing_keywords"],
            summary=result["summary"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ATS analysis failed: {str(e)}")


@operative_router.post(
    "/auto-apply",
    response_model=AutoApplyResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def operative_auto_apply(request: AutoApplyRequest):
    """
    Auto-fill a job application form using browser automation.
    Alternative endpoint with /api/operative prefix.
    """
    try:
        result = await run_auto_apply(
            job_url=request.job_url,
            user_data=request.user_data
        )
        return AutoApplyResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-apply failed: {str(e)}")