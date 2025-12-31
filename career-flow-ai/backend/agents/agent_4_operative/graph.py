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
    
    # Extract Resume Data
    resume_data = user_profile.get("resume", user_profile)
    
    # Call Gemini to rewrite
    rewritten_content = rewrite_resume_content(
        original_resume_json=resume_data,
        job_description=job_description
    )
    
    # Print summary diff
    orig_summary = resume_data.get("summary", resume_data.get("experience_summary", ""))
    new_summary = rewritten_content.get("summary", "")
    
    print(f"\n   🔍 --- SUMMARY DIFF ---")
    print(f"   🔴 OLD: {str(orig_summary)[:100]}...")
    print(f"   🟢 NEW: {new_summary[:100]}...")
    print("   -----------------------\n")
    
    return {
        "rewritten_content": rewritten_content,
        "application_status": "pending"
    }


def render_node(state: Agent4State) -> dict:
    """
    Node that generates PDF and uploads directly to Supabase (no local storage).
    """
    print("🖨️ [Agent 4] Rendering PDF...")
    rewritten_content = state["rewritten_content"]
    user_profile = state["user_profile"]
    
    # Merge rewritten content with original profile data
    resume_data = {
        **user_profile,
        **rewritten_content
    }
    
    # Get user_id for file naming
    user_id = user_profile.get("user_id", str(uuid.uuid4()))
    
    # Generate PDF to temp file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        temp_path = tmp_file.name
    
    try:
        # Generate PDF
        generate_pdf(resume_data, temp_path)
        print(f"   📄 PDF generated (temp)")
        
        # Upload to Supabase storage
        pdf_url = upload_resume_to_storage(temp_path, user_id)
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
            print(f"   🗑️ Temp file cleaned up")
    
    return {
        "pdf_path": "",  # No local path
        "pdf_url": pdf_url
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
    recruiter_info = find_recruiter_email(company_domain)
    
    return {
        "recruiter_email": recruiter_info["email"],
        "application_status": "ready"  # Resume is ready to be sent
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
