import os
import json
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables
load_dotenv()


def analyze_rejection(job_desc: str, resume_content: dict) -> str:
    """
    Analyzes why a resume was rejected for a specific job.
    
    Args:
        job_desc: The job description text.
        resume_content: The resume data as a dictionary.
    
    Returns:
        A concise gap analysis string identifying missing skills or gaps.
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.3
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert career coach and hiring manager.
Analyze why the given resume was likely rejected for the specified job.

Your task:
1. Identify specific missing skills, qualifications, or experience gaps.
2. Highlight mismatches between job requirements and resume content.
3. Note any ATS optimization issues (missing keywords, formatting).

Be concise and actionable. Focus on the TOP 3 most critical gaps."""),
        ("human", """Job Description:
{job_desc}

Resume Content:
{resume_content}

Provide a concise gap analysis explaining why this resume was rejected.""")
    ])
    
    chain = prompt | llm
    
    response = chain.invoke({
        "job_desc": job_desc,
        "resume_content": json.dumps(resume_content, indent=2)
    })
    
    return response.content


def update_vector_memory(
    user_id: str,
    gap_analysis: str,
    create_anti_pattern: bool = True
) -> dict:
    """
    Updates the user's vector memory with rejection analysis.
    
    Args:
        user_id: The unique identifier for the user.
        gap_analysis: The gap analysis string from analyze_rejection.
        create_anti_pattern: Whether to create a negative vector for anti-patterns.
    
    Returns:
        A dictionary with status and updated metadata.
    """
    # Initialize Pinecone
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index_name = os.getenv("PINECONE_INDEX_NAME", "ai-verse")
    index = pc.Index(index_name)
    
    # Initialize embeddings
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )
    
    result = {
        "status": "success",
        "user_id": user_id,
        "updated_metadata": {},
        "anti_pattern_created": False
    }
    
    try:
        # Fetch existing user vector
        fetch_response = index.fetch(ids=[user_id], namespace="users")
        
        if user_id in fetch_response.vectors:
            existing_vector = fetch_response.vectors[user_id]
            existing_metadata = existing_vector.metadata or {}
            
            # Get or initialize rejection history
            rejection_history = existing_metadata.get("rejection_history", [])
            
            # Append new gap analysis with timestamp
            rejection_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "gap_analysis": gap_analysis
            }
            rejection_history.append(rejection_entry)
            
            # Keep only last 10 rejections to avoid metadata bloat
            rejection_history = rejection_history[-10:]
            
            # Update metadata
            updated_metadata = {
                **existing_metadata,
                "rejection_history": rejection_history,
                "last_rejection": datetime.utcnow().isoformat(),
                "total_rejections": len(rejection_history)
            }
            
            # Upsert with updated metadata
            index.upsert(
                vectors=[{
                    "id": user_id,
                    "values": existing_vector.values,
                    "metadata": updated_metadata
                }],
                namespace="users"
            )
            
            result["updated_metadata"] = updated_metadata
        else:
            result["status"] = "user_not_found"
            result["message"] = f"No vector found for user_id: {user_id}"
            return result
        
        # Create anti-pattern vector for negative prompting
        if create_anti_pattern:
            anti_pattern_id = f"anti_{user_id}_{hash(gap_analysis) % 10000}"
            
            # Generate embedding for the gap analysis
            gap_embedding = embeddings.embed_query(gap_analysis)
            
            anti_pattern_metadata = {
                "user_id": user_id,
                "type": "anti_pattern",
                "gap_analysis": gap_analysis,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Upsert to anti-patterns namespace
            index.upsert(
                vectors=[{
                    "id": anti_pattern_id,
                    "values": gap_embedding,
                    "metadata": anti_pattern_metadata
                }],
                namespace="anti-patterns"
            )
            
            result["anti_pattern_created"] = True
            result["anti_pattern_id"] = anti_pattern_id
            
    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)
    
    return result


def check_anti_patterns(user_id: str, job_description: str, threshold: float = 0.85) -> dict:
    """
    Checks if a job description matches known anti-patterns for a user.
    """
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index_name = os.getenv("PINECONE_INDEX_NAME", "ai-verse")
    index = pc.Index(index_name)
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )
    
    # Generate embedding for job description
    job_embedding = embeddings.embed_query(job_description)
    
    # Query anti-patterns namespace
    query_response = index.query(
        vector=job_embedding,
        top_k=5,
        namespace="anti-patterns",
        filter={"user_id": {"$eq": user_id}},
        include_metadata=True
    )
    
    matches = []
    is_anti_pattern = False
    
    for match in query_response.matches:
        if match.score >= threshold:
            is_anti_pattern = True
            matches.append({
                "id": match.id,
                "score": match.score,
                "gap_analysis": match.metadata.get("gap_analysis", "")
            })
    
    return {
        "is_anti_pattern": is_anti_pattern,
        "matches": matches,
        "recommendation": "Consider skipping this job - similar positions led to rejections." if is_anti_pattern else "No anti-pattern matches found."
    }
