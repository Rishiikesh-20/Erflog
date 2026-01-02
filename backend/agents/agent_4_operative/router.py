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
    ErrorResponse
)
from .service import agent4_service


agent4_router = APIRouter(
    prefix="/agent4",
    tags=["Agent 4 - Application Operative"]
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
async def analyze_rejection(request: AnalyzeRejectionRequest):
    """
    Analyze why a resume was rejected and update the learning loop.
    
    - Identifies skill gaps and mismatches
    - Creates anti-pattern vectors in Pinecone
    - Returns actionable recommendations
    """
    try:
        result = agent4_service.analyze_rejection(
            user_id=request.user_id,
            job_description=request.job_description,
            rejection_reason=request.rejection_reason
        )
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
