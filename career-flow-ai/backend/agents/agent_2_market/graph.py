"""
Agent 2: Market Sentinel
LangGraph node for searching jobs and storing them in Supabase + Pinecone.

SQL Schema for Required Tables:
================================================================================

-- Create jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT,
    link TEXT,
    summary TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_jobs_title ON jobs(title);
CREATE INDEX idx_jobs_company ON jobs(company);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);

================================================================================
"""

import os
from typing import Any
from core.state import AgentState
from core.db import db_manager
from .tools import search_jobs, generate_embedding
from pinecone import Pinecone, ServerlessSpec


def init_pinecone():
    """
    Initialize and return Pinecone index.
    """
    try:
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            print("[Market] PINECONE_API_KEY not found")
            return None
        
        index_name = os.getenv("PINECONE_INDEX_NAME", "career-flow-jobs")
        
        # Initialize Pinecone client (new SDK)
        pc = Pinecone(api_key=api_key)
        
        # Get or create index
        if index_name not in pc.list_indexes().names():
            print(f"Creating Pinecone index: {index_name}")
            pc.create_index(
                name=index_name,
                dimension=768, 
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
            
        index = pc.Index(index_name)
        return index
    
    except ImportError:
        print("[Market] pinecone library not installed")
        return None
    except Exception as e:
        print(f"[Market] Pinecone initialization failed: {str(e)}")
        return None


def market_scan_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node function for the Market Sentinel Agent.
    """
    job_matches = []
    
    try:
        # Step 1: Get skills from state and form search query
        skills = state.get("skills", [])
        
        if not skills or len(skills) == 0:
            print("[Market] No skills found in state, using default query")
            search_query = "Software Engineer Python jobs"
        else:
            top_skills = skills[:3]
            search_query = f"Software Engineer jobs {' '.join(top_skills)}"
        
        print(f"[Market] Searching jobs with query: {search_query}")
        
        # Step 2: Search for jobs
        jobs = search_jobs(search_query)
        print(f"[Market] Found {len(jobs)} jobs")
        
        if not jobs:
            print("[Market] No jobs found")
            updated_state = state.copy()
            updated_state["job_matches"] = []
            updated_state["results"] = {
                **state.get("results", {}),
                "market": {
                    "jobs_found": 0,
                    "jobs_saved": 0,
                    "vectors_saved": 0,
                    "message": "No jobs found"
                }
            }
            return updated_state
        
        # Step 3: Save jobs to Supabase
        print("[Market] Saving jobs to Supabase...")
        supabase = db_manager.get_client()
        saved_jobs = []
        
        for job in jobs:
            try:
                job_data = {
                    "title": job.get("title", "Unknown Title"),
                    "company": job.get("company", "Unknown Company"),
                    "link": job.get("link", ""),
                    "summary": job.get("summary", ""),
                }
                
                response = supabase.table("jobs").insert(job_data).execute()
                
                if response.data:
                    saved_job = response.data[0]
                    # Restore the full description if available (from tools.py)
                    if "description" in job:
                        saved_job["description"] = job["description"]
                    else:
                        saved_job["description"] = job.get("summary", "")
                        
                    saved_jobs.append(saved_job)
                    print(f"[Market] Saved job: {job_data['title']} at {job_data['company']}")
                
            except Exception as e:
                print(f"[Market] Failed to save job to Supabase: {str(e)}")
                continue
        
        print(f"[Market] Saved {len(saved_jobs)} jobs to Supabase")
        
        # Step 4: Save vectors to Pinecone
        print("[Market] Saving vectors to Pinecone...")
        pinecone_index = init_pinecone()
        vectors_saved = 0
        
        if pinecone_index:
            vectors_to_upsert = []
            
            for saved_job in saved_jobs:
                try:
                    # Generate embedding from job summary
                    job_text = f"{saved_job['title']} at {saved_job['company']}. {saved_job['summary']}"
                    embedding = generate_embedding(job_text)
                    
                    # Prepare vector for Pinecone
                    vector_id = f"job_{saved_job['id']}"
                    
                    metadata = {
                        "job_id": saved_job["id"],
                        "title": saved_job["title"],
                        "company": saved_job["company"],
                        "link": saved_job.get("link", ""),
                        "summary": saved_job.get("summary", "") # <--- ADDED THIS LINE
                    }
                    
                    vectors_to_upsert.append({
                        "id": vector_id,
                        "values": embedding,
                        "metadata": metadata
                    })
                    
                except Exception as e:
                    print(f"[Market] Failed to generate embedding for job {saved_job['id']}: {str(e)}")
                    continue
            
            # Batch upsert vectors to Pinecone (Namespace: default)
            if vectors_to_upsert:
                try:
                    pinecone_index.upsert(vectors=vectors_to_upsert)
                    vectors_saved = len(vectors_to_upsert)
                    print(f"[Market] Saved {vectors_saved} vectors to Pinecone")
                except Exception as e:
                    print(f"[Market] Failed to upsert vectors to Pinecone: {str(e)}")
        else:
            print("[Market] Pinecone not available, skipping vector storage")
        
        # Step 5: Prepare job matches for state
        job_matches = [
            {
                "id": job["id"],
                "title": job["title"],
                "company": job["company"],
                "link": job.get("link", ""),
                "description": job.get("description", job.get("summary", "")), # Ensure description is passed
                "summary": job.get("summary", "")[:200],
            }
            for job in saved_jobs
        ]
        
        print(f"[Market] Successfully processed {len(job_matches)} jobs")
        
        # Update and return state
        updated_state = state.copy()
        updated_state["job_matches"] = job_matches
        updated_state["results"] = {
            **state.get("results", {}),
            "market": {
                "jobs_found": len(jobs),
                "jobs_saved": len(saved_jobs),
                "vectors_saved": vectors_saved,
                "search_query": search_query,
                "job_ids": [job["id"] for job in saved_jobs],
                "job_matches": job_matches  # Add job_matches to results for API
            }
        }
        
        return updated_state
    
    except Exception as e:
        print(f"[Market] Error in market_scan_node: {str(e)}")
        updated_state = state.copy()
        updated_state["job_matches"] = job_matches
        updated_state["results"] = {
            **state.get("results", {}),
            "market_error": str(e)
        }
        return updated_state