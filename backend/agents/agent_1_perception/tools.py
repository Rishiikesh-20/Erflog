"""
Agent 1 Perception - Helper Tools (LangChain Edition)
1. Parse PDF
2. Extract Data (LangChain Chain)
3. Generate Embeddings (LangChain Embeddings)
4. Upload PDF to Supabase Storage
5. Generate Skill Quiz (Verification)
"""

import os
import json
from typing import Any, Optional, Dict, List
from pypdf import PdfReader
from supabase import create_client

# --- LANGCHAIN IMPORTS ---
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser


def parse_pdf(file_path: str) -> str:
    """Parse a PDF file and extract all text."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Error parsing PDF: {str(e)}")


def extract_structured_data(text: str) -> dict[str, Any]:
    """
    Extract structured data using a LangChain extraction chain.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY must be set in .env")
    
    # 1. Initialize the LLM
    # Using gemini-2.0-flash for JSON stability
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash", 
        temperature=0, 
        google_api_key=api_key
    )
    
    # 2. Define the Output Parser
    parser = JsonOutputParser()
    
    # 3. Get format instructions and escape curly braces to prevent PromptTemplate conflicts
    format_instructions = parser.get_format_instructions()
    # Escape any { } in the format_instructions that aren't template variables
    format_instructions_escaped = format_instructions.replace("{", "{{").replace("}", "}}")
    
    # 3. Define the Prompt Template
    prompt = PromptTemplate(
        template="""
        You are an expert Resume Parser. 
        Extract the following information from the resume into a JSON object with these keys:
        - "name": string (full name of the person)
        - "email": string (email address)
        - "skills": array of strings (flat list of all technical skills, e.g., ["Python", "React", "Docker"])
        - "experience_summary": string (brief summary of work experience)
        - "education": array of objects with "institution" and "degree" keys
        
        IMPORTANT RULES:
        1. "skills" must be a SINGLE FLAT LIST of strings. Do not categorize them.
        2. Example: ["Python", "React", "Docker", "AWS"] NOT {{"languages": ["Python"]}}
        3. Return ONLY valid JSON, no markdown code blocks.
        
        RESUME TEXT:
        {text}
        
        Return the JSON object:
        """,
        input_variables=["text"],
    )
    
    # 4. Create the Chain
    chain = prompt | llm | parser
    
    try:
        print("[LangChain] Extracting structured profile data...")
        data = chain.invoke({"text": text})
        
        # --- ROBUST FLATTENING LOGIC ---
        raw_skills = data.get("skills", [])
        flat_skills = []
        
        if isinstance(raw_skills, str):
            # Case 1: Gemini gave a single string "Python, Java, Go"
            if "," in raw_skills:
                flat_skills = [s.strip() for s in raw_skills.split(",")]
            else:
                flat_skills = [raw_skills]
                
        elif isinstance(raw_skills, dict):
            # Case 2: Gemini gave a dict {'languages': [...]}
            for category, items in raw_skills.items():
                if isinstance(items, list):
                    flat_skills.extend([str(i) for i in items])
                elif isinstance(items, str):
                    flat_skills.append(items)
                    
        elif isinstance(raw_skills, list):
            # Case 3: List (Mixed content)
            for item in raw_skills:
                if isinstance(item, dict):
                    # If list contains dicts, flatten values
                    for val in item.values():
                        if isinstance(val, list): flat_skills.extend([str(v) for v in val])
                        else: flat_skills.append(str(val))
                elif isinstance(item, str):
                    # Clean stringified dicts
                    if item.startswith("{") and ":" in item:
                        continue 
                    flat_skills.append(item)
        
        # Final cleanup: Remove empty strings and duplicates
        data["skills"] = list(set([s for s in flat_skills if s and isinstance(s, str)]))
        # -------------------------------

        return data

    except Exception as e:
        print(f"[LangChain] Extraction Error: {e}")
        return {
            "name": None,
            "email": None, 
            "skills": [], 
            "experience_summary": "Extraction failed", 
            "education": []
        }


def generate_embedding(text: str) -> list[float]:
    """
    Generate embeddings using LangChain's wrapper.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY must be set in .env")

    try:
        embeddings_model = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001", 
            google_api_key=api_key
        )
        return embeddings_model.embed_query(text)
    except Exception as e:
        raise Exception(f"Error generating embedding: {str(e)}")


def upload_resume_to_storage(pdf_path: str, user_id: str) -> str:
    """
    Uploads the PDF to Supabase 'Resume' bucket and returns a Signed URL.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    # CRITICAL: Use Service Role Key to bypass RLS for uploads
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not service_key:
        print("⚠️ Warning: SUPABASE_SERVICE_ROLE_KEY not found. Upload might fail due to permissions.")
        service_key = os.getenv("SUPABASE_KEY")  # Fallback
    
    # Initialize client
    supabase = create_client(supabase_url, service_key)
    
    bucket_name = "Resume"
    file_name = f"{user_id}.pdf"
    
    print(f"[Perception] Uploading original PDF to Storage (Bucket: {bucket_name})...")
    
    try:
        with open(pdf_path, "rb") as f:
            file_data = f.read()
            
        # Upload (overwrite if exists)
        supabase.storage.from_(bucket_name).upload(
            path=file_name,
            file=file_data,
            file_options={"content-type": "application/pdf", "upsert": "true"}
        )
        
        # Generate Signed URL (1 year validity)
        signed_url_response = supabase.storage.from_(bucket_name).create_signed_url(
            path=file_name,
            expires_in=31536000 
        )
        
        # Handle SDK version differences
        if isinstance(signed_url_response, dict):
            signed_url = signed_url_response.get("signedURL")
        else:
            signed_url = signed_url_response 
             
        print(f"[Perception] PDF Uploaded! URL generated.")
        return signed_url

    except Exception as e:
        print(f"[Perception] ❌ Error uploading PDF: {str(e)}")
        return None


# =============================================================================
# SKILL VERIFICATION: Quiz Generation
# =============================================================================

def generate_skill_quiz(skill_name: str, level: str = "intermediate") -> Optional[Dict[str, Any]]:
    """
    Generate a multiple-choice quiz question for skill verification.
    
    Args:
        skill_name: The skill to test (e.g., "React", "Python", "Docker")
        level: Difficulty level - "beginner", "intermediate", "advanced"
        
    Returns:
        Dict with question, options, correct_index, explanation
        Or None if generation fails
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️ GEMINI_API_KEY not set")
        return None
    
    # 1. Initialize LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",  # Switched to 1.5-flash
        temperature=0.7,  # Slight creativity for varied questions
        google_api_key=api_key
    )
    
    # 2. Setup Parser
    parser = JsonOutputParser()
    
    # 3. Define Prompt
    prompt = PromptTemplate(
        template="""
        You are a technical interviewer creating a skill verification quiz.
        
        Generate ONE multiple-choice question to verify someone's knowledge of: {skill_name}
        Difficulty Level: {level}
        
        Requirements:
        - Question should test practical/applied knowledge, not just definitions
        - For {level} level:
          - beginner: Basic concepts and syntax
          - intermediate: Common patterns and best practices  
          - advanced: Edge cases, performance, architecture decisions
        - Provide exactly 4 options (only ONE correct)
        - Options should be plausible (no obviously wrong answers)
        
        {format_instructions}
        
        Return a JSON object with these exact keys:
        - "question": The question text
        - "options": Array of exactly 4 answer strings
        - "correct_index": Index (0-3) of the correct answer
        - "explanation": Brief explanation of why the answer is correct
        """,
        input_variables=["skill_name", "level"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    
    # 4. Create Chain
    chain = prompt | llm | parser
    
    try:
        print(f"[Quiz] Generating {level} question for: {skill_name}")
        result = chain.invoke({
            "skill_name": skill_name,
            "level": level
        })
        
        # Validate response structure
        if not all(k in result for k in ["question", "options", "correct_index"]):
            print(f"[Quiz] Invalid response structure: {result}")
            return None
            
        if len(result.get("options", [])) != 4:
            print(f"[Quiz] Expected 4 options, got {len(result.get('options', []))}")
            return None
            
        if not isinstance(result.get("correct_index"), int) or result["correct_index"] not in range(4):
            print(f"[Quiz] Invalid correct_index: {result.get('correct_index')}")
            return None
        
        return result
        
    except Exception as e:
        print(f"[Quiz] Generation Error: {e}")
        return None


# =============================================================================
# ONBOARDING: Generate 5 Quiz Questions
# =============================================================================

def generate_onboarding_questions(
    skills: List[str], 
    target_roles: List[str]
) -> Optional[List[Dict[str, Any]]]:
    """
    Generate 5 MCQ questions for onboarding based on user's skills and target roles.
    
    Args:
        skills: User's listed skills
        target_roles: User's target job roles
        
    Returns:
        List of 5 questions with id, question, options, correct_index, skill_being_tested
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️ GEMINI_API_KEY not set")
        return None
    
    # 1. Initialize LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.7,
        google_api_key=api_key
    )
    
    # 2. Setup Parser
    parser = JsonOutputParser()
    
    # 3. Build context from skills and roles
    skills_str = ", ".join(skills[:8]) if skills else "general programming"
    roles_str = ", ".join(target_roles[:3]) if target_roles else "software engineering"
    
    # 4. Define Prompt
    prompt = PromptTemplate(
        template="""
        You are creating an onboarding assessment for a career platform.
        
        Generate exactly 5 multiple-choice questions to assess a candidate with these details:
        - Skills: {skills}
        - Target Roles: {target_roles}
        
        Requirements:
        1. Questions should test practical knowledge relevant to their skills and target roles
        2. Mix difficulty: 2 easy, 2 medium, 1 challenging
        3. Each question should have exactly 4 options with only ONE correct answer
        4. Questions should feel professional and relevant to job interviews
        5. Cover different skills if possible
        
        {format_instructions}
        
        Return a JSON object with this structure:
        {{
            "questions": [
                {{
                    "id": "q1",
                    "question": "Question text here",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_index": 0,
                    "skill_being_tested": "Python"
                }},
                ... (4 more questions)
            ]
        }}
        
        Important: Return exactly 5 questions.
        """,
        input_variables=["skills", "target_roles"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    
    # 5. Create Chain
    chain = prompt | llm | parser
    
    try:
        print(f"[Onboarding Quiz] Generating 5 questions for skills: {skills_str}")
        result = chain.invoke({
            "skills": skills_str,
            "target_roles": roles_str
        })
        
        questions = result.get("questions", [])
        
        # Validate we have 5 questions
        if len(questions) < 5:
            print(f"[Onboarding Quiz] Warning: Only got {len(questions)} questions")
            return None
        
        # Validate each question structure
        validated_questions = []
        for i, q in enumerate(questions[:5]):
            if not all(k in q for k in ["question", "options", "correct_index"]):
                print(f"[Onboarding Quiz] Question {i} missing required fields")
                continue
            
            if len(q.get("options", [])) != 4:
                print(f"[Onboarding Quiz] Question {i} doesn't have 4 options")
                continue
                
            validated_questions.append({
                "id": q.get("id", f"q{i+1}"),
                "question": q["question"],
                "options": q["options"],
                "correct_index": q["correct_index"],
                "skill_being_tested": q.get("skill_being_tested", skills[i % len(skills)] if skills else "General")
            })
        
        if len(validated_questions) < 5:
            print(f"[Onboarding Quiz] Only {len(validated_questions)} valid questions after validation")
            return None
            
        return validated_questions
        
    except Exception as e:
        print(f"[Onboarding Quiz] Generation Error: {e}")
        return None