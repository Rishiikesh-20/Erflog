import os
import json
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from pinecone import Pinecone
from google import genai
from google.genai import types

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
    """Initialize Pinecone and Gemini clients lazily to prevent cold-start delays."""
    global pc, index, client
    
    if not PINECONE_API_KEY or not GEMINI_API_KEY:
        raise RuntimeError("❌ CRITICAL: Missing PINECONE_API_KEY or GEMINI_API_KEY in environment.")
    
    if pc is None:
        try:
            pc = Pinecone(api_key=PINECONE_API_KEY)
            index = pc.Index(INDEX_NAME)
            logger.info(f"✅ Connected to Pinecone Index: {INDEX_NAME}")
        except Exception as e:
            logger.error(f"❌ Pinecone Connection Failed: {e}")
            raise e
            
    if client is None:
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            logger.info("✅ Connected to Google Gemini")
        except Exception as e:
            logger.error(f"❌ Gemini Connection Failed: {e}")
            raise e

# --- Core Logic: Vector Search ---

def search_jobs(user_query_text: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """
    1. Vectorizes the user's resume/query.
    2. Searches the Pinecone 'jobs' namespace (or default).
    3. Normalizes metadata to matches.
    """
    _init_clients()
    logger.info(f"🔍 Vectorizing query: '{user_query_text[:40]}...'")

    try:
        # 1. Generate Embedding (768 Dimensions for text-embedding-004)
        response = client.models.embed_content(
            model="text-embedding-004",
            contents=user_query_text,
        )
        # Handle difference in response structure between SDK versions
        user_vector = response.embeddings[0].values

        # 2. Query Pinecone
        # Note: Jobs are typically in the default namespace ("") or a specific "jobs" namespace.
        # If your seed script didn't specify a namespace, use namespace="" or remove the arg.
        search_results = index.query(
            vector=user_vector,
            top_k=top_k,
            include_metadata=True,
            namespace="" # Defaults to the global namespace where jobs usually live
        )

        matches = []
        for match in search_results['matches']:
            # 3. Normalize Data based on YOUR schema
            md = match.get('metadata', {})
            
            job_obj = {
                "id": str(md.get("job_id", match['id'])), # Fallback to Pinecone ID if job_id missing
                "score": match['score'],
                "title": md.get("title", "Unknown Role"),
                "company": md.get("company", "Unknown Company"),
                "description": md.get("summary", md.get("description", "No description available.")),
                "link": md.get("link", "#"),
                "tier": "C" # Default Tier
            }
            matches.append(job_obj)

        logger.info(f"✅ Found {len(matches)} raw matches.")
        return matches

    except Exception as e:
        logger.error(f"❌ Search Failed: {e}")
        return []

# --- Core Logic: Gap Analysis (Gemini) ---

def generate_gap_roadmap(user_skills_text: str, job_description: str) -> Dict[str, Any]:
    """
    Generates a structured Learning Roadmap for Tier B candidates.
    Uses a High-Fidelity Prompt for actionable results.
    """
    _init_clients()
    logger.info("🚧 Triggering Gap Analysis & Roadmap Generation...")

    # The "World-Class" Prompt
    prompt = f"""
    ROLE: You are the Chief Technical Architect and Career Strategist at an elite tech consultancy.
    
    OBJECTIVE: 
    Perform a ruthless, precise Gap Analysis between a Candidate's Profile and a Target Job Description.
    If gaps exist, engineer a high-velocity "3-Day Micro-Roadmap" to bridge them.
    
    --- CONTEXT ---
    CANDIDATE PROFILE: 
    "{user_skills_text[:2000]}"
    
    TARGET JOB: 
    "{job_description[:2000]}"
    
    --- INSTRUCTIONS ---
    1. GAP IDENTIFICATION: Identify exactly 3 critical technical skills the candidate is missing or needs to polish. Be specific (e.g., instead of "AWS", say "AWS Lambda & API Gateway").
    2. RESOURCE CURATION: For each day, provide:
       - A specific conceptual topic.
       - A "Task" (Actionable exercise).
       - One OFFICIAL DOCUMENTATION link (e.g., React Docs, Python Docs).
       - One YOUTUBE SEARCH QUERY URL.
    
    3. FORMATTING: Return ONLY raw JSON. No Markdown. No preambles.
    
    --- JSON STRUCTURE ---
    {{
      "analysis_summary": "One sentence summary of why this is a 'Reach' job.",
      "missing_skills": ["Specific Skill 1", "Specific Skill 2", "Specific Skill 3"],
      "roadmap": [
        {{
          "day": 1,
          "focus": "Skill 1 Name",
          "topic": "Deep dive into...",
          "task": "Build a mini-prototype that...",
          "resources": [
             {{ "label": "Official Docs", "url": "https://..." }},
             {{ "label": "Video Tutorial", "url": "https://www.youtube.com/results?search_query=specific+query+here" }}
          ]
        }},
        ... (Day 2 and 3)
      ]
    }}
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json" # Enforce JSON mode
            )
        )
        
        # Parse Response
        raw_text = response.text.strip()
        # Cleanup if model adds markdown blocks despite config
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:-3]
            
        roadmap_data = json.loads(raw_text)
        logger.info("✅ Roadmap Generated Successfully.")
        return roadmap_data

    except Exception as e:
        logger.error(f"❌ Roadmap Generation Error: {e}")
        # Fail-safe Fallback
        return {
            "analysis_summary": "Automated analysis currently unavailable.",
            "missing_skills": ["Key Tech Stack Analysis"],
            "roadmap": []
        }

# --- Core Logic: The Strategist Orchestrator ---

def process_career_strategy(user_query: str) -> Dict[str, Any]:
    """
    The Main Entry Point for Agent 3.
    Orchestrates Search -> Classification (Tiers) -> Gap Analysis.
    """
    # 1. Search
    raw_matches = search_jobs(user_query)
    
    processed_results = []
    
    # 2. Classify & Enrich
    for job in raw_matches:
        score = job['score']
        
        # --- TIER A: READY (> 85%) ---
        if score >= 0.85:
            job['tier'] = "A"
            job['status'] = "Ready to Deploy"
            job['action'] = "Auto-Apply"
            job['ui_color'] = "green"
            job['roadmap'] = None # No roadmap needed
            
        # --- TIER B: REACH (60% - 84%) ---
        elif 0.60 <= score < 0.85:
            job['tier'] = "B"
            job['status'] = "Gap Detected"
            job['action'] = "View Roadmap"
            job['ui_color'] = "orange"
            
            # 🚀 Trigger GenAI for Roadmap
            # We pass the user query + job summary to the generator
            job['roadmap'] = generate_gap_roadmap(user_query, job['description'])
            
        # --- TIER C: DISCARD (< 60%) ---
        else:
            job['tier'] = "C"
            job['status'] = "Low Match"
            job['action'] = "Ignore"
            job['ui_color'] = "gray"
            job['roadmap'] = None
        
        # Only add Tier A and B to final display (Filter out noise if desired, or keep all)
        if score >= 0.50: 
            processed_results.append(job)

    # Sort by Score Descending
    processed_results.sort(key=lambda x: x['score'], reverse=True)

    return {
        "status": "success",
        "matches_found": len(processed_results),
        "strategy_report": processed_results
    }