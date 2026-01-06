from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


# ==================== REQUEST SCHEMAS ====================

class GenerateResumeRequest(BaseModel):
    """Request to generate an optimized resume."""
    user_id: str = Field(..., description="UUID of the user from Supabase profiles table")
    job_description: str = Field(..., description="Target job description text")
    job_id: Optional[str] = Field(None, description="Optional job ID if fetching from database")


class GenerateResumeAuthenticatedRequest(BaseModel):
    """Request to generate an optimized resume for authenticated user (no user_id needed)."""
    job_description: str = Field(..., description="Target job description text")
    job_id: Optional[str] = Field(None, description="Optional job ID if fetching from database")


class GenerateResumeByProfileIdRequest(BaseModel):
    """Request using profile ID instead of UUID."""
    profile_id: int = Field(..., description="Profile ID from Supabase profiles table")
    job_description: str = Field(..., description="Target job description text")


class AnalyzeRejectionRequest(BaseModel):
    """Request to analyze why a resume was rejected."""
    user_id: str = Field(..., description="UUID of the user")
    job_description: str = Field(..., description="Job description that led to rejection")
    rejection_reason: Optional[str] = Field(None, description="Optional rejection feedback")


class GenerateApplicationResponsesRequest(BaseModel):
    """Request to generate application question responses."""
    # ENSURE THIS SAYS user_id, NOT profile_id
    user_id: str = Field(..., description="UUID of the user from Supabase profiles table")
    
    job_description: str = Field(..., description="Target job description text")
    company_name: str = Field(..., description="Name of the company applying to")
    job_title: str = Field(..., description="Title of the position")
    additional_context: Optional[str] = Field(None, description="Any additional context or specific requirements")

# ==================== RESPONSE SCHEMAS ====================

class ApplicationResponses(BaseModel):
    """Generated responses for common application questions."""
    why_join_company: str = Field(..., description="Why do you want to join this company?")
    about_yourself: str = Field(..., description="Tell us about yourself / Professional summary")
    relevant_skills: str = Field(..., description="Relevant skills and technical expertise")
    work_experience: str = Field(..., description="Work experience and key achievements")
    why_good_fit: str = Field(..., description="Why are you a good fit for this role?")
    problem_solving: str = Field(..., description="Problem-solving or challenges faced")
    additional_info: str = Field(..., description="Additional information")
    availability: str = Field(..., description="Availability, location, or other logistics")


class GenerateApplicationResponsesResponse(BaseModel):
    """Response containing all generated application answers."""
    success: bool
    user_id: str
    company_name: str
    job_title: str
    responses: ApplicationResponses
    processing_time_ms: int
    message: str


class ResumeOutput(BaseModel):
    """Generated resume output."""
    name: str
    email: str
    phone: Optional[str] = ""
    location: Optional[str] = ""
    linkedin: Optional[str] = ""
    github: Optional[str] = ""
    summary: str
    experience: list[dict]
    education: list[dict]
    skills: list[str]
    certifications: Optional[list[dict]] = []
    projects: Optional[list[dict]] = []


class GenerateResumeResponse(BaseModel):
    """Response from resume generation."""
    success: bool
    user_id: str = ""
    original_profile: Optional[dict] = {}
    optimized_resume: Optional[dict] = {}
    pdf_path: str = ""
    pdf_url: Optional[str] = ""  # Supabase storage URL
    recruiter_email: Optional[str] = None
    application_status: Literal["pending", "ready", "applied", "rejected", "failed"] = "pending"
    processing_time_ms: int = 0
    message: str = ""


class AnalyzeRejectionResponse(BaseModel):
    """Response from rejection analysis."""
    success: bool
    user_id: str
    gap_analysis: str
    recommendations: list[str]
    anti_pattern_created: bool


# ==================== ATS SCORING SCHEMAS ====================

class AtsRequest(BaseModel):
    """Request to calculate ATS score for a resume."""
    resume_text: str = Field(..., description="The full text content of the resume to analyze")


class AtsScoreResponse(BaseModel):
    """Response containing ATS score analysis."""
    success: bool
    score: int = Field(..., ge=0, le=100, description="ATS compatibility score from 0-100")
    missing_keywords: list[str] = Field(default_factory=list, description="Recommended keywords to add")
    summary: str = Field(..., description="Brief analysis summary")


# ==================== AUTO-APPLY SCHEMAS ====================

class AutoApplyRequest(BaseModel):
    """Request to auto-fill a job application form."""
    job_url: str = Field(..., description="URL of the job application page")
    user_data: dict = Field(..., description="User information for form filling (name, email, phone, etc.)")
    user_id: Optional[str] = Field(None, description="User ID to fetch resume from Supabase storage (stored as {user_id}.pdf)")
    resume_path: Optional[str] = Field(None, description="Local file path to resume PDF/DOCX to upload")
    resume_url: Optional[str] = Field(None, description="URL to download resume from (e.g., Supabase storage URL)")


class AutoApplyResponse(BaseModel):
    """Response from auto-apply operation."""
    success: bool
    job_url: str
    message: str
    details: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    agent: str
    version: str
    timestamp: str


class ErrorResponse(BaseModel):
    """Error response."""
    success: bool = False
    error: str
    detail: Optional[str] = None
