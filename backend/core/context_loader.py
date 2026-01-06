from agents.agent_3_strategist.graph import get_interview_gap_analysis
import logging

logger = logging.getLogger("ContextLoader")

def fetch_interview_context(user_id: str, job_id: str):
    logger.info(f"[Context] Fetching for User: {user_id}, Job: {job_id}")
    
    agent3_result = get_interview_gap_analysis(
        job_id=str(job_id),
        user_id=str(user_id)
    )
    
    # Handle empty result (error case)
    if not agent3_result or "error" in agent3_result:
        error_msg = f"Failed to fetch context: {agent3_result.get('error', 'Unknown error')}"
        logger.error(f"[Context] {error_msg}")
        raise ValueError(error_msg)
    
    job_data = agent3_result.get("job", {})
    user_data = agent3_result.get("user", {})
    gap_analysis = agent3_result.get("gap_analysis", {})
    similarity_score = agent3_result.get("similarity_score", 0.0)
    
    # Handle case where gap_analysis might be a list instead of dict
    if isinstance(gap_analysis, list):
        logger.warning(f"[Context] gap_analysis is a list, converting to empty dict")
        gap_analysis = {}
    
    logger.info(f"[Context] Job: {job_data.get('title', 'Unknown')} at {job_data.get('company', 'Unknown')}")
    logger.info(f"[Context] User: {user_data.get('name', 'Unknown')}")
    logger.info(f"[Context] Description length: {len(job_data.get('description', ''))} chars")
    
    # Validate required fields
    if not job_data.get("title") or not user_data.get("name"):
        error_msg = "Missing required job or user information"
        logger.error(f"[Context] {error_msg}")
        raise ValueError(error_msg)
    
    gap_report = {
        "status": "gap_detected" if gap_analysis.get("missing_skills") else "ready",
        "similarity_score": similarity_score,
        "match_tier": gap_analysis.get("match_tier", "B"),
        "missing_skills": gap_analysis.get("missing_skills", []),
        "weak_areas": gap_analysis.get("weak_areas", []),
        "suggested_questions": gap_analysis.get("suggested_questions", []),
        "assessment": gap_analysis.get("assessment", "")
    }

    return {
        "job": job_data,
        "user": user_data,
        "gaps": gap_report
    }
