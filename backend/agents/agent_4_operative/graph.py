"""
Agent 4 – Application Operative  (ReACT version)

Instead of a deterministic  mutate → render → hunt  pipeline, the LLM
now **reasons about which tools to use and in what order**.

Architecture:
    create_react_agent(llm, tools, prompt)
          │
          ▼
    ┌──────────┐     tool_calls?     ┌───────────┐
    │  agent   │ ──── YES ──────────▶│  tools    │
    │  (LLM)   │ ◀──────────────────│ (execute) │
    └──────────┘                     └───────────┘
          │ NO tool_calls (done)
          ▼
        END

The LLM decides:
  • Whether a resume needs tailoring
  • Whether to check the ATS score
  • Whether to re-tailor if the score is low
  • Whether to hunt for a recruiter email
"""

import os
import json
import logging
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from .state import Agent4State  # kept for backward compat with router/service types

load_dotenv()
logger = logging.getLogger("Agent4")

# =============================================================================
# LLM
# =============================================================================

def _get_llm():
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY / GOOGLE_API_KEY not set")
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.2,
        google_api_key=api_key,
    )

# =============================================================================
# TOOLS  (wrapped with @tool so the LLM gets JSON schemas)
# =============================================================================

@tool
def tailor_resume(user_id: str, job_description: str) -> str:
    """Download the user's original resume, optimise it for the given job
    description, generate a polished PDF, and upload it to storage.

    Returns a JSON string with keys: status, pdf_url, pdf_path,
    ats_score_before, ats_score_after.
    """
    from .tools import mutate_resume_for_job
    result = mutate_resume_for_job(user_id, job_description)
    return json.dumps(result, default=str)


@tool
def check_ats_score(resume_text: str) -> str:
    """Analyse resume text and return an ATS (Applicant Tracking System)
    compatibility score from 0-100, a list of missing keywords, and a
    brief summary.

    Returns JSON with keys: score, missing_keywords, summary.
    """
    from .tools import calculate_ats_score_sync
    result = calculate_ats_score_sync(resume_text)
    return json.dumps(result, default=str)


@tool
def hunt_recruiter(company_domain: str) -> str:
    """Attempt to find recruiter / HR email addresses for the given company
    domain (e.g. 'google.com').

    Returns JSON with keys: email, confidence, source, alternatives.
    """
    from .tools import find_recruiter_email
    result = find_recruiter_email(company_domain)
    return json.dumps(result, default=str)


@tool
def generate_responses(
    user_profile_json: str,
    job_description: str,
    company_name: str,
    job_title: str,
) -> str:
    """Generate copy-paste-ready responses for common job-application
    questions (why this company, tell us about yourself, etc.).

    user_profile_json must be a JSON string of the user's profile dict.
    Returns JSON with keys like why_join_company, about_yourself, etc.
    """
    from .tools import generate_application_responses
    profile = json.loads(user_profile_json)
    result = generate_application_responses(
        user_profile=profile,
        job_description=job_description,
        company_name=company_name,
        job_title=job_title,
    )
    return json.dumps(result, default=str)


# Collect all tools the agent can use
AGENT4_TOOLS = [tailor_resume, check_ats_score, hunt_recruiter, generate_responses]


# =============================================================================
# SYSTEM PROMPT — tells the LLM *how* to be an agent
# =============================================================================

AGENT4_SYSTEM_PROMPT = """You are Agent 4 — the Application Operative of Career Flow AI.

Your mission is to help a job applicant prepare the strongest possible
application for a specific job.  You have access to the following tools:

1. **tailor_resume** – Download, optimise, and re-render the user's resume
   as a PDF targeted at the job description.
2. **check_ats_score** – Score the resume text for ATS compatibility (0-100).
3. **hunt_recruiter** – Find recruiter emails for the target company.
4. **generate_responses** – Create copy-paste application answers.

## Decision Guidelines
- ALWAYS start by tailoring the resume.
- After tailoring, check the ATS score.  If the score is below 70,
  consider re-tailoring with more keywords.
- Try to find a recruiter email — but if the company domain is unknown,
  skip this step gracefully.
- Only generate application responses if the user has asked for them or
  the job description suggests an application form.
- When you are done, summarise what you accomplished in a clear final
  message.

## Important
- The user_id is provided in the first message.  Always pass it to tools
  that require it.
- Think step-by-step.  Explain your reasoning briefly before each tool call.
- If a tool fails, acknowledge the error and continue with the next step.
"""

# =============================================================================
# BUILD THE REACT AGENT
# =============================================================================

checkpointer = MemorySaver()

# create_react_agent returns a compiled LangGraph graph with:
#   - an "agent" node (LLM call)
#   - a "tools" node (tool execution)
#   - conditional edge: if LLM emits tool_calls → tools, else → END
react_agent = create_react_agent(
    model=_get_llm(),
    tools=AGENT4_TOOLS,
    prompt=AGENT4_SYSTEM_PROMPT,
    checkpointer=checkpointer,
)

# Alias for backward compatibility — service.py does `from .graph import app`
app = react_agent


# =============================================================================
# PUBLIC ENTRY POINT
# =============================================================================

def run_agent4(job_description: str, user_profile: dict) -> dict:
    """
    Run the Agent 4 ReACT workflow.

    Instead of a fixed pipeline, the LLM now *decides* which tools to
    call and in which order, reasoning about the results at each step.

    Args:
        job_description: Target job description text.
        user_profile: Dict with at least ``user_id``.

    Returns:
        The final state dict from the ReACT agent, including all messages.
    """
    user_id = user_profile.get("user_id", "unknown")

    # Build the initial human message with all context the LLM needs
    initial_message = (
        f"Please prepare my application for this job.\n\n"
        f"**My user_id:** {user_id}\n\n"
        f"**Job Description:**\n{job_description}\n\n"
        f"Start by tailoring my resume, then check the ATS score, "
        f"and find the recruiter email if possible."
    )

    config = {"configurable": {"thread_id": f"agent4_{user_id}"}}

    result = react_agent.invoke(
        {"messages": [("user", initial_message)]},
        config=config,
    )

    # Extract useful fields from the message history for backward compat
    final_message = result["messages"][-1].content if result["messages"] else ""

    return {
        "job_description": job_description,
        "user_profile": user_profile,
        "rewritten_content": {},
        "pdf_path": "",
        "pdf_url": "",
        "recruiter_email": "",
        "application_status": "ready",
        "feedback_loop": {},
        "agent_reasoning": final_message,
        "messages": result["messages"],
    }
