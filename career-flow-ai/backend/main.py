"""
Career Flow AI - Main Application Entry Point
FastAPI Server for Agentic AI Backend
"""

import os
from dotenv import load_dotenv

# Load env FIRST before any other imports
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import routers
from agents.agent_4_operative import agent4_router

app = FastAPI(
    title="Career Flow AI API",
    description="AI-powered career automation system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(agent4_router)


@app.get("/")
async def root():
    return {
        "message": "Career Flow AI API",
        "version": "1.0.0",
        "agents": {
            "agent4": "/agent4 - Application Operative"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "message": "Career Flow AI Backend is running"
        }
    )

@app.post("/analyze")
async def analyze_career(request: AnalyzeRequest):
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": "Analysis request received",
            "data": {}
        }
    )

@app.post("/api/match")
async def match_agent(request: SearchRequest):
    if not request.query:
        raise HTTPException(status_code=400, detail="Query text is required")
    
    results = search_jobs(request.query)
    final_response = []
    
    for job in results:
        if job['score'] > 0.80:
            job['status'] = "Ready"
            job['action'] = "Apply Now"
            job['roadmap_details'] = None
            final_response.append(job)
        else:
            job['status'] = "Learning Path Required"
            job['action'] = "Start Roadmap"
            
            roadmap_data = generate_gap_roadmap(request.query, job['description'])
            job['roadmap_details'] = roadmap_data
            
            final_response.append(job)
    
    return {
        "status": "success",
        "count": len(final_response),
        "matches": final_response
    }

@app.post("/api/generate-kit")
async def generate_kit_endpoint(request: KitRequest):
    pdf_path = generate_deployment_kit(
        request.user_name, 
        request.job_title, 
        request.job_company
    )
    
    return FileResponse(
        path=pdf_path, 
        filename=os.path.basename(pdf_path),
        media_type='application/pdf'
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")