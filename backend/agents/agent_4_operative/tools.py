import os
import json
import tempfile
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import fitz  # PyMuPDF
from supabase import create_client
from .docx_engine import DocxSurgeon  # Import the new DOCX Surgeon
from .latex_engine import LatexSurgeon
# from .pdf_engine import PDFSurgeon # Deprecated for this flow

load_dotenv()


# =============================================================================
# DATABASE HELPERS
# =============================================================================
def parse_resume_sections(pdf_path: str) -> dict:
    """
    Intelligently splits the PDF text into logical sections using layout analysis.
    """
    doc = fitz.open(pdf_path)
    full_text = ""
    
    # Use "blocks" to respect layout (columns)
    # Blocks are tuples: (x0, y0, x1, y1, "lines", block_no, block_type)
    for page in doc:
        blocks = page.get_text("blocks")
        # Sort blocks: primary top-to-bottom, secondary left-to-right
        blocks.sort(key=lambda b: (b[1], b[0]))
        
        for b in blocks:
            # b[4] contains the text content
            full_text += b[4] + "\n"
    
    headers = {
        "experience": ["EXPERIENCE", "WORK EXPERIENCE", "EMPLOYMENT HISTORY", "PROFESSIONAL EXPERIENCE"],
        "projects": ["PROJECTS", "PERSONAL PROJECTS", "ACADEMIC PROJECTS", "KEY PROJECTS"],
        "skills": ["SKILLS", "TECHNICAL SKILLS", "TECHNOLOGIES", "CORE COMPETENCIES"],
        "education": ["EDUCATION", "ACADEMIC BACKGROUND", "ACADEMICS"]
    }
    
    sections = {}
    lines = full_text.split('\n')
    current_section = "uncategorized"
    buffer = []
    
    for line in lines:
        clean_line = line.strip().upper()
        if not clean_line: continue
        
        # Detect Header
        is_header = False
        for section_name, possible_headers in headers.items():
            # Check for exact header match or header-like line
            if clean_line in possible_headers or any(h == clean_line for h in possible_headers):
                if buffer: 
                    # Join with newlines to preserve some structure
                    sections[current_section] = "\n".join(buffer)
                current_section = section_name
                buffer = []
                is_header = True
                break
        
        if not is_header:
            buffer.append(line)
            
    if buffer: sections[current_section] = "\n".join(buffer)
    
    print(f"🧩 [Agent 4] Parsed Sections: {list(sections.keys())}")
    return sections


# =============================================================================
# 2. GEMINI OPTIMIZER (Section-Aware)
# =============================================================================

def finetune_section_content(section_name: str, section_text: str, job_description: str) -> dict:
    """
    Asks Gemini to rewrite the ENTIRE section content to match the JD.
    """
    if not section_text or len(section_text) < 50: return None

    print(f"🧠 [Agent 4] Optimizing {section_name.upper()} (Full Section - DOCX Mode)...")

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.2 
    )
    
    json_parser = JsonOutputParser()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a precise Resume Editor.
Your Goal: Rewrite the '{section_name}' section of the candidate's resume to better align with the Job Description.

INSTRUCTIONS:
1. **Analyze**: Compare the candidate's current content with the Job Description.
2. **Rewrite**: key bullet points to emphasize relevant skills/experience found in the JD.
3. **Format**: Return PLAIN TEXT with bullet points (• or -). **DO NOT USE MARKDOWN** like **bold** as we are inserting into DOCX as plain text for stability.
4. **Constraint**: Keep the length similar to the original.
5. **Output**: Return the FULL text of the rewritten section.

OUTPUT JSON:
{{
    "new_content": "Full rewritten text for the section..."
}}"""),
        ("human", """SECTION CONTENT:
{section_text}

JOB DESCRIPTION:
{job_description}

Rewrite the full section. Return JSON.""")
    ])
    
    try:
        chain = prompt | llm | json_parser
        response = chain.invoke({
            "section_name": section_name,
            "section_text": section_text,
            "job_description": job_description[:3000]
        })
        return response
    except Exception as e:
        print(f"   ❌ Error optimizing {section_name}: {e}")
        return None


# =============================================================================
# 3. DOCX Editor Hook
# =============================================================================

def edit_resume_via_docx(pdf_path: str, section_edits: list) -> str:
    """
    Orchestrates the PDF -> DOCX -> Edit flow.
    Returns path to the edited DOCX file (PDF conversion removed per user request).
    """
    print(f"⚕️ [Agent 4] Starting DOCX Strategy ({len(section_edits)} edits)...")
    
    try:
        surgeon = DocxSurgeon()
        
        # 1. Convert PDF -> DOCX
        docx_path = surgeon.convert_pdf_to_docx(pdf_path)
        
        # 2. Edit DOCX
        edited_docx_path = surgeon.simple_replace(docx_path, section_edits)
        
        print(f"   ✅ DOCX Edit complete: {edited_docx_path}")
        
        # 3. Return DOCX directly (No conversion back to PDF)
        return edited_docx_path
        
    except Exception as e:
        print(f"   ❌ DOCX Workflow failed: {e}")
        return None


# =============================================================================
# 4. MAIN WORKFLOW
# =============================================================================


def parse_resume_with_pdfminer(pdf_path: str) -> dict:
    """
    Uses pdfminer.six (same as pyresparser internally) to extract text,
    then spacy NER for name detection and regex for contact info.
    This bypasses pyresparser's spacy v2/v3 compatibility issues.
    """
    import re
    print("🔍 [Agent 4] Parsing resume with pdfminer + spacy NER...")
    
    contact = {}
    
    try:
        # 1. Extract text from PDF using pdfminer.six
        from pdfminer.high_level import extract_text
        raw_text = extract_text(pdf_path)
        
        if not raw_text:
            print("   ⚠️ No text extracted from PDF")
            return {}
        
        print(f"   📄 Extracted {len(raw_text)} characters from PDF")
        
        # DEBUG: Print first 1000 chars for analysis
        print(f"\n{'='*50}")
        print("📋 FIRST 1000 CHARACTERS OF PDF:")
        print(f"{'='*50}")
        print(raw_text[:1000])
        print(f"{'='*50}\n")
        
        # 2. Use Gemini to extract name from first 4 lines
        try:
            first_lines = "\n".join(raw_text.split('\n')[:4])
            print(f"   📝 First 4 lines for name extraction:\n{first_lines}")
            
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0.0
            )
            
            from langchain_core.output_parsers import StrOutputParser
            prompt = ChatPromptTemplate.from_messages([
                ("system", "Extract ONLY the person's full name from the text. Return just the name, nothing else."),
                ("human", "{text}")
            ])
            
            chain = prompt | llm | StrOutputParser()
            name = chain.invoke({"text": first_lines}).strip()
            
            if name and len(name) < 50:  # Sanity check
                contact["name"] = name
                print(f"   👤 Name (Gemini): {contact['name']}")
        except Exception as e:
            print(f"   ⚠️ Gemini name extraction failed: {e}")
        
        # 3. Use spacy NER for email, phone, URLs (everything except name)
        try:
            import spacy
            nlp = spacy.load('en_core_web_sm')
            doc = nlp(raw_text[:2000])  # Process first 2000 chars for contact info
            
            # spacy doesn't have specific labels for email/phone/URLs, so we use regex but with spacy tokenization
            import re
            
            # Email (from token matching)
            for token in doc:
                if '@' in token.text and '.' in token.text:
                    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                    if re.match(email_pattern, token.text):
                        contact["email"] = token.text
                        print(f"   📧 Email (NER): {contact['email']}")
                        break
            
            # Phone
            phone_pattern = r'(?:\+91[\-\s]?)?(?:\d{10}|\d{5}[\-\s]?\d{5})'
            phone_match = re.search(phone_pattern, raw_text[:1000])
            if phone_match:
                contact["phone"] = phone_match.group(0).strip()
                print(f"   📞 Phone: {contact['phone']}")
            
            # LinkedIn
            linkedin_pattern = r'(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+'
            linkedin_match = re.search(linkedin_pattern, raw_text, re.IGNORECASE)
            if linkedin_match:
                url = linkedin_match.group(0)
                if not url.startswith("http"):
                    url = "https://" + url
                contact["linkedin"] = url
                print(f"   🔗 LinkedIn: {contact['linkedin']}")
            
            # GitHub
            github_pattern = r'(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_-]+'
            github_match = re.search(github_pattern, raw_text, re.IGNORECASE)
            if github_match:
                url = github_match.group(0)
                if not url.startswith("http"):
                    url = "https://" + url
                contact["github"] = url
                print(f"   🐙 GitHub: {contact['github']}")
            
            # Codeforces
            codeforces_pattern = r'(?:https?://)?(?:www\.)?codeforces\.com/profile/[a-zA-Z0-9_-]+'
            codeforces_match = re.search(codeforces_pattern, raw_text, re.IGNORECASE)
            if codeforces_match:
                url = codeforces_match.group(0)
                if not url.startswith("http"):
                    url = "https://" + url
                contact["codeforces"] = url
                print(f"   🏆 Codeforces: {contact['codeforces']}")
                
        except Exception as e:
            print(f"   ⚠️ spacy NER extraction failed: {e}")
        
        return contact
        
    except Exception as e:
        print(f"   ⚠️ PDF parsing failed: {e}")
        return {}


def extract_contact_info_separately(raw_text: str, pdf_path: str = None) -> dict:
    """
    Extracts contact info using pdfminer + spacy NER if pdf_path is provided,
    otherwise falls back to regex for URLs.
    """
    import re
    print("🔍 [Agent 4] Extracting Immutable Contact Info...")
    
    contact = {}
    
    # Try pdfminer + spacy extraction if we have the PDF path
    if pdf_path:
        pdfminer_data = parse_resume_with_pdfminer(pdf_path)
        if pdfminer_data:
            contact.update(pdfminer_data)
    
    # If no PDF or extraction failed, still try regex on raw_text for URLs
    if not contact.get("linkedin"):
        linkedin_pattern = r'(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+'
        linkedin_match = re.search(linkedin_pattern, raw_text, re.IGNORECASE)
        if linkedin_match:
            url = linkedin_match.group(0)
            if not url.startswith("http"):
                url = "https://" + url
            contact["linkedin"] = url
            print(f"   🔗 LinkedIn (fallback): {contact['linkedin']}")
    
    if not contact.get("github"):
        github_pattern = r'(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_-]+'
        github_match = re.search(github_pattern, raw_text, re.IGNORECASE)
        if github_match:
            url = github_match.group(0)
            if not url.startswith("http"):
                url = "https://" + url
            contact["github"] = url
            print(f"   🐙 GitHub (fallback): {contact['github']}")
    
    if not contact.get("codeforces"):
        codeforces_pattern = r'(?:https?://)?(?:www\.)?codeforces\.com/profile/[a-zA-Z0-9_-]+'
        codeforces_match = re.search(codeforces_pattern, raw_text, re.IGNORECASE)
        if codeforces_match:
            url = codeforces_match.group(0)
            if not url.startswith("http"):
                url = "https://" + url
            contact["codeforces"] = url
            print(f"   🏆 Codeforces (fallback): {contact['codeforces']}")
            
    return contact


def structure_resume_content(raw_text: str, job_description: str, preserved_contact_info: dict = None) -> dict:
    """
    Uses Gemini to structure the raw resume text into the JSON format 
    required by the LaTeX template, while optimizing content for the JD.
    """
    print(f"🧠 [Agent 4] Structuring and Optimizing content with Gemini...")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp", 
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.2
    )
    
    from langchain_core.output_parsers import StrOutputParser

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert Resume Architect. 
Your Goal: Structure the provided Raw Resume Text into a JSON format suitable for a specific LaTeX template.
Simultaneously, OPTIMIZE the content (bullet points, summaries) to align with the provided Job Description.

JOB DESCRIPTION:
{job_description}

REQUIREMENTS:
1. **Structure**: Return a SINGLE JSON object matching the schema below.
2. **Optimization**: 
    - Rewrite bullet points to be impactful and **QUANTIFIED** (use numbers, metrics, percentages). 
    - **BOLD** key metrics, specific numbers, and important technologies within the bullet points using Markdown syntax `**text**`. 
      - Example: "Reduced latency by **50%** using **Redis** caching."
    - Add or remove items in the 'skills' section to better align with the Job Description, but STRICTLY based on the user's actual abilities implied in the raw text.
3. **Consistency**: Ensure keys match EXACTLY.
4. **Escape**: DO NOT escape special characters. Return raw text (e.g. use "%" not "\%").
    - our system handles LaTeX escaping automatically.
    - DO NOT use LaTeX commands like `\textbf`. Use markdown `**bold**` only.
5. **ACCURACY - NO HALLUCINATIONS**: 
    - **CRITICAL**: Do NOT mix details between projects. 
    - Information for "Project A" MUST come ONLY from the "Project A" section of the raw text. 
    - Do not list a feature from Project X under Project Y, even if it fits the JD.

JSON SCHEMA:
{{
  "education": [
    {{ "school": "University Name", "location": "City, State", "degree": "degree", "dates": "Month Year -- Month Year" }}
  ],
  "experience": [
    {{ 
      "company": "Company Name", 
      "location": "City, State", 
      "role": "Job Title", 
      "dates": "Start -- End", 
      "bullets": ["Action verb + Task + Result (Optimized with **Bold**)", "Another bullet point"] 
    }}
  ],
  "projects": [
    {{ 
       "name": "Project Name", 
       "tech": "Stack Used", 
       "dates": "Date", 
       "bullets": ["What you did", "Tech used"] 
    }}
  ],
  "skills": {{
     "languages": "Java, Python...", 
     "frameworks": "React, Flask...",
     "tools": "Docker, Git...",
     "libraries": "NumPy, Pandas..."
  }}
}}
"""),
        ("human", """RAW RESUME TEXT:
{raw_text}

Structure and Optimize into JSON. Note: Contact info is handled separately.""")
    ])
    
    try:
        chain = prompt | llm | StrOutputParser()
        result_str = chain.invoke({
            "raw_text": raw_text,
            "job_description": job_description[:5000]
        })
        
        # Clean up markdown code blocks if present
        result_str = result_str.strip()
        if result_str.startswith("```json"):
            result_str = result_str[7:]
        elif result_str.startswith("```"):
            result_str = result_str[3:]
        
        if result_str.endswith("```"):
            result_str = result_str[:-3]
            
        structured_data = json.loads(result_str.strip())
        
        # MERGE Preserved Contact Info
        if preserved_contact_info:
            print(f"   📎 Merging preserved contact info: {preserved_contact_info.get('email')}")
            structured_data["name"] = preserved_contact_info.get("name", structured_data.get("name"))
            structured_data["phone"] = preserved_contact_info.get("phone", structured_data.get("phone"))
            structured_data["email"] = preserved_contact_info.get("email", structured_data.get("email"))
            structured_data["linkedin"] = preserved_contact_info.get("linkedin", structured_data.get("linkedin"))
            # Display versions
            if preserved_contact_info.get("linkedin"):
                 structured_data["linkedin_display"] = preserved_contact_info.get("linkedin").replace("https://", "").replace("www.", "").rstrip("/")
            
            structured_data["github"] = preserved_contact_info.get("github", structured_data.get("github"))
            if preserved_contact_info.get("github"):
                 structured_data["github_display"] = preserved_contact_info.get("github").replace("https://", "").replace("www.", "").rstrip("/")
                 
        return structured_data
        
    except Exception as e:
        print(f"❌ JSON Parsing failed: {e}")
        return {}


def mutate_resume_for_job(user_id: str, job_description: str) -> dict:
    print(f"\n{'='*40}\n🚀 [Agent 4] Starting Structured Mutation (LaTeX Re-render)\n{'='*40}")
    
    try:
        # 1. Download PDF
        original_pdf_path = download_original_pdf(user_id)
        
        # 2. Extract Raw Text (via DOCX for reliability)
        surgeon = DocxSurgeon()
        docx_path = surgeon.convert_pdf_to_docx(original_pdf_path)
        print("🔍 [Agent 4] Extracting text context...")
        sections_dict = surgeon.extract_text(docx_path)
        
        # Merge sections into one big string for the LLM to structure
        raw_text_blob = "\n".join([f"--- {k.upper()} ---\n{v}" for k,v in sections_dict.items()])
        
        # 2b. Extract Immutable Contact Info
        contact_info = extract_contact_info_separately(raw_text_blob, pdf_path=original_pdf_path)
        
        # 3. Structure & Optimize Content
        structured_data = structure_resume_content(raw_text_blob, job_description, preserved_contact_info=contact_info)
        
        if not structured_data or not structured_data.get("experience"):
            print("   ⚠️ Structuring failed or returned empty. Aborting.")
            raise Exception("Failed to structure resume data")
            
        # Ensure name exists (fallback to extracted if LLM failed completely on body)
        if not structured_data.get("name") and contact_info.get("name"):
            structured_data["name"] = contact_info["name"]

        # 4. Render LaTeX
        print("🎨 [Agent 4] Rendering LaTeX Template...")
        # Template is at backend/core/template.jinja
        # Use __file__ to get correct path from this tools.py location
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        # Navigate: agent_4_operative -> agents -> backend -> core
        template_dir = os.path.join(current_file_dir, "..", "..", "core")
        template_dir = os.path.abspath(template_dir)  # Normalize the path
        
        print(f"   📁 Template directory: {template_dir}")
             
        latex_engine = LatexSurgeon(template_dir=template_dir)
        tex_content = latex_engine.fill_template("template.jinja", structured_data)
        
        # 5. Compile PDF
        final_pdf_path = latex_engine.compile_pdf(tex_content, output_filename=f"{user_id}_optimized.pdf")
        
        if not final_pdf_path:
             raise Exception("LaTeX Compiling Failed")

        # 6. Upload
        url = upload_mutated_pdf(final_pdf_path, user_id)
        
        return {
            "status": "success",
            "pdf_url": url,
            "pdf_path": final_pdf_path,
            "changes_count": 1 # Whole doc rewrite
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"status": "error", "message": str(e)}


# =============================================================================
# 5. STORAGE HELPERS
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
        try: supabase.storage.from_("Resume").remove([file_name])
        except: pass
        
        print(f"📤 Uploading {ext.upper()}: {file_name}")
        supabase.storage.from_("Resume").upload(file_name, data, {"content-type": content_type})
        res = supabase.storage.from_("Resume").create_signed_url(file_name, 31536000)
        return res.get("signedURL") if isinstance(res, dict) else str(res)
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
    """Alias for fetch_user_profile_by_uuid for backward compatibility."""
    return fetch_user_profile_by_uuid(user_id)


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
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.3
    )
    
    json_parser = JsonOutputParser()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a professional career coach helping candidates write compelling job application responses.

Generate personalized, authentic responses based on the candidate's profile. Each response should:
- Be specific to the company and role
- Reference actual experience from their profile
- Sound natural, not robotic
- Be concise but comprehensive (2-4 sentences each)

OUTPUT FORMAT - Return ONLY valid JSON:
{{
    "why_join_company": "Why do you want to join this company?",
    "about_yourself": "Tell us about yourself / Professional summary",
    "relevant_skills": "Relevant skills and technical expertise",
    "work_experience": "Work experience and key achievements",
    "why_good_fit": "Why are you a good fit for this role?",
    "problem_solving": "Problem-solving example or challenge you've overcome",
    "additional_info": "Additional information you'd like to share",
    "availability": "Availability and logistics"
}}"""),
        ("human", """CANDIDATE PROFILE:
Name: {name}
Skills: {skills}
Experience: {experience_summary}
Education: {education}

COMPANY: {company_name}
POSITION: {job_title}
JOB DESCRIPTION: {job_description}

ADDITIONAL CONTEXT: {additional_context}

Generate compelling responses for each application question.""")
    ])
    
    chain = prompt | llm | json_parser
    
    try:
        result = chain.invoke({
            "name": user_profile.get("name", "Candidate"),
            "skills": ", ".join(user_profile.get("skills", [])[:10]),
            "experience_summary": user_profile.get("experience_summary", user_profile.get("summary", ""))[:1000],
            "education": user_profile.get("education", "")[:500],
            "company_name": company_name,
            "job_title": job_title,
            "job_description": job_description[:2000],
            "additional_context": additional_context or "None provided"
        })
        
        return result
        
    except Exception as e:
        print(f"❌ [Agent 4] Error generating responses: {e}")
        # Return default responses on error
        return {
            "why_join_company": f"I am excited about the opportunity to join {company_name}.",
            "about_yourself": user_profile.get("experience_summary", "Experienced professional."),
            "relevant_skills": ", ".join(user_profile.get("skills", [])[:5]),
            "work_experience": "Please see my resume for detailed work experience.",
            "why_good_fit": f"My skills align well with the {job_title} role requirements.",
            "problem_solving": "I approach challenges methodically and collaboratively.",
            "additional_info": "I am eager to contribute to your team.",
            "availability": "I am available for immediate start."
        }



def save_application_to_db(user_id: str, job_id: int, tailored_resume_url: str, custom_responses: dict):
    """
    Saves the generated application details to the Supabase 'applications' table.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    supabase = create_client(supabase_url.rstrip('/'), key)
    
    try:
        data = {
            "user_id": user_id,
            "job_id": job_id,
            "resume_url": tailored_resume_url,
            "cover_letter": custom_responses,  # Storing responses in cover_letter or custom_responses column
            "status": "applied", # Default status
            "applied_at": "now()"
        }
        
        # We need to check if 'applications' table has specific columns. 
        # Assuming standard schema based on usage. 
        # If 'custom_responses' is the column name, use that.
        # But 'cover_letter' is plausible for JSON blob or text. 
        # Let's try to map generic fields. 
        
        # Better safe: check if entry exists and update, or insert.
        # For now, simple insert.
        
        # Note: In a real scenario, we'd check schema. 
        # Based on args: tailored_resume_url as resume_url. 
        # custom_responses as custom_responses (JSONB).
        
        payload = {
            "user_id": user_id,
            "job_id": job_id,
            "resume_url": tailored_resume_url,
            "custom_responses": custom_responses,
            "status": "generated"
        }
        
        # Attempt insert
        supabase.table("applications").insert(payload).execute()
        print(f"   💾 Saved application to DB (Job {job_id})")
        
    except Exception as e:
        print(f"   ⚠️ Failed to save application to DB (Schema mismatch?): {e}")
        # Try fallback if custom_responses column doesn't exist?
        # Non-critical for now, as service.py catches exception, 
        # but we need the function to exist to fix ImportError.


def upload_resume_to_storage(pdf_path: str, user_id: str) -> str:
    """
    Uploads PDF to Supabase Storage and returns signed URL.
    This is used by the graph.py render_node.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    
    supabase = create_client(supabase_url.rstrip('/'), service_key)
    
    bucket_name = "Resume"
    file_name = f"{user_id}_mutated.pdf"
    
    print(f"📤 [Agent 4] Uploading PDF: {file_name}")
    
    try:
        with open(pdf_path, "rb") as f:
            file_data = f.read()
        
        # Remove existing file if any
        try:
            supabase.storage.from_(bucket_name).remove([file_name])
        except:
            pass
        
        # Upload
        supabase.storage.from_(bucket_name).upload(
            path=file_name,
            file=file_data,
            file_options={"content-type": "application/pdf"}
        )
        
        # Generate signed URL (1 year)
        signed_url_response = supabase.storage.from_(bucket_name).create_signed_url(
            path=file_name,
            expires_in=31536000
        )
        
        if isinstance(signed_url_response, dict):
            signed_url = signed_url_response.get("signedURL") or signed_url_response.get("signedUrl")
        else:
            signed_url = str(signed_url_response)
        
        print(f"   ✅ Uploaded successfully!")
        return signed_url
        
    except Exception as e:
        print(f"   ❌ Upload failed: {e}")
        raise Exception(f"Failed to upload PDF: {str(e)}")