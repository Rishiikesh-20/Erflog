import os
import json
from dotenv import load_dotenv
from pinecone import Pinecone
from supabase import create_client
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# Load environment variables
load_dotenv()


def fetch_user_profile_from_db(user_id: str) -> dict:
    """
    Fetches user profile from Pinecone metadata and Supabase.
    
    Args:
        user_id: The user's unique identifier (stored in Pinecone).
    
    Returns:
        The full user profile/resume data from Supabase.
    """
    # 1. Initialize Pinecone and fetch vector metadata
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(os.getenv("PINECONE_INDEX_NAME", "ai-verse"))
    
    # Fetch vector by user_id from 'users' namespace
    fetch_response = index.fetch(ids=[user_id], namespace="users")
    
    if user_id not in fetch_response.vectors:
        raise ValueError(f"User {user_id} not found in Pinecone")
    
    # Get the Supabase profile_id from metadata
    metadata = fetch_response.vectors[user_id].metadata
    profile_id = metadata.get("profile_id")
    
    if not profile_id:
        raise ValueError(f"No profile_id in Pinecone metadata for user {user_id}")
    
    # 2. Fetch full profile from Supabase
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )
    
    response = supabase.table("profiles").select("*").eq("id", profile_id).execute()
    
    if not response.data:
        raise ValueError(f"Profile {profile_id} not found in Supabase")
    
    profile = response.data[0]
    
    # Return the resume_json field which contains the full structured resume
    return profile.get("resume_json", profile)


def rewrite_resume_content(original_resume_json: dict, job_description: str) -> dict:
    """
    Rewrites resume 'Summary' and 'Experience' bullets to match job description keywords.
    
    Args:
        original_resume_json: The original resume data as a dictionary.
        job_description: The target job description text.
    
    Returns:
        A dictionary containing the rewritten resume in the same schema.
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.3
    )
    
    json_parser = JsonOutputParser()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert resume writer and ATS optimization specialist.
Your task is to rewrite the 'Summary' and 'Experience' sections of a resume to better match a job description.

STRICT RULES:
1. Extract relevant keywords from the job description and incorporate them naturally.
2. Remain 100% truthful to the original resume content - do not fabricate skills or experiences.
3. Optimize bullet points for ATS (Applicant Tracking Systems) by using action verbs and quantifiable achievements.
4. Maintain the exact same JSON schema as the input resume.
5. Only modify 'summary' and 'experience' fields - keep all other fields unchanged.

OUTPUT FORMAT:
Return ONLY valid JSON matching the exact schema of the input resume. No additional text or explanation."""),
        ("human", """Original Resume JSON:
{original_resume}

Target Job Description:
{job_description}

Rewrite the resume to optimize for this job while staying truthful to the original content.
Return the complete resume as valid JSON.""")
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
    Currently a mock implementation - replace with actual Hunter.io integration.
    
    Args:
        company_domain: The company's domain (e.g., 'google.com').
    
    Returns:
        A dictionary with recruiter information.
    """
    # TODO: Implement actual Hunter.io API integration
    # hunter_api_key = os.getenv("HUNTER_API_KEY")
    # import requests
    # response = requests.get(
    #     f"https://api.hunter.io/v2/domain-search",
    #     params={"domain": company_domain, "api_key": hunter_api_key}
    # )
    
    # Mock response for now
    return {
        "email": f"recruiter@{company_domain}",
        "first_name": "Hiring",
        "last_name": "Manager",
        "position": "Talent Acquisition",
        "confidence": 85,
        "source": "mock"
    }
