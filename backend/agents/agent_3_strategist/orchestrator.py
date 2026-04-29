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
# LANGGRAPH TOOLS (for the ReACT orchestrator agent)
# =============================================================================

from langchain_core.tools import tool as lc_tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

@lc_tool
def enrich_single_job(
    job_json: str,
    user_skills_csv: str,
    user_profile_json: str,
) -> str:
    """Enrich a single job with a learning roadmap (if match < 80%) and
    application text.

    Args:
        job_json: JSON string of the job dict (must include title, company,
                  score, summary/description).
        user_skills_csv: Comma-separated list of the user's skills.
        user_profile_json: JSON string of the user's profile dict.

    Returns:
        JSON string of the enriched job dict with ``roadmap`` and
        ``application_text`` keys added.
    """
    job = json.loads(job_json)
    user_profile = json.loads(user_profile_json)
    user_skills = [s.strip() for s in user_skills_csv.split(",") if s.strip()]

    score = job.get("score", 0)
    match_pct = job.get("match_percentage", score)

    enriched = {**job}

    # Roadmap only for weaker matches
    if match_pct < 0.80:
        enriched["roadmap"] = generate_roadmap_for_job(user_skills, job)
        enriched["needs_improvement"] = True
    else:
        enriched["roadmap"] = None
        enriched["needs_improvement"] = False

    # Application text for every job
    enriched["application_text"] = generate_application_text(user_profile, job)
    enriched["resume_url"] = None

    return json.dumps(enriched, default=str)


@lc_tool
def analyse_career_strategy(
    user_skills_csv: str,
    top_jobs_json: str,
) -> str:
    """Given the user's skills and a JSON list of their top matched jobs,
    produce a brief career strategy recommendation.

    Returns JSON with keys: recommended_job, reason, next_steps.
    """
    from .graph import process_career_strategy  # existing helper

    jobs = json.loads(top_jobs_json)
    result = process_career_strategy(user_skills_csv, jobs)
    return json.dumps(result, default=str)


ORCHESTRATOR_TOOLS = [enrich_single_job, analyse_career_strategy]

ORCHESTRATOR_SYSTEM_PROMPT = """You are the Career Strategist Orchestrator of Career Flow AI.

You receive a list of matched jobs for a user and must enrich each one.

## Your Tools
1. **enrich_single_job** – For each job, call this to generate a learning
   roadmap (only when match < 80%) and application text.
2. **analyse_career_strategy** – After enriching all jobs, call this once
   with the user's skills and the top 3 jobs to produce a career strategy.

## Instructions
- Process every job in the list by calling enrich_single_job for each one.
- After all jobs are enriched, call analyse_career_strategy once.
- Summarise the results when done.
- If any tool call fails for a specific job, skip it and continue with the
  next job.  Never stop the entire run because of one failure.
"""


def _get_orchestrator_llm():
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.1,
        google_api_key=api_key,
    )


# =============================================================================
# PUBLIC API  (backward-compatible signature)
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
    Run the full orchestration workflow for a user deterministically.

    This is the hybrid approach:
    1. Deterministic loop: Enrich each job (roadmap if match < 80%, plus app text)
    2. LLM call: Synthesize career strategy from the top jobs

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
    logger.info(f"🚀 Starting hybrid orchestration for user {user_id[:8]}...")
    from .graph import process_career_strategy

    try:
        user_skills = user_profile.get("skills", [])
        skills_csv = ", ".join(user_skills) if isinstance(user_skills, list) else str(user_skills)

        # 1. Deterministic Enrichment Loop
        enriched_jobs = []
        for job in (jobs or []):
            score = job.get("score", 0)
            match_pct = job.get("match_percentage", score)

            enriched = {**job}

            # Roadmap only for weaker matches
            if match_pct < 0.80:
                try:
                    enriched["roadmap"] = generate_roadmap_for_job(user_skills, job)
                    enriched["needs_improvement"] = True
                except Exception as e:
                    logger.warning(f"Roadmap generation failed for job {job.get('id')}: {e}")
                    enriched["roadmap"] = None
                    enriched["needs_improvement"] = False
            else:
                enriched["roadmap"] = None
                enriched["needs_improvement"] = False

            # Application text for every job
            try:
                enriched["application_text"] = generate_application_text(user_profile, job)
            except Exception as e:
                logger.warning(f"App text generation failed for job {job.get('id')}: {e}")
                enriched["application_text"] = None
                
            enriched["resume_url"] = None
            enriched_jobs.append(enriched)

        # 2. LLM Strategy Synthesis
        career_strategy = {}
        if enriched_jobs:
            try:
                career_strategy = process_career_strategy(skills_csv, enriched_jobs[:3])
            except Exception as e:
                logger.error(f"Career strategy synthesis failed: {e}")

        # 3. Compile output
        today_data = {
            "jobs": enriched_jobs,
            "hackathons": hackathons or [],
            "news": news or [],
            "hot_skills": hot_skills or [],
            "career_strategy": career_strategy,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "stats": {
                "jobs_count": len(enriched_jobs),
                "jobs_with_roadmap": sum(1 for j in enriched_jobs if j.get("roadmap")),
                "high_match_jobs": sum(1 for j in enriched_jobs if not j.get("needs_improvement")),
                "hackathons_count": len(hackathons or []),
                "news_count": len(news or []),
            },
        }

        logger.info(f"✅ Hybrid orchestration complete for user {user_id[:8]}")
        return today_data

    except Exception as e:
        logger.error(f"❌ Orchestration failed: {e}")
        import traceback
        traceback.print_exc()

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
                "error": str(e),
            },
        }

