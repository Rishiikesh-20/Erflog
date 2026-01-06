"""
Pydantic schemas for LeetCode Problem Solving Agent
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class Blind75Problem(BaseModel):
    """A single Blind 75 problem"""
    id: int
    title: str
    slug: str
    difficulty: str  # "Easy", "Medium", "Hard"
    category: str
    leetcode_url: str
    priority: int  # 1 = must do, 2 = recommended, 3 = optional


class Blind75Category(BaseModel):
    """A category of Blind 75 problems"""
    name: str
    icon: str
    color: str
    problems: List[Blind75Problem]


class LeetCodeProfile(BaseModel):
    """User's LeetCode profile stats (from external API)"""
    total_solved: int = 0
    easy_solved: int = 0
    medium_solved: int = 0
    hard_solved: int = 0
    ranking: Optional[int] = None


class QuizAnswers(BaseModel):
    """User's self-assessment quiz answers"""
    # Category name -> skill level ("weak", "okay", "strong")
    answers: Dict[str, str] = Field(default_factory=dict)


class RecommendRequest(BaseModel):
    """Request body for getting AI recommendations"""
    quiz_answers: Dict[str, str] = Field(
        default_factory=dict,
        description="Category name -> skill level mapping"
    )
    leetcode_profile: Optional[LeetCodeProfile] = None
    solved_problem_ids: List[int] = Field(
        default_factory=list,
        description="List of already solved problem IDs"
    )


class RecommendResponse(BaseModel):
    """Response with AI-recommended problem IDs"""
    recommended_ids: List[int]
    source: str  # "gemini", "local", "fallback"
    reasoning: Optional[str] = None


class ProgressRequest(BaseModel):
    """Request to update user's progress"""
    solved_problem_ids: List[int] = Field(
        default_factory=list,
        description="List of solved problem IDs"
    )
    quiz_answers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional quiz answers to save"
    )


class ProgressResponse(BaseModel):
    """Response with user's progress data"""
    solved_problem_ids: List[int]
    quiz_answers: Dict[str, str]
    total_solved: int


class ProblemsResponse(BaseModel):
    """Response with all Blind 75 problems"""
    categories: List[Blind75Category]
    total_count: int
