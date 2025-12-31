import os
import re
import uuid
import json
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

from .state import Agent4State
from .tools import rewrite_resume_content, find_recruiter_email
from .pdf_engine import generate_pdf

# Load environment variables
load_dotenv()

# Artifacts directory for debugging
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "resumes")


def mutate_node(state: Agent4State) -> dict:
    """
    Node that rewrites resume content to match job description.
    Also saves JSON artifacts for debugging/diffing.
    """
    print("✍️ [Agent 4] Mutating Resume...")
    job_description = state["job_description"]
    user_profile = state["user_profile"]
    
    # 1. Extract Resume Data
    resume_data = user_profile.get("resume", user_profile)
    
    # --- GENERATE ORIGINAL PDF FOR COMPARISON ---
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    
    original_pdf_path = os.path.join(ARTIFACTS_DIR, "debug_ORIGINAL_resume.pdf")
    generate_pdf(resume_data, original_pdf_path)
    print(f"   📄 Original PDF saved: {original_pdf_path}")
    # ---------------------------------------------
    
    # 2. Call Gemini
    rewritten_content = rewrite_resume_content(
        original_resume_json=resume_data,
        job_description=job_description
    )
    
    # --- DEBUGGING / CHECKING LOGIC ---
    # Save Original JSON
    orig_path = os.path.join(ARTIFACTS_DIR, "debug_original.json")
    with open(orig_path, "w") as f:
        json.dump(resume_data, f, indent=2)
        
    # Save Mutated JSON
    mutated_path = os.path.join(ARTIFACTS_DIR, "debug_mutated.json")
    with open(mutated_path, "w") as f:
        json.dump(rewritten_content, f, indent=2)

    print(f"   💾 Saved JSONs for inspection:\n      - {orig_path}\n      - {mutated_path}")

    # Print a Quick Text Diff of the Summary
    orig_summary = resume_data.get("summary", "")
    new_summary = rewritten_content.get("summary", "")
    
    print("\n   🔍 --- SUMMARY DIFF ---")
    print(f"   🔴 OLD: {orig_summary[:100]}...")
    print(f"   🟢 NEW: {new_summary[:100]}...")
    print("   -----------------------\n")
    
    # --- GENERATE MUTATED PDF FOR COMPARISON ---
    mutated_resume_data = {**resume_data, **rewritten_content}
    mutated_pdf_path = os.path.join(ARTIFACTS_DIR, "debug_MUTATED_resume.pdf")
    generate_pdf(mutated_resume_data, mutated_pdf_path)
    print(f"   📄 Mutated PDF saved: {mutated_pdf_path}")
    print(f"\n   👉 Compare PDFs:\n      - {original_pdf_path}\n      - {mutated_pdf_path}\n")
    # -------------------------------------------
    
    return {
        "rewritten_content": rewritten_content,
        "application_status": "pending"
    }


def render_node(state: Agent4State) -> dict:
    """
    Node that generates PDF from rewritten resume content.
    """
    print("🖨️ [Agent 4] Rendering PDF...")
    rewritten_content = state["rewritten_content"]
    user_profile = state["user_profile"]
    
    # Merge rewritten content with original profile data to ensure no fields are lost
    # (Rewritten takes precedence)
    resume_data = {**user_profile, **rewritten_content}
    
    # Ensure output directory exists
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    
    # Generate unique filename: "john_doe_a1b2c3d4.pdf"
    user_name = resume_data.get("name", "candidate").replace(" ", "_").lower()
    clean_name = re.sub(r'[^a-zA-Z0-9_]', '', user_name) # Sanitize filename
    filename = f"{clean_name}_{uuid.uuid4().hex[:8]}.pdf"
    output_path = os.path.join(ARTIFACTS_DIR, filename)
    
    # Generate PDF
    # Note: Ensure generate_pdf returns the string path
    pdf_path = generate_pdf(resume_data, output_path)
    
    return {"pdf_path": pdf_path}


def hunt_node(state: Agent4State) -> dict:
    """
    Node that finds recruiter email for the target company.
    """
    print("🕵️ [Agent 4] Hunting Recruiter...")
    job_description = state["job_description"]
    
    # Extract company domain safely
    company_domain = extract_company_domain(job_description)
    
    recruiter_email = None
    if company_domain:
        print(f"   -> Target Domain: {company_domain}")
        # FAIL-SAFE: Handle case where find_recruiter_email returns None
        try:
            recruiter_info = find_recruiter_email(company_domain)
            if recruiter_info and "email" in recruiter_info:
                recruiter_email = recruiter_info["email"]
        except Exception as e:
            print(f"   -> Warning: Hunter failed: {e}")
    else:
        print("   -> Could not extract domain from JD.")

    return {
        "recruiter_email": recruiter_email, # Can be None, handled by UI
        "application_status": "ready" if recruiter_email else "manual_review"
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
