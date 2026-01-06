# backend/agents/agent_1_perception/service.py
import os
import uuid
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import UploadFile, HTTPException
from supabase import create_client
from pinecone import Pinecone

# Import tools
from .tools import (
    parse_pdf, 
    extract_structured_data, 
    generate_embedding, 
    upload_resume_to_storage,
    generate_skill_quiz,
    generate_onboarding_questions
)
from .github_watchdog import (
    fetch_user_recent_activity,
    analyze_code_context,
    extract_username_from_url,
    get_latest_commit_sha
)

# Import ATS scoring from Agent 4
from agents.agent_4_operative.tools import calculate_ats_score

# Redis cache integration
from services.cache_service import cache_service


class PerceptionService:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.supabase = create_client(self.supabase_url, self.supabase_key)
        
        # Init Pinecone
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "career-flow")
        self.index = self.pc.Index(self.index_name)

    # =========================================================================
    # RESUME PROCESSING
    # =========================================================================
    
    async def process_resume_upload(self, file: UploadFile, user_id: str) -> dict:
        """
        Handles the full flow: PDF Save -> Parse -> Gemini -> DB -> Pinecone
        Now also initializes skills_metadata for resume-extracted skills.
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

            # 5. Build skills_metadata from extracted skills
            skills_list = extracted_data.get("skills", [])
            now = datetime.utcnow().isoformat()
            
            skills_metadata = {}
            for skill in skills_list:
                skills_metadata[skill] = {
                    "source": "resume",
                    "verification_status": "pending",
                    "level": None,
                    "evidence": "Listed in resume",
                    "last_seen": now
                }

            # 6. Calculate ATS Score for primary resume
            print(f"📊 [Agent 1] Calculating ATS score for user: {user_id}")
            try:
                ats_result = await calculate_ats_score(resume_text)
                ats_score = ats_result.get("score", 0)
                print(f"✅ [Agent 1] ATS Score: {ats_score}")
            except Exception as e:
                print(f"⚠️ [Agent 1] ATS scoring failed: {e}")
                ats_score = 0

            # 7. Prepare DB Record (Supabase Profiles)
            profile_data = {
                "user_id": user_id,
                "name": extracted_data.get("name"),
                "email": extracted_data.get("email"),
                "skills": skills_list,  # Legacy array
                "skills_metadata": skills_metadata,  # Rich metadata
                "experience_summary": summary,
                "education": extracted_data.get("education"),
                "resume_json": extracted_data,
                "resume_text": resume_text,
                "resume_url": resume_url,
                "ATS_SCORE": str(ats_score),  # Save ATS score as TEXT
            }

            # 7. Upsert to DB
            self.supabase.table("profiles").upsert(profile_data).execute()

            # 8. Upsert to Pinecone (full profile schema)
            vector_data = {
                "id": user_id, 
                "values": embedding,
                "metadata": {
                    "user_id": user_id,
                    "name": extracted_data.get("name") or "",
                    "email": extracted_data.get("email") or "",
                    "skills": skills_list,
                    "target_roles": [],  # Will be set during onboarding
                    "education": str(extracted_data.get("education") or []),
                    "experience_summary": summary,
                    "github_url": "",
                    "linkedin_url": "",
                    "resume_text": resume_text[:1000] if resume_text else "",  # Truncate for metadata limits
                    "resume_url": resume_url or "",
                    "onboarding_completed": False,
                    "quiz_completed": False,
                    "quiz_score": 0,
                    "type": "user_profile"
                }
            }
            self.index.upsert(vectors=[vector_data], namespace="users")

            return profile_data

        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

    # =========================================================================
    # PROFILE SETTINGS UPDATES
    # =========================================================================
    
    async def update_profile_fields(
        self,
        user_id: str,
        name: Optional[str] = None,
        github_url: Optional[str] = None,
        linkedin_url: Optional[str] = None
    ) -> dict:
        """
        Update basic profile fields from Settings page.
        
        Args:
            user_id: User's UUID
            name: New display name
            github_url: GitHub profile URL
            linkedin_url: LinkedIn profile URL
            
        Returns:
            Updated profile data
        """
        update_data = {}
        updated_fields = []
        
        if name is not None:
            update_data["name"] = name
            updated_fields.append("name")
        
        if github_url is not None:
            # Validate GitHub URL format
            if github_url:  # Only validate if not empty
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
        
        if not update_data:
            return {"status": "no_changes", "updated_fields": [], "user_id": user_id}
        
        # Add timestamp
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        # Update database
        self.supabase.table("profiles").update(update_data).eq("user_id", user_id).execute()
        
        # Update Pinecone metadata if name changed
        if name:
            try:
                self.index.update(
                    id=user_id,
                    set_metadata={"name": name},
                    namespace="users"
                )
            except Exception as e:
                print(f"[Profile] Pinecone update warning: {e}")
        
        return {
            "status": "success", 
            "updated_fields": updated_fields, 
            "user_id": user_id,
            "message": f"Updated: {', '.join(updated_fields)}"
        }
    
    async def update_primary_resume(self, file: UploadFile, user_id: str) -> dict:
        """
        Replace user's primary resume.
        
        - Deletes old resume from S3
        - Uploads new resume
        - Re-processes and updates profile
        
        Args:
            file: New resume PDF file
            user_id: User's UUID
            
        Returns:
            Updated profile data
        """
        # 1. Get current resume_url to delete old file
        response = self.supabase.table("profiles").select("resume_url").eq("user_id", user_id).execute()
        
        if response.data and response.data[0].get("resume_url"):
            # Delete old file from storage
            old_file = f"{user_id}.pdf"
            try:
                self.supabase.storage.from_("Resume").remove([old_file])
                print(f"[Resume] Deleted old primary resume: {old_file}")
            except Exception as e:
                print(f"[Resume] Warning: Could not delete old file: {e}")
        
        # 2. Process new resume (reuse existing method)
        result = await self.process_resume_upload(file, user_id)
        
        return {
            "status": "success",
            "message": "Primary resume updated successfully",
            "resume_url": result.get("resume_url"),
            "profile": result
        }
    
    async def get_full_profile(self, user_id: str) -> dict:
        """
        Get full profile data for Settings page.
        
        Returns all profile fields including resume URLs.
        """
        response = self.supabase.table("profiles").select("*").eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        profile = response.data[0]
        
        return {
            "status": "success",
            "profile": {
                "user_id": profile.get("user_id"),
                "name": profile.get("name"),
                "email": profile.get("email"),
                "github_url": profile.get("github_url"),
                "linkedin_url": profile.get("linkedin_url"),
                "resume_url": profile.get("resume_url"),  # Primary resume
                "sec_resume_url": profile.get("sec_resume_url"),  # Secondary/tailored resume
                "ats_score": profile.get("ATS_SCORE"),  # ATS compatibility score
                "skills": profile.get("skills", []),
                "target_roles": profile.get("target_roles", []),
                "onboarding_completed": profile.get("onboarding_completed", False),
                "quiz_completed": profile.get("quiz_completed", False),
                "updated_at": profile.get("updated_at")
            }
        }

    async def calculate_ats_on_demand(self, user_id: str) -> dict:
        """
        Calculate ATS score on demand for existing users.
        
        Called when Settings page loads and ATS_SCORE is NULL.
        Fetches resume_text, calculates score, saves to DB, and returns it.
        """
        # 1. Fetch resume_text from profile
        response = self.supabase.table("profiles").select(
            "resume_text, ATS_SCORE"
        ).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        profile = response.data[0]
        resume_text = profile.get("resume_text")
        existing_score = profile.get("ATS_SCORE")
        
        # If score already exists, just return it
        if existing_score:
            return {
                "status": "exists",
                "ats_score": existing_score,
                "message": "ATS score already calculated"
            }
        
        # If no resume text, can't calculate
        if not resume_text or len(resume_text.strip()) < 50:
            return {
                "status": "error",
                "ats_score": None,
                "message": "No resume text available. Please upload a resume first."
            }
        
        # 2. Calculate ATS score
        print(f"📊 [Agent 1] Calculating ATS score on demand for user: {user_id}")
        try:
            ats_result = await calculate_ats_score(resume_text)
            ats_score = ats_result.get("score", 0)
            print(f"✅ [Agent 1] ATS Score calculated: {ats_score}")
        except Exception as e:
            print(f"⚠️ [Agent 1] ATS scoring failed: {e}")
            return {
                "status": "error",
                "ats_score": None,
                "message": f"Failed to calculate ATS score: {str(e)}"
            }
        
        # 3. Save to database
        self.supabase.table("profiles").update({
            "ATS_SCORE": str(ats_score)
        }).eq("user_id", user_id).execute()
        
        return {
            "status": "success",
            "ats_score": str(ats_score),
            "message": "ATS score calculated and saved"
        }

    # =========================================================================
    # ONBOARDING
    # =========================================================================
    
    async def update_user_onboarding(
        self,
        user_id: str,
        github_url: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        target_roles: Optional[List[str]] = None
    ) -> dict:
        """Updates user profile with onboarding information."""
        update_data = {}
        updated_fields = []
        
        if github_url is not None:
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
            return {"status": "no_changes", "updated_fields": [], "user_id": user_id}
        
        self.supabase.table("profiles").update(update_data).eq("user_id", user_id).execute()
        
        return {"status": "success", "updated_fields": updated_fields, "user_id": user_id}

    # =========================================================================
    # GITHUB WATCHDOG (Refactored for skills_metadata)
    # =========================================================================
    
    async def run_github_watchdog(self, user_id: str) -> Optional[dict]:
        """
        Scans user's GitHub activity stream for skill analysis.
        
        REFACTORED: Now updates skills_metadata instead of just appending to skills array.
        - Uses SHA-based caching to avoid redundant LLM calls
        - New skills: source="github", verification_status="pending"
        - Existing skills: Updates evidence and last_seen
        - Syncs skills_metadata keys to legacy skills array
        """
        # 1. Get user's profile from database
        response = self.supabase.table("profiles").select(
            "github_url, skills, skills_metadata"
        ).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found. Please upload your resume first.")
        
        profile = response.data[0]
        github_url = profile.get("github_url")
        current_skills = profile.get("skills") or []
        current_metadata = profile.get("skills_metadata") or {}
        
        if not github_url:
            raise HTTPException(
                status_code=400,
                detail="GitHub URL not set. Please complete onboarding first via PATCH /api/perception/onboarding"
            )
        
        # 2. Extract username from URL
        username = extract_username_from_url(github_url)
        if not username:
            raise HTTPException(status_code=400, detail=f"Invalid GitHub URL format: {github_url}")
        
        # 3. Get current SHA from GitHub (quick check)
        current_sha = get_latest_commit_sha(username)
        
        # 4. CHECK CACHE: If SHA matches cached SHA, return cached insights instantly
        cache_response = self.supabase.table("github_activity_cache").select(
            "last_analyzed_sha, detected_skills, repos_touched, tech_stack, insight_message, analyzed_at"
        ).eq("user_id", user_id).execute()
        
        if cache_response.data and len(cache_response.data) > 0:
            cache = cache_response.data[0]
            cached_sha = cache.get("last_analyzed_sha")
            
            if cached_sha and current_sha and cached_sha == current_sha:
                print(f"[Watchdog] ✓ Cache HIT - SHA unchanged ({cached_sha[:7]}), returning cached insights")
                
                # Return cached data
                cached_skills = cache.get("detected_skills") or []
                # Extract skill names from cached skills for display
                cached_skill_names = [s.get("skill") for s in cached_skills if s.get("skill")]
                
                return {
                    "updated_skills": current_skills,
                    "skills_metadata": current_metadata,
                    "analysis": {"detected_skills": cached_skills},
                    "repos_touched": cache.get("repos_touched") or [],
                    "latest_sha": cached_sha,
                    "new_skills": cached_skill_names,  # Return cached skills so they display
                    "existing_skills_updated": [],
                    "insights": {
                        "repos_active": cache.get("repos_touched") or [],
                        "main_focus": cache.get("tech_stack", [])[0] if cache.get("tech_stack") else None,
                        "tech_stack": cache.get("tech_stack") or [],
                        "message": cache.get("insight_message") or "Your GitHub profile is already synced!"
                    },
                    "from_cache": True
                }
        
        print(f"[Watchdog] Cache MISS - Running fresh analysis for user: {username}")
        
        # 5. Fetch recent activity from Events API
        activity = fetch_user_recent_activity(username)
        
        if not activity or not activity.get("recent_code_context"):
            print(f"[Watchdog] No recent code activity found for {username}")
            return {
                "updated_skills": current_skills,
                "skills_metadata": current_metadata,
                "analysis": None,
                "message": "No recent code activity found on GitHub",
                "new_skills": [],
                "insights": None
            }
        
        # 4. Analyze the code context
        analysis = analyze_code_context(activity["recent_code_context"])
        
        if not analysis:
            return {
                "updated_skills": current_skills,
                "skills_metadata": current_metadata,
                "analysis": None,
                "message": "Could not analyze code context",
                "new_skills": [],
                "insights": None
            }
        
        # 5. Update skills_metadata with detected skills
        now = datetime.utcnow().isoformat()
        detected_skills = analysis.get('detected_skills', [])
        
        # Track NEW skills (not in current profile)
        new_skills_added = []
        existing_skills_updated = []
        
        for item in detected_skills:
            skill_name = item.get('skill')
            level = item.get('level', 'intermediate')
            evidence = item.get('evidence', 'Detected in recent GitHub activity')
            
            if skill_name in current_metadata:
                # Skill exists - update evidence and last_seen
                current_metadata[skill_name]["evidence"] = evidence
                current_metadata[skill_name]["last_seen"] = now
                if current_metadata[skill_name].get("level") is None:
                    current_metadata[skill_name]["level"] = level
                existing_skills_updated.append(skill_name)
            else:
                # New skill from GitHub
                current_metadata[skill_name] = {
                    "source": "github",
                    "verification_status": "pending",
                    "level": level,
                    "evidence": evidence,
                    "last_seen": now
                }
                new_skills_added.append(skill_name)
        
        # 6. Sync skills array from skills_metadata keys (for backward compatibility)
        final_skills = list(current_metadata.keys())
        
        # 7. Update Database with both columns
        self.supabase.table("profiles").update({
            "skills": final_skills,
            "skills_metadata": current_metadata,
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
        
        # 9. Generate friendly insights
        repos = activity.get("repos_touched", [])
        top_skills = [s.get('skill') for s in detected_skills[:3]]
        
        insight_message = self._generate_insight_message(repos, top_skills, new_skills_added)
        
        insights = {
            "repos_active": repos,
            "main_focus": top_skills[0] if top_skills else None,
            "tech_stack": top_skills,
            "message": insight_message
        }
        
        # 10. CACHE WRITE: Store insights for future cache hits
        latest_sha = activity.get("latest_commit_sha")
        if latest_sha:
            try:
                # Upsert to cache table
                cache_data = {
                    "user_id": user_id,
                    "last_analyzed_sha": latest_sha,
                    "detected_skills": detected_skills,
                    "repos_touched": repos,
                    "tech_stack": top_skills,
                    "insight_message": insight_message,
                    "analyzed_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                # Check if cache entry exists
                existing = self.supabase.table("github_activity_cache").select("id").eq("user_id", user_id).execute()
                
                if existing.data and len(existing.data) > 0:
                    # Update existing cache
                    self.supabase.table("github_activity_cache").update(cache_data).eq("user_id", user_id).execute()
                    print(f"[Watchdog] ✓ Cache UPDATED for SHA {latest_sha[:7]}")
                else:
                    # Insert new cache entry
                    self.supabase.table("github_activity_cache").insert(cache_data).execute()
                    print(f"[Watchdog] ✓ Cache CREATED for SHA {latest_sha[:7]}")
                    
            except Exception as e:
                print(f"[Watchdog] ⚠️ Cache write warning: {e}")
        
        return {
            "updated_skills": final_skills,
            "skills_metadata": current_metadata,
            "analysis": analysis,
            "repos_touched": repos,
            "latest_sha": latest_sha,
            "new_skills": new_skills_added,
            "existing_skills_updated": existing_skills_updated,
            "insights": insights,
            "from_cache": False
        }
    
    def _generate_insight_message(self, repos: List[str], top_skills: List[str], new_skills: List[str]) -> str:
        """Generate a friendly insight message about the user's recent activity."""
        messages = []
        
        if repos:
            repo_names = [r.split('/')[-1] for r in repos[:2]]  # Get short repo names
            messages.append(f"🚀 You've been active on {', '.join(repo_names)}")
        
        if top_skills:
            messages.append(f"💻 Working with {', '.join(top_skills[:3])}")
        
        if new_skills:
            messages.append(f"✨ New skills detected: {', '.join(new_skills[:3])}")
        elif top_skills:
            messages.append("👍 Keep up the great work!")
        
        return " • ".join(messages) if messages else "Activity synced successfully!"

    # =========================================================================
    # GITHUB ACTIVITY CHECK (Polling)
    # =========================================================================
    
    async def check_github_activity(
        self, 
        user_id: str, 
        last_known_sha: Optional[str] = None
    ) -> dict:
        """Quick check for new GitHub activity (used for polling)."""
        response = self.supabase.table("profiles").select("github_url").eq("user_id", user_id).execute()
        
        if not response.data or not response.data[0].get("github_url"):
            return {"status": "no_github", "message": "GitHub URL not configured"}
        
        github_url = response.data[0]["github_url"]
        username = extract_username_from_url(github_url)
        
        if not username:
            return {"status": "error", "message": "Invalid GitHub URL"}
        
        current_sha = get_latest_commit_sha(username)
        
        if not current_sha:
            return {"status": "no_activity", "message": "No recent activity found"}
        
        if last_known_sha == current_sha:
            return {"status": "no_change", "current_sha": current_sha}
        
        print(f"🔔 New GitHub activity detected for {username} (SHA: {current_sha[:7]})")
        
        result = await self.run_github_watchdog(user_id)
        
        return {
            "status": "updated",
            "new_sha": current_sha,
            "updated_skills": result.get("updated_skills", []) if result else [],
            "new_skills": result.get("new_skills", []) if result else [],
            "insights": result.get("insights") if result else None,
            "repos_touched": result.get("repos_touched", []) if result else [],
            "from_cache": result.get("from_cache", False) if result else False
        }

    # =========================================================================
    # SKILL VERIFICATION: Quiz
    # =========================================================================
    
    async def generate_quiz(
        self, 
        user_id: str, 
        skill_name: str, 
        level: str = "intermediate"
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a quiz question for skill verification.
        
        Args:
            user_id: Authenticated user's ID
            skill_name: Skill to verify (e.g., "React")
            level: Difficulty level
            
        Returns:
            Dict with quiz_id, question, options, and correct_index
        """
        # Verify user has this skill in their profile
        response = self.supabase.table("profiles").select("skills_metadata").eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        skills_metadata = response.data[0].get("skills_metadata") or {}
        
        # Allow quiz even if skill not in profile (for adding new skills)
        if skill_name in skills_metadata:
            # Use existing level if available
            existing_level = skills_metadata[skill_name].get("level")
            if existing_level:
                level = existing_level
        
        # Generate quiz using LangChain tool
        quiz_data = generate_skill_quiz(skill_name, level)
        
        if not quiz_data:
            raise HTTPException(status_code=500, detail="Failed to generate quiz question")
        
        # Create unique quiz ID
        quiz_id = str(uuid.uuid4())
        
        return {
            "quiz_id": quiz_id,
            "skill_name": skill_name,
            "question": quiz_data["question"],
            "options": quiz_data["options"],
            "correct_index": quiz_data["correct_index"],  # In production, store server-side
            "explanation": quiz_data.get("explanation", "")
        }

    async def verify_quiz_attempt(
        self,
        user_id: str,
        skill_name: str,
        passed: bool
    ) -> Dict[str, Any]:
        """
        Update skill verification status based on quiz result.
        
        Args:
            user_id: Authenticated user's ID
            skill_name: Skill that was tested
            passed: Whether the user answered correctly
            
        Returns:
            Dict with new_status and message
        """
        # Get current profile
        response = self.supabase.table("profiles").select(
            "skills, skills_metadata"
        ).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        profile = response.data[0]
        skills_metadata = profile.get("skills_metadata") or {}
        skills_list = profile.get("skills") or []
        
        now = datetime.utcnow().isoformat()
        
        if passed:
            # Update or create skill metadata with verified status
            if skill_name in skills_metadata:
                skills_metadata[skill_name]["verification_status"] = "verified"
                skills_metadata[skill_name]["last_seen"] = now
            else:
                # Add new skill via quiz verification
                skills_metadata[skill_name] = {
                    "source": "quiz",
                    "verification_status": "verified",
                    "level": "intermediate",
                    "evidence": "Passed verification quiz",
                    "last_seen": now
                }
            
            # Sync skills array
            if skill_name not in skills_list:
                skills_list.append(skill_name)
            
            new_status = "verified"
            message = f"🎉 Congratulations! Your {skill_name} skill has been verified."
        else:
            # Don't change status on failure, but log the attempt
            if skill_name in skills_metadata:
                skills_metadata[skill_name]["last_seen"] = now
            
            new_status = skills_metadata.get(skill_name, {}).get("verification_status", "pending")
            message = f"Not quite right. Your {skill_name} status remains: {new_status}"
        
        # Update database
        self.supabase.table("profiles").update({
            "skills": skills_list,
            "skills_metadata": skills_metadata
        }).eq("user_id", user_id).execute()
        
        # Update Pinecone if skills changed
        try:
            self.index.update(
                id=user_id,
                set_metadata={"skills": skills_list},
                namespace="users"
            )
        except Exception as e:
            print(f"[Quiz] Pinecone update warning: {e}")
        
        return {
            "correct": passed,
            "new_status": new_status,
            "message": message,
            "skills_metadata": skills_metadata.get(skill_name, {})
        }

    # =========================================================================
    # ONBOARDING: Status Check
    # =========================================================================
    
    async def check_onboarding_status(self, user_id: str) -> Dict[str, Any]:
        """
        Check if user needs to complete onboarding.
        Returns onboarding status and completion details.
        """
        try:
            # Try to get profile with all columns (some may not exist yet)
            response = self.supabase.table("profiles").select("*").eq("user_id", user_id).execute()
        except Exception as e:
            print(f"Error fetching profile: {e}")
            # If table query fails, assume new user
            return {
                "needs_onboarding": True,
                "onboarding_step": 1,
                "profile_complete": False,
                "has_resume": False,
                "has_quiz_completed": False
            }
        
        if not response.data:
            # No profile exists - user needs full onboarding
            return {
                "needs_onboarding": True,
                "onboarding_step": 1,
                "profile_complete": False,
                "has_resume": False,
                "has_quiz_completed": False
            }
        
        profile = response.data[0]
        
        # Check completion flags (handle missing columns gracefully)
        onboarding_done = profile.get("onboarding_completed", False) or False
        quiz_done = profile.get("quiz_completed", False) or False
        has_resume = bool(profile.get("resume_url"))
        has_skills = bool(profile.get("skills") and len(profile.get("skills", [])) > 0)
        has_target_roles = bool(profile.get("target_roles") and len(profile.get("target_roles", [])) > 0)
        has_education = bool(profile.get("education") and len(profile.get("education", [])) > 0)
        
        # Determine if onboarding is needed
        if onboarding_done and quiz_done:
            return {
                "needs_onboarding": False,
                "onboarding_step": None,
                "profile_complete": True,
                "has_resume": has_resume,
                "has_quiz_completed": True
            }
        
        # Determine which step they're on
        if not has_skills or not has_target_roles or not has_education:
            step = 2  # Need to fill profile details
        elif not quiz_done:
            step = 4  # Need to complete quiz
        else:
            step = 3  # Need social links (optional but recommended)
        
        return {
            "needs_onboarding": True,
            "onboarding_step": step,
            "profile_complete": has_skills and has_target_roles and has_education,
            "has_resume": has_resume,
            "has_quiz_completed": quiz_done
        }

    # =========================================================================
    # ONBOARDING: Complete Profile Setup
    # =========================================================================
    
    async def complete_onboarding(
        self,
        user_id: str,
        name: str,
        email: Optional[str],
        skills: List[str],
        target_roles: List[str],
        education: List[Dict[str, Any]],
        experience_summary: Optional[str] = None,
        github_url: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        leetcode_url: Optional[str] = None,
        has_resume: bool = False
    ) -> Dict[str, Any]:
        """
        Complete onboarding with all user profile data.
        Can be called whether or not user uploaded a resume.
        """
        now = datetime.utcnow().isoformat()
        
        # Build skills_metadata for manual/edited skills
        skills_metadata = {}
        for skill in skills:
            skills_metadata[skill] = {
                "source": "resume" if has_resume else "manual",
                "verification_status": "pending",
                "level": None,
                "evidence": "Listed during onboarding",
                "last_seen": now
            }
        
        # Validate GitHub URL if provided
        if github_url:
            username = extract_username_from_url(github_url)
            if not username:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid GitHub URL format. Expected: https://github.com/username"
                )
        
        # Prepare profile data
        profile_data = {
            "user_id": user_id,
            "name": name,
            "email": email,
            "skills": skills,
            "skills_metadata": skills_metadata,
            "target_roles": target_roles,
            "education": education,
            "experience_summary": experience_summary or "",
            "github_url": github_url,
            "linkedin_url": linkedin_url,
            "leetcode_url": leetcode_url,
            "onboarding_completed": False,  # Will be True after quiz
            "updated_at": now
        }
        
        # Upsert to database
        self.supabase.table("profiles").upsert(profile_data).execute()
        
        # Generate embedding for vector search
        if experience_summary or skills:
            summary_text = experience_summary or f"Skills: {', '.join(skills)}. Target roles: {', '.join(target_roles)}"
            embedding = generate_embedding(summary_text)
            
            # Upsert to Pinecone (full profile schema)
            vector_data = {
                "id": user_id,
                "values": embedding,
                "metadata": {
                    "user_id": user_id,
                    "name": name,
                    "email": email or "",
                    "skills": skills,
                    "target_roles": target_roles,
                    "education": str(education) if education else "[]",
                    "experience_summary": experience_summary or "",
                    "github_url": github_url or "",
                    "linkedin_url": linkedin_url or "",
                    "resume_text": "",  # Not available in manual onboarding
                    "resume_url": "",  # Will be set if resume uploaded
                    "onboarding_completed": False,  # True after quiz
                    "quiz_completed": False,
                    "quiz_score": 0,
                    "type": "user_profile"
                }
            }
            self.index.upsert(vectors=[vector_data], namespace="users")
        
        return {
            "status": "success",
            "message": "Profile saved. Please complete the quiz to finish onboarding.",
            "next_step": "quiz",
            "profile": profile_data
        }

    # =========================================================================
    # ONBOARDING: Generate Quiz Questions
    # =========================================================================
    
    async def generate_onboarding_quiz(
        self,
        user_id: str,
        skills: List[str],
        target_roles: List[str]
    ) -> Dict[str, Any]:
        """
        Generate 5 MCQ questions based on user's skills and target roles.
        Uses Gemini to create relevant technical questions.
        """
        # Get profile for context
        response = self.supabase.table("profiles").select(
            "skills, target_roles, education"
        ).eq("user_id", user_id).execute()
        
        if response.data:
            profile = response.data[0]
            skills = skills or profile.get("skills", [])
            target_roles = target_roles or profile.get("target_roles", [])
        
        if not skills and not target_roles:
            raise HTTPException(
                status_code=400,
                detail="No skills or target roles found. Please complete profile setup first."
            )
        
        # Generate questions using Gemini
        questions = generate_onboarding_questions(skills, target_roles)
        
        if not questions or len(questions) < 5:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate quiz questions. Please try again."
            )
        
        return {
            "status": "success",
            "questions": questions
        }

    # =========================================================================
    # ONBOARDING: Submit Quiz and Complete
    # =========================================================================
    
    async def submit_onboarding_quiz(
        self,
        user_id: str,
        answers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Submit quiz answers and mark onboarding as complete.
        
        Args:
            user_id: User's ID
            answers: List of {question_id, selected_index, correct_index}
        """
        # Calculate score
        correct_count = sum(
            1 for a in answers 
            if a.get("selected_index") == a.get("correct_index")
        )
        total = len(answers)
        score = int((correct_count / total) * 100) if total > 0 else 0
        
        # Update profile - mark onboarding complete
        now = datetime.utcnow().isoformat()
        
        update_data = {
            "onboarding_completed": True,
            "quiz_completed": True,
            "quiz_score": score,  # Now an integer
            "quiz_completed_at": now,
            "updated_at": now
        }
        
        self.supabase.table("profiles").update(update_data).eq("user_id", user_id).execute()
        
        return {
            "status": "success",
            "score": score,
            "correct": correct_count,
            "total": total,
            "message": f"Great job! You scored {correct_count}/{total}. Welcome to Erflog!",
            "onboarding_complete": True,
            "trigger_cold_start": True  # Signal frontend to trigger cold start
        }

    # =========================================================================
    # DASHBOARD: Get Insights
    # =========================================================================
    
    async def get_dashboard_insights(self, user_id: str) -> Dict[str, Any]:
        """
        Generate dashboard data for authenticated users.
        
        OPTIMIZED WITH REDIS:
        - Cache-first reads for profile, today_data, github_activity_cache
        - Falls back to Supabase on cache miss
        - Hydrates cache after DB reads for future requests
        """
        # =====================================================================
        # Get user profile (CACHE-FIRST)
        # =====================================================================
        profile = cache_service.get_profile(user_id)
        if not profile:
            # Cache miss - fetch from DB
            response = self.supabase.table("profiles").select("*").eq("user_id", user_id).execute()
            
            if not response.data:
                raise HTTPException(status_code=404, detail="Profile not found")
            
            profile = response.data[0]
            # Hydrate cache
            cache_service.set_profile(user_id, profile)
        
        user_name = profile.get("name", "User")
        skills = profile.get("skills", []) or []
        target_roles = profile.get("target_roles", []) or []
        github_url = profile.get("github_url")
        
        # Calculate profile strength
        strength = 0
        if profile.get("name"): strength += 15
        if profile.get("resume_url"): strength += 25
        if skills and len(skills) >= 3: strength += 20
        if target_roles: strength += 15
        if github_url: strength += 15
        if profile.get("quiz_completed"): strength += 10
        
        # =====================================================================
        # Get personalized data from today_data (CACHE-FIRST - already cached by strategist)
        # =====================================================================
        cached_today = cache_service.get_today_data(user_id)
        
        if cached_today:
            data = cached_today.get("data", {})
        else:
            # Cache miss - fetch from DB and hydrate
            today_data_response = self.supabase.table("today_data").select(
                "data_json, updated_at"
            ).eq("user_id", user_id).execute()
            
            if today_data_response.data:
                data = today_data_response.data[0].get("data_json", {})
                # Hydrate cache
                cache_service.set_today_data(user_id, {
                    "data": data,
                    "updated_at": today_data_response.data[0].get("updated_at")
                })
            else:
                data = {}
        
        top_jobs = []
        hot_skills = []
        news_cards = []
            
        # Get top 3 jobs for dashboard
        jobs_data = data.get("jobs", [])[:3]
        for job in jobs_data:
            top_jobs.append({
                "id": str(job.get("supabase_id", job.get("id", ""))),
                "title": job.get("title", "Unknown"),
                "company": job.get("company", "Unknown"),
                "match_score": int(job.get("score", 0) * 100),
                "key_skills": skills[:3] if skills else []
            })
            
        # Get AI-generated hot skills from today_data (if available)
        hot_skills_data = data.get("hot_skills", [])
        if hot_skills_data:
            hot_skills = hot_skills_data[:3]
            
        # Get news from today_data
        news_data = data.get("news", [])[:2]
        for news in news_data:
            news_cards.append({
                "title": news.get("title", "Tech Update"),
                "summary": news.get("summary", "")[:100],
                "relevance": "Based on your profile"
            })
        
        # Fallback: Generate hot skills from trending if not in today_data
        if not hot_skills:
            trending = ["AI/ML", "Rust", "Go", "Kubernetes", "GraphQL"]
            for skill in trending[:3]:
                if skill not in skills:
                    hot_skills.append({
                        "skill": skill,
                        "demand_trend": "rising",
                        "reason": f"High demand in {target_roles[0] if target_roles else 'tech'} roles"
                    })
        
        # Fallback: Static news if not in today_data
        if not news_cards:
            news_cards = [
                {
                    "title": "AI Skills in High Demand",
                    "summary": "Companies are actively seeking engineers with AI/ML experience",
                    "relevance": "Based on your target roles"
                },
                {
                    "title": "Remote Work Trends 2026",
                    "summary": "75% of tech companies now offer remote-first positions",
                    "relevance": "Job market insight"
                }
            ]
        
        # =====================================================================
        # Get GitHub insights from CACHE-FIRST (Redis then Supabase)
        # =====================================================================
        github_insights = None
        if github_url:
            # Try Redis first
            cached_github = cache_service.get_github_activity(user_id)
            
            if cached_github:
                repos = cached_github.get("repos_touched", []) or []
                detected = cached_github.get("detected_skills", []) or []
                
                github_insights = {
                    "repo_name": repos[0] if repos else "your repositories",
                    "recent_commits": len(repos),
                    "detected_skills": detected[:3] if isinstance(detected, list) else [],
                    "insight_text": cached_github.get("insight_message") or f"Your recent activity shows strong focus on {skills[0] if skills else 'development'}",
                    "from_cache": True,
                    "analyzed_at": cached_github.get("analyzed_at")
                }
            else:
                # Cache miss - fetch from Supabase and hydrate Redis
                try:
                    cache_response = self.supabase.table("github_activity_cache").select(
                        "detected_skills, repos_touched, tech_stack, insight_message, analyzed_at"
                    ).eq("user_id", user_id).execute()
                    
                    if cache_response.data:
                        cache = cache_response.data[0]
                        repos = cache.get("repos_touched", []) or []
                        detected = cache.get("detected_skills", []) or []
                        
                        github_insights = {
                            "repo_name": repos[0] if repos else "your repositories",
                            "recent_commits": len(repos),
                            "detected_skills": detected[:3] if isinstance(detected, list) else [],
                            "insight_text": cache.get("insight_message") or f"Your recent activity shows strong focus on {skills[0] if skills else 'development'}",
                            "from_cache": True,
                            "analyzed_at": cache.get("analyzed_at")
                        }
                        
                        # Hydrate Redis cache
                        cache_service.set_github_activity(user_id, cache)
                except Exception as e:
                    print(f"[Dashboard] GitHub cache read error: {e}")
        
        return {
            "user_name": user_name,
            "profile_strength": strength,
            "top_jobs": top_jobs,
            "hot_skills": hot_skills,
            "github_insights": github_insights,
            "news_cards": news_cards,
            "agent_status": "active"
        }


# Singleton Instance
agent1_service = PerceptionService()
