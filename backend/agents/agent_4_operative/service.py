import time
from typing import Optional
from .tools import (
    mutate_resume_for_job, 
    save_application_status, 
    analyze_rejection,
    fetch_user_profile,
    generate_application_responses
)


"""
Agent 4 Service - Resume Mutation Service
"""


def generate_resume(user_id: str = None, job_description: str = None, job_id: str | int = None, **kwargs) -> dict:
    """
    Main service function to generate/mutate a resume for a job.
    
    Args:
        user_id: User's UUID (required).
        job_description: Target job description (required).
        job_id: Optional Job ID to link application in DB.
    
    Returns:
        Dict with pdf_url, changes_made, etc.
    """
    import time
    start_time = time.time()
    
    if not user_id:
        return {
            "success": False,
            "status": "error",
            "user_id": "",
            "original_profile": {},
            "optimized_resume": {},
            "pdf_path": "",
            "pdf_url": "",
            "application_status": "failed",
            "processing_time_ms": 0,
            "message": "Please provide a user_id."
        }
    
    if not job_description:
        return {
            "success": False,
            "status": "error", 
            "user_id": user_id,
            "original_profile": {},
            "optimized_resume": {},
            "pdf_path": "",
            "pdf_url": "",
            "application_status": "failed",
            "processing_time_ms": 0,
            "message": "Please provide a job description."
        }
    
    # Use the new mutation flow
    result = mutate_resume_for_job(user_id, job_description)
    
    processing_time = int((time.time() - start_time) * 1000)
    
    # Build response compatible with GenerateResumeResponse schema
    response = {
        "success": result.get("status") == "success",
        "status": result.get("status", "error"),
        "user_id": user_id,
        "original_profile": {},  # Not needed for this flow
        "optimized_resume": {
            "changes": result.get("replacements", []),
            "keywords": result.get("keywords_added", [])
        },
        "pdf_path": result.get("pdf_path", ""),
        "pdf_url": result.get("pdf_url", ""),
        "application_status": "ready" if result.get("status") == "success" else "failed",
        "processing_time_ms": processing_time,
        "message": result.get("message", "Resume generated successfully" if result.get("status") == "success" else "Failed to generate resume")
    }
    
    # Save to DB if job_id is present and result was successful
    if job_id and result.get("status") == "success":
        try:
            # Ensure job_id is int (schema says int8)
            job_id_int = int(job_id)
            
            save_application_status(
                user_id=user_id,
                job_id=str(job_id_int),
                status="resume_generated",
                result_data={
                    "tailored_resume_url": result.get("pdf_url"),
                    "custom_responses": response.get("optimized_resume")
                }
            )
        except Exception as e:
            print(f"⚠️ [Agent 4] Failed to save application to DB: {e}")
            # Don't fail the whole request if DB save fails
            
    return response


# Singleton instance
class Agent4Service:
    """
    Service layer for Agent 4.
    Acts as a clean bridge between the API Router and the Logic Tools.
    """
    
    def __init__(self):
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of dependencies."""
        if not self._initialized:
            from .graph import app
            from .tools import (
                fetch_user_profile,
                build_resume_from_profile,
                rewrite_resume_content,
                find_recruiter_email,
                generate_application_responses
            )
            from .pdf_engine import generate_pdf
            
            self.app = app
            self.fetch_user_profile_by_uuid = fetch_user_profile  # Alias for compatibility
            self.fetch_user_profile = fetch_user_profile
            self.build_resume_from_profile = build_resume_from_profile
            self.rewrite_resume_content = rewrite_resume_content
            self.find_recruiter_email = find_recruiter_email
            self.generate_pdf = generate_pdf
            self.generate_application_responses = generate_application_responses
            
            self._initialized = True
    
    def generate_resume(
        self,
        user_id: str,
        job_description: str,
        job_id: Optional[str] = None
    ) -> dict:
        """
        Orchestrates resume generation by calling the mutation tool directly.
        """
        print(f"🚀 [Service] Generating resume for User {user_id}")
        start_time = time.time()
        
        # 1. Direct Tool Call (Replaces the complex Graph invocation)
        result = mutate_resume_for_job(user_id, job_description)
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # 2. Check if mutation was successful
        if result.get("status") == "error":
            raise ValueError(result.get("message", "Resume generation failed"))
        
        # 3. Logging to DB
        if job_id and result.get("status") == "success":
            try:
                save_application_status(
                    user_id=user_id,
                    job_id=str(job_id),
                    status="resume_generated",
                    result_data={
                        "pdf_url": result.get("pdf_url"),
                        "processing_time": f"{processing_time_ms}ms"
                    }
                )
            except Exception as e:
                print(f"⚠️ [Service] DB save failed: {e}")

        # 4. Transform result to match GenerateResumeResponse schema
        return {
            "success": True,
            "user_id": user_id,
            "original_profile": {},  # Could fetch from DB if needed
            "optimized_resume": {},  # Could include structured data if needed
            "pdf_path": result.get("pdf_path", ""),
            "pdf_url": result.get("pdf_url", ""),
            "recruiter_email": None,
            "application_status": "ready",
            "processing_time_ms": processing_time_ms,
            "message": "Resume generated successfully"
        }

    def generate_resume_by_profile_id(self, profile_id: str, job_description: str) -> dict:
        """Wrapper for backward compatibility."""
        return self.generate_resume(user_id=profile_id, job_description=job_description)

    async def analyze_rejection(self, user_id: str, job_description: str, rejection_reason: str) -> dict:
        """Wrapper for rejection analysis."""
        return await analyze_rejection(user_id, job_description, rejection_reason)

    def generate_responses(self, user_id: str, job_description: str, company_name: str, job_title: str, additional_context: str = None) -> dict:
        """
        Generates interview/application responses.
        """
        print(f"📝 [Service] Generating responses for {company_name}")
        start_time = time.time()
        
        # Fetch data
        user_profile = fetch_user_profile(user_id)
        
        # Call the logic (Assumes this function exists in tools.py)
        responses = generate_application_responses(
            user_profile=user_profile,
            job_description=job_description,
            company_name=company_name,
            job_title=job_title,
            additional_context=additional_context
        )
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "success": True,
            "user_id": user_id,
            "company_name": company_name,
            "job_title": job_title,
            "responses": responses,
            "processing_time_ms": processing_time_ms,
            "message": "Application responses generated successfully"
        }

# Singleton Instance
agent4_service = Agent4Service()