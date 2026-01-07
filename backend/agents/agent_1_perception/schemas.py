# backend/agents/agent_1_perception/schemas.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


# =============================================================================
# Skill Metadata Models (Part 3: Verification Layer)
# =============================================================================

class SkillMetadata(BaseModel):
    """Rich skill profile with verification status"""
    source: str  # "resume", "github", "quiz", "manual"
    verification_status: str = "pending"  # "pending", "verified", "rejected"
    level: Optional[str] = None  # "beginner", "intermediate", "advanced", "expert"
    evidence: Optional[str] = None  # Description of how skill was detected
    last_seen: Optional[str] = None  # ISO timestamp of last detection


class ProfileResponse(BaseModel):
    """Response model for user profile"""
    user_id: str
    name: Optional[str]
    email: Optional[str]
    resume_url: Optional[str]
    skills: List[str]  # Legacy array for backward compatibility
    skills_metadata: Dict[str, SkillMetadata] = {}  # Rich skill profiles
    experience_summary: Optional[str]


# =============================================================================
# Education Model
# =============================================================================

class EducationItem(BaseModel):
    """Education entry"""
    institution: Optional[str] = None
    degree: Optional[str] = None
    course: Optional[str] = None
    year: Optional[str] = None


# =============================================================================
# Full Onboarding Models (New Flow)
# =============================================================================

class OnboardingStep1Request(BaseModel):
    """Step 1: Resume upload (processed separately) or skip to manual"""
    skip_resume: bool = False


class OnboardingStep2Request(BaseModel):
    """Step 2: Edit extracted data or enter manually"""
    name: str
    email: Optional[str] = None
    skills: List[str]
    target_roles: List[str]
    education: List[EducationItem]
    experience_summary: Optional[str] = None


class OnboardingStep3Request(BaseModel):
    """Step 3: Social links"""
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None


class OnboardingQuizAnswer(BaseModel):
    """Single quiz answer"""
    question_id: str
    selected_index: int
    correct_index: int


class OnboardingQuizSubmission(BaseModel):
    """Submit all 5 quiz answers"""
    answers: List[OnboardingQuizAnswer]


class OnboardingCompleteRequest(BaseModel):
    """
    Complete onboarding - combines all steps data
    For cases where frontend sends all data at once
    """
    # Personal Info
    name: str
    email: Optional[str] = None
    
    # Skills & Targets
    skills: List[str]
    target_roles: List[str]
    
    # Education
    education: List[EducationItem]
    experience_summary: Optional[str] = None
    
    # Social Links (optional)
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    leetcode_url: Optional[str] = None
    
    # Whether resume was uploaded
    has_resume: bool = False


class OnboardingStatusResponse(BaseModel):
    """Check if user needs onboarding"""
    needs_onboarding: bool
    onboarding_step: Optional[int] = None  # Which step they're on if incomplete
    profile_complete: bool = False
    has_resume: bool = False
    has_quiz_completed: bool = False


class QuizQuestion(BaseModel):
    """Single quiz question for onboarding"""
    id: str
    question: str
    options: List[str]
    correct_index: int  # For stateless verification
    skill_being_tested: str


class OnboardingQuizResponse(BaseModel):
    """5 MCQ questions for onboarding"""
    questions: List[QuizQuestion]


# =============================================================================
# Dashboard Insights Models
# =============================================================================

class JobInsight(BaseModel):
    """Top job for today"""
    id: str
    title: str
    company: str
    match_score: float
    key_skills: List[str]


class SkillInsight(BaseModel):
    """Hot skill to learn"""
    skill: str
    demand_trend: str  # "rising", "stable", "declining"
    reason: str


class GitHubInsight(BaseModel):
    """GitHub activity insight"""
    repo_name: str
    recent_commits: int
    detected_skills: List[str]
    insight_text: str


class NewsCard(BaseModel):
    """Industry news/insight"""
    title: str
    summary: str
    relevance: str


class DashboardInsightsResponse(BaseModel):
    """Dashboard data for authenticated users"""
    user_name: str
    profile_strength: int  # 0-100
    top_jobs: List[JobInsight]
    hot_skills: List[SkillInsight]
    github_insights: Optional[GitHubInsight] = None
    news_cards: List[NewsCard]
    agent_status: str  # "active", "syncing", "idle"


# =============================================================================
# Quiz Models (Skill Verification)
# =============================================================================

class QuizRequest(BaseModel):
    """Request to generate a skill verification quiz"""
    skill_name: str  # e.g., "React", "Python"
    level: Optional[str] = "intermediate"  # Difficulty level


class QuizResponse(BaseModel):
    """Generated quiz question"""
    quiz_id: str  # Unique ID to track this quiz attempt
    skill_name: str
    question: str
    options: List[str]  # 4 options (A, B, C, D)


class QuizSubmission(BaseModel):
    """User's answer submission"""
    quiz_id: str
    skill_name: str
    answer_index: int  # 0-3 corresponding to options
    expected_correct_index: Optional[int] = None


class QuizResult(BaseModel):
    """Result of quiz verification"""
    correct: bool
    new_status: str  # "verified" or "pending"
    message: str


# =============================================================================
# GitHub Sync Models
# =============================================================================

class GithubSyncResponse(BaseModel):
    """Response from GitHub sync operation"""
    updated_skills: List[str]
    skills_metadata: Dict[str, Any] = {}
    analysis: Optional[Dict[str, Any]] = None


# =============================================================================
# Onboarding Models
# =============================================================================

class OnboardingRequest(BaseModel):
    """Request body for user onboarding - all fields optional"""
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    target_roles: Optional[List[str]] = None


class OnboardingResponse(BaseModel):
    """Response from onboarding update"""
    status: str
    updated_fields: List[str]
    user_id: str


# =============================================================================
# Watchdog Models
# =============================================================================

class WatchdogCheckRequest(BaseModel):
    """Request for watchdog polling (used by frontend)"""
    last_known_sha: Optional[str] = None
