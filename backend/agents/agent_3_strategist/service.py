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
import math
from typing import Any, Optional, Dict, List
from datetime import datetime, timezone, date
from supabase import create_client
from pinecone import Pinecone
from google import genai
from dotenv import load_dotenv

# Redis cache integration
from services.cache_service import cache_service

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

# =========================================================================
# RECENCY BOOSTING CONFIGURATION
# =========================================================================
OVERSAMPLE_FACTOR = 5  # Query 5x more results for reranking
SEMANTIC_WEIGHT = 0.6  # 60% weight for semantic similarity
RECENCY_WEIGHT = 0.4   # 40% weight for recency
RECENCY_DECAY_LAMBDA = 0.03  # Exponential decay rate (90 day half-life)


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
    
    @staticmethod
    def calculate_recency_score(posted_at: Optional[date]) -> float:
        """
        Calculate recency score using exponential decay.
        
        Args:
            posted_at: Date when the job/hackathon/news was posted
            
        Returns:
            Float between 0.0 and 1.0:
            - 1.0 = posted today
            - 0.8 = posted 7 days ago
            - 0.5 = posted 30 days ago
            - 0.2 = posted 60 days ago
            - 0.0 = posted 90+ days ago or no date
        """
        if not posted_at:
            # No date available - assume very old
            return 0.1
        
        try:
            # Handle both date and datetime objects
            if isinstance(posted_at, datetime):
                posted_at = posted_at.date()
            
            today = datetime.now(timezone.utc).date()
            days_old = (today - posted_at).days
            
            # Exponential decay: score = e^(-lambda * days)
            recency_score = math.exp(-RECENCY_DECAY_LAMBDA * days_old)
            
            # Clamp between 0 and 1
            return max(0.0, min(1.0, recency_score))
            
        except Exception as e:
            logger.warning(f"Error calculating recency score: {e}")
            return 0.1
    
    def _fetch_timestamps_batch(
        self, 
        supabase_ids: List[int], 
        namespace: str
    ) -> Dict[str, Optional[date]]:
        """
        Fetch posted_at/created_at timestamps in batch from Supabase.
        
        Args:
            supabase_ids: List of Supabase record IDs
            namespace: Pinecone namespace (maps to table name)
            
        Returns:
            Dict mapping pinecone_id (str) -> posted_at (date)
        """
        if not supabase_ids:
            return {}
        
        # Map namespace to table name
        table_map = {
            NAMESPACE_JOBS: "jobs",
            NAMESPACE_HACKATHONS: "hackathons",
            NAMESPACE_NEWS: "market_news"
        }
        table_name = table_map.get(namespace, "jobs")
        
        # Determine which date column to use
        date_column = "posted_at" if table_name in ["jobs", "hackathons"] else "published_at"
        
        try:
            # Batch fetch timestamps
            response = self.supabase.table(table_name).select(
                f"id, {date_column}, created_at"
            ).in_("id", supabase_ids).execute()
            
            # Build lookup dict
            timestamps = {}
            for record in response.data:
                record_id = str(record.get("id"))
                
                # Prefer posted_at/published_at, fallback to created_at
                date_value = record.get(date_column) or record.get("created_at")
                
                if date_value:
                    # Parse string to date if needed
                    if isinstance(date_value, str):
                        try:
                            date_value = datetime.fromisoformat(date_value.replace('Z', '+00:00')).date()
                        except:
                            date_value = None
                    elif isinstance(date_value, datetime):
                        date_value = date_value.date()
                
                timestamps[record_id] = date_value
            
            logger.debug(f"Fetched {len(timestamps)} timestamps from {table_name}")
            return timestamps
            
        except Exception as e:
            logger.warning(f"Failed to fetch timestamps from {table_name}: {e}")
            return {}
    
    def _query_namespace(
        self, 
        user_vector: list[float], 
        namespace: str, 
        top_k: int
    ) -> list[dict[str, Any]]:
        """
        Query a Pinecone namespace with user's vector using hybrid scoring.
        
        RECENCY BOOSTING STRATEGY:
        1. Oversample from Pinecone (5x more results)
        2. Fetch timestamps from PostgreSQL in batch
        3. Calculate hybrid score: (semantic × 0.6) + (recency × 0.4)
        4. Re-rank and return top_k results
        
        Returns list of matches with metadata sorted by hybrid score.
        """
        if not self.pinecone_index:
            return []
        
        try:
            # Step 1: Oversample from Pinecone
            oversample_k = top_k * OVERSAMPLE_FACTOR
            results = self.pinecone_index.query(
                vector=user_vector,
                top_k=oversample_k,
                include_metadata=True,
                namespace=namespace
            )
            
            raw_matches = results.get("matches", [])
            if not raw_matches:
                return []
            
            # Step 2: Extract supabase_ids for batch timestamp fetch
            supabase_ids = []
            for match in raw_matches:
                sid = match.get("metadata", {}).get("supabase_id")
                if sid:
                    try:
                        supabase_ids.append(int(sid))
                    except (ValueError, TypeError):
                        pass
            
            # Step 3: Fetch timestamps in batch
            timestamps = self._fetch_timestamps_batch(supabase_ids, namespace)
            
            # Step 4: Calculate hybrid scores and re-rank
            scored_matches = []
            for match in raw_matches:
                metadata = match.get("metadata", {})
                supabase_id = str(metadata.get("supabase_id", ""))
                
                # Semantic score from Pinecone
                semantic_score = match.get("score", 0.0)
                
                # Recency score from timestamp
                posted_at = timestamps.get(supabase_id)
                recency_score = self.calculate_recency_score(posted_at)
                
                # Hybrid score
                final_score = (semantic_score * SEMANTIC_WEIGHT) + (recency_score * RECENCY_WEIGHT)
                
                # Build match dict with hybrid score
                match_dict = {
                    "id": match.get("id"),
                    "score": round(final_score, 4),  # Hybrid score
                    "semantic_score": round(semantic_score, 4),  # Original
                    "recency_score": round(recency_score, 4),  # Recency component
                    "title": metadata.get("title", "Unknown"),
                    "company": metadata.get("company", "Unknown"),
                    "link": metadata.get("link", ""),
                    "summary": metadata.get("summary", ""),
                    "source": metadata.get("source", ""),
                    "platform": metadata.get("platform", ""),
                    "location": metadata.get("location", ""),
                    "type": metadata.get("type", namespace),
                    "supabase_id": metadata.get("supabase_id"),
                    "posted_at": posted_at.isoformat() if posted_at else None,
                }
                
                scored_matches.append(match_dict)
            
            # Step 5: Sort by hybrid score (descending) and return top_k
            scored_matches.sort(key=lambda x: x["score"], reverse=True)
            final_matches = scored_matches[:top_k]
            
            # Log recency boost stats
            if final_matches:
                avg_recency = sum(m["recency_score"] for m in final_matches) / len(final_matches)
                logger.info(
                    f"[Recency Boost] {namespace}: {len(final_matches)} results, "
                    f"avg_recency={avg_recency:.2f}, "
                    f"top_hybrid={final_matches[0]['score']:.3f}"
                )
            
            return final_matches
        
        except Exception as e:
            logger.error(f"Query failed for namespace {namespace}: {e}")
            return []
    
    def _save_today_data(self, user_id: str, data: dict[str, Any]) -> bool:
        """
        Save/update user's today_data (upsert).
        Uses write-through: DB first, then cache.
        Replaces previous day's data for this user.
        """
        try:
            updated_at = datetime.now(timezone.utc).isoformat()
            payload = {
                "user_id": user_id,
                "data_json": data,
                "updated_at": updated_at
            }
            
            # Upsert: insert or update on conflict (DB first for consistency)
            self.supabase.table("today_data").upsert(
                payload,
                on_conflict="user_id"
            ).execute()
            
            # Update cache after successful DB write (write-through)
            cache_service.set_today_data(user_id, {
                "data": data,
                "updated_at": updated_at
            })
            
            return True
        except Exception as e:
            logger.error(f"Failed to save today_data for {user_id}: {e}")
            return False
    
    def get_user_today_data(self, user_id: str) -> Optional[dict[str, Any]]:
        """
        Get a user's today_data.
        Uses cache-first strategy with DB fallback.
        """
        # Try cache first
        cached = cache_service.get_today_data(user_id)
        if cached:
            logger.debug(f"Cache HIT for today_data:{user_id}")
            return cached
        
        # Cache miss - fetch from DB
        logger.debug(f"Cache MISS for today_data:{user_id}, fetching from DB")
        try:
            result = self.supabase.table("today_data").select(
                "data_json, updated_at"
            ).eq("user_id", user_id).single().execute()
            
            if result.data:
                data = {
                    "data": result.data.get("data_json", {}),
                    "updated_at": result.data.get("updated_at")
                }
                # Hydrate cache for future reads
                cache_service.set_today_data(user_id, data)
                return data
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
        For jobs with match < 80%, generates roadmaps.
        For ALL jobs, generates default application text.
        
        CRON CACHE WARMING: Also refreshes profile and github_activity caches.
        Returns the generated today_data.
        """
        logger.info(f"Processing user: {user_id}")
        
        # =========================================================================
        # CACHE WARMING: Fetch and cache full profile during cron
        # =========================================================================
        profile_response = self.supabase.table("profiles").select("*").eq("user_id", user_id).execute()
        
        user_skills = []
        target_roles = []
        user_profile = {}
        github_url = None
        
        if profile_response.data:
            profile_data = profile_response.data[0]
            user_skills = profile_data.get("skills", []) or []
            target_roles = profile_data.get("target_roles", []) or []
            github_url = profile_data.get("github_url")
            user_profile = {
                "name": profile_data.get("name", "Candidate"),
                "skills": user_skills,
                "target_roles": target_roles,
                "experience_summary": profile_data.get("experience_summary", "")
            }
            
            # Warm the profile cache
            cache_service.set_profile(user_id, profile_data)
            logger.info(f"🔥 Cache WARMED for profile:{user_id}")
        
        # =========================================================================
        # CACHE WARMING: Fetch and cache github_activity during cron
        # =========================================================================
        if github_url:
            try:
                github_response = self.supabase.table("github_activity_cache").select(
                    "detected_skills, repos_touched, tech_stack, insight_message, analyzed_at"
                ).eq("user_id", user_id).execute()
                
                if github_response.data:
                    cache_service.set_github_activity(user_id, github_response.data[0])
                    logger.info(f"🔥 Cache WARMED for github_activity:{user_id}")
            except Exception as e:
                logger.warning(f"Could not warm github_activity cache: {e}")
        
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
        
        # =========================================================================
        # NEW: Use orchestrator to enrich jobs with roadmaps and application text
        # This happens at fetch time - no further processing after cron job
        # =========================================================================
        try:
            from .orchestrator import run_orchestration
            
            logger.info(f"🎯 Running orchestration for {len(jobs)} jobs...")
            today_data = run_orchestration(
                user_id=user_id,
                user_profile=user_profile,
                jobs=jobs,
                hackathons=hackathons,
                news=news,
                hot_skills=hot_skills
            )
            logger.info(f"✅ Orchestration complete: {today_data.get('stats', {})}")
            
        except Exception as e:
            logger.error(f"❌ Orchestration failed, using basic data: {e}")
            # Fallback to basic data without enrichment
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
            stats = today_data.get("stats", {})
            logger.info(f"✅ Saved today_data for {user_id}: {stats.get('jobs_count', 0)} jobs ({stats.get('jobs_with_roadmap', 0)} with roadmaps), {stats.get('hackathons_count', 0)} hackathons, {stats.get('news_count', 0)} news")
        
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
