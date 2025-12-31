"""
Agent 1 Perception - Helper Tools
1. Parse PDF
2. Extract Data (Gemini)
3. Generate Embeddings
4. Upload PDF to Supabase Storage
"""

import json
import os
from typing import Any
import google.generativeai as genai
from pypdf import PdfReader
from supabase import create_client

def init_gemini():
    """Initialize Gemini API."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY must be set in .env")
    genai.configure(api_key=api_key)

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
    """Extract structured data using Gemini."""
    init_gemini()
    prompt = f"""
    Please analyze the following resume/document text and extract the following information in JSON format:
    {{
        "name": "Full name",
        "email": "Email address",
        "skills": ["skill1", "skill2"],
        "experience_summary": "Brief summary",
        "education": "Education details"
    }}
    Resume Text:
    {text}
    Return ONLY valid JSON.
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = response_text
        
        data = json.loads(json_str)
        # Ensure list
        if not isinstance(data.get("skills"), list):
            data["skills"] = [str(data.get("skills", ""))] if data.get("skills") else []
        return data
    except Exception as e:
        raise Exception(f"Error extracting data: {str(e)}")

def generate_embedding(text: str) -> list[float]:
    """Generate embeddings."""
    init_gemini()
    try:
        result = genai.embed_content(model="models/embedding-001", content=text)
        return result['embedding']
    except Exception as e:
        raise Exception(f"Error generating embedding: {str(e)}")

def upload_resume_to_storage(pdf_path: str, user_id: str) -> str:
    """
    Uploads the PDF to Supabase 'Resume' bucket and returns a Signed URL.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    # CRITICAL: We use Service Role Key to bypass RLS for uploads
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not service_key:
        print("⚠️ Warning: SUPABASE_SERVICE_ROLE_KEY not found. Upload might fail due to permissions.")
        service_key = os.getenv("SUPABASE_KEY") # Fallback
    
    # Initialize client
    supabase = create_client(supabase_url, service_key)
    
    bucket_name = "Resume"
    # We rename the file to the user_id to keep it unique and linkable
    file_name = f"{user_id}.pdf"
    
    print(f"[Perception] Uploading original PDF to Storage (Bucket: {bucket_name})...")
    
    try:
        with open(pdf_path, "rb") as f:
            file_data = f.read()
            
        # Try upload (overwrite if exists)
        supabase.storage.from_(bucket_name).upload(
            path=file_name,
            file=file_data,
            file_options={"content-type": "application/pdf", "upsert": "true"}
        )
        
        # Generate a Signed URL valid for 1 year (31536000 seconds)
        # or use .get_public_url(file_name) if the bucket is public
        signed_url_response = supabase.storage.from_(bucket_name).create_signed_url(
            path=file_name,
            expires_in=31536000 
        )
        
        # Handle different SDK versions return types
        if isinstance(signed_url_response, dict):
             signed_url = signed_url_response.get("signedURL")
        else:
             signed_url = signed_url_response # In some versions it returns the string directly
             
        print(f"[Perception] PDF Uploaded! URL generated.")
        return signed_url

    except Exception as e:
        print(f"[Perception] ❌ Error uploading PDF: {str(e)}")
        return None