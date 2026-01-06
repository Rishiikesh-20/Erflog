import os
import json
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from pinecone import Pinecone
from google import genai
from google.genai import types
import numpy as np
from .roadmap import generate_gap_roadmap
load_dotenv()

logger = logging.getLogger("Agent3")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "ai-verse")

pc: Optional[Pinecone] = None
index = None
client: Optional[genai.Client] = None

def _init_clients():
    global pc, index, client
    
    if not PINECONE_API_KEY or not GEMINI_API_KEY:
        raise RuntimeError("Missing API Keys")
    
    if pc is None:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        index = pc.Index(INDEX_NAME)
            
    if client is None:
        client = genai.Client(api_key=GEMINI_API_KEY)

def search_jobs(user_query_text: str, top_k: int = 10) -> List[Dict[str, Any]]:
    _init_clients()

    try:
        response = client.models.embed_content(
            model="text-embedding-004",
            contents=user_query_text,
        )
        user_vector = response.embeddings[0].values

        search_results = index.query(
            vector=user_vector,
            top_k=top_k,
            include_metadata=True,
            namespace="" 
        )

        matches = []
        for match in search_results['matches']:
            md = match.get('metadata', {})
            job_obj = {
                "id": match['id'],  # Use the actual Pinecone ID (e.g., "hackathon_13")
                "score": match['score'],
                "title": md.get("title", "Unknown Role"),
                "company": md.get("company", md.get("company_name", "Unknown Company")),
                "description": md.get("summary", md.get("description", "No description available.")),
                "link": md.get("link", md.get("link_to_apply", "#")),
                "tier": "C"
            }
            matches.append(job_obj)

        return matches
    except Exception as e:
        logger.error(f"Search Failed: {e}")
        return []

def generate_gap_roadmap(user_skills_text: str, job_description: str) -> Dict[str, Any]:
    _init_clients()

    prompt = f"""
    ROLE: Elite Technical Career Strategist.
    OBJECTIVE: Gap Analysis & 3-Day Micro-Roadmap.
    
    CANDIDATE: "{user_skills_text[:1500]}"
    JOB: "{job_description[:1500]}"
    
    TASK:
    1. Identify 3 missing skills.
    2. Create a 3-Day Roadmap (Topic, Task, 1 Doc Link, 1 YouTube Search Link).
    
    OUTPUT JSON:
    {{
      "missing_skills": ["Skill 1", "Skill 2"],
      "roadmap": [
        {{
          "day": 1,
          "topic": "...",
          "task": "...",
          "resources": [
             {{ "name": "Docs", "url": "https://..." }},
             {{ "name": "Video", "url": "https://www.youtube.com/results?search_query=..." }}
          ]
        }}
      ]
    }}
    RETURN JSON ONLY.
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"Roadmap Generation Error: {e}")
        return None

def get_interview_gap_analysis(job_id: str, user_id: str) -> Dict[str, Any]:
    _init_clients()
    
    try:
        # Clean job_id (remove .0 suffix if present)
        job_id_clean = str(int(float(job_id)))
        print(f"[Agent3] Fetching job_id={job_id_clean} from Pinecone (namespace='')")
        
        job_fetch = index.fetch(ids=[job_id_clean], namespace="")
        job_vector = None
        job_metadata = {}
        
        if job_fetch and job_fetch.get('vectors'):
            job_data = job_fetch['vectors'].get(job_id_clean)
            if job_data:
                job_vector = job_data.get('values')
                job_metadata = job_data.get('metadata', {})
                print(f"[Agent3] ✅ Found job: {job_metadata.get('title', 'Unknown')}")
            else:
                print(f"[Agent3] ❌ Job {job_id_clean} not in fetch result. Available IDs: {list(job_fetch['vectors'].keys())}")
        else:
            print(f"[Agent3] ❌ Empty fetch result for job {job_id_clean}")
        
        if not job_vector:
            print(f"[Agent3] ⚠️ Job {job_id_clean} not found in Pinecone, returning Unknown")
            
            # List some available jobs to help debug (use 768 dimensions for this index)
            try:
                sample_query = index.query(
                    vector=[0.1] * 768,  # Match index dimension (768 not 1536)
                    top_k=5,
                    namespace="",
                    include_metadata=True
                )
                if sample_query and sample_query.get('matches'):
                    available_jobs = [f"{m['id']}:{m.get('metadata', {}).get('title', 'No Title')}" for m in sample_query['matches'][:5]]
                    print(f"[Agent3] 💡 Sample available jobs: {available_jobs}")
            except Exception as e:
                print(f"[Agent3] Could not fetch sample jobs: {e}")
            
            return {
                "job": {"title": "Unknown", "company": "Unknown", "description": "", "summary": ""},
                "user": {"name": "Unknown", "skills": [], "summary": ""},
                "similarity_score": 0.0,
                "gap_analysis": {}
            }
        
        print(f"[Agent3] Fetching user_id={user_id} from Pinecone (namespace='users')")
        user_fetch = index.fetch(ids=[str(user_id)], namespace="users")
        user_vector = None
        user_metadata = {}
        
        if user_fetch and user_fetch.get('vectors'):
            user_data = user_fetch['vectors'].get(str(user_id))
            if user_data:
                user_vector = user_data.get('values')
                user_metadata = user_data.get('metadata', {})
                print(f"[Agent3] ✅ Found user: {user_metadata.get('name', 'Unknown')}")
            else:
                print(f"[Agent3] ❌ User not in fetch result")
        else:
            print(f"[Agent3] ❌ Empty fetch result for user")
        
        if not user_vector:
            print(f"[Agent3] ⚠️ User {user_id} not found in Pinecone")
            return {
                "job": job_metadata,
                "user": {"name": "Unknown"},
                "similarity_score": 0.0,
                "gap_analysis": {}
            }
        
        job_vec = np.array(job_vector)
        user_vec = np.array(user_vector)
        
        similarity = np.dot(job_vec, user_vec) / (np.linalg.norm(job_vec) * np.linalg.norm(user_vec))
        similarity_score = float(similarity)
        
        job_title = job_metadata.get("title", "Unknown Position")
        job_company = job_metadata.get("company", "Unknown Company")
        job_desc = job_metadata.get("description") or job_metadata.get("summary", "")
        
        user_name = user_metadata.get("name", "Candidate")
        user_skills = user_metadata.get("skills", [])
        if isinstance(user_skills, str):
            user_skills = [s.strip() for s in user_skills.split(",")]
        
        skills_text = ", ".join(user_skills) if user_skills else "Not specified"
        
        gap_prompt = f"""
        ROLE: Technical Gap Analyzer
        JOB: {job_title} at {job_company}
        DESC: {job_desc[:1000]}
        CANDIDATE: {user_name}
        SKILLS: {skills_text}
        SCORE: {similarity_score:.2%}
        
        TASK: Identify missing skills based on score.
        - >85%: 1-2 minor gaps
        - 50-85%: 2-3 key gaps
        - <50%: 3-4 critical gaps
        
        RETURN JSON:
        {{
            "missing_skills": ["skill1", "skill2"],
            "weak_areas": ["area1", "area2"],
            "suggested_questions": ["Question 1?", "Question 2?"],
            "match_tier": "A/B/C"
        }}
        """
        
        gap_response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=gap_prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        gap_text = gap_response.text.replace("```json", "").replace("```", "").strip()
        gap_analysis = json.loads(gap_text)
        
        # Ensure gap_analysis is a dict, not a list
        if not isinstance(gap_analysis, dict):
            print(f"[Agent3] ⚠️ gap_analysis is not a dict: {type(gap_analysis)}, using empty dict")
            gap_analysis = {
                "missing_skills": [],
                "weak_areas": [],
                "suggested_questions": [],
                "match_tier": "B"
            }
        
        return {
            "job": {
                "title": job_title,
                "company": job_company,
                "description": job_desc,
                "summary": job_metadata.get("summary", "")
            },
            "user": {
                "name": user_name,
                "skills": user_skills,
                "summary": user_metadata.get("experience_summary", "")
            },
            "similarity_score": similarity_score,
            "gap_analysis": gap_analysis
        }
        
    except Exception as e:
        logger.error(f"Agent 3 Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

def process_career_strategy(user_skills: str, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
    _init_clients()

    if not jobs:
        return {"error": "No jobs to analyze"}

    top_jobs = jobs[:3]
    job_info = "\n".join([
        f"- {j['title']} at {j['company']} (Score: {j['score']:.2f})"
        for j in top_jobs
    ])

    prompt = f"""
    CANDIDATE SKILLS: {user_skills[:1000]}
    TOP JOBS:
    {job_info}
    
    Provide brief career strategy advice in JSON:
    {{
        "recommended_job": "title",
        "reason": "1 sentence why",
        "next_steps": ["step1", "step2"]
    }}
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text.replace("```json", "").replace("```", "").strip())
    except Exception as e:
        logger.error(f"Strategy Error: {e}")
        return {"error": str(e)}