# backend/agents/agent_1_perception/service.py
import os
import uuid
import tempfile
from pathlib import Path
from typing import Optional, List
from fastapi import UploadFile, HTTPException
from supabase import create_client
from pinecone import Pinecone

# Import your tools
from .tools import parse_pdf, extract_structured_data, generate_embedding, upload_resume_to_storage
from .github_watchdog import (
    fetch_user_recent_activity,
    analyze_code_context,
    extract_username_from_url,
    get_latest_commit_sha
)


class PerceptionService:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.supabase = create_client(self.supabase_url, self.supabase_key)
        
        # Init Pinecone
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "career-flow")
        self.index = self.pc.Index(self.index_name)

    async def process_resume_upload(self, file: UploadFile, user_id: str) -> dict:
        """
        Handles the full flow: PDF Save -> Parse -> Gemini -> DB -> Pinecone
        
        Args:
            file: Uploaded PDF file
            user_id: Authenticated user's ID from JWT (user["sub"])
        """
        # 1. Save File Temporarily
        temp_dir = Path(tempfile.gettempdir()) / "agent1_uploads"
        temp_dir.mkdir(exist_ok=True)
        pdf_path = temp_dir / f"{user_id}_{file.filename}"
        
        with open(pdf_path, "wb") as f:
            content = await file.read()
            f.write(content)

        try:
            # 2. Upload to Storage (Long-term)
            resume_url = upload_resume_to_storage(str(pdf_path), user_id)

            # 3. Parse & Extract
            resume_text = parse_pdf(str(pdf_path))
            extracted_data = extract_structured_data(resume_text)
            
            # 4. Generate Vector
            summary = extracted_data.get("experience_summary", resume_text[:500])
            embedding = generate_embedding(summary)

            # 5. Prepare DB Record (Supabase Profiles)
            profile_data = {
                "user_id": user_id,
                "name": extracted_data.get("name"),
                "email": extracted_data.get("email"),
                "skills": extracted_data.get("skills", []),
                "experience_summary": summary,
                "education": extracted_data.get("education"),
                "resume_json": extracted_data,
                "resume_text": resume_text,
                "resume_url": resume_url,
            }

            # 6. Upsert to DB (Using upsert to handle updates)
            self.supabase.table("profiles").upsert(profile_data).execute()

            # 7. Upsert to Pinecone (Namespace: users)
            vector_data = {
                "id": user_id, 
                "values": embedding,
                "metadata": {
                    "email": extracted_data.get("email"),
                    "skills": extracted_data.get("skills", []),
                    "type": "user_profile"
                }
            }
            self.index.upsert(vectors=[vector_data], namespace="users")

            return profile_data

        finally:
            # Cleanup temp file
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

    async def update_user_onboarding(
        self,
        user_id: str,
        github_url: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        target_roles: Optional[List[str]] = None
    ) -> dict:
        """
        Updates user profile with onboarding information.
        
        Args:
            user_id: Authenticated user's ID from JWT
            github_url: GitHub profile URL (e.g., https://github.com/username)
            linkedin_url: LinkedIn profile URL
            target_roles: List of target job roles
            
        Returns:
            Dict with status, updated_fields, and user_id
        """
        # Build update payload with only provided fields
        update_data = {}
        updated_fields = []
        
        if github_url is not None:
            # Validate GitHub URL format
            username = extract_username_from_url(github_url)
            if not username:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid GitHub URL format. Expected: https://github.com/username"
                )
            update_data["github_url"] = github_url
            updated_fields.append("github_url")
            
        if linkedin_url is not None:
            update_data["linkedin_url"] = linkedin_url
            updated_fields.append("linkedin_url")
            
        if target_roles is not None:
            update_data["target_roles"] = target_roles
            updated_fields.append("target_roles")
        
        if not update_data:
            return {
                "status": "no_changes",
                "updated_fields": [],
                "user_id": user_id
            }
        
        # Update database
        self.supabase.table("profiles").update(update_data).eq("user_id", user_id).execute()
        
        return {
            "status": "success",
            "updated_fields": updated_fields,
            "user_id": user_id
        }

    async def run_github_watchdog(self, user_id: str) -> Optional[dict]:
        """
        Scans user's GitHub activity stream for skill analysis.
        
        NOTE: No longer takes github_url as parameter.
        Looks up the stored github_url from the user's profile.
        
        Args:
            user_id: Authenticated user's ID from JWT
            
        Returns:
            Dict with updated_skills and analysis, or None if failed
            
        Raises:
            HTTPException: If user hasn't completed onboarding (no github_url)
        """
        # 1. Get user's github_url from database
        response = self.supabase.table("profiles").select("github_url, skills").eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Profile not found. Please upload your resume first."
            )
        
        profile = response.data[0]
        github_url = profile.get("github_url")
        current_skills = profile.get("skills") or []
        
        if not github_url:
            raise HTTPException(
                status_code=400,
                detail="GitHub URL not set. Please complete onboarding first via PATCH /api/perception/onboarding"
            )
        
        # 2. Extract username from URL
        username = extract_username_from_url(github_url)
        if not username:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid GitHub URL format: {github_url}"
            )
        
        print(f"[Watchdog] Scanning GitHub activity for user: {username}")
        
        # 3. Fetch recent activity from Events API
        activity = fetch_user_recent_activity(username)
        
        if not activity or not activity.get("recent_code_context"):
            print(f"[Watchdog] No recent code activity found for {username}")
            return {
                "updated_skills": current_skills,
                "analysis": None,
                "message": "No recent code activity found on GitHub"
            }
        
        # 4. Analyze the code context
        analysis = analyze_code_context(activity["recent_code_context"])
        
        if not analysis:
            return {
                "updated_skills": current_skills,
                "analysis": None,
                "message": "Could not analyze code context"
            }
        
        # 5. Extract new skills
        new_skills = [item['skill'] for item in analysis.get('detected_skills', [])]
        
        # 6. Merge skills (new skills first, then unique old skills)
        unique_old = [s for s in current_skills if s not in new_skills]
        final_skills = new_skills + unique_old
        
        # 7. Update Database
        self.supabase.table("profiles").update({
            "skills": final_skills,
            "last_scan_timestamp": "now()"
        }).eq("user_id", user_id).execute()
        
        # 8. Update Pinecone metadata
        try:
            self.index.update(
                id=user_id,
                set_metadata={"skills": final_skills},
                namespace="users"
            )
        except Exception as e:
            print(f"[Watchdog] Pinecone update warning: {e}")
        
        return {
            "updated_skills": final_skills,
            "analysis": analysis,
            "repos_touched": activity.get("repos_touched", []),
            "latest_sha": activity.get("latest_commit_sha")
        }

    async def check_github_activity(
        self, 
        user_id: str, 
        last_known_sha: Optional[str] = None
    ) -> dict:
        """
        Quick check for new GitHub activity (used for polling).
        
        Args:
            user_id: Authenticated user's ID
            last_known_sha: Last commit SHA known by the frontend
            
        Returns:
            Dict with status and optionally new analysis data
        """
        # 1. Get user's github_url from database
        response = self.supabase.table("profiles").select("github_url").eq("user_id", user_id).execute()
        
        if not response.data or not response.data[0].get("github_url"):
            return {"status": "no_github", "message": "GitHub URL not configured"}
        
        github_url = response.data[0]["github_url"]
        username = extract_username_from_url(github_url)
        
        if not username:
            return {"status": "error", "message": "Invalid GitHub URL"}
        
        # 2. Get latest commit SHA
        current_sha = get_latest_commit_sha(username)
        
        if not current_sha:
            return {"status": "no_activity", "message": "No recent activity found"}
        
        # 3. Compare with last known SHA
        if last_known_sha == current_sha:
            return {"status": "no_change", "current_sha": current_sha}
        
        # 4. New activity detected - run full analysis
        print(f"🔔 New GitHub activity detected for {username} (SHA: {current_sha[:7]})")
        
        result = await self.run_github_watchdog(user_id)
        
        return {
            "status": "updated",
            "new_sha": current_sha,
            "updated_skills": result.get("updated_skills", []) if result else [],
            "analysis": result.get("analysis") if result else None,
            "repos_touched": result.get("repos_touched", []) if result else []
        }


# Singleton Instance
agent1_service = PerceptionService()
