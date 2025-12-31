from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


# ==================== REQUEST SCHEMAS ====================

class GenerateResumeRequest(BaseModel):
    """Request to generate an optimized resume."""
    user_id: str = Field(..., description="UUID of the user from Supabase profiles table")
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


# ==================== RESPONSE SCHEMAS ====================

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
    user_id: str
    original_profile: dict
    optimized_resume: dict
    pdf_path: str
    pdf_url: Optional[str] = ""  # Supabase storage URL
    recruiter_email: Optional[str] = None
    application_status: Literal["pending", "ready", "applied", "rejected"]
    processing_time_ms: int
    message: str


class AnalyzeRejectionResponse(BaseModel):
    """Response from rejection analysis."""
    success: bool
    user_id: str
    gap_analysis: str
    recommendations: list[str]
    anti_pattern_created: bool


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
