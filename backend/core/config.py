"""
Interview Configuration - Environment-based settings for Agent 5
"""
import os

# =============================================================================
# Interview Turn Configuration (from ENV)
# =============================================================================

# Technical Interview Stages
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

# HR Interview Stages  
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
# Audio Configuration
# =============================================================================

# Silence detection settings
SILENCE_THRESHOLD = int(os.getenv("AUDIO_SILENCE_THRESHOLD", "500"))
SILENCE_DURATION = float(os.getenv("AUDIO_SILENCE_DURATION", "0.8"))
COOLDOWN_SECONDS = float(os.getenv("AUDIO_COOLDOWN_SECONDS", "1.0"))

# =============================================================================
# Interview States for Audio State Machine
# =============================================================================

class AudioState:
    IDLE = "idle"
    THINKING = "thinking"
    SPEAKING = "speaking"
    LISTENING = "listening"
