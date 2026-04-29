"""
Career Flow AI — Central Configuration
=======================================
Single source of truth for ALL environment variables and system constants.
Import from here instead of calling os.getenv() scattered across services.

Usage:
    from core.config import PINECONE_INDEX_NAME, SUPABASE_URL, validate_env
"""

import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("Config")

# =============================================================================
# Supabase
# =============================================================================
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# =============================================================================
# Pinecone — ONE index, explicit namespaces
# =============================================================================
#
#  All agents write to / read from the SAME Pinecone index.
#  Namespaces keep data logically separated:
#
#   "users"      — user profile vectors (Agent 1)
#   ""           — job vectors          (Agent 2, default namespace)
#   "hackathon"  — hackathon vectors    (Agent 2)
#   "news"       — news vectors         (Agent 2)
#
PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "career-flow")

# Pinecone namespace constants — import these instead of using raw strings
PINECONE_NS_USERS = "users"
PINECONE_NS_JOBS = ""          # Pinecone default namespace
PINECONE_NS_HACKATHONS = "hackathon"
PINECONE_NS_NEWS = "news"

# Pinecone index dimension (text-embedding-004 / gemini-embedding-001)
PINECONE_DIMENSION = 768

# =============================================================================
# Google / Gemini
# =============================================================================
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", GEMINI_API_KEY)  # alias

# =============================================================================
# Redis / ARQ worker
# =============================================================================
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

# =============================================================================
# External API Keys (optional — agents degrade gracefully if absent)
# =============================================================================
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY", "")
JSEARCH_API_KEY: str = os.getenv("JSEARCH_API_KEY", "")
NEWSDATA_API_KEY: str = os.getenv("NEWSDATA_API_KEY", "")

# =============================================================================
# Interview Configuration (Agent 5)
# =============================================================================

TECHNICAL_INTERVIEW_CONFIG = {
    "TOTAL_TURNS": int(os.getenv("INTERVIEW_TECHNICAL_TOTAL_TURNS", "6")),
    "STAGES": {
        "intro": {
            "turns": int(os.getenv("INTERVIEW_TECHNICAL_INTRO_TURNS", "1")),
            "next": "resume",
            "prompt_type": "technical_intro"
        },
        "resume": {
            "turns": int(os.getenv("INTERVIEW_TECHNICAL_RESUME_TURNS", "2")),
            "next": "challenge",
            "prompt_type": "resume_focused"
        },
        "challenge": {
            "turns": int(os.getenv("INTERVIEW_TECHNICAL_CHALLENGE_TURNS", "2")),
            "next": "conclusion",
            "prompt_type": "technical_challenge"
        },
        "conclusion": {
            "turns": int(os.getenv("INTERVIEW_TECHNICAL_CONCLUSION_TURNS", "1")),
            "next": "end",
            "prompt_type": "conclusion"
        }
    }
}

HR_INTERVIEW_CONFIG = {
    "TOTAL_TURNS": int(os.getenv("INTERVIEW_HR_TOTAL_TURNS", "6")),
    "STAGES": {
        "intro": {
            "turns": int(os.getenv("INTERVIEW_HR_INTRO_TURNS", "1")),
            "next": "behavioral",
            "prompt_type": "hr_intro"
        },
        "behavioral": {
            "turns": int(os.getenv("INTERVIEW_HR_BEHAVIORAL_TURNS", "2")),
            "next": "experience",
            "prompt_type": "behavioral"
        },
        "experience": {
            "turns": int(os.getenv("INTERVIEW_HR_EXPERIENCE_TURNS", "2")),
            "next": "conclusion",
            "prompt_type": "experience"
        },
        "conclusion": {
            "turns": int(os.getenv("INTERVIEW_HR_CONCLUSION_TURNS", "1")),
            "next": "end",
            "prompt_type": "conclusion"
        }
    }
}

def get_interview_config(interview_type: str = "TECHNICAL") -> dict:
    """Get interview configuration based on type."""
    if interview_type.upper() == "HR":
        return HR_INTERVIEW_CONFIG
    return TECHNICAL_INTERVIEW_CONFIG

def get_stages_for_type(interview_type: str = "TECHNICAL") -> dict:
    """Get stage configuration for interview type."""
    config = get_interview_config(interview_type)
    return config["STAGES"]

def get_total_turns(interview_type: str = "TECHNICAL") -> int:
    """Get total turns for interview type."""
    config = get_interview_config(interview_type)
    return config["TOTAL_TURNS"]

# =============================================================================
# Audio Configuration (Agent 5)
# =============================================================================
SILENCE_THRESHOLD = int(os.getenv("AUDIO_SILENCE_THRESHOLD", "500"))
SILENCE_DURATION = float(os.getenv("AUDIO_SILENCE_DURATION", "0.8"))
COOLDOWN_SECONDS = float(os.getenv("AUDIO_COOLDOWN_SECONDS", "1.0"))

class AudioState:
    IDLE = "idle"
    THINKING = "thinking"
    SPEAKING = "speaking"
    LISTENING = "listening"

# =============================================================================
# Environment Validation — call this at startup in main.py
# =============================================================================

# Required env vars — startup fails fast if any are missing
_REQUIRED_VARS = [
    ("SUPABASE_URL", SUPABASE_URL),
    ("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_SERVICE_ROLE_KEY),
    ("PINECONE_API_KEY", PINECONE_API_KEY),
    ("GEMINI_API_KEY", GEMINI_API_KEY),
]

def validate_env(strict: bool = True) -> bool:
    """
    Validate that all required environment variables are set.

    Args:
        strict: If True, call sys.exit(1) on failure (recommended for production).
                If False, log warnings and return False instead.

    Returns:
        True if all required vars are present, False otherwise.
    """
    missing = [name for name, value in _REQUIRED_VARS if not value]

    if missing:
        msg = (
            f"❌ STARTUP FAILED — {len(missing)} required environment variable(s) "
            f"are not set: {', '.join(missing)}\n"
            "Please configure them in your .env file or deployment environment."
        )
        logger.critical(msg)
        if strict:
            sys.exit(1)
        return False

    logger.info(
        f"✅ Environment validated — "
        f"Supabase OK, Pinecone index='{PINECONE_INDEX_NAME}', Gemini OK, Redis='{REDIS_URL}'"
    )
    return True
