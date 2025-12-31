# ... (Imports remain the same) ...
import uuid
import os
from typing import Any
from core.state import AgentState
from core.db import db_manager
from .tools import parse_pdf, extract_structured_data, generate_embedding
from pinecone import Pinecone, ServerlessSpec

def init_pinecone():
    """Initialize Pinecone client."""
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY missing in .env")
    return Pinecone(api_key=api_key)

def perception_node(state: AgentState) -> dict[str, Any]:
    try:
        # ... (PDF Parsing and Gemini Extraction Logic stays the same) ...
        # [Copy steps 1-5 from your previous code here, or just paste the whole function below]
        
        pdf_path = state.get("context", {}).get("pdf_path")
        if not pdf_path:
            raise ValueError("PDF file path not provided")
        
        # 1. Parse PDF
        print(f"[Perception] Parsing PDF: {pdf_path}")
        resume_text = parse_pdf(pdf_path)
        
        # 2. Extract Data
        print("[Perception] Extracting structured data...")
        extracted_data = extract_structured_data(resume_text)
        
        # 3. Generate Embedding
        print("[Perception] Generating embedding...")
        experience_summary = extracted_data.get("experience_summary", resume_text[:500])
        embedding = generate_embedding(experience_summary)
        
        # 4. Generate IDs
        user_id = str(uuid.uuid4())
        
        # 5. Store Structured Data -> Supabase
        print("[Perception] Storing JSON in Supabase...")
        supabase = db_manager.get_client()
        
        profile_data = {
            "user_id": user_id,
            "name": extracted_data.get("name"),
            "email": extracted_data.get("email"),
            "skills": extracted_data.get("skills", []),
            "experience_summary": extracted_data.get("experience_summary"),
            "education": extracted_data.get("education"),
            "resume_json": extracted_data,
        }
        
        profile_response = supabase.table("profiles").insert(profile_data).execute()
        if not profile_response.data:
            raise Exception("Supabase insert failed")
            
        profile_id = profile_response.data[0]["id"]

        # 6. Store Vector -> Pinecone (NAMESPACE ADDED HERE)
        print("[Perception] Storing Vector in Pinecone (Namespace: users)...")
        pc = init_pinecone()
        index_name = os.getenv("PINECONE_INDEX_NAME", "career-agent")
        
        if index_name not in pc.list_indexes().names():
            print(f"Creating Pinecone index: {index_name}")
            pc.create_index(
                name=index_name,
                dimension=768, 
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
            
        index = pc.Index(index_name)
        
        vector_data = {
            "id": user_id, 
            "values": embedding,
            "metadata": {
                "profile_id": profile_id,
                "email": extracted_data.get("email"),
                "skills": extracted_data.get("skills", [])
            }
        }
        
        # --- THE CHANGE IS HERE ---
        index.upsert(vectors=[vector_data], namespace="users")
        # --------------------------
        
        print(f"[Perception] Success! User: {user_id}")
        
        # 7. Update State
        updated_state = state.copy()
        updated_state["resume_text"] = resume_text
        updated_state["skills"] = extracted_data.get("skills", [])
        updated_state["user_id"] = user_id
        
        return updated_state
    
    except Exception as e:
        print(f"[Perception] Error: {str(e)}")
        updated_state = state.copy()
        updated_state["results"] = {**state.get("results", {}), "error": str(e)}
        raise e