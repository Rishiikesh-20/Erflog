import os
import time
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Agent4Service:
    """
    Service layer for Agent 4 - Application Operative.
    Handles all business logic and orchestrates the workflow.
    """
    
    def __init__(self):
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of dependencies."""
        if not self._initialized:
            from .graph import app
            from .tools import (
                fetch_user_profile_by_uuid,
                fetch_user_profile,
                build_resume_from_profile,
                rewrite_resume_content,
                find_recruiter_email
            )
            from .pdf_engine import generate_pdf
            
            self.app = app
            self.fetch_user_profile_by_uuid = fetch_user_profile_by_uuid
            self.fetch_user_profile = fetch_user_profile
            self.build_resume_from_profile = build_resume_from_profile
            self.rewrite_resume_content = rewrite_resume_content
            self.find_recruiter_email = find_recruiter_email
            self.generate_pdf = generate_pdf
            
            self._initialized = True
    
    def generate_resume(
        self,
        user_id: str,
        job_description: str,
        job_id: Optional[str] = None
    ) -> dict:
        """
        Generate an optimized resume for a user targeting a specific job.
        
        Args:
            user_id: UUID of the user from Supabase.
            job_description: Target job description.
            job_id: Optional job ID for tracking.
        
        Returns:
            Dictionary with optimized resume, PDF path, and metadata.
        """
        self._ensure_initialized()
        start_time = time.time()
        
        # 1. Fetch user profile from Supabase
        profile = self.fetch_user_profile_by_uuid(user_id)
        user_profile = self.build_resume_from_profile(profile)
        
        # Add user_id to profile for file naming
        user_profile["user_id"] = user_id
        
        # 2. Run the Agent 4 workflow
        from .state import Agent4State
        
        initial_state: Agent4State = {
            "job_description": job_description,
            "user_profile": user_profile,
            "rewritten_content": {},
            "pdf_path": "",
            "pdf_url": "",
            "recruiter_email": "",
            "application_status": "pending",
            "feedback_loop": {}
        }
        
        result = self.app.invoke(initial_state)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return {
            "success": True,
            "user_id": user_id,
            "original_profile": user_profile,
            "optimized_resume": result.get("rewritten_content", {}),
            "pdf_path": result.get("pdf_path", ""),
            "pdf_url": result.get("pdf_url", ""),
            "recruiter_email": result.get("recruiter_email"),
            "application_status": result.get("application_status", "pending"),
            "processing_time_ms": processing_time,
            "message": "Resume generated successfully"
        }
    
    def generate_resume_by_profile_id(
        self,
        profile_id: int,
        job_description: str
    ) -> dict:
        """
        Generate resume using profile ID instead of UUID.
        """
        self._ensure_initialized()
        start_time = time.time()
        
        # Fetch profile and get user_id
        from core.db import db_manager
        supabase = db_manager.get_client()
        response = supabase.table("profiles").select("user_id").eq("id", profile_id).execute()
        
        if not response.data:
            raise ValueError(f"Profile {profile_id} not found")
        
        user_id = response.data[0]["user_id"]
        return self.generate_resume(user_id, job_description)
    
    def analyze_rejection(
        self,
        user_id: str,
        job_description: str,
        rejection_reason: Optional[str] = None
    ) -> dict:
        """
        Analyze why a resume was rejected and update learning.
        """
        self._ensure_initialized()
        
        from .evolution import analyze_rejection, update_vector_memory
        
        # Fetch user profile
        profile = self.fetch_user_profile_by_uuid(user_id)
        user_profile = self.build_resume_from_profile(profile)
        
        # Analyze the rejection
        gap_analysis = analyze_rejection(job_description, user_profile)
        
        # Update vector memory with anti-pattern
        memory_result = update_vector_memory(user_id, gap_analysis)
        
        # Extract recommendations
        recommendations = [
            line.strip() 
            for line in gap_analysis.split('\n') 
            if line.strip() and not line.startswith('#')
        ][:5]
        
        return {
            "success": True,
            "user_id": user_id,
            "gap_analysis": gap_analysis,
            "recommendations": recommendations,
            "anti_pattern_created": memory_result.get("anti_pattern_created", False)
        }
    
    def get_pdf_url(self, pdf_path: str) -> str:
        """
        Get the URL/path to access a generated PDF.
        """
        # For now, return the local path
        # In production, upload to Supabase storage and return URL
        return pdf_path


# Singleton instance
agent4_service = Agent4Service()
