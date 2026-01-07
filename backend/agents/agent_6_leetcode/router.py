"""
LeetCode Problem Solving Router

API endpoints for:
- GET  /api/leetcode/problems   - Get all Blind 75 problems
- POST /api/leetcode/recommend  - Get AI recommendations
- GET  /api/leetcode/progress   - Get user's progress
- POST /api/leetcode/progress   - Save user's progress
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from auth.dependencies import get_current_user
from .service import leetcode_service
from .schemas import (
    RecommendRequest,
    RecommendResponse,
    ProgressRequest,
    ProgressResponse,
    ProblemsResponse
)

router = APIRouter(prefix="/api/leetcode", tags=["LeetCode"])


@router.get("/problems", response_model=ProblemsResponse)
async def get_problems():
    """
    Get all Blind 75 problems organized by category.
    
    Returns:
        ProblemsResponse with categories and total_count
    """
    data = leetcode_service.get_all_problems()
    return ProblemsResponse(
        categories=data["categories"],
        total_count=data["total_count"]
    )


@router.post("/recommend", response_model=RecommendResponse)
async def get_recommendations(
    request: RecommendRequest,
    user: Dict = Depends(get_current_user)
):
    """
    Get AI-powered problem recommendations based on user's quiz answers.
    
    Uses Gemini AI when available, falls back to local algorithm.
    
    Args:
        request: RecommendRequest with quiz_answers, leetcode_profile, solved_problem_ids
        
    Returns:
        RecommendResponse with recommended_ids and source
    """
    user_id = user["sub"]
    
    leetcode_profile = None
    if request.leetcode_profile:
        leetcode_profile = request.leetcode_profile.dict()
    
    result = leetcode_service.get_recommendations(
        user_id=user_id,
        quiz_answers=request.quiz_answers,
        leetcode_profile=leetcode_profile,
        solved_problem_ids=request.solved_problem_ids
    )
    
    return RecommendResponse(
        recommended_ids=result["recommended_ids"],
        source=result["source"],
        reasoning=result.get("reasoning")
    )


@router.get("/progress", response_model=ProgressResponse)
async def get_progress(user: Dict = Depends(get_current_user)):
    """
    Get user's LeetCode progress.
    
    Returns:
        ProgressResponse with solved_problem_ids, quiz_answers, and total_solved
    """
    user_id = user["sub"]
    data = leetcode_service.get_user_progress(user_id)
    
    return ProgressResponse(
        solved_problem_ids=data["solved_problem_ids"],
        quiz_answers=data["quiz_answers"],
        total_solved=data["total_solved"]
    )


@router.post("/progress", response_model=ProgressResponse)
async def save_progress(
    request: ProgressRequest,
    user: Dict = Depends(get_current_user)
):
    """
    Save user's LeetCode progress.
    
    Args:
        request: ProgressRequest with solved_problem_ids and optional quiz_answers
        
    Returns:
        ProgressResponse with saved data
    """
    user_id = user["sub"]
    
    try:
        data = leetcode_service.save_user_progress(
            user_id=user_id,
            solved_problem_ids=request.solved_problem_ids,
            quiz_answers=request.quiz_answers,
            user_email=user.get("email")
        )
        
        return ProgressResponse(
            solved_problem_ids=data["solved_problem_ids"],
            quiz_answers=data["quiz_answers"],
            total_solved=data["total_solved"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save progress: {str(e)}")
