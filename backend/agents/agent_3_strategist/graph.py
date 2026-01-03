import os
import json
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from pinecone import Pinecone
from google import genai
from google.genai import types

# Import the new roadmap generator
from .roadmap import generate_gap_roadmap

# --- Configuration & Setup ---
load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [Agent 3] - %(levelname)s - %(message)s')
logger = logging.getLogger("Agent3")

# Environment Variables
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "ai-verse")

# Global Clients (Lazy Loading)
pc: Optional[Pinecone] = None
index = None
client: Optional[genai.Client] = None

def _init_clients():
    """Initialize Pinecone and Gemini clients lazily."""
    global pc, index, client
    
    if not PINECONE_API_KEY or not GEMINI_API_KEY:
        raise RuntimeError("❌ CRITICAL: Missing PINECONE_API_KEY or GEMINI_API_KEY.")
    
    if pc is None:
        try:
            pc = Pinecone(api_key=PINECONE_API_KEY)
            index = pc.Index(INDEX_NAME)
        except Exception as e:
            logger.error(f"❌ Pinecone Connection Failed: {e}")
            raise e
            
    if client is None:
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
        except Exception as e:
            logger.error(f"❌ Gemini Connection Failed: {e}")
            raise e

# --- Core Logic: Vector Search ---

def search_jobs(user_query_text: str, top_k: int = 10) -> List[Dict[str, Any]]:
    _init_clients()
    logger.info(f"🔍 Vectorizing query: '{user_query_text[:40]}...'")

    try:
        response = client.models.embed_content(
            model="text-embedding-004",
            contents=user_query_text,
        )
        user_vector = response.embeddings[0].values

        # Query Pinecone
        search_results = index.query(
            vector=user_vector,
            top_k=top_k,
            include_metadata=True,
            namespace="" 
        )

        matches = []
        for match in search_results['matches']:
            md = match.get('metadata', {})
            # Normalize Schema
            job_obj = {
                "id": str(md.get("job_id", match['id'])),
                "score": match['score'],
                "title": md.get("title", "Unknown Role"),
                "company": md.get("company", md.get("company_name", "Unknown Company")),
                "description": md.get("summary", md.get("description", "No description available.")),
                "link": md.get("link", md.get("link_to_apply", "#")),
                "tier": "C" # Default
            }
            matches.append(job_obj)

        return matches
    except Exception as e:
        logger.error(f"❌ Search Failed: {e}")
        return []

def process_career_strategy(user_query: str, max_jobs: int = 5) -> Dict[str, Any]:
    """
    Main Orchestrator with ADJUSTED THRESHOLDS.
    Limited to 5 jobs for faster response.
    Only generates roadmap for top 2 Tier B jobs.
    """
    raw_matches = search_jobs(user_query, top_k=max_jobs)  # Limit search to 5
    processed_results = []
    tier_b_count = 0  # Track Tier B jobs that got roadmaps
    
    for job in raw_matches:
        score = job['score']
        
        # --- TIER A: READY (> 85%) ---
        if score >= 0.85:
            job['tier'] = "A"
            job['status'] = "Ready to Deploy"
            job['action'] = "Auto-Apply"
            job['ui_color'] = "green"
            job['roadmap_details'] = None 
            
        # --- TIER B: REACH (40% - 85%) --- 
        elif 0.40 <= score < 0.85:
            job['tier'] = "B"
            job['status'] = "Gap Detected"
            job['action'] = "Start Roadmap"
            job['ui_color'] = "orange"
            
            # Only generate roadmap for top 2 Tier B jobs (expensive API call)
            if tier_b_count < 2:
                job['roadmap_details'] = generate_gap_roadmap(user_query, job['description'])
                tier_b_count += 1
            else:
                job['roadmap_details'] = None  # Skip roadmap for remaining Tier B
            
        # --- TIER C: DISCARD (< 40%) ---
        else:
            job['tier'] = "C"
            job['status'] = "Low Match"
            job['action'] = "Ignore"
            job['ui_color'] = "gray"
            job['roadmap_details'] = None
        
        # Filter noise (Keep jobs > 30%)
        if score >= 0.30: 
            processed_results.append(job)

    # Sort matches by score
    processed_results.sort(key=lambda x: x['score'], reverse=True)

    return {
        "status": "success",
        "matches_found": len(processed_results),
        "strategy_report": processed_results
    }