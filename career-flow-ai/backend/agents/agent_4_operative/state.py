from typing import TypedDict, Literal


class FeedbackLoop(TypedDict, total=False):
    """Stores analysis data if application is rejected."""
    rejection_reason: str
    analysis: str
    suggestions: list[str]
    timestamp: str


class RewrittenContent(TypedDict, total=False):
    """JSON output from the LLM rewriter."""
    resume: dict
    cover_letter: str
    tailored_skills: list[str]
    matched_keywords: list[str]


class Agent4State(TypedDict):
    """State model for Agent 4 (Application Operative)."""
    job_description: str
    user_profile: dict
    rewritten_content: RewrittenContent
    pdf_path: str
    recruiter_email: str
    application_status: Literal["pending", "applied", "rejected"]
    feedback_loop: FeedbackLoop
