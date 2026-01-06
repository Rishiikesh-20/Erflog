# backend/agents/agent_3_strategist/orchestrator.py

"""
Agent 3 + Agent 4 Orchestrator using LangGraph

This orchestrator handles the complete daily workflow:
1. Fetch jobs, hackathons, news for each user (Agent 3)
2. For jobs with match < 80%, generate roadmaps
3. For all jobs, generate default application text (Agent 4)
4. For all jobs, generate tailored LaTeX resume and upload to Supabase (Agent 4)
5. Store everything in today_data table

The cron job will call this orchestrator once per day.
After initial processing, no further processing takes place.
"""

import os
import json
import logging
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger("Orchestrator")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# =============================================================================
# STATE DEFINITION
# =============================================================================

class OrchestratorState(TypedDict):
    """State for the orchestration workflow."""
    user_id: str
    user_profile: Dict[str, Any]
    user_vector: List[float]
    
    # Fetched data
    jobs: List[Dict[str, Any]]
    hackathons: List[Dict[str, Any]]
    news: List[Dict[str, Any]]
    hot_skills: List[Dict[str, Any]]
    
    # Processed data (enriched jobs with roadmaps and application text)
    enriched_jobs: List[Dict[str, Any]]
    
    # Status
    status: str
    error: Optional[str]


# =============================================================================
# GEMINI CLIENT
# =============================================================================

_client: Optional[genai.Client] = None

def get_gemini_client() -> genai.Client:
    """Get or create Gemini client."""
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY not set")
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


# =============================================================================
# ROADMAP GENERATION (Enhanced from Agent 3)
# =============================================================================

def generate_roadmap_for_job(
    user_skills: List[str],
    job: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate a 3-day learning roadmap for a job.
    Returns a structured roadmap with nodes/edges for visualization.
    """
    client = get_gemini_client()
    
    job_title = job.get("title", "Unknown Position")
    job_company = job.get("company", "Unknown Company")
    job_description = job.get("summary", "") or job.get("description", "")
    match_score = job.get("score", 0)
    
    skills_text = ", ".join(user_skills) if user_skills else "Not specified"
    
    prompt = f"""You are an expert Technical Curriculum Architect specializing in skill gap analysis.

TASK: Create a 3-day intensive learning roadmap as a DIRECTED ACYCLIC GRAPH (DAG).

CONTEXT:
- Job: {job_title} at {job_company}
- Match Score: {match_score:.1%}
- Candidate Skills: {skills_text}
- Job Requirements: {job_description[:1500]}

REQUIREMENTS:
1. Identify 4-6 critical learning topics/concepts the candidate needs
2. Create a dependency graph showing learning order
3. Distribute topics across 3 days (day 1, 2, 3)
4. Include practical resources (official docs + YouTube search links)

OUTPUT FORMAT (JSON ONLY):
{{
    "missing_skills": ["Skill 1", "Skill 2", "Skill 3"],
    "match_percentage": {match_score * 100:.0f},
    "graph": {{
        "nodes": [
            {{
                "id": "node1",
                "label": "Topic Name",
                "day": 1,
                "type": "concept",
                "description": "What will be learned and why"
            }},
            {{
                "id": "node2", 
                "label": "Practical Implementation",
                "day": 2,
                "type": "practice",
                "description": "Hands-on exercises"
            }},
            {{
                "id": "node3",
                "label": "Project Application",
                "day": 3,
                "type": "project",
                "description": "Build something real"
            }}
        ],
        "edges": [
            {{ "source": "node1", "target": "node2" }},
            {{ "source": "node2", "target": "node3" }}
        ]
    }},
    "resources": {{
        "node1": [
            {{ "name": "Official Docs", "url": "https://..." }},
            {{ "name": "Video Tutorial", "url": "https://www.youtube.com/results?search_query=..." }}
        ]
    }},
    "estimated_hours": 12,
    "focus_areas": ["Area 1", "Area 2"]
}}

Return ONLY valid JSON, no markdown, no explanations."""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        text = response.text.replace("```json", "").replace("```", "").strip()
        roadmap = json.loads(text)
        
        # Validate structure
        if "graph" not in roadmap or "nodes" not in roadmap.get("graph", {}):
            raise ValueError("Invalid roadmap structure")
        
        logger.info(f"✅ Generated roadmap for {job_title}: {len(roadmap['graph']['nodes'])} nodes")
        return roadmap
        
    except Exception as e:
        logger.error(f"❌ Roadmap generation failed for {job_title}: {e}")
        # Return fallback roadmap
        return {
            "missing_skills": ["Core Job Requirements"],
            "match_percentage": match_score * 100,
            "graph": {
                "nodes": [
                    {"id": "node1", "label": "Study Job Requirements", "day": 1, "type": "concept", "description": "Understand key requirements"},
                    {"id": "node2", "label": "Practice Core Skills", "day": 2, "type": "practice", "description": "Hands-on exercises"},
                    {"id": "node3", "label": "Build Portfolio Project", "day": 3, "type": "project", "description": "Apply learnings"}
                ],
                "edges": [
                    {"source": "node1", "target": "node2"},
                    {"source": "node2", "target": "node3"}
                ]
            },
            "resources": {
                "node1": [{"name": "Job Posting", "url": "#"}]
            },
            "estimated_hours": 12,
            "focus_areas": ["Technical Skills"]
        }


# =============================================================================
# APPLICATION TEXT GENERATION (Agent 4)
# =============================================================================

def generate_application_text(
    user_profile: Dict[str, Any],
    job: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate default application text for a job.
    Returns copy-paste ready responses for common application questions.
    """
    client = get_gemini_client()
    
    job_title = job.get("title", "Position")
    job_company = job.get("company", "Company")
    job_description = job.get("summary", "") or job.get("description", "")
    
    user_name = user_profile.get("name", "Candidate")
    user_skills = user_profile.get("skills", [])
    user_experience = user_profile.get("experience_summary", "")
    
    skills_text = ", ".join(user_skills[:10]) if isinstance(user_skills, list) else str(user_skills)
    
    prompt = f"""You are an expert career coach helping craft compelling job application responses.

CONTEXT:
- Candidate: {user_name}
- Skills: {skills_text}
- Experience: {user_experience[:500]}
- Target Job: {job_title} at {job_company}
- Job Description: {job_description[:1000]}

TASK: Generate professional, personalized responses for common application questions.

OUTPUT FORMAT (JSON ONLY):
{{
    "why_this_company": "2-3 sentences explaining genuine interest in {job_company}...",
    "why_this_role": "2-3 sentences on why this {job_title} role is ideal...",
    "short_intro": "Elevator pitch - 2-3 sentences introducing yourself...",
    "cover_letter_opening": "Compelling first paragraph for cover letter...",
    "cover_letter_body": "Main paragraph highlighting relevant experience...",
    "cover_letter_closing": "Professional closing paragraph with call to action...",
    "key_achievements": ["Achievement 1 relevant to this role", "Achievement 2", "Achievement 3"],
    "questions_for_interviewer": ["Thoughtful question 1 about the role", "Question 2 about company/team"]
}}

Make responses specific to the job and company. Be professional but personable.
Return ONLY valid JSON."""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        text = response.text.replace("```json", "").replace("```", "").strip()
        application_text = json.loads(text)
        
        logger.info(f"✅ Generated application text for {job_title} at {job_company}")
        return application_text
        
    except Exception as e:
        logger.error(f"❌ Application text generation failed: {e}")
        return {
            "why_this_company": f"I am excited about the opportunity at {job_company}.",
            "why_this_role": f"The {job_title} position aligns well with my career goals.",
            "short_intro": f"I am a professional with experience relevant to this role.",
            "cover_letter_opening": f"I am writing to express my interest in the {job_title} position.",
            "cover_letter_body": "My background and skills make me a strong candidate.",
            "cover_letter_closing": "I look forward to discussing how I can contribute to your team.",
            "key_achievements": ["Relevant achievement"],
            "questions_for_interviewer": ["What does success look like in this role?"]
        }


# =============================================================================
# TAILORED RESUME GENERATION (Agent 4 - LaTeX)
# =============================================================================

def generate_tailored_resume(
    user_id: str,
    job: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate a tailored LaTeX resume for a specific job using Agent 4's engine.
    
    This function:
    1. Downloads the user's original resume PDF
    2. Extracts and structures content
    3. Optimizes content for the job description
    4. Renders LaTeX template
    5. Compiles PDF
    6. Uploads to Supabase storage
    
    Args:
        user_id: The user's UUID
        job: Job dictionary with title, company, description, etc.
    
    Returns:
        Dictionary with status, pdf_url (if success), or error message
    """
    try:
        # Import Agent 4's mutate function (relative import from sibling package)
        from agents.agent_4_operative.tools import mutate_resume_for_job
        
        # Build job description string for the optimizer
        job_title = job.get("title", "Position")
        job_company = job.get("company", "Company")
        job_description = job.get("summary", "") or job.get("description", "")
        job_requirements = job.get("requirements", [])
        
        # Build comprehensive job description
        if isinstance(job_requirements, list):
            requirements_text = "\n".join(f"- {req}" for req in job_requirements)
        else:
            requirements_text = str(job_requirements) if job_requirements else ""
        
        full_job_description = f"""
Job Title: {job_title}
Company: {job_company}

Description:
{job_description}

Requirements:
{requirements_text}
"""
        
        logger.info(f"🎨 Generating tailored resume for {job_title} at {job_company}")
        
        # Call Agent 4's mutate function
        result = mutate_resume_for_job(user_id, full_job_description)
        
        if result.get("status") == "success":
            logger.info(f"✅ Resume generated and uploaded: {result.get('pdf_url', 'N/A')[:60]}...")
            return result
        else:
            logger.error(f"❌ Resume mutation failed: {result.get('message', 'Unknown error')}")
            return result
            
    except ImportError as e:
        logger.error(f"❌ Failed to import Agent 4 tools: {e}")
        return {"status": "error", "message": f"Import error: {e}"}
    except Exception as e:
        logger.error(f"❌ Tailored resume generation failed: {e}")
        return {"status": "error", "message": str(e)}


# =============================================================================
# LANGGRAPH NODES
# =============================================================================

def enrich_jobs_node(state: OrchestratorState) -> dict:
    """
    Process all jobs:
    - Jobs with score >= 0.80: No roadmap needed (high match)
    - Jobs with score < 0.80: Generate roadmap
    - All jobs: Generate default application text
    
    Note: Resume generation is user-triggered (not part of cron) to avoid heavy processing.
    """
    jobs = state.get("jobs", [])
    user_id = state.get("user_id")
    user_profile = state.get("user_profile", {})
    user_skills = user_profile.get("skills", [])
    
    if not jobs:
        logger.warning("No jobs to enrich")
        return {"enriched_jobs": [], "status": "no_jobs"}
    
    enriched_jobs = []
    
    for idx, job in enumerate(jobs):
        score = job.get("score", 0)
        job_id = job.get("id", "unknown")
        job_title = job.get("title", "Position")
        job_company = job.get("company", "Company")
        
        logger.info(f"Processing job {idx+1}/{len(jobs)}: {job_title} at {job_company} (score: {score:.2%})")
        
        enriched_job = {**job}
        
        # Generate roadmap only for jobs with match < 80%
        if score < 0.80:
            logger.info(f"  → Generating roadmap (score {score:.1%} < 80%)")
            enriched_job["roadmap"] = generate_roadmap_for_job(user_skills, job)
            enriched_job["needs_improvement"] = True
        else:
            logger.info(f"  → High match ({score:.1%} >= 80%), no roadmap needed")
            enriched_job["roadmap"] = None
            enriched_job["needs_improvement"] = False
        
        # Generate application text for ALL jobs
        logger.info(f"  → Generating application text")
        enriched_job["application_text"] = generate_application_text(user_profile, job)
        
        # Resume URL is null - user will generate on-demand via Apply page
        enriched_job["resume_url"] = None
        
        enriched_jobs.append(enriched_job)
    
    logger.info(f"✅ Enriched {len(enriched_jobs)} jobs")
    return {"enriched_jobs": enriched_jobs, "status": "enriched"}


def finalize_node(state: OrchestratorState) -> dict:
    """
    Final node - prepare data for storage.
    """
    enriched_jobs = state.get("enriched_jobs", [])
    
    # Count statistics
    jobs_with_roadmap = sum(1 for j in enriched_jobs if j.get("roadmap"))
    high_match_jobs = sum(1 for j in enriched_jobs if not j.get("needs_improvement"))
    
    logger.info(f"📊 Final Stats: {len(enriched_jobs)} jobs total")
    logger.info(f"   - High match (≥80%): {high_match_jobs}")
    logger.info(f"   - Need improvement: {jobs_with_roadmap}")
    
    return {"status": "complete"}


# =============================================================================
# BUILD GRAPH
# =============================================================================

def build_orchestrator_graph() -> StateGraph:
    """Build the orchestrator workflow graph."""
    workflow = StateGraph(OrchestratorState)
    
    # Add nodes
    workflow.add_node("enrich_jobs", enrich_jobs_node)
    workflow.add_node("finalize", finalize_node)
    
    # Define edges
    workflow.add_edge(START, "enrich_jobs")
    workflow.add_edge("enrich_jobs", "finalize")
    workflow.add_edge("finalize", END)
    
    return workflow.compile()


# Create singleton graph instance
orchestrator_graph = build_orchestrator_graph()


# =============================================================================
# PUBLIC API
# =============================================================================

def run_orchestration(
    user_id: str,
    user_profile: Dict[str, Any],
    jobs: List[Dict[str, Any]],
    hackathons: List[Dict[str, Any]] = None,
    news: List[Dict[str, Any]] = None,
    hot_skills: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run the full orchestration workflow for a user.
    
    Args:
        user_id: User's UUID
        user_profile: User profile data (name, skills, experience_summary)
        jobs: List of matched jobs from Pinecone
        hackathons: List of matched hackathons
        news: List of matched news
        hot_skills: AI-generated hot skills
    
    Returns:
        Complete today_data with enriched jobs (roadmaps + application text)
    """
    logger.info(f"🚀 Starting orchestration for user {user_id[:8]}...")
    
    initial_state: OrchestratorState = {
        "user_id": user_id,
        "user_profile": user_profile,
        "user_vector": [],
        "jobs": jobs or [],
        "hackathons": hackathons or [],
        "news": news or [],
        "hot_skills": hot_skills or [],
        "enriched_jobs": [],
        "status": "starting",
        "error": None
    }
    
    try:
        result = orchestrator_graph.invoke(initial_state)
        
        # Build final today_data structure
        today_data = {
            "jobs": result.get("enriched_jobs", []),
            "hackathons": hackathons or [],
            "news": news or [],
            "hot_skills": hot_skills or [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "stats": {
                "jobs_count": len(result.get("enriched_jobs", [])),
                "jobs_with_roadmap": sum(1 for j in result.get("enriched_jobs", []) if j.get("roadmap")),
                "high_match_jobs": sum(1 for j in result.get("enriched_jobs", []) if not j.get("needs_improvement")),
                "hackathons_count": len(hackathons or []),
                "news_count": len(news or [])
            }
        }
        
        logger.info(f"✅ Orchestration complete for user {user_id[:8]}")
        return today_data
        
    except Exception as e:
        logger.error(f"❌ Orchestration failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Return basic data without enrichment on failure
        return {
            "jobs": jobs or [],
            "hackathons": hackathons or [],
            "news": news or [],
            "hot_skills": hot_skills or [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "stats": {
                "jobs_count": len(jobs or []),
                "hackathons_count": len(hackathons or []),
                "news_count": len(news or []),
                "error": str(e)
            }
        }
