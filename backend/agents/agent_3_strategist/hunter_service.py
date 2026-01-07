# backend/agents/agent_3_strategist/hunter_service.py

"""
Hunter.io Integration Service

Provides functionality to:
1. Find recruiter/HR emails from company domains using Hunter.io API
2. Generate personalized outreach email templates using LLM
"""

import os
import logging
import httpx
from typing import Optional, Dict, List, Any
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [Hunter.io] - %(levelname)s - %(message)s')
logger = logging.getLogger("HunterService")

# Environment Variables
HUNTER_IO_KEY = os.getenv("HUNTER_IO_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Hunter.io API endpoints
HUNTER_DOMAIN_SEARCH_URL = "https://api.hunter.io/v2/domain-search"


class HunterService:
    """
    Hunter.io integration for finding recruiter emails and generating outreach templates.
    """
    
    def __init__(self):
        """Initialize Hunter.io service."""
        self.api_key = HUNTER_IO_KEY
        self.gemini_client = None
        
        if GEMINI_API_KEY:
            try:
                self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
                logger.info("✅ Gemini client initialized for email template generation")
            except Exception as e:
                logger.error(f"❌ Gemini initialization failed: {e}")
    
    def _extract_domain_from_company(self, company_name: str) -> str:
        """
        Convert company name to likely domain.
        E.g., 'Google' -> 'google.com', 'Meta Platforms' -> 'meta.com'
        """
        # Clean and normalize company name
        name = company_name.lower().strip()
        
        # Remove common suffixes
        suffixes = [
            " inc", " inc.", " llc", " ltd", " ltd.", " corp", " corp.",
            " corporation", " company", " co", " co.", " technologies",
            " tech", " software", " systems", " platforms", " group"
        ]
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        
        # Remove special characters and spaces
        name = name.replace(" ", "").replace(",", "").replace(".", "")
        
        # Add .com
        return f"{name}.com"
    
    async def find_recruiter_emails(
        self, 
        company: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Find recruiter/HR emails for a company using Hunter.io Domain Search API.
        
        Args:
            company: Company name or domain
            limit: Maximum number of emails to return
            
        Returns:
            Dict with emails list and metadata
        """
        if not self.api_key:
            logger.warning("HUNTER_IO_KEY not configured")
            return {
                "success": False,
                "error": "Hunter.io API key not configured",
                "emails": []
            }
        
        # Extract domain from company name
        domain = company if "." in company else self._extract_domain_from_company(company)
        
        logger.info(f"🔍 Searching Hunter.io for domain: {domain}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # First try: Broad search to get ANY emails
                response = await client.get(
                    HUNTER_DOMAIN_SEARCH_URL,
                    params={
                        "domain": domain,
                        "api_key": self.api_key,
                        "limit": limit * 3,  # Fetch more to filter for recruiters
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    emails_data = data.get("data", {}).get("emails", [])
                    
                    # Filter and prioritize HR/recruiting roles
                    hr_keywords = [
                        "recruiter", "recruiting", "talent", "hr", "human resources",
                        "people", "hiring", "acquisition", "staffing"
                    ]
                    
                    prioritized = []
                    others = []
                    
                    for email_info in emails_data:
                        position = (email_info.get("position") or "").lower()
                        department = (email_info.get("department") or "").lower()
                        
                        is_hr = any(kw in position or kw in department for kw in hr_keywords)
                        
                        email_entry = {
                            "email": email_info.get("value"),
                            "first_name": email_info.get("first_name"),
                            "last_name": email_info.get("last_name"),
                            "full_name": f"{email_info.get('first_name', '')} {email_info.get('last_name', '')}".strip(),
                            "position": email_info.get("position"),
                            "department": email_info.get("department"),
                            "confidence": email_info.get("confidence", 0),
                            "is_recruiter": is_hr
                        }
                        
                        if is_hr:
                            prioritized.append(email_entry)
                        else:
                            others.append(email_entry)
                    
                    # Combine with HR contacts first, then others up to limit
                    all_emails = prioritized + others
                    final_emails = all_emails[:limit]
                    
                    logger.info(f"✅ Found {len(final_emails)} emails ({len(prioritized)} recruiters)")
                    
                    return {
                        "success": True,
                        "domain": domain,
                        "company": data.get("data", {}).get("organization"),
                        "emails": final_emails,
                        "total_found": len(emails_data),
                        "recruiter_count": len(prioritized)
                    }
                
                elif response.status_code == 400:
                    # Domain not found or invalid
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get("errors", [{}])[0].get("details", "Domain not found in Hunter.io database")
                    logger.warning(f"Hunter.io domain not found: {domain} - {error_msg}")
                    return {
                        "success": True,  # Return success with empty emails
                        "domain": domain,
                        "company": company,
                        "emails": [],
                        "total_found": 0,
                        "recruiter_count": 0,
                        "message": f"No emails found for {domain}. This company may not be in Hunter.io's database yet."
                    }
                
                elif response.status_code == 401:
                    logger.error("Hunter.io API key is invalid")
                    return {
                        "success": False,
                        "error": "Invalid Hunter.io API key",
                        "emails": []
                    }
                
                elif response.status_code == 429:
                    logger.error("Hunter.io rate limit exceeded")
                    return {
                        "success": False,
                        "error": "Rate limit exceeded. Please try again later.",
                        "emails": []
                    }
                
                else:
                    logger.error(f"Hunter.io API error: {response.status_code}")
                    return {
                        "success": False,
                        "error": f"API error: {response.status_code}",
                        "emails": []
                    }
                    
        except httpx.TimeoutException:
            logger.error("Hunter.io request timed out")
            return {
                "success": False,
                "error": "Request timed out. Please try again.",
                "emails": []
            }
        except Exception as e:
            logger.error(f"Hunter.io search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "emails": []
            }
    
    async def generate_outreach_email(
        self,
        user_name: str,
        user_skills: List[str],
        job_title: str,
        company: str,
        recruiter_name: Optional[str] = None
    ) -> str:
        """
        Generate a personalized, soft outreach email template using LLM.
        
        Args:
            user_name: Name of the job seeker
            user_skills: List of user's skills
            job_title: Title of the job they're applying for
            company: Company name
            recruiter_name: Name of the recruiter (optional)
            
        Returns:
            Generated email template string
        """
        if not self.gemini_client:
            # Return a basic template if no LLM available
            return self._get_fallback_template(user_name, job_title, company, recruiter_name)
        
        try:
            recruiter_greeting = f"Hi {recruiter_name.split()[0]}," if recruiter_name else "Hi there,"
            
            prompt = f"""You are a career coach helping a job seeker craft a professional yet warm outreach email to a recruiter.

JOB SEEKER DETAILS:
- Name: {user_name}
- Key Skills: {', '.join(user_skills[:6]) if user_skills else 'Software Development'}
- Target Role: {job_title}
- Target Company: {company}

RECRUITER: {recruiter_name or 'Hiring Team'}

Write a SHORT, PROFESSIONAL outreach email that:
1. Is warm and personable, NOT robotic or overly formal
2. Briefly mentions genuine interest in the {job_title} role
3. Highlights 1-2 relevant skills without bragging
4. Asks a thoughtful question or expresses desire to learn more
5. Is concise - NO MORE than 100 words for the body
6. Does NOT include subject line - just the email body
7. Starts with "{recruiter_greeting}"
8. Ends with "Best regards,\n{user_name}"

Return ONLY the email text. No markdown, no explanations."""

            response = self.gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            
            email_text = response.text.strip()
            
            # Clean up any markdown artifacts
            if email_text.startswith("```"):
                email_text = email_text.split("```")[1]
                if email_text.startswith("\n"):
                    email_text = email_text[1:]
                email_text = email_text.strip()
            
            logger.info(f"✅ Generated outreach email template for {company}")
            return email_text
            
        except Exception as e:
            logger.error(f"Email generation failed: {e}")
            return self._get_fallback_template(user_name, job_title, company, recruiter_name)
    
    def _get_fallback_template(
        self,
        user_name: str,
        job_title: str,
        company: str,
        recruiter_name: Optional[str] = None
    ) -> str:
        """Return a basic email template as fallback."""
        greeting = f"Hi {recruiter_name.split()[0]}," if recruiter_name else "Hi there,"
        
        return f"""{greeting}

I recently came across the {job_title} position at {company} and I'm very excited about the opportunity. Your company's work really resonates with my background and career goals.

I'd love to learn more about the role and share how my experience could contribute to your team. Would you have a few minutes for a brief chat?

Thank you for your time!

Best regards,
{user_name}"""


# Singleton instance
_hunter_service: Optional[HunterService] = None

def get_hunter_service() -> HunterService:
    """Get or create singleton Hunter service instance."""
    global _hunter_service
    if _hunter_service is None:
        _hunter_service = HunterService()
    return _hunter_service
