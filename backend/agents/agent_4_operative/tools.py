import os
import json
import tempfile
import asyncio
import re
from dotenv import load_dotenv

# AI & LangChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

# PDF & Document Processing
import fitz  # PyMuPDF
from .docx_engine import DocxSurgeon 
from .latex_engine import LatexSurgeon

# Database
from supabase import create_client

# Evolution / Memory (Importing from your evolution.py)
try:
    from .evolution import update_vector_memory
    EVOLUTION_AVAILABLE = True
except ImportError:
    EVOLUTION_AVAILABLE = False
    print("⚠️ 'evolution.py' not found or Pinecone not configured.")

# Browser Automation
try:
    from browser_use import Agent, Browser
    # v0.1.1 uses direct params for Browser, not BrowserConfig
    BROWSER_USE_AVAILABLE = True
except ImportError as e:
    BROWSER_USE_AVAILABLE = False
    print(f"⚠️ 'browser-use' library not found. Auto-apply will be disabled. Error: {e}")

load_dotenv()

# =============================================================================
# 1. ATS SCORING
# =============================================================================

async def calculate_ats_score(resume_text: str) -> dict:
    """Analyzes resume text and returns an ATS compatibility score."""
    print("📊 [Agent 4] Calculating ATS Score...")
    
    if not resume_text or len(resume_text.strip()) < 50:
        return {"score": 0, "missing_keywords": [], "summary": "Resume text too short."}
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.1
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert ATS scanner. Return JSON with 'score' (0-100), 'missing_keywords' (list), and 'summary'."),
        ("human", "Analyze this resume text:\n{resume_text}")
    ])
    
    try:
        chain = prompt | llm | JsonOutputParser()
        result = await chain.ainvoke({"resume_text": resume_text[:8000]})
        result["score"] = max(0, min(100, int(result.get("score", 50))))
        return result
    except Exception as e:
        print(f"   ❌ ATS Analysis error: {e}")
        return {"score": 0, "missing_keywords": [], "summary": "Error during analysis."}


# =============================================================================
# 2. AUTO-APPLY AGENT
# =============================================================================

# Keep a reference to browsers to prevent them from closing immediately
_global_browser_refs = []

async def run_auto_apply(job_url: str, user_data: dict, user_id: str = None, job_id: str = None, resume_path: str = None) -> dict:
    """Launches browser agent to auto-fill forms and optionally upload resume."""
    if not BROWSER_USE_AVAILABLE:
        return {
            "success": False, 
            "job_url": job_url,
            "message": "Browser automation libraries not installed. Run: pip install browser-use",
            "details": "browser-use library is required for auto-apply functionality"
        }

    print(f"🤖 [Agent 4] Starting Auto-Apply for: {job_url}")
    if resume_path:
        print(f"📄 [Agent 4] Resume file: {resume_path}")
    browser = None
    status = "pending"
    reason = "Initializing..."
    
    try:
        # browser-use v0.11.x requires its own LLM wrappers
        from browser_use.llm.google import ChatGoogle
        
        llm = ChatGoogle(
            model="gemini-2.0-flash",
            api_key=os.getenv("GEMINI_API_KEY"),
        )
        # v0.11.x - Browser() takes no params for local browser
        browser = Browser()
        
        # Keep browser alive
        _global_browser_refs.append(browser)
        
        clean_data = {k: v for k, v in user_data.items() if v}
        user_data_str = "\n".join([f"- {key}: {value}" for key, value in clean_data.items()])
        
        # Build resume upload instruction if resume_path is provided
        resume_instruction = ""
        if resume_path and os.path.exists(resume_path):
            resume_instruction = f"""
        5. RESUME UPLOAD: For the resume/CV upload field, use the upload_file action with the file path: {resume_path}
           - Find the file input element (usually hidden behind 'Upload Resume', 'Attach Resume', 'Choose File' button)
           - Use action: {{"upload_file": {{"index": <element_index>, "file": "{resume_path}"}}}}
           - Do NOT try to type the file path - use the upload_file action only
        """
        elif resume_path:
            print(f"   ⚠️ Resume file not found at: {resume_path}")
        
        task = f"""
        GOAL: Apply to job at {job_url}
        USER DATA: {user_data_str}
        INSTRUCTIONS:
        1. Click 'Apply'. 
        2. Fill all form fields with the user data provided above.
        3. For dropdown/select fields, choose the most appropriate option.
        4. For required fields not in user data, use 'NA' or skip if possible.
        {resume_instruction}
        6. DO NOT SUBMIT. Stop before clicking the final submit button.
        7. Report all fields you filled and any issues encountered.
        
        IMPORTANT: For file uploads, you MUST use the upload_file action, not input_text or click_element.
        Example: {{"upload_file": {{"index": 11, "file": "/path/to/file.pdf"}}}}
        """
        
        # v0.11.x Agent API
        agent = Agent(task=task, llm=llm, browser=browser)
        history = await agent.run()
        final_result = history.final_result() if hasattr(history, 'final_result') else str(history)
        reason = str(final_result) if final_result else "No result returned"
        
        # Detect failure conditions from the result text
        failure_keywords = [
            "not found", "404", "page doesn't exist", "no longer available",
            "error", "failed", "could not", "unable to", "captcha", 
            "login required", "sign in", "access denied", "forbidden"
        ]
        
        reason_lower = reason.lower()
        if any(keyword in reason_lower for keyword in failure_keywords):
            status = "failed"
        else:
            status = "success"

    except Exception as e:
        status = "failed"
        reason = str(e)
    # NOTE: Do NOT close the browser properly here (await browser.close())
    # 1. Browser object in v0.11.x doesn't have a close() method
    # 2. We WANT to keep it open for the user to review
    
    if user_id and job_id:
        save_application_status(user_id, job_id, status, {"message": reason})
    
    return {
        "success": status == "success", 
        "job_url": job_url,
        "message": reason if status == "failed" else "Auto-fill completed. Please review and submit manually.",
        "details": reason
    }


def save_application_status(user_id: str, job_id: str, status: str, result_data: dict):
    """Upserts application status to Supabase."""
    try:
        supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
        j_id = int(job_id) if str(job_id).isdigit() else None
        if not j_id: return

        payload = {
            "user_id": user_id, 
            "job_id": j_id, 
            "status": status, 
            "application_metadata": result_data, 
            "updated_at": "now()"
        }
        supabase.table("applications").insert(payload).execute()
    except Exception as e:
        print(f"   ⚠️ DB Update failed: {e}")


# =============================================================================
# 3. RESUME PROCESSING
# =============================================================================

def mutate_resume_for_job(user_id: str, job_description: str) -> dict:
    """Orchestrates resume tailoring."""
    print(f"\n🚀 [Agent 4] Tailoring resume for User: {user_id}")
    try:
        original_pdf = download_file(user_id, f"{user_id}.pdf")
        
        from pdfminer.high_level import extract_text
        raw_text = extract_text(original_pdf)
        print(f"📄 [Agent 4] Extracted {len(raw_text)} chars from original PDF")
        
        contact_info = parse_resume_contact(raw_text) # Helper defined below
        
        structured_data = structure_resume_content(raw_text, job_description, contact_info)
        
        # Handle case where structure_resume_content returns None
        if structured_data is None:
            print("❌ [Agent 4] Error: structure_resume_content returned None")
            raise ValueError("Failed to structure resume content - Gemini API may be unavailable")
        
        print(f"📋 [Agent 4] Structured data keys: {list(structured_data.keys())}")
        print(f"📋 [Agent 4] Name: {structured_data.get('name', 'MISSING!')}")
        
        # Resolve paths
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "core"))
        
        latex_engine = LatexSurgeon(template_dir=template_dir)
        tex_content = latex_engine.fill_template("template.jinja", structured_data)
        print(f"📝 [Agent 4] Generated {len(tex_content)} chars of LaTeX")
        
        final_pdf_path = latex_engine.compile_pdf(tex_content, output_filename=f"{user_id}_optimized.pdf")
        
        if not final_pdf_path: 
            raise Exception("LaTeX compilation failed - no PDF generated")
        
        # Validate PDF file exists and has content
        if not os.path.exists(final_pdf_path):
            raise Exception(f"PDF file not found at {final_pdf_path}")
        
        file_size = os.path.getsize(final_pdf_path)
        print(f"📦 [Agent 4] Generated PDF size: {file_size} bytes")
        
        if file_size < 1000:  # PDF should be at least 1KB
            raise Exception(f"Generated PDF is too small ({file_size} bytes), likely corrupted")
        
        # Verify it's a valid PDF by checking magic bytes
        with open(final_pdf_path, "rb") as f:
            header = f.read(8)
            if not header.startswith(b'%PDF'):
                raise Exception(f"Generated file is not a valid PDF (header: {header[:20]})")
        
        print(f"✅ [Agent 4] PDF validation passed")
            
        public_url = upload_file(final_pdf_path, f"{user_id}_mutated.pdf")
        
        # Save tailored resume URL to profiles.sec_resume_url
        try:
            supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
            supabase.table("profiles").update({
                "sec_resume_url": public_url
            }).eq("user_id", user_id).execute()
            print(f"✅ [Agent 4] Saved tailored resume URL to profiles.sec_resume_url")
        except Exception as db_err:
            print(f"⚠️ [Agent 4] Failed to save sec_resume_url to DB: {db_err}")
            # Don't fail the whole request if DB update fails
        
        return {"status": "success", "pdf_url": public_url, "pdf_path": final_pdf_path}
    except Exception as e:
        print(f"❌ Mutation failed: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

def structure_resume_content(raw_text: str, jd: str, contact: dict) -> dict:
    """Structures raw text into JSON for LaTeX."""
    print("🔧 [Agent 4] Starting structure_resume_content...")
    
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.getenv("GEMINI_API_KEY"))
        
        # FIX: Use double curly braces {{ }} for literal JSON examples so LangChain doesn't treat them as variables
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Resume Architect. 
Task: Structure the raw resume text into JSON for a LaTeX template.
Optimize the content to match the Job Description (JD).
- Quantify achievements.
- Use **markdown bold** for metrics/skills.
- Extract ALL contact info from the resume (name, phone, email, linkedin, github).
- Return ONLY valid JSON.

JSON Schema:
{{
  "name": "Full Name from resume",
  "phone": "Phone number or empty string",
  "email": "Email address",
  "linkedin": "LinkedIn URL or empty string",
  "linkedin_display": "linkedin.com/in/username or empty string",
  "github": "GitHub URL or empty string",  
  "github_display": "github.com/username or empty string",
  "education": [{{"school": "...", "degree": "...", "dates": "...", "location": "..."}}],
  "experience": [{{"company": "...", "role": "...", "dates": "...", "location": "...", "bullets": ["..."]}}],
  "projects": [{{"name": "...", "tech": "...", "dates": "...", "bullets": ["..."]}}],
  "skills": {{"languages": "...", "frameworks": "...", "tools": "...", "libraries": "..."}}
}}

IMPORTANT: 
- "name" is REQUIRED - extract from top of resume
- "skills.libraries" is REQUIRED - if not found, use "N/A"
- All string fields should have values (use empty string "" if not found, never null)"""),
            ("human", "RESUME:\n{resume}\n\nJD:\n{jd}")
        ])
        
        chain = prompt | llm | JsonOutputParser()
        print("🔧 [Agent 4] Calling Gemini LLM...")
        data = chain.invoke({"resume": raw_text[:4000], "jd": jd[:2000]})
        print(f"🔧 [Agent 4] Gemini response type: {type(data)}")
        
    except Exception as e:
        print(f"⚠️ [Agent 4] LLM call failed: {e}")
        import traceback
        traceback.print_exc()
        data = None
    
    # Handle case where LLM returns None or fails
    if data is None:
        print("⚠️ [Agent 4] Gemini returned None, using fallback structure")
        data = {}
    
    # Merge contact info (LLM may have extracted it, but regex fallback is reliable)
    data.update(contact)
    
    # Ensure all required fields have defaults to prevent LaTeX compilation errors
    defaults = {
        "name": "Candidate Name",
        "phone": "",
        "email": "",
        "linkedin": "",
        "linkedin_display": "",
        "github": "",
        "github_display": "",
        "education": [],
        "experience": [],
        "projects": [],
        "skills": {"languages": "N/A", "frameworks": "N/A", "tools": "N/A", "libraries": "N/A"}
    }
    
    for key, default_val in defaults.items():
        if key not in data or data[key] is None:
            data[key] = default_val
        elif key == "skills" and isinstance(data.get("skills"), dict):
            # Ensure all skill sub-fields exist
            for sk in ["languages", "frameworks", "tools", "libraries"]:
                if sk not in data["skills"] or data["skills"][sk] is None:
                    data["skills"][sk] = "N/A"
    
    print(f"✅ [Agent 4] Returning structured data with {len(data)} keys")
    return data

def parse_resume_contact(raw_text: str) -> dict:
    """Simple regex extractor for contact info."""
    contact = {}
    email = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', raw_text)
    if email: contact["email"] = email.group(0)
    # Add name extraction via LLM if needed here
    return contact


# =============================================================================
# 4. REJECTION ANALYSIS & COACHING (With Memory)
# =============================================================================

async def analyze_rejection(user_id: str, job_description: str, rejection_input: str) -> dict:
    """Analyzes rejection and saves to Vector Memory."""
    print(f"📉 [Agent 4] Analyzing rejection for User: {user_id}")
    
    # 1. Fetch User Context
    user_profile = fetch_user_profile(user_id)
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.getenv("GEMINI_API_KEY"))
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a Career Coach. Analyze why the candidate was rejected based on JD and Rejection Reason. Return JSON with 'root_cause', 'missing_hard_skills' (list), 'improvement_plan' (list of actionable steps)."),
        ("human", "JD: {jd}\nRejection: {input}\nUser Skills: {skills}")
    ])
    
    anti_pattern_created = False
    
    try:
        # 1. Generate Analysis
        chain = prompt | llm | JsonOutputParser()
        analysis = await chain.ainvoke({
            "jd": job_description[:3000], 
            "input": rejection_input,
            "skills": user_profile.get("skills", [])
        })
        
        # 2. Save to Pinecone Memory (Evolution)
        if EVOLUTION_AVAILABLE:
            print("   🧠 Updating Vector Memory (Pinecone)...")
            # Convert analysis dict to string for embedding
            analysis_text = f"Root Cause: {analysis.get('root_cause')}. Missing: {analysis.get('missing_hard_skills')}"
            update_vector_memory(user_id, analysis_text, create_anti_pattern=True)
            anti_pattern_created = True
        
        # Build gap analysis string
        root_cause = analysis.get("root_cause", "Unable to determine")
        missing_skills = analysis.get("missing_hard_skills", [])
        if isinstance(missing_skills, list):
            missing_skills_str = ", ".join(missing_skills)
        else:
            missing_skills_str = str(missing_skills)
        
        gap_analysis = f"Root Cause: {root_cause}. Missing Skills: {missing_skills_str}"
        
        # Build recommendations list
        improvement_plan = analysis.get("improvement_plan", [])
        if isinstance(improvement_plan, str):
            recommendations = [improvement_plan]
        elif isinstance(improvement_plan, list):
            recommendations = improvement_plan
        else:
            recommendations = []
        
        return {
            "success": True,
            "user_id": user_id,
            "gap_analysis": gap_analysis,
            "recommendations": recommendations,
            "anti_pattern_created": anti_pattern_created
        }
    except Exception as e:
        print(f"   ❌ Analysis failed: {e}")
        return {
            "success": False,
            "user_id": user_id,
            "gap_analysis": f"Analysis failed: {str(e)}",
            "recommendations": [],
            "anti_pattern_created": False
        }


# =============================================================================
# 5. GENERATE APPLICATION RESPONSES (Added this!)
# =============================================================================

def download_original_pdf(user_id: str) -> str:
    supabase_url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    supabase = create_client(supabase_url.rstrip('/'), key)
    
    try:
        print(f"📥 Downloading: {user_id}.pdf")
        data = supabase.storage.from_("Resume").download(f"{user_id}.pdf")
        path = os.path.join(tempfile.gettempdir(), f"original_{user_id}.pdf")
        with open(path, "wb") as f: f.write(data)
        return path
    except Exception as e:
        raise Exception(f"Download failed: {e}")

def upload_mutated_pdf(file_path: str, user_id: str) -> str:
    """
    Uploads tailored/mutated PDF to Supabase Storage.
    
    - Deletes previous secondary resume from S3 if exists
    - Uploads new tailored resume
    - Updates sec_resume_url in profiles table
    """
    supabase_url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    supabase = create_client(supabase_url.rstrip('/'), key)
    
    # Determine extension and mime type
    is_docx = file_path.endswith(".docx")
    ext = "docx" if is_docx else "pdf"
    content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if is_docx else "application/pdf"
    
    file_name = f"{user_id}_mutated.{ext}"
    
    try:
        with open(file_path, "rb") as f: data = f.read()
        
        # Delete previous secondary resume from storage
        try:
            # Try to remove both PDF and DOCX variants
            supabase.storage.from_("Resume").remove([f"{user_id}_mutated.pdf"])
            supabase.storage.from_("Resume").remove([f"{user_id}_mutated.docx"])
            print(f"   🗑️ Deleted old secondary resume from S3")
        except: 
            pass  # File may not exist, that's ok
        
        # Upload new secondary resume
        print(f"📤 Uploading {ext.upper()}: {file_name}")
        supabase.storage.from_("Resume").upload(file_name, data, {"content-type": content_type})
        res = supabase.storage.from_("Resume").create_signed_url(file_name, 31536000)
        signed_url = res.get("signedURL") if isinstance(res, dict) else str(res)
        
        # Update sec_resume_url in profiles table
        try:
            supabase.table("profiles").update({
                "sec_resume_url": signed_url
            }).eq("user_id", user_id).execute()
            print(f"   ✅ Updated sec_resume_url in profiles")
        except Exception as db_err:
            print(f"   ⚠️ Failed to update sec_resume_url (column may not exist): {db_err}")
        
        return signed_url
    except Exception as e:
        raise Exception(f"Upload failed: {e}")
# =============================================================================
# REWRITE RESUME CONTENT FOR JOB DESCRIPTION
# =============================================================================

def rewrite_resume_content(user_profile: dict, job_description: str) -> dict:
    """
    Rewrite resume content to better match the job description.
    
    Args:
        user_profile: User's profile/resume data.
        job_description: Target job description.
    
    Returns:
        Dictionary with rewritten resume sections.
    """
    # This is a placeholder for full-resume rewrites (vs surgical edits)
    # The surgical editing is handled by mutate_resume_for_job
    return {
        "summary": user_profile.get("summary", ""),
        "experience": user_profile.get("experience", []),
        "skills": user_profile.get("skills", []),
        "education": user_profile.get("education", []),
        "rewritten": True
    }


# =============================================================================
# ADDITIONAL HELPER FUNCTIONS FOR SERVICE
# =============================================================================

def fetch_user_profile(user_id: str) -> dict:
    """
    Fetch user profile from Supabase by user_id (UUID).
    
    Args:
        user_id: The UUID of the user.
    
    Returns:
        Profile dict or empty dict if not found.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not supabase_url or not key:
        print("⚠️ Missing Supabase credentials")
        return {}
    
    supabase = create_client(supabase_url.rstrip('/'), key)
    response = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
    
    if response.data and len(response.data) > 0:
        return response.data[0]
    return {}


def build_resume_from_profile(profile: dict) -> dict:
    """
    Builds a structured resume dict from a Supabase profile record.
    
    Args:
        profile: Raw profile data from Supabase profiles table.
    
    Returns:
        Structured resume dictionary.
    """
    # Extract resume_json if available, otherwise build from profile fields
    resume_json = profile.get("resume_json", {}) or {}
    
    return {
        "name": profile.get("name") or resume_json.get("name", ""),
        "email": profile.get("email") or resume_json.get("email", ""),
        "phone": resume_json.get("phone", ""),
        "location": resume_json.get("location", ""),
        "linkedin": profile.get("linkedin_url") or resume_json.get("linkedin", ""),
        "github": profile.get("github_url") or resume_json.get("github", ""),
        "summary": profile.get("experience_summary") or resume_json.get("summary", ""),
        "experience_summary": profile.get("experience_summary", ""),
        "skills": profile.get("skills", []) or resume_json.get("skills", []),
        "education": profile.get("education") or resume_json.get("education", ""),
        "experience": resume_json.get("experience", []),
        "projects": resume_json.get("projects", []),
        "certifications": resume_json.get("certifications", []),
        "resume_url": profile.get("resume_url", ""),
        "resume_text": profile.get("resume_text", ""),
        "resume": resume_json  # Keep full resume_json for backward compatibility
    }


def find_recruiter_email(company_domain: str) -> dict:
    """
    Attempts to find recruiter email for a company.
    
    Args:
        company_domain: Company domain (e.g., 'google.com')
    
    Returns:
        Dict with email and confidence score.
    """
    if not company_domain:
        return {"email": None, "confidence": 0, "source": "none"}
    
    # Common recruiter email patterns
    patterns = [
        f"recruiting@{company_domain}",
        f"careers@{company_domain}",
        f"jobs@{company_domain}",
        f"hr@{company_domain}",
        f"talent@{company_domain}"
    ]
    
    # For now, return the most common pattern
    # In production, you'd verify these with an email validation API
    return {
        "email": patterns[0],
        "confidence": 0.6,
        "source": "pattern_match",
        "alternatives": patterns[1:]
    }


def generate_application_responses(
    user_profile: dict,
    job_description: str,
    company_name: str,
    job_title: str,
    additional_context: str = None
) -> dict:
    """
    Generate copy-paste ready responses for common job application questions.
    
    Args:
        user_profile: User's profile/resume data.
        job_description: Target job description.
        company_name: Name of the company.
        job_title: Title of the position.
        additional_context: Any additional context.
    
    Returns:
        Dictionary with all application responses.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser

def generate_application_responses(user_profile: dict, job_description: str, company_name: str, job_title: str, additional_context: str = None) -> dict:
    """Generates copy-paste ready responses for job applications."""
    print(f"📝 [Agent 4] Generating responses for {company_name}")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.3
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful career assistant. 
Generate personalized responses for a job application.
Return JSON with these keys: 
"why_join_company", "about_yourself", "relevant_skills", "work_experience", "why_good_fit", "problem_solving", "additional_info", "availability".
Keep answers professional and concise (2-4 sentences)."""),
        ("human", """User Profile: {profile}
Company: {company}
Role: {role}
JD: {jd}
Context: {context}""")
    ])
    
    try:
        chain = prompt | llm | JsonOutputParser()
        result = chain.invoke({
            "profile": str(user_profile)[:2000],
            "company": company_name,
            "role": job_title,
            "jd": job_description[:2000],
            "context": additional_context or ""
        })
        return result
    except Exception as e:
        print(f"   ❌ Response generation failed: {e}")
        return {}


# =============================================================================
# UTILS
# =============================================================================

def download_file(user_id: str, filename: str) -> str:
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    data = supabase.storage.from_("Resume").download(filename)
    path = os.path.join(tempfile.gettempdir(), f"download_{filename}")
    with open(path, "wb") as f: f.write(data)
    return path

def upload_file(file_path: str, destination_name: str) -> str:
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    with open(file_path, "rb") as f:
        file_data = f.read()
        print(f"📦 [Agent 4] Uploading {len(file_data)} bytes to {destination_name}")
        
        # Set proper content-type for PDF files
        file_options = {
            "upsert": "true",
            "content-type": "application/pdf"
        }
        supabase.storage.from_("Resume").upload(destination_name, file_data, file_options)
    # Use signed URL for private buckets
    res = supabase.storage.from_("Resume").create_signed_url(destination_name, 31536000) # 1 year
    return res.get("signedURL") if isinstance(res, dict) else str(res)

