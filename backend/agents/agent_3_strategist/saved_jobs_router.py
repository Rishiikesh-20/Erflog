"""
Saved Jobs & Global Roadmap Router
Handles saving jobs, fetching saved jobs, and merging roadmaps
"""

import os
import json
import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client
import google.generativeai as genai

# Initialize
router = APIRouter(prefix="/api/saved-jobs", tags=["Saved Jobs"])

# Supabase client
def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    return create_client(url, key)

# Gemini client
def get_llm():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash")

# =============================================================================
# Request/Response Models
# =============================================================================

class SaveJobRequest(BaseModel):
    user_id: str
    original_job_id: str
    title: str
    company: str
    description: Optional[str] = None
    link: Optional[str] = None
    score: Optional[float] = None
    roadmap_details: Optional[dict] = None
    full_job_data: Optional[dict] = None  # Full job data for complete save
    progress: Optional[dict] = None  # User progress on roadmap nodes

class SavedJobResponse(BaseModel):
    id: str
    user_id: str
    original_job_id: str
    title: str
    company: str
    description: Optional[str] = None
    link: Optional[str] = None
    score: Optional[float] = None
    roadmap_details: Optional[dict] = None
    progress: Optional[dict] = None  # User progress on roadmap nodes
    created_at: str

class MergeRoadmapsRequest(BaseModel):
    job_ids: List[str]  # IDs from saved_jobs table
    name: Optional[str] = "My Master Plan"

class GlobalRoadmapResponse(BaseModel):
    id: str
    name: str
    merged_graph: dict
    source_job_ids: List[str]
    created_at: str

# =============================================================================
# Saved Jobs Endpoints
# =============================================================================

@router.post("/save", response_model=SavedJobResponse)
async def save_job(request: SaveJobRequest):
    """Save a job to user's saved jobs list"""
    supabase = get_supabase()
    
    # Check if job is already saved
    existing = supabase.table("saved_jobs").select("id").eq(
        "user_id", request.user_id
    ).eq("original_job_id", request.original_job_id).execute()
    
    if existing.data:
        raise HTTPException(status_code=400, detail="Job already saved")
    
    # Merge full_job_data into roadmap_details for complete storage
    roadmap_data = request.roadmap_details or {}
    if request.full_job_data:
        roadmap_data = {
            **roadmap_data,
            "full_job_data": request.full_job_data
        }
    
    # Save the job
    job_data = {
        "user_id": request.user_id,
        "original_job_id": request.original_job_id,
        "title": request.title,
        "company": request.company,
        "description": request.description,
        "link": request.link,
        "score": request.score,
        "roadmap_details": roadmap_data,
        "progress": request.progress or {},  # Initialize empty progress
    }
    
    result = supabase.table("saved_jobs").insert(job_data).execute()
    
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to save job")
    
    saved_job = result.data[0]
    return SavedJobResponse(
        id=saved_job["id"],
        user_id=saved_job["user_id"],
        original_job_id=saved_job["original_job_id"],
        title=saved_job["title"],
        company=saved_job["company"],
        description=saved_job.get("description"),
        link=saved_job.get("link"),
        score=saved_job.get("score"),
        roadmap_details=saved_job.get("roadmap_details"),
        progress=saved_job.get("progress"),
        created_at=saved_job["created_at"]
    )


@router.get("/list/{user_id}", response_model=List[SavedJobResponse])
async def get_saved_jobs(user_id: str):
    """Get all saved jobs for a user"""
    supabase = get_supabase()
    
    result = supabase.table("saved_jobs").select("*").eq(
        "user_id", user_id
    ).order("created_at", desc=True).execute()
    
    return [
        SavedJobResponse(
            id=job["id"],
            user_id=job["user_id"],
            original_job_id=job["original_job_id"],
            title=job["title"],
            company=job["company"],
            description=job.get("description"),
            link=job.get("link"),
            score=job.get("score"),
            roadmap_details=job.get("roadmap_details"),
            progress=job.get("progress"),
            created_at=job["created_at"]
        )
        for job in result.data
    ]


@router.delete("/remove/{job_id}")
async def remove_saved_job(job_id: str):
    """Remove a job from saved jobs"""
    supabase = get_supabase()
    
    result = supabase.table("saved_jobs").delete().eq("id", job_id).execute()
    
    return {"status": "success", "message": "Job removed from saved jobs"}


@router.get("/check/{user_id}/{original_job_id}")
async def check_job_saved(user_id: str, original_job_id: str):
    """Check if a specific job is already saved"""
    supabase = get_supabase()
    
    result = supabase.table("saved_jobs").select("id").eq(
        "user_id", user_id
    ).eq("original_job_id", original_job_id).execute()
    
    return {"is_saved": len(result.data) > 0, "saved_job_id": result.data[0]["id"] if result.data else None}


class UpdateProgressRequest(BaseModel):
    node_id: str
    completed: bool


@router.put("/progress/{job_id}")
async def update_progress(job_id: str, request: UpdateProgressRequest):
    """Update progress on a roadmap node for a saved job"""
    supabase = get_supabase()
    
    # Get current job
    result = supabase.table("saved_jobs").select("progress").eq("id", job_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Saved job not found")
    
    # Update progress dict
    current_progress = result.data[0].get("progress") or {}
    current_progress[request.node_id] = {
        "completed": request.completed,
        "updated_at": datetime.now().isoformat()
    }
    
    # Save updated progress
    update_result = supabase.table("saved_jobs").update({
        "progress": current_progress
    }).eq("id", job_id).execute()
    
    if not update_result.data:
        raise HTTPException(status_code=500, detail="Failed to update progress")
    
    return {
        "status": "success",
        "progress": current_progress,
        "message": f"Progress updated for node {request.node_id}"
    }


@router.get("/progress/{job_id}")
async def get_progress(job_id: str):
    """Get progress for a saved job"""
    supabase = get_supabase()
    
    result = supabase.table("saved_jobs").select("progress, roadmap_details").eq("id", job_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Saved job not found")
    
    progress = result.data[0].get("progress") or {}
    roadmap = result.data[0].get("roadmap_details") or {}
    
    # Calculate completion percentage
    total_nodes = 0
    completed_nodes = 0
    
    # Count nodes from graph
    graph = roadmap.get("graph", {})
    if not graph and roadmap.get("full_job_data"):
        graph = roadmap.get("full_job_data", {}).get("roadmap", {}).get("graph", {})
    
    nodes = graph.get("nodes", [])
    total_nodes = len(nodes)
    
    for node in nodes:
        node_id = node.get("id")
        if node_id and progress.get(node_id, {}).get("completed"):
            completed_nodes += 1
    
    completion_percentage = (completed_nodes / total_nodes * 100) if total_nodes > 0 else 0
    
    return {
        "progress": progress,
        "total_nodes": total_nodes,
        "completed_nodes": completed_nodes,
        "completion_percentage": round(completion_percentage, 1)
    }


# =============================================================================
# Roadmap Merge Endpoints
# =============================================================================

@router.post("/merge-roadmaps", response_model=GlobalRoadmapResponse)
async def merge_roadmaps(request: MergeRoadmapsRequest):
    """Merge roadmaps from multiple saved jobs using LLM"""
    if len(request.job_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 jobs required for merging")
    
    supabase = get_supabase()
    llm = get_llm()
    
    # Fetch all selected saved jobs with their roadmaps
    jobs = []
    for job_id in request.job_ids:
        result = supabase.table("saved_jobs").select("*").eq("id", job_id).execute()
        if result.data:
            jobs.append(result.data[0])
    
    if len(jobs) < 2:
        raise HTTPException(status_code=404, detail="Could not find enough jobs to merge")
    
    # Prepare roadmaps for LLM - extract resources from each job
    roadmaps_data = []
    all_resources = {}
    for job in jobs:
        roadmap = job.get("roadmap_details", {})
        # Extract resources from the roadmap
        job_resources = roadmap.get("resources", {})
        if roadmap.get("full_job_data"):
            full_data = roadmap.get("full_job_data", {})
            if full_data.get("roadmap") and full_data["roadmap"].get("resources"):
                job_resources = full_data["roadmap"]["resources"]
        
        # Merge resources
        for node_id, resources in job_resources.items():
            if node_id not in all_resources:
                all_resources[node_id] = []
            all_resources[node_id].extend(resources)
        
        roadmaps_data.append({
            "job_title": job["title"],
            "company": job["company"],
            "roadmap": roadmap,
            "resources": job_resources
        })
    
    # Create merge prompt - 3 weeks max with resources
    merge_prompt = f"""You are an expert career advisor. Merge the following job roadmaps into a single, comprehensive master roadmap.

INPUT ROADMAPS:
{json.dumps(roadmaps_data, indent=2)}

Create a merged roadmap that:
1. Combines all missing skills from all jobs, removing duplicates
2. Prioritizes skills that appear in multiple jobs (higher priority)
3. Creates a logical learning sequence
4. **IMPORTANT: The total plan should be 3 WEEKS MAXIMUM (21 days)**
5. Groups skills by category (Programming, Frameworks, Tools, Soft Skills, etc.)
6. **Include learning resources and links from the input roadmaps for each skill**

Return ONLY valid JSON in this exact format:
{{
    "title": "Master Career Roadmap",
    "description": "A comprehensive 3-week roadmap combining goals for: [list job titles]",
    "total_estimated_weeks": 3,
    "skill_categories": [
        {{
            "category": "Category Name",
            "skills": [
                {{
                    "name": "Skill Name",
                    "priority": "high" | "medium" | "low",
                    "appears_in_jobs": ["Job Title 1", "Job Title 2"],
                    "estimated_days": <number between 1-5>,
                    "resources": [
                        {{"name": "Resource Name", "url": "https://..."}},
                        {{"name": "YouTube Tutorial", "url": "https://youtube.com/..."}}
                    ]
                }}
            ]
        }}
    ],
    "learning_path": [
        {{
            "phase": 1,
            "title": "Week 1: Foundation",
            "duration_days": 7,
            "skills": ["skill1", "skill2"],
            "milestone": "What you'll achieve",
            "daily_plan": [
                {{"day": 1, "focus": "Topic", "resources": [{{"name": "...", "url": "..."}}]}}
            ]
        }},
        {{
            "phase": 2,
            "title": "Week 2: Practice",
            "duration_days": 7,
            "skills": ["skill3", "skill4"],
            "milestone": "What you'll achieve",
            "daily_plan": []
        }},
        {{
            "phase": 3,
            "title": "Week 3: Projects & Interview Prep",
            "duration_days": 7,
            "skills": ["skill5", "skill6"],
            "milestone": "What you'll achieve",
            "daily_plan": []
        }}
    ],
    "combined_missing_skills": ["skill1", "skill2", "skill3"],
    "all_resources": [
        {{"skill": "Skill Name", "resources": [{{"name": "...", "url": "..."}}]}}
    ],
    "source_jobs": [
        {{
            "title": "Job Title",
            "company": "Company Name"
        }}
    ]
}}"""

    try:
        response = llm.generate_content(merge_prompt)
        response_text = response.text.strip()
        
        # Clean markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()
        
        merged_roadmap = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"[Merge] JSON Parse Error: {e}")
        print(f"[Merge] Raw response: {response.text[:500]}")
        # Fallback: create a basic merged roadmap
        all_skills = []
        for job in jobs:
            roadmap = job.get("roadmap_details", {})
            skills = roadmap.get("missing_skills", [])
            all_skills.extend(skills)
        
        merged_roadmap = {
            "title": "Master Career Roadmap",
            "description": f"Combined roadmap for {len(jobs)} jobs",
            "combined_missing_skills": list(set(all_skills)),
            "source_jobs": [{"title": j["title"], "company": j["company"]} for j in jobs],
            "skill_categories": [],
            "learning_path": []
        }
    except Exception as e:
        print(f"[Merge] LLM Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate merged roadmap: {str(e)}")
    
    # Save to global_roadmaps table
    roadmap_data = {
        "name": request.name,
        "merged_graph": merged_roadmap,
        "source_job_ids": request.job_ids
    }
    
    result = supabase.table("global_roadmaps").insert(roadmap_data).execute()
    
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to save merged roadmap")
    
    saved = result.data[0]
    return GlobalRoadmapResponse(
        id=saved["id"],
        name=saved["name"],
        merged_graph=saved["merged_graph"],
        source_job_ids=saved["source_job_ids"],
        created_at=saved["created_at"]
    )


@router.get("/global-roadmaps/{user_id}", response_model=List[GlobalRoadmapResponse])
async def get_global_roadmaps(user_id: str):
    """Get all merged roadmaps (global roadmaps don't have user_id currently, returns all)"""
    supabase = get_supabase()
    
    result = supabase.table("global_roadmaps").select("*").order("created_at", desc=True).execute()
    
    return [
        GlobalRoadmapResponse(
            id=r["id"],
            name=r["name"],
            merged_graph=r["merged_graph"],
            source_job_ids=r["source_job_ids"],
            created_at=r["created_at"]
        )
        for r in result.data
    ]


@router.get("/global-roadmap/{roadmap_id}", response_model=GlobalRoadmapResponse)
async def get_global_roadmap(roadmap_id: str):
    """Get a specific merged roadmap"""
    supabase = get_supabase()
    
    result = supabase.table("global_roadmaps").select("*").eq("id", roadmap_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    
    r = result.data[0]
    return GlobalRoadmapResponse(
        id=r["id"],
        name=r["name"],
        merged_graph=r["merged_graph"],
        source_job_ids=r["source_job_ids"],
        created_at=r["created_at"]
    )


@router.delete("/global-roadmap/{roadmap_id}")
async def delete_global_roadmap(roadmap_id: str):
    """Delete a merged roadmap"""
    supabase = get_supabase()
    
    supabase.table("global_roadmaps").delete().eq("id", roadmap_id).execute()
    
    return {"status": "success", "message": "Roadmap deleted"}
