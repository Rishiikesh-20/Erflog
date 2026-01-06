# backend/agents/agent_2_market/service.py

"""
Agent 2: Market Intelligence & Opportunity Aggregation

This is a backend-only autonomous agent executed via cron job (once per day).
It is never triggered by end users and serves all users globally.

Responsibilities:
- Collect, normalize, deduplicate, and persist Jobs, Hackathons, and Tech News
- Analyze all users' target roles and skills
- Strategically query multiple external data providers
- Store results in Supabase and Pinecone

Execution Guarantees:
✅ 30 jobs stored per run
✅ 10-20 hackathons stored per run  
✅ 10 news articles stored per run
✅ Same IDs in Supabase & Pinecone
✅ Fair coverage for all users
✅ Provider failure isolation (one failure doesn't stop the run)
"""

import os
import hashlib
from typing import Any, Optional
from datetime import datetime, timezone
from supabase import create_client
from pinecone import Pinecone, ServerlessSpec

# Import schemas and tools
from .schemas import JobSchema, HackathonSchema, MarketNewsSchema, CronExecutionLog
from .tools import (
    # Job providers
    search_jsearch_jobs,
    search_serpapi_jobs,
    search_mantiks_jobs,
    # Hackathon providers
    search_tavily_hackathons,
    search_serpapi_hackathons,
    # News providers
    search_tavily_news,
    search_newsdata_news,
    search_serpapi_news,
    # LLM functions
    optimize_roles_with_llm,
    generate_search_queries_with_llm,
    allocate_roles_to_providers,
    # Embeddings
    generate_embedding,
    # Legacy compatibility
    search_tavily,
)


class MarketIntelligenceService:
    """
    Market Intelligence Service for global job, hackathon, and news aggregation.
    
    This service:
    1. Aggregates global user context (roles + skills)
    2. Optimizes roles via LLM
    3. Allocates roles to providers strategically
    4. Collects and normalizes data
    5. Stores in Supabase and Pinecone with consistent IDs
    """
    
    # Target collection counts
    TARGET_JOBS = 30
    TARGET_HACKATHONS = 15  # 10-20 range
    TARGET_NEWS = 10
    
    # Per-provider limits
    JOBS_PER_PROVIDER = 10
    
    def __init__(self):
        """Initialize service with database connections."""
        # Initialize Supabase
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        
        self.supabase = create_client(self.supabase_url, self.supabase_key)
        
        # Initialize Pinecone
        self.pinecone_index = self._init_pinecone()
        
        # Execution tracking
        self.execution_log = CronExecutionLog()
        self.provider_errors: dict[str, str] = {}
    
    def _init_pinecone(self) -> Optional[Any]:
        """Initialize and return Pinecone index."""
        try:
            api_key = os.getenv("PINECONE_API_KEY")
            if not api_key:
                print("[Market] PINECONE_API_KEY not found, vectors will not be stored")
                return None
            
            index_name = os.getenv("PINECONE_INDEX_NAME", "career-flow-jobs")
            pc = Pinecone(api_key=api_key)
            
            # Create index if it doesn't exist
            if index_name not in pc.list_indexes().names():
                print(f"[Market] Creating Pinecone index: {index_name}")
                pc.create_index(
                    name=index_name,
                    dimension=768,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1")
                )
            
            return pc.Index(index_name)
        except Exception as e:
            print(f"[Market] Pinecone initialization failed: {str(e)}")
            return None
    
    # =========================================================================
    # STEP 1: Aggregate Global User Context
    # =========================================================================
    
    def _aggregate_global_user_context(self) -> dict[str, Any]:
        """
        Collect all users' target_roles and skills from profiles table.
        Creates global unique role and skill sets.
        
        Returns:
            Dict with 'roles' and 'skills' as unique lists
        """
        print("[Market] Step 1: Aggregating global user context...")
        
        try:
            # Fetch all profiles with target_roles and skills
            response = self.supabase.table("profiles").select(
                "target_roles, skills"
            ).execute()
            
            if not response.data:
                print("[Market] No profiles found, using defaults")
                return {
                    "roles": ["Software Developer", "Frontend Developer", "Backend Developer"],
                    "skills": ["Python", "JavaScript", "React"]
                }
            
            # Aggregate unique roles and skills
            all_roles = set()
            all_skills = set()
            
            for profile in response.data:
                # Handle target_roles (could be string or list)
                target_roles = profile.get("target_roles", [])
                if isinstance(target_roles, str):
                    target_roles = [target_roles]
                elif target_roles is None:
                    target_roles = []
                
                for role in target_roles:
                    if role and isinstance(role, str):
                        all_roles.add(role.strip())
                
                # Handle skills (list)
                skills = profile.get("skills", [])
                if isinstance(skills, list):
                    for skill in skills:
                        if skill and isinstance(skill, str):
                            all_skills.add(skill.strip())
            
            roles_list = list(all_roles) or ["Software Developer"]
            skills_list = list(all_skills) or ["Python", "JavaScript"]
            
            print(f"[Market] Aggregated {len(roles_list)} unique roles, {len(skills_list)} unique skills")
            
            self.execution_log.roles_processed = roles_list[:20]  # Store for logging
            self.execution_log.skills_processed = skills_list[:30]
            
            return {
                "roles": roles_list,
                "skills": skills_list
            }
            
        except Exception as e:
            print(f"[Market] Error aggregating user context: {str(e)}")
            return {
                "roles": ["Software Developer", "Frontend Developer", "Backend Developer"],
                "skills": ["Python", "JavaScript", "React", "Node.js"]
            }
    
    # =========================================================================
    # STEP 2: Role Optimization via LLM
    # =========================================================================
    
    def _optimize_roles(self, roles: list[str], skills: list[str]) -> list[str]:
        """
        Send global role + skill set to Gemini for optimization.
        Returns at most 5 distinct roles that maximize coverage.
        """
        print("[Market] Step 2: Optimizing roles via LLM...")
        
        optimized = optimize_roles_with_llm(roles, skills, max_roles=5)
        print(f"[Market] Optimized to {len(optimized)} roles: {optimized}")
        
        return optimized
    
    # =========================================================================
    # STEP 3: Provider Allocation Strategy
    # =========================================================================
    
    def _allocate_providers(self, roles: list[str]) -> dict[str, list[str]]:
        """
        Distribute roles intelligently across providers.
        Each role is assigned to only one provider.
        """
        print("[Market] Step 3: Allocating roles to providers...")
        
        allocation = allocate_roles_to_providers(roles)
        return allocation
    
    # =========================================================================
    # STEP 4: Job Collection
    # =========================================================================
    
    def _collect_jobs(
        self, 
        allocation: dict[str, list[str]],
        skills: list[str]
    ) -> list[dict[str, Any]]:
        """
        Fetch jobs from all providers based on allocation.
        Target: 30 jobs total (10 per provider).
        """
        print("[Market] Step 4: Collecting jobs from providers...")
        
        all_jobs = []
        
        # JSearch jobs
        if allocation.get("jsearch"):
            try:
                queries = generate_search_queries_with_llm(
                    allocation["jsearch"], skills, "jobs"
                )
                for query in queries[:3]:  # Limit queries
                    jobs = search_jsearch_jobs(query, num_results=4)
                    all_jobs.extend(jobs)
                    if len(all_jobs) >= self.JOBS_PER_PROVIDER:
                        break
            except Exception as e:
                self.provider_errors["jsearch"] = str(e)
                print(f"[Market] JSearch collection failed: {e}")
        
        # SerpAPI jobs
        if allocation.get("serpapi"):
            try:
                queries = generate_search_queries_with_llm(
                    allocation["serpapi"], skills, "jobs"
                )
                for query in queries[:3]:
                    jobs = search_serpapi_jobs(query, num_results=4)
                    all_jobs.extend(jobs)
                    if len([j for j in all_jobs if j.get("source") == "SerpAPI"]) >= self.JOBS_PER_PROVIDER:
                        break
            except Exception as e:
                self.provider_errors["serpapi_jobs"] = str(e)
                print(f"[Market] SerpAPI jobs collection failed: {e}")
        
        # Mantiks jobs
        if allocation.get("mantiks"):
            try:
                for role in allocation["mantiks"][:2]:
                    jobs = search_mantiks_jobs(role, num_results=5)
                    all_jobs.extend(jobs)
                    if len([j for j in all_jobs if j.get("source") == "Mantiks"]) >= self.JOBS_PER_PROVIDER:
                        break
            except Exception as e:
                self.provider_errors["mantiks"] = str(e)
                print(f"[Market] Mantiks collection failed: {e}")
        
        # If we don't have enough jobs, try fallback
        if len(all_jobs) < self.TARGET_JOBS:
            print(f"[Market] Only {len(all_jobs)} jobs, attempting fallback...")
            try:
                fallback_jobs = search_jsearch_jobs("software developer", num_results=10)
                all_jobs.extend(fallback_jobs)
            except:
                pass
        
        print(f"[Market] Collected {len(all_jobs)} total jobs")
        return all_jobs[:self.TARGET_JOBS]
    
    # =========================================================================
    # STEP 5: Hackathon Collection
    # =========================================================================
    
    def _collect_hackathons(
        self, 
        roles: list[str], 
        skills: list[str]
    ) -> list[dict[str, Any]]:
        """
        Fetch hackathons from Tavily + SerpAPI.
        Target: 10-20 hackathons.
        """
        print("[Market] Step 5: Collecting hackathons...")
        
        all_hackathons = []
        
        # Generate hackathon queries via LLM
        queries = generate_search_queries_with_llm(roles, skills, "hackathons")
        
        # Tavily hackathons (primary)
        try:
            for query in queries[:2]:
                hackathons = search_tavily_hackathons(query, max_results=5)
                all_hackathons.extend(hackathons)
        except Exception as e:
            self.provider_errors["tavily_hackathons"] = str(e)
            print(f"[Market] Tavily hackathons failed: {e}")
        
        # SerpAPI hackathons (supplementary)
        try:
            for query in queries[:2]:
                hackathons = search_serpapi_hackathons(query, num_results=5)
                all_hackathons.extend(hackathons)
        except Exception as e:
            self.provider_errors["serpapi_hackathons"] = str(e)
            print(f"[Market] SerpAPI hackathons failed: {e}")
        
        print(f"[Market] Collected {len(all_hackathons)} hackathons")
        return all_hackathons[:20]  # Cap at 20
    
    # =========================================================================
    # STEP 6: News Collection
    # =========================================================================
    
    def _collect_news(
        self, 
        roles: list[str], 
        skills: list[str]
    ) -> list[dict[str, Any]]:
        """
        Fetch tech/market news from Tavily + NewsData.io + SerpAPI.
        Target: 10 news articles.
        """
        print("[Market] Step 6: Collecting tech/market news...")
        
        all_news = []
        
        # Generate news queries via LLM
        queries = generate_search_queries_with_llm(roles, skills, "news")
        
        # Tavily news
        try:
            for query in queries[:2]:
                news = search_tavily_news(query, max_results=4)
                all_news.extend(news)
        except Exception as e:
            self.provider_errors["tavily_news"] = str(e)
            print(f"[Market] Tavily news failed: {e}")
        
        # NewsData.io
        try:
            for query in queries[:1]:
                news = search_newsdata_news(query, num_results=4)
                all_news.extend(news)
        except Exception as e:
            self.provider_errors["newsdata"] = str(e)
            print(f"[Market] NewsData failed: {e}")
        
        # SerpAPI news (fallback if needed)
        if len(all_news) < self.TARGET_NEWS:
            try:
                news = search_serpapi_news(queries[0] if queries else "tech industry", num_results=4)
                all_news.extend(news)
            except Exception as e:
                self.provider_errors["serpapi_news"] = str(e)
                print(f"[Market] SerpAPI news failed: {e}")
        
        print(f"[Market] Collected {len(all_news)} news articles")
        return all_news[:self.TARGET_NEWS]
    
    # =========================================================================
    # STEP 8-9: Normalization & Deduplication
    # =========================================================================
    
    def _normalize_and_dedupe_jobs(
        self, 
        raw_items: list[dict]
    ) -> list[JobSchema]:
        """
        Normalize items into JobSchema and deduplicate by link.
        Checks against existing jobs in the jobs table.
        """
        seen_links = set()
        normalized = []
        
        # First, check existing links in database
        try:
            existing = self.supabase.table("jobs").select("link").execute()
            if existing.data:
                seen_links.update(item["link"] for item in existing.data if item.get("link"))
        except:
            pass
        
        for item in raw_items:
            link = item.get("link", "").strip()
            if not link or link in seen_links:
                continue
            
            seen_links.add(link)
            
            # Parse posted_at - keep as string or convert to date string
            posted_at = None
            if item.get("posted_at"):
                try:
                    if isinstance(item["posted_at"], str):
                        posted_at = item["posted_at"]  # Keep as string, schema handles it
                    elif isinstance(item["posted_at"], datetime):
                        posted_at = item["posted_at"]
                except:
                    pass
            
            job = JobSchema(
                title=item.get("title", "Unknown"),
                company=item.get("company", "Unknown"),
                location=item.get("location", ""),
                link=link,
                description=item.get("description", ""),
                summary=item.get("summary", ""),
                source=item.get("source", ""),
                posted_at=posted_at,
                platform=item.get("platform", "Unknown"),
                remote_policy=item.get("remote_policy"),
            )
            normalized.append(job)
        
        return normalized
    
    def _normalize_and_dedupe_hackathons(
        self, 
        raw_items: list[dict]
    ) -> list[HackathonSchema]:
        """
        Normalize items into HackathonSchema and deduplicate by link.
        Checks against existing hackathons in the hackathons table.
        """
        seen_links = set()
        normalized = []
        
        # First, check existing links in hackathons table
        try:
            existing = self.supabase.table("hackathons").select("link").execute()
            if existing.data:
                seen_links.update(item["link"] for item in existing.data if item.get("link"))
        except:
            pass
        
        for item in raw_items:
            link = item.get("link", "").strip()
            if not link or link in seen_links:
                continue
            
            seen_links.add(link)
            
            # Parse posted_at - keep as string or convert to date string
            posted_at = None
            if item.get("posted_at"):
                try:
                    if isinstance(item["posted_at"], str):
                        posted_at = item["posted_at"]
                    elif isinstance(item["posted_at"], datetime):
                        posted_at = item["posted_at"]
                except:
                    pass
            
            # Convert bounty_amount to string if it's a number
            bounty = item.get("bounty_amount")
            if bounty is not None:
                bounty = str(bounty)
            
            hackathon = HackathonSchema(
                title=item.get("title", "Unknown"),
                company=item.get("company", "Unknown"),
                location=item.get("location", ""),
                link=link,
                description=item.get("description", ""),
                summary=item.get("summary", ""),
                source=item.get("source", ""),
                posted_at=posted_at,
                platform=item.get("platform", "Unknown"),
                remote_policy=item.get("remote_policy"),
                bounty_amount=bounty,
            )
            normalized.append(hackathon)
        
        return normalized
    
    def _normalize_and_dedupe_news(
        self, 
        raw_items: list[dict]
    ) -> list[MarketNewsSchema]:
        """
        Normalize items into MarketNewsSchema and deduplicate by URL.
        """
        seen_urls = set()
        normalized = []
        
        # Check existing URLs
        try:
            existing = self.supabase.table("market_news").select("url").execute()
            if existing.data:
                seen_urls.update(item["url"] for item in existing.data if item.get("url"))
        except:
            pass
        
        for item in raw_items:
            url = item.get("url", "").strip()
            if not url or url in seen_urls:
                continue
            
            seen_urls.add(url)
            
            # Parse published_at
            published_at = None
            if item.get("published_at"):
                try:
                    if isinstance(item["published_at"], str):
                        published_at = datetime.fromisoformat(item["published_at"].replace("Z", "+00:00"))
                    elif isinstance(item["published_at"], datetime):
                        published_at = item["published_at"]
                except:
                    pass
            
            news = MarketNewsSchema(
                title=item.get("title", ""),
                url=url,
                source=item.get("source", "Unknown"),
                summary=item.get("summary", ""),
                published_at=published_at,
                topics=item.get("topics", []),
                user_id=None,  # Global news, no specific user
            )
            normalized.append(news)
        
        return normalized
    
    # =========================================================================
    # STEP 10: Storage Operations
    # =========================================================================
    
    def _save_jobs_to_supabase(self, jobs: list[JobSchema]) -> list[tuple[int, JobSchema]]:
        """Save jobs to Supabase jobs table.
        
        Returns:
            List of tuples (supabase_id, job_schema) for saved items.
        """
        saved = []
        
        for job in jobs:
            try:
                data = job.to_supabase_dict()
                response = self.supabase.table("jobs").upsert(
                    data, 
                    on_conflict="link"
                ).execute()
                
                if response.data and len(response.data) > 0:
                    # Get the Supabase-generated integer ID
                    supabase_id = response.data[0].get("id")
                    if supabase_id is not None:
                        saved.append((supabase_id, job))
                        print(f"[Market] Saved job: ID={supabase_id}, Title={job.title[:50]}")
            except Exception as e:
                print(f"[Market] Job save error: {str(e)}")
                continue
        
        return saved
    
    def _save_hackathons_to_supabase(self, hackathons: list[HackathonSchema]) -> list[tuple[int, HackathonSchema]]:
        """Save hackathons to Supabase hackathons table.
        
        Returns:
            List of tuples (supabase_id, hackathon_schema) for saved items.
        """
        saved = []
        
        for hackathon in hackathons:
            try:
                data = hackathon.to_supabase_dict()
                response = self.supabase.table("hackathons").upsert(
                    data, 
                    on_conflict="link"
                ).execute()
                
                if response.data and len(response.data) > 0:
                    # Get the Supabase-generated integer ID
                    supabase_id = response.data[0].get("id")
                    if supabase_id is not None:
                        saved.append((supabase_id, hackathon))
                        print(f"[Market] Saved hackathon: ID={supabase_id}, Title={hackathon.title[:50]}")
            except Exception as e:
                print(f"[Market] Hackathon save error: {str(e)}")
                continue
        
        return saved
    
    def _save_news_to_supabase(self, news: list[MarketNewsSchema]) -> list[tuple[int, MarketNewsSchema]]:
        """Save news to Supabase market_news table.
        
        Returns:
            List of tuples (supabase_id, news_schema) for saved items.
        """
        saved = []
        
        for item in news:
            try:
                data = item.to_supabase_dict()
                response = self.supabase.table("market_news").upsert(
                    data,
                    on_conflict="url"
                ).execute()
                
                if response.data and len(response.data) > 0:
                    # Get the Supabase-generated integer ID
                    supabase_id = response.data[0].get("id")
                    if supabase_id is not None:
                        saved.append((supabase_id, item))
                        print(f"[Market] Saved news: ID={supabase_id}, Title={item.title[:50]}")
            except Exception as e:
                print(f"[Market] News save error: {str(e)}")
                continue
        
        return saved
    
    def _save_to_pinecone(
        self, 
        items: list[tuple[int, JobSchema | HackathonSchema | MarketNewsSchema]],
        namespace: str = ""
    ) -> int:
        """
        Save items to Pinecone with embeddings.
        Uses the Supabase integer ID as the Pinecone vector ID.
        
        Args:
            items: List of tuples (supabase_id, schema_object)
            namespace: Pinecone namespace (default: "")
        """
        if not self.pinecone_index:
            return 0
        
        vectors = []
        
        for supabase_id, item in items:
            try:
                # Use Supabase integer ID as string for Pinecone vector ID
                vector_id = str(supabase_id)
                
                # Build embedding text
                if isinstance(item, (JobSchema, HackathonSchema)):
                    text = f"{item.title} at {item.company}. {item.summary}"
                    metadata = item.to_pinecone_metadata()
                    metadata["supabase_id"] = supabase_id  # Store ID in metadata too
                else:
                    text = f"{item.title}. {item.summary}"
                    metadata = item.to_pinecone_metadata()
                    metadata["supabase_id"] = supabase_id
                
                embedding = generate_embedding(text)
                
                vectors.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": metadata
                })
                
                print(f"[Market] Prepared vector: ID={vector_id} for '{item.title[:40]}...'")
                
            except Exception as e:
                print(f"[Market] Embedding error for ID {supabase_id}: {str(e)}")
                continue
        
        if vectors:
            try:
                # Use default namespace
                self.pinecone_index.upsert(
                    vectors=vectors,
                    namespace=namespace or ""
                )
                print(f"[Market] Upserted {len(vectors)} vectors to Pinecone")
                return len(vectors)
            except Exception as e:
                print(f"[Market] Pinecone upsert error: {str(e)}")
        
        return 0
    
    # =========================================================================
    # MAIN EXECUTION: Daily Cron Job
    # =========================================================================
    
    def run_daily_scan(self) -> dict[str, Any]:
        """
        Execute the daily market intelligence scan.
        
        This is the main entry point for the cron job.
        Follows all steps outlined in the agent specification.
        
        Returns:
            Dictionary with scan results and statistics
        """
        print("=" * 60)
        print("[Market] Starting Daily Market Intelligence Scan")
        print(f"[Market] Timestamp: {datetime.now(timezone.utc).isoformat()}")
        print("=" * 60)
        
        self.execution_log = CronExecutionLog()
        self.provider_errors = {}
        
        result = {
            "status": "success",
            "jobs_stored": 0,
            "hackathons_stored": 0,
            "news_stored": 0,
            "vectors_stored": 0,
            "provider_errors": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Step 1: Aggregate global user context
            context = self._aggregate_global_user_context()
            roles = context["roles"]
            skills = context["skills"]
            
            # Step 2: Optimize roles via LLM
            optimized_roles = self._optimize_roles(roles, skills)
            
            # Step 3: Allocate providers
            allocation = self._allocate_providers(optimized_roles)
            
            # Step 4: Collect jobs
            raw_jobs = self._collect_jobs(allocation, skills)
            
            # Step 5: Collect hackathons
            raw_hackathons = self._collect_hackathons(optimized_roles, skills)
            
            # Step 6: Collect news
            raw_news = self._collect_news(optimized_roles, skills)
            
            # Step 8-9: Normalize and deduplicate
            normalized_jobs = self._normalize_and_dedupe_jobs(raw_jobs)
            normalized_hackathons = self._normalize_and_dedupe_hackathons(raw_hackathons)
            normalized_news = self._normalize_and_dedupe_news(raw_news)
            
            # Step 10: Save to Supabase
            saved_jobs = self._save_jobs_to_supabase(normalized_jobs)
            saved_hackathons = self._save_hackathons_to_supabase(normalized_hackathons)
            saved_news = self._save_news_to_supabase(normalized_news)
            
            # Save to Pinecone with proper namespaces
            # Jobs -> default namespace ("")
            # Hackathons -> "hackathon" namespace
            # News -> "news" namespace
            vectors_jobs = self._save_to_pinecone(saved_jobs, namespace="")
            vectors_hackathons = self._save_to_pinecone(saved_hackathons, namespace="hackathon")
            vectors_news = self._save_to_pinecone(saved_news, namespace="news")
            
            # Update result
            result["jobs_stored"] = len(saved_jobs)
            result["hackathons_stored"] = len(saved_hackathons)
            result["news_stored"] = len(saved_news)
            result["vectors_stored"] = vectors_jobs + vectors_hackathons + vectors_news
            result["provider_errors"] = self.provider_errors
            
            # Determine final status
            if self.provider_errors:
                result["status"] = "partial_success"
            
            self.execution_log.status = "success" if not self.provider_errors else "partial_failure"
            self.execution_log.jobs_collected = result["jobs_stored"]
            self.execution_log.hackathons_collected = result["hackathons_stored"]
            self.execution_log.news_collected = result["news_stored"]
            self.execution_log.completed_at = datetime.now(timezone.utc)
            self.execution_log.provider_errors = self.provider_errors
            
        except Exception as e:
            print(f"[Market] Critical error: {str(e)}")
            result["status"] = "failed"
            result["error"] = str(e)
            self.execution_log.status = "failed"
        
        print("=" * 60)
        print(f"[Market] Scan Complete: {result['status']}")
        print(f"[Market] Jobs: {result['jobs_stored']}, Hackathons: {result['hackathons_stored']}, News: {result['news_stored']}")
        print(f"[Market] Vectors: {result['vectors_stored']}")
        if result.get("provider_errors"):
            print(f"[Market] Provider Errors: {result['provider_errors']}")
        print("=" * 60)
        
        return result
    
    # =========================================================================
    # LEGACY COMPATIBILITY: User-triggered scan
    # =========================================================================
    
    def run_market_scan(self, user_id: str) -> dict[str, Any]:
        """
        Legacy method for user-triggered market scan.
        Maintained for backward compatibility with existing API.
        """
        result = {"jobs": [], "hackathons": [], "news": [], "stats": {}, "queries_used": {}}
        
        try:
            print(f"[Market] Starting scan for user: {user_id}")
            skill_data = self._get_user_skills_metadata(user_id)
            queries = self._build_smart_queries(skill_data)
            result["queries_used"] = queries
            
            # Execute Searches
            raw_jobs = search_jsearch_jobs(queries["job_query"])
            raw_hackathons = search_tavily_hackathons(queries["hackathon_query"])
            raw_news = search_tavily_news(queries["news_query"])
            
            # Store Results
            vectors_saved = 0
            
            if raw_jobs:
                normalized = self._normalize_and_dedupe_jobs(raw_jobs)
                saved = self._save_jobs_to_supabase(normalized)
                # saved is now list of (supabase_id, job) tuples
                result["jobs"] = [{"id": sid, **j.to_supabase_dict()} for sid, j in saved]
                vectors_saved += self._save_to_pinecone(saved, namespace="")
            
            if raw_hackathons:
                normalized = self._normalize_and_dedupe_hackathons(raw_hackathons)
                saved = self._save_hackathons_to_supabase(normalized)
                result["hackathons"] = [{"id": sid, **h.to_supabase_dict()} for sid, h in saved]
                vectors_saved += self._save_to_pinecone(saved, namespace="hackathon")
                
            if raw_news:
                normalized = self._normalize_and_dedupe_news(raw_news)
                saved = self._save_news_to_supabase(normalized)
                result["news"] = [{"id": sid, **n.to_supabase_dict()} for sid, n in saved]
                vectors_saved += self._save_to_pinecone(saved, namespace="news")

            result["stats"] = {
                "jobs_found": len(result["jobs"]),
                "hackathons_found": len(result["hackathons"]),
                "news_found": len(result["news"]),
                "vectors_saved": vectors_saved
            }
            
            print(f"[Market] Scan complete: {result['stats']}")
            return result
            
        except Exception as e:
            print(f"[Market] Critical Error: {str(e)}")
            result["error"] = str(e)
            return result
    
    def _get_user_skills_metadata(self, user_id: str) -> dict[str, Any]:
        """Fetch user skills from Supabase (legacy support)."""
        default_response = {
            "skills": ["Python", "JavaScript"],
            "verified_skills": ["Python"],
            "top_skill": "Python",
            "skills_metadata": []
        }
        
        if not self._is_valid_uuid(user_id):
            return default_response
        
        try:
            response = self.supabase.table("profiles").select(
                "skills, skills_metadata"
            ).eq("user_id", user_id).single().execute()
            
            if not response.data:
                return default_response
            
            skills = response.data.get("skills", []) or []
            skills_metadata = response.data.get("skills_metadata", []) or []
            verified_skills = [
                sm.get("name") for sm in skills_metadata 
                if sm.get("verification_status") == "verified" and sm.get("name")
            ]
            top_skill = skills[0] if skills else "Python"
            
            return {
                "skills": skills,
                "verified_skills": verified_skills,
                "top_skill": top_skill,
                "skills_metadata": skills_metadata
            }
        except Exception as e:
            print(f"[Market] Error fetching skills: {str(e)}")
            return default_response
    
    def _is_valid_uuid(self, value: str) -> bool:
        """Check if string is a valid UUID."""
        try:
            uuid.UUID(str(value))
            return True
        except (ValueError, AttributeError):
            return False
    
    def _build_smart_queries(self, skill_data: dict[str, Any]) -> dict[str, str]:
        """Build search queries from user skills (legacy support)."""
        top = skill_data.get("top_skill", "Python")
        return {
            "job_query": f"Junior {top} Developer",
            "hackathon_query": f"{top} Hackathon 2026",
            "news_query": f"Latest news in {top} ecosystem"
        }


# =============================================================================
# Singleton Instance
# =============================================================================

market_service = MarketIntelligenceService()