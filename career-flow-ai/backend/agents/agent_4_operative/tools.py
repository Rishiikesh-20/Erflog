import os
import json
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# Load environment variables
load_dotenv()


def download_resume_pdf(user_id: str, output_dir: str = None) -> str:
    """
    Downloads resume PDF from Supabase storage bucket 'Resume'.
    
    Args:
        user_id: The user ID (e.g., '123' for file 'USER-123.pdf').
        output_dir: Directory to save the downloaded PDF.
    
    Returns:
        Path to the downloaded PDF file.
    """
    from core.db import db_manager
    
    supabase = db_manager.get_client()
    
    # File name format: USER-{user_id}.pdf
    file_name = f"USER-{user_id}.pdf"
    bucket_name = "Resume"
    
    print(f"📥 Downloading resume from Supabase bucket '{bucket_name}'...")
    print(f"   File: {file_name}")
    
    # Download file from Supabase storage
    response = supabase.storage.from_(bucket_name).download(file_name)
    
    # Set output directory
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "downloads")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Save to local file
    local_path = os.path.join(output_dir, file_name)
    with open(local_path, "wb") as f:
        f.write(response)
    
    print(f"   ✅ Saved to: {local_path}")
    
    return local_path


def get_resume_public_url(user_id: str) -> str:
    """
    Gets the public URL for a resume PDF in Supabase storage.
    
    Args:
        user_id: The user ID (e.g., '123' for file 'USER-123.pdf').
    
    Returns:
        Public URL to the PDF.
    """
    from core.db import db_manager
    
    supabase = db_manager.get_client()
    
    file_name = f"USER-{user_id}.pdf"
    bucket_name = "Resume"
    
    # Get public URL
    response = supabase.storage.from_(bucket_name).get_public_url(file_name)
    
    return response


def fetch_user_profile_by_uuid(user_id: str) -> dict:
    """
    Fetches full user profile from Supabase by user_id (UUID).
    
    Args:
        user_id: The UUID of the user (e.g., '22c91dc9-4238-499b-a107-5b1abf3b919c').
    
    Returns:
        The full user profile with all fields.
    """
    from core.db import db_manager
    
    supabase = db_manager.get_client()
    
    response = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
    
    if not response.data:
        raise ValueError(f"Profile with user_id '{user_id}' not found in Supabase")
    
    profile = response.data[0]
    
    print(f"📡 Found profile in Supabase:")
    print(f"   User ID: {profile.get('user_id')}")
    print(f"   Name: {profile.get('name')}")
    print(f"   Email: {profile.get('email')}")
    print(f"   Skills: {profile.get('skills', [])[:5]}...")
    
    return profile


def build_resume_from_profile(profile: dict) -> dict:
    """
    Builds a structured resume dict from Supabase profile data.
    Uses resume_json if available, otherwise constructs from individual fields.
    
    Args:
        profile: The profile data from Supabase.
    
    Returns:
        Structured resume dictionary ready for PDF generation.
    """
    # If resume_json exists and is valid, use it
    resume_json = profile.get("resume_json")
    if resume_json and isinstance(resume_json, dict):
        return resume_json
    
    # Otherwise, construct from individual fields
    return {
        "name": profile.get("name", "Unknown"),
        "email": profile.get("email", ""),
        "skills": profile.get("skills", []),
        "summary": profile.get("experience_summary", ""),
        "experience_summary": profile.get("experience_summary", ""),
        "education": profile.get("education", []),
        "resume_text": profile.get("resume_text", ""),
    }


def fetch_user_profile(profile_id: int) -> dict:
    """
    Fetches full user profile from Supabase by profile ID.
    """
    from core.db import db_manager
    
    supabase = db_manager.get_client()
    
    response = supabase.table("profiles").select("*").eq("id", profile_id).execute()
    
    if not response.data:
        raise ValueError(f"Profile {profile_id} not found in Supabase")
    
    profile = response.data[0]
    
    print(f"📡 Found profile in Supabase:")
    print(f"   ID: {profile.get('id')}")
    print(f"   Name: {profile.get('name')}")
    print(f"   Email: {profile.get('email')}")
    print(f"   Skills: {profile.get('skills', [])[:5]}...")
    
    return build_resume_from_profile(profile)


def rewrite_resume_content(original_resume_json: dict, job_description: str) -> dict:
    """
    Rewrites resume content to match job description keywords.
    Sends profile data to Gemini and builds an optimized resume.
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.3
    )
    
    json_parser = JsonOutputParser()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert resume writer and ATS optimization specialist.
Your task is to create/rewrite a professional resume optimized for the target job description.

INPUT: You will receive user profile data which may include:
- name, email, skills, experience_summary, education, resume_text

YOUR TASK:
1. Extract relevant keywords from the job description and incorporate them naturally.
2. Create a professional summary tailored to the job.
3. Format experience bullets with action verbs and quantifiable achievements.
4. Remain 100% truthful - do not fabricate skills or experiences.
5. If resume_text exists, use it as the primary source for experience details.

OUTPUT FORMAT - Return ONLY valid JSON with this exact structure:
{{
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "",
    "location": "",
    "linkedin": "",
    "github": "",
    "summary": "Professional summary tailored to job...",
    "experience": [
        {{
            "title": "Job Title",
            "company": "Company Name",
            "location": "City, State",
            "start_date": "Month Year",
            "end_date": "Month Year or Present",
            "bullets": ["Achievement 1...", "Achievement 2..."]
        }}
    ],
    "education": [
        {{
            "degree": "Degree Name",
            "institution": "University Name",
            "graduation_date": "Year",
            "gpa": ""
        }}
    ],
    "skills": ["Skill 1", "Skill 2", "..."],
    "certifications": [],
    "projects": []
}}

No additional text or explanation - ONLY the JSON."""),
        ("human", """User Profile Data:
{original_resume}

Target Job Description:
{job_description}

Build an ATS-optimized resume JSON for this job.""")
    ])
    
    chain = prompt | llm | json_parser
    
    rewritten_resume = chain.invoke({
        "original_resume": json.dumps(original_resume_json, indent=2),
        "job_description": job_description
    })
    
    return rewritten_resume


def find_recruiter_email(company_domain: str) -> dict:
    """
    Finds recruiter email using Hunter.io API.
    Currently a mock implementation.
    """
    return {
        "email": f"recruiter@{company_domain}",
        "first_name": "Hiring",
        "last_name": "Manager",
        "position": "Talent Acquisition",
        "confidence": 85,
        "source": "mock"
    }


def upload_resume_to_storage(pdf_path: str, user_id: str, expires_in: int = 86400) -> str:
    """
    Uploads the generated resume PDF to Supabase storage bucket 'Resume'.
    Uses service role key to bypass RLS.
    """
    import os
    from supabase import create_client
    
    supabase_url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not service_key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY not found in .env")
    
    print(f"   🔑 Using service role key: {service_key[:20]}...")
    
    # Create a new client with service role key (bypasses RLS)
    supabase = create_client(supabase_url.rstrip('/'), service_key)
    
    bucket_name = "Resume"
    file_name = f"{user_id}.pdf"
    
    print(f"📤 Uploading resume to Supabase storage...")
    print(f"   Bucket: {bucket_name}")
    print(f"   File: {file_name}")
    
    # Read the PDF file
    with open(pdf_path, "rb") as f:
        file_data = f.read()
    
    # Try to remove existing file first (ignore errors)
    try:
        supabase.storage.from_(bucket_name).remove([file_name])
        print(f"   🗑️ Removed existing file")
    except Exception as e:
        print(f"   ℹ️ No existing file to remove: {e}")
    
    # Upload to Supabase storage
    try:
        response = supabase.storage.from_(bucket_name).upload(
            path=file_name,
            file=file_data,
            file_options={"content-type": "application/pdf"}
        )
        print(f"   📦 Upload response: {response}")
    except Exception as e:
        # If file exists, try update instead
        if "Duplicate" in str(e) or "already exists" in str(e):
            print(f"   🔄 File exists, updating...")
            response = supabase.storage.from_(bucket_name).update(
                path=file_name,
                file=file_data,
                file_options={"content-type": "application/pdf"}
            )
        else:
            raise e
    
    # Get signed URL
    signed_url_response = supabase.storage.from_(bucket_name).create_signed_url(
        path=file_name,
        expires_in=expires_in
    )
    signed_url = signed_url_response.get("signedURL", "")
    
    print(f"   ✅ Uploaded successfully!")
    print(f"   📎 Signed URL: {signed_url[:80]}...")
    
    return signed_url
