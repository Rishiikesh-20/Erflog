# backend/agents/agent_3_strategist/service.py

"""
Agent 3: Strategist - Daily Personalized Data Matching Service

This service runs as a daily cron job to:
1. Fetch all users from profiles table
2. For each user, get their profile vector from Pinecone
3. Match against jobs (default namespace), hackathons, and news
4. Store top matches in today_data table (upsert - replaces previous day's data)
"""

import os
import logging
from typing import Any, Optional
from datetime import datetime, timezone
from supabase import create_client
from pinecone import Pinecone
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [Agent 3] - %(levelname)s - %(message)s')
logger = logging.getLogger("Agent3")

# Environment Variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "ai-verse")
USER_INDEX_NAME = os.getenv("PINECONE_USER_INDEX_NAME", "career-flow-users")

# Pinecone Namespaces
NAMESPACE_JOBS = ""  # default namespace
NAMESPACE_HACKATHONS = "hackathon"
NAMESPACE_NEWS = "news"


class StrategistService:
    """
    Daily Personalized Data Matching Service.
    
    Matches each user's profile vector against:
    - Jobs (top 10) from default namespace
    - Hackathons (top 10) from hackathon namespace
    - News (top 5) from news namespace
    
    Results are stored in today_data table, replacing previous day's data.
    """
    
    def __init__(self):
        """Initialize service with database and vector connections."""
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.pinecone_index = None
        self.user_index = None
        self.gemini_client = None
        self._init_clients()
    
    def _init_clients(self):
        """Initialize Pinecone and Gemini clients."""
        if not PINECONE_API_KEY:
            logger.warning("PINECONE_API_KEY not set, vector search disabled")
            return
        
        try:
            pc = Pinecone(api_key=PINECONE_API_KEY)
            self.pinecone_index = pc.Index(INDEX_NAME)
            
            # User vectors index (for getting user embeddings)
            if USER_INDEX_NAME in pc.list_indexes().names():
                self.user_index = pc.Index(USER_INDEX_NAME)
            
            logger.info(f"✅ Pinecone connected: {INDEX_NAME}")
        except Exception as e:
            logger.error(f"❌ Pinecone connection failed: {e}")
        
        if GEMINI_API_KEY:
            try:
                self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
                logger.info("✅ Gemini client initialized")
            except Exception as e:
                logger.error(f"❌ Gemini connection failed: {e}")
    
    def _get_user_embedding(self, user_id: str) -> Optional[list[float]]:
        """
        Get user's profile embedding from Pinecone user index.
        Falls back to generating embedding from profile text if not found.
        """
        # Try to get from user index first
        if self.user_index:
            try:
                result = self.user_index.fetch(ids=[user_id])
                if result.vectors and user_id in result.vectors:
                    return result.vectors[user_id].values
            except Exception as e:
                logger.warning(f"Failed to fetch user vector: {e}")
        
        # Fallback: Generate from profile data
        try:
            profile = self.supabase.table("profiles").select(
                "skills, target_roles, experience_summary, education"
            ).eq("user_id", user_id).single().execute()
            
            if not profile.data:
                return None
            
            # Build profile text
            skills = profile.data.get("skills", []) or []
            roles = profile.data.get("target_roles", []) or []
            experience = profile.data.get("experience_summary", "") or ""
            education = profile.data.get("education", "") or ""
            
            profile_text = f"""
            Skills: {', '.join(skills) if isinstance(skills, list) else skills}
            Target Roles: {', '.join(roles) if isinstance(roles, list) else roles}
            Experience: {experience}
            Education: {education}
            """.strip()
            
            if not profile_text or len(profile_text) < 10:
                return None
            
            # Generate embedding
            if self.gemini_client:
                response = self.gemini_client.models.embed_content(
                    model="text-embedding-004",
                    contents=profile_text,
                )
                return response.embeddings[0].values
            
        except Exception as e:
            logger.error(f"Failed to get/generate user embedding: {e}")
        
        return None
    
    def _query_namespace(
        self, 
        user_vector: list[float], 
        namespace: str, 
        top_k: int
    ) -> list[dict[str, Any]]:
        """
        Query a Pinecone namespace with user's vector.
        Returns list of matches with metadata.
        """
        if not self.pinecone_index:
            return []
        
        try:
            results = self.pinecone_index.query(
                vector=user_vector,
                top_k=top_k,
                include_metadata=True,
                namespace=namespace
            )
            
            matches = []
            for match in results.get("matches", []):
                metadata = match.get("metadata", {})
                matches.append({
                    "id": match.get("id"),
                    "score": round(match.get("score", 0), 4),
                    "title": metadata.get("title", "Unknown"),
                    "company": metadata.get("company", "Unknown"),
                    "link": metadata.get("link", ""),
                    "summary": metadata.get("summary", ""),
                    "source": metadata.get("source", ""),
                    "platform": metadata.get("platform", ""),
                    "location": metadata.get("location", ""),
                    "type": metadata.get("type", namespace),
                    "supabase_id": metadata.get("supabase_id"),
                })
            
            return matches
        
        except Exception as e:
            logger.error(f"Query failed for namespace {namespace}: {e}")
            return []
    
    def _save_today_data(self, user_id: str, data: dict[str, Any]) -> bool:
        """
        Save/update user's today_data (upsert).
        Replaces previous day's data for this user.
        """
        try:
            payload = {
                "user_id": user_id,
                "data_json": data,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Upsert: insert or update on conflict
            self.supabase.table("today_data").upsert(
                payload,
                on_conflict="user_id"
            ).execute()
            
            return True
        except Exception as e:
            logger.error(f"Failed to save today_data for {user_id}: {e}")
            return False
    
    def get_user_today_data(self, user_id: str) -> Optional[dict[str, Any]]:
        """
        Get a user's today_data from database.
        Used by API endpoints.
        """
        try:
            result = self.supabase.table("today_data").select(
                "data_json, updated_at"
            ).eq("user_id", user_id).single().execute()
            
            if result.data:
                return {
                    "data": result.data.get("data_json", {}),
                    "updated_at": result.data.get("updated_at")
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get today_data for {user_id}: {e}")
            return None
    
    def _generate_hot_skills(self, user_skills: list[str], target_roles: list[str], matched_jobs: list[dict]) -> list[dict]:
        """
        Generate AI-powered hot skills recommendations based on user profile and job matches.
        Uses Gemini to analyze skill gaps and trending technologies.
        """
        if not self.gemini_client:
            # Fallback to static trending skills
            trending = ["AI/ML", "Rust", "Go", "Kubernetes", "GraphQL"]
            return [
                {"skill": s, "demand_trend": "rising", "reason": f"High demand in {target_roles[0] if target_roles else 'tech'} roles"}
                for s in trending[:3] if s not in user_skills
            ]
        
        try:
            # Build context from jobs
            job_titles = [j.get("title", "") for j in matched_jobs[:5]]
            job_summaries = [j.get("summary", "")[:100] for j in matched_jobs[:3]]
            
            prompt = f"""You are a career skills advisor. Based on the user's profile and job market data, suggest 3 hot skills to learn.

USER PROFILE:
- Current Skills: {', '.join(user_skills[:10]) if user_skills else 'Not specified'}
- Target Roles: {', '.join(target_roles[:3]) if target_roles else 'Software Developer'}

MATCHED JOB TITLES:
{', '.join(job_titles) if job_titles else 'Various tech roles'}

Return ONLY a valid JSON array with exactly 3 skills:
[
  {{"skill": "SkillName", "demand_trend": "rising", "reason": "Brief reason why important"}},
  ...
]

Focus on skills the user DOESN'T already have that are in high demand. Keep reasons under 50 chars.
Return ONLY the JSON array, no markdown."""

            response = self.gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            
            import json
            text = response.text.strip()
            # Clean markdown if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            skills = json.loads(text)
            if isinstance(skills, list) and len(skills) > 0:
                return skills[:3]
                
        except Exception as e:
            logger.warning(f"Hot skills generation failed: {e}")
        
        # Fallback
        return [
            {"skill": "AI/ML", "demand_trend": "rising", "reason": "High demand across all tech roles"},
            {"skill": "Cloud Architecture", "demand_trend": "rising", "reason": "Essential for modern systems"},
            {"skill": "System Design", "demand_trend": "stable", "reason": "Key for senior positions"}
        ]
    
    def process_single_user(self, user_id: str) -> dict[str, Any]:
        """
        Process a single user: get their vector and match against all namespaces.
        Also generates AI hot skills recommendations.
        Returns the generated today_data.
        """
        logger.info(f"Processing user: {user_id}")
        
        # Get user profile first (for skills and roles)
        profile_response = self.supabase.table("profiles").select(
            "skills, target_roles"
        ).eq("user_id", user_id).execute()
        
        user_skills = []
        target_roles = []
        if profile_response.data:
            user_skills = profile_response.data[0].get("skills", []) or []
            target_roles = profile_response.data[0].get("target_roles", []) or []
        
        # Get user embedding
        user_vector = self._get_user_embedding(user_id)
        if not user_vector:
            logger.warning(f"No embedding found for user {user_id}")
            return {"error": "No user embedding found"}
        
        # Query all namespaces
        jobs = self._query_namespace(user_vector, NAMESPACE_JOBS, top_k=10)
        hackathons = self._query_namespace(user_vector, NAMESPACE_HACKATHONS, top_k=10)
        news = self._query_namespace(user_vector, NAMESPACE_NEWS, top_k=5)
        
        # Generate AI hot skills based on user profile and matched jobs
        hot_skills = self._generate_hot_skills(user_skills, target_roles, jobs)
        
        # Build today_data
        today_data = {
            "jobs": jobs,
            "hackathons": hackathons,
            "news": news,
            "hot_skills": hot_skills,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "stats": {
                "jobs_count": len(jobs),
                "hackathons_count": len(hackathons),
                "news_count": len(news)
            }
        }
        
        # Save to database (upsert - replaces previous day)
        success = self._save_today_data(user_id, today_data)
        
        if success:
            logger.info(f"✅ Saved today_data for {user_id}: {len(jobs)} jobs, {len(hackathons)} hackathons, {len(news)} news")
        
        return today_data
    
    def run_daily_matching(self) -> dict[str, Any]:
        """
        Main cron entry point: Process all users.
        
        Runs once per day to:
        1. Fetch all user_ids from profiles table
        2. For each user, generate personalized matches
        3. Store in today_data table (replaces previous day's data)
        """
        logger.info("=" * 60)
        logger.info("[Agent 3] Starting Daily User Matching")
        logger.info(f"[Agent 3] Timestamp: {datetime.now(timezone.utc).isoformat()}")
        logger.info("=" * 60)
        
        result = {
            "status": "success",
            "users_processed": 0,
            "users_failed": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Fetch all users
            users_response = self.supabase.table("profiles").select("user_id").execute()
            
            if not users_response.data:
                logger.warning("No users found in profiles table")
                result["status"] = "no_users"
                return result
            
            user_ids = [u["user_id"] for u in users_response.data]
            logger.info(f"Found {len(user_ids)} users to process")
            
            # Process each user
            for user_id in user_ids:
                try:
                    self.process_single_user(user_id)
                    result["users_processed"] += 1
                except Exception as e:
                    logger.error(f"Failed to process user {user_id}: {e}")
                    result["users_failed"] += 1
            
            if result["users_failed"] > 0:
                result["status"] = "partial_success"
            
        except Exception as e:
            logger.error(f"Critical error in daily matching: {e}")
            result["status"] = "failed"
            result["error"] = str(e)
        
        logger.info("=" * 60)
        logger.info(f"[Agent 3] Daily Matching Complete: {result['status']}")
        logger.info(f"[Agent 3] Processed: {result['users_processed']}, Failed: {result['users_failed']}")
        logger.info("=" * 60)
        
        return result


# Singleton instance
_service: Optional[StrategistService] = None

def get_strategist_service() -> StrategistService:
    """Get or create singleton service instance."""
    global _service
    if _service is None:
        _service = StrategistService()
    return _service
