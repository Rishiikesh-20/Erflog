# backend/agents/agent_2_market/service.py

"""
Agent 2: Market Sentinel - Service Layer
Strategy: JSearch for Jobs, Tavily for Hackathons/News.
"""

import os
from typing import Any
from supabase import create_client
from pinecone import Pinecone, ServerlessSpec

# Import tools (Zyte removed)
from .tools import (
    search_jsearch_jobs, 
    search_tavily, 
    generate_embedding
)

class MarketService:
    """Service class for Market Sentinel agent operations."""
    
    def __init__(self):
        # Initialize Supabase client
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.supabase = create_client(self.supabase_url, self.supabase_key)
        
        # Initialize Pinecone
        self.pinecone_index = self._init_pinecone()
    
    def _init_pinecone(self):
        """Initialize and return Pinecone index."""
        try:
            api_key = os.getenv("PINECONE_API_KEY")
            if not api_key:
                print("[Market] PINECONE_API_KEY not found")
                return None
            
            index_name = os.getenv("PINECONE_INDEX_NAME", "career-flow-jobs")
            pc = Pinecone(api_key=api_key)
            
            if index_name not in pc.list_indexes().names():
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
    
    def _get_user_skills_metadata(self, user_id: str) -> dict[str, Any]:
        """Fetch user skills from Supabase."""
        default_response = {
            "skills": ["Python", "JavaScript"],
            "verified_skills": ["Python"],
            "top_skill": "Python",
            "skills_metadata": []
        }
        
        # Handle test/dummy IDs gracefully
        if not self._is_valid_uuid(user_id):
            return default_response
        
        try:
            response = self.supabase.table("profiles").select(
                "skills, skills_metadata"
            ).eq("user_id", user_id).single().execute()
            
            if not response.data: return default_response
            
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
        import uuid
        try:
            uuid.UUID(str(value))
            return True
        except (ValueError, AttributeError):
            return False
    
    def _build_smart_queries(self, skill_data: dict[str, Any]) -> dict[str, str]:
        top = skill_data.get("top_skill", "Python")
        return {
            "job_query": f"Junior {top} Developer",
            "hackathon_query": f"{top} Hackathon 2026",
            "news_query": f"Latest news in {top} ecosystem"
        }
    
    def _save_jobs_to_db(self, items: list[dict], item_type: str) -> list[dict]:
        """Save jobs/hackathons to Supabase (Table: jobs)."""
        saved_items = []
        for item in items:
            try:
                link = item.get("link", "").strip()
                if not link: continue
                
                job_data = {
                    "title": item.get("title", "Unknown"),
                    "company": item.get("company", "Unknown"),
                    "link": link,  # Uses 'link' column per schema
                    "summary": item.get("summary", "")[:1000],
                    "type": item_type,
                    "platform": item.get("platform", "Unknown"),
                    "location": item.get("location", ""),
                }
                if item_type == "hackathon" and item.get("bounty_amount"):
                    job_data["bounty_amount"] = item.get("bounty_amount")
                
                # Upsert on 'link'
                response = self.supabase.table("jobs").upsert(
                    job_data, on_conflict="link"
                ).execute()
                
                if response.data:
                    saved = response.data[0]
                    saved["description"] = item.get("description", "")
                    saved_items.append(saved)
            except Exception as e:
                print(f"[Market] Job Save Error: {str(e)}")
                continue
        return saved_items

    def _save_news_to_db(self, news_items: list[dict]) -> list[dict]:
        """Save news to Supabase (Table: market_news)."""
        saved_news = []
        for item in news_items:
            try:
                link = item.get("link", "").strip()
                if not link: continue

                news_data = {
                    "title": item.get("title", ""),
                    # MAPPING: API sends 'link', DB expects 'url' (based on your schema)
                    "url": link, 
                    "summary": item.get("summary", ""),
                    "source": item.get("source", ""),
                    "published_at": item.get("published_at"),
                }
                
                # Upsert on 'url' (Ensure this column is UNIQUE in DB)
                response = self.supabase.table("market_news").upsert(
                    news_data, on_conflict="url"
                ).execute()
                
                if response.data:
                    saved_news.append(response.data[0])
            except Exception as e:
                print(f"[Market] News Save Error: {str(e)}")
                continue
        return saved_news

    def _save_vectors_to_pinecone(self, items: list[dict], item_type: str) -> int:
        if not self.pinecone_index: return 0
        vectors = []
        for item in items:
            try:
                text = f"{item['title']} at {item['company']}. {item.get('summary', '')}"
                embedding = generate_embedding(text)
                metadata = {
                    "item_id": item["id"],
                    "type": item_type,
                    "title": item["title"],
                    "company": item["company"],
                    "link": item.get("link") or item.get("url", ""),
                    "summary": item.get("summary", "")[:500]
                }
                vectors.append({"id": f"{item_type}_{item['id']}", "values": embedding, "metadata": metadata})
            except Exception: continue
        
        if vectors:
            try:
                self.pinecone_index.upsert(vectors=vectors)
                return len(vectors)
            except Exception: pass
        return 0

    def run_market_scan(self, user_id: str) -> dict[str, Any]:
        """Execute Instant Search Only (No Zyte)."""
        result = {"jobs": [], "hackathons": [], "news": [], "stats": {}, "queries_used": {}}
        
        try:
            print(f"[Market] Starting scan for user: {user_id}")
            skill_data = self._get_user_skills_metadata(user_id)
            queries = self._build_smart_queries(skill_data)
            result["queries_used"] = queries
            
            # Execute Searches
            raw_jobs = search_jsearch_jobs(queries["job_query"])
            raw_hackathons = search_tavily(queries["hackathon_query"], search_type="hackathon")
            raw_news = search_tavily(queries["news_query"], search_type="news")
            
            # Store Results
            vectors_saved = 0
            
            if raw_jobs:
                saved = self._save_jobs_to_db(raw_jobs, "job")
                result["jobs"] = saved
                vectors_saved += self._save_vectors_to_pinecone(saved, "job")
            
            if raw_hackathons:
                saved = self._save_jobs_to_db(raw_hackathons, "hackathon")
                result["hackathons"] = saved
                vectors_saved += self._save_vectors_to_pinecone(saved, "hackathon")
                
            if raw_news:
                saved = self._save_news_to_db(raw_news)
                result["news"] = saved
                # News usually doesn't need vectors, but you can add if needed

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

# Singleton
market_service = MarketService()