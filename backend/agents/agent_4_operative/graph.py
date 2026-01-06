import os
import re
import uuid
import json
import tempfile
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

from .state import Agent4State
from .tools import rewrite_resume_content, find_recruiter_email, upload_resume_to_storage
from .pdf_engine import generate_pdf

# Load environment variables
load_dotenv()


def mutate_node(state: Agent4State) -> dict:
    """
    Node that rewrites resume content to match job description.
    """
    print("✍️ [Agent 4] Mutating Resume...")
    job_description = state["job_description"]
    user_profile = state["user_profile"]
    
    # Get the user_id - this MUST match the PDF filename in storage
    user_id = user_profile.get("user_id")
    if not user_id:
        raise ValueError("user_id is required in user_profile to download the original PDF")
    
    print(f"   User ID for PDF download: {user_id}")
    
    # Import and run the mutation flow
    from .tools import mutate_resume_for_job
    
    result = mutate_resume_for_job(user_id, job_description)
    
    return {
        "rewritten_content": {},  # Content is baked into the PDF, no separate dict needed
        "pdf_url": result.get("pdf_url", ""),
        "pdf_path": result.get("pdf_path", ""),
        "application_status": "ready" if result.get("status") == "success" else "pending"
    }


def render_node(state: Agent4State) -> dict:
    """
    Node that handles PDF - in the new flow, PDF is already generated in mutate_node.
    This node just passes through the results.
    """
    print("🖨️ [Agent 4] Render Node (PDF already generated in mutate step)")
    
    # PDF was already generated and uploaded in mutate_node via mutate_resume_for_job
    return {
        "pdf_path": state.get("pdf_path", ""),
        "pdf_url": state.get("pdf_url", "")
    }


def hunt_node(state: Agent4State) -> dict:
    """
    Node that finds recruiter email for the target company.
    """
    print("🕵️ [Agent 4] Hunting Recruiter...")
    job_description = state["job_description"]
    
    # Extract company domain from job description
    company_domain = extract_company_domain(job_description)
    print(f"   -> Target Domain: {company_domain}")
    
    # Find recruiter email
    from .tools import find_recruiter_email
    recruiter_info = find_recruiter_email(company_domain)
    
    return {
        "recruiter_email": recruiter_info.get("email"),
        "application_status": "ready"
    }


def extract_company_domain(job_description: str) -> str:
    """
    Extracts company domain from job description with stricter regex.
    """
    # 1. Look for explicit email domains first (most accurate)
    email_match = re.search(r"[\w\.-]+@([\w\.-]+\.\w+)", job_description)
    if email_match:
        domain = email_match.group(1).lower()
        # Filter out common generic domains
        if domain not in ["gmail.com", "yahoo.com", "hotmail.com"]:
            return domain

    # 2. Look for "Company: X" or "at X" but enforce capitalization or specific structure
    # This regex looks for "at [CapitalizedWord]" to avoid "at 9am"
    company_match = re.search(r"(?:at|company:)\s+([A-Z][\w]+)", job_description)
    if company_match:
        company = company_match.group(1).lower()
        return f"{company}.com" # naive inference, but better than nothing
    
    return None # Return None instead of "unknown-company.com" to trigger fallback


# Build the graph
def build_graph() -> StateGraph:
    """
    Builds and returns the Agent 4 workflow graph.
    """
    workflow = StateGraph(Agent4State)
    
    # Add nodes
    workflow.add_node("mutate", mutate_node)
    workflow.add_node("render", render_node)
    workflow.add_node("hunt", hunt_node)
    
    # Define the flow
    workflow.add_edge(START, "mutate")
    workflow.add_edge("mutate", "render")
    workflow.add_edge("render", "hunt")
    workflow.add_edge("hunt", END)
    
    return workflow

# Compile the graph
workflow = build_graph()
app = workflow.compile()


def run_agent4(job_description: str, user_profile: dict) -> Agent4State:
    """
    Run the Agent 4 workflow with the given job description and user profile.
    """
    # Initialize the state
    initial_state = Agent4State(
        job_description=job_description,
        user_profile=user_profile,
        application_status="pending"
    )
    
    # Run the workflow
    final_state = app.invoke(initial_state)
    
    return final_state
