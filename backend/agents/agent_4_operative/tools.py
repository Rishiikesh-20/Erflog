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
    from browser_use import Agent, Browser, BrowserConfig
    # v0.1.x uses langchain LLMs directly, not browser_use.llm
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
        # browser-use v0.1.x uses LangChain LLMs directly
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.0
        )
        # v0.1.x uses BrowserConfig
        browser = Browser(config=BrowserConfig(headless=False, disable_security=True))
        
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
        
        agent = Agent(task=task, llm=llm, browser=browser)
        history = await agent.run()
        final_result = history.final_result()
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
    finally:
        if browser: await browser.close()
            
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
        contact_info = parse_resume_contact(raw_text) # Helper defined below
        
        structured_data = structure_resume_content(raw_text, job_description, contact_info)
        
        # Resolve paths
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "core"))
        
        latex_engine = LatexSurgeon(template_dir=template_dir)
        tex_content = latex_engine.fill_template("template.jinja", structured_data)
        final_pdf_path = latex_engine.compile_pdf(tex_content, output_filename=f"{user_id}_optimized.pdf")
        
        if not final_pdf_path: raise Exception("LaTeX compilation failed")
            
        public_url = upload_file(final_pdf_path, f"{user_id}_mutated.pdf")
        
        return {"status": "success", "pdf_url": public_url, "pdf_path": final_pdf_path}
    except Exception as e:
        print(f"❌ Mutation failed: {e}")
        return {"status": "error", "message": str(e)}

def structure_resume_content(raw_text: str, jd: str, contact: dict) -> dict:
    """Structures raw text into JSON for LaTeX."""
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.getenv("GEMINI_API_KEY"))
    
    # FIX: Use double curly braces {{ }} for literal JSON examples so LangChain doesn't treat them as variables
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Resume Architect. 
Task: Structure the raw resume text into JSON for a LaTeX template.
Optimize the content to match the Job Description (JD).
- Quantify achievements.
- Use **markdown bold** for metrics/skills.
- Return ONLY valid JSON.

JSON Schema:
{{
  "education": [{{"school": "...", "degree": "...", "dates": "...", "location": "..."}}],
  "experience": [{{"company": "...", "role": "...", "dates": "...", "location": "...", "bullets": ["..."]}}],
  "projects": [{{"name": "...", "tech": "...", "dates": "...", "bullets": ["..."]}}],
  "skills": {{"languages": "...", "frameworks": "...", "tools": "..."}}
}}"""),
        ("human", "RESUME:\n{resume}\n\nJD:\n{jd}")
    ])
    
    chain = prompt | llm | JsonOutputParser()
    data = chain.invoke({"resume": raw_text[:4000], "jd": jd[:2000]})
    data.update(contact)
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
        supabase.storage.from_("Resume").upload(destination_name, f.read(), {"upsert": "true"})
    return supabase.storage.from_("Resume").get_public_url(destination_name)

def fetch_user_profile(user_id: str) -> dict:
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    response = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
    if response.data: return response.data[0]
    return {}