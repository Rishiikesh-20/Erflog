# backend/agents/agent_1_perception/service.py
import os
import shutil
import uuid
import tempfile
from pathlib import Path
from fastapi import UploadFile
from supabase import create_client
from pinecone import Pinecone, ServerlessSpec

# Import your tools
from .tools import parse_pdf, extract_structured_data, generate_embedding, upload_resume_to_storage
from .github_watchdog import fetch_and_analyze_github, get_latest_user_activity

class PerceptionService:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # Use Service Key!
        self.supabase = create_client(self.supabase_url, self.supabase_key)
        
        # Init Pinecone
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "career-flow")
        self.index = self.pc.Index(self.index_name)

    async def process_resume_upload(self, file: UploadFile, user_id: str = None) -> dict:
        """
        Handles the full flow: PDF Save -> Parse -> Gemini -> DB -> Pinecone
        """
        # 1. Generate ID if not provided (Anonymous vs Auth flow)
        if not user_id:
            user_id = str(uuid.uuid4())

        # 2. Save File Temporarily
        temp_dir = Path(tempfile.gettempdir()) / "agent1_uploads"
        temp_dir.mkdir(exist_ok=True)
        pdf_path = temp_dir / f"{user_id}_{file.filename}"
        
        with open(pdf_path, "wb") as f:
            content = await file.read()
            f.write(content)

        try:
            # 3. Upload to Storage (Long-term)
            resume_url = upload_resume_to_storage(str(pdf_path), user_id)

            # 4. Parse & Extract
            resume_text = parse_pdf(str(pdf_path))
            extracted_data = extract_structured_data(resume_text)
            
            # 5. Generate Vector
            summary = extracted_data.get("experience_summary", resume_text[:500])
            embedding = generate_embedding(summary)

            # 6. Prepare DB Record (Supabase Profiles)
            profile_data = {
                "user_id": user_id, # Matches Auth ID (Primary Key)
                "name": extracted_data.get("name"),
                "email": extracted_data.get("email"),
                "skills": extracted_data.get("skills", []),
                "experience_summary": summary,
                "education": extracted_data.get("education"),
                "resume_json": extracted_data,
                "resume_text": resume_text,
                "resume_url": resume_url,
                "created_at": "now()"
            }

            # 7. Upsert to DB (Using upsert to handle updates)
            self.supabase.table("profiles").upsert(profile_data).execute()

            # 8. Upsert to Pinecone (Namespace: users)
            vector_data = {
                "id": user_id, 
                "values": embedding,
                "metadata": {
                    "email": extracted_data.get("email"),
                    "skills": extracted_data.get("skills", []),
                    "type": "user_profile"
                }
            }
            self.index.upsert(vectors=[vector_data], namespace="users")

            return profile_data

        finally:
            # Cleanup temp file
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

    async def run_github_watchdog(self, user_id: str, github_url: str):
        """
        Can be called by API (Sync Button) OR Scheduler (Background Loop)
        """
        # 1. Analyze
        analysis = fetch_and_analyze_github(github_url)
        if not analysis:
            return None

        new_skills = [item['skill'] for item in analysis.get('detected_skills', [])]

        # 2. Get Current Skills from DB
        response = self.supabase.table("profiles").select("skills").eq("user_id", user_id).execute()
        current_skills = []
        if response.data:
            current_skills = response.data[0].get("skills") or []

        # 3. Merge (New skills first)
        unique_old = [s for s in current_skills if s not in new_skills]
        final_skills = new_skills + unique_old

        # 4. Update DB
        self.supabase.table("profiles").update({
            "skills": final_skills,
            "github_url": github_url
        }).eq("user_id", user_id).execute()

        # 5. Update Pinecone (CRITICAL for Agent 2 to find better jobs)
        # We need to re-fetch the user embedding or generate a new "skill vector"
        # For now, we update the metadata so metadata filtering works
        self.index.update(
            id=user_id,
            set_metadata={"skills": final_skills},
            namespace="users"
        )

        return {"updated_skills": final_skills, "analysis": analysis}

# Singleton Instance
agent1_service = PerceptionService()