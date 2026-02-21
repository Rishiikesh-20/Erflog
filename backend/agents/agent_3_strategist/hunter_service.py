import os
import httpx
from typing import Dict, Any, List
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

class HunterService:
    def __init__(self):
        self.api_key = os.getenv("HUNTER_IO_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

    async def find_recruiter_emails(self, company: str, limit: int = 5) -> Dict[str, Any]:
        """
        Uses Hunter.io Domain Search API to find emails for a given company.
        Prioritizes HR and recruiting roles if possible.
        """
        if not self.api_key:
            return {"success": False, "error": "Hunter.io API key is not configured"}

        url = "https://api.hunter.io/v2/domain-search"
        params = {
            "company": company,
            "limit": limit,
            "department": "hr",
            "api_key": self.api_key
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                print(f"[HunterService] API Response Status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json().get("data", {})
                    domain = data.get("domain", "")
                    emails_data = data.get("emails", [])

                    emails = []
                    recruiter_count = 0

                    for e in emails_data:
                        emails.append({
                            "email": e.get("value"),
                            "full_name": f"{e.get('first_name', '')} {e.get('last_name', '')}".strip() or "Unknown",
                            "position": e.get("position") or "HR / Recruiter",
                            "confidence": e.get("confidence", 0)
                        })
                        recruiter_count += 1
                        
                    # If HR department filter returns nothing, try without department filter
                    if not emails:
                        del params["department"]
                        retry_resp = await client.get(url, params=params)
                        if retry_resp.status_code == 200:
                            retry_data = retry_resp.json().get("data", {})
                            domain = retry_data.get("domain", domain)
                            emails_data = retry_data.get("emails", [])
                            
                            for e in emails_data:
                                pos = (e.get("position") or "Employee").lower()
                                if any(kw in pos for kw in ["hr", "human", "recruit", "talent", "people"]):
                                    recruiter_count += 1
                                
                                emails.append({
                                    "email": e.get("value"),
                                    "full_name": f"{e.get('first_name', '')} {e.get('last_name', '')}".strip() or "Unknown",
                                    "position": e.get("position") or "Employee",
                                    "confidence": e.get("confidence", 0)
                                })
                                
                    return {
                        "success": True,
                        "domain": domain,
                        "emails": emails[:limit],
                        "total_found": len(emails),
                        "recruiter_count": recruiter_count
                    }
                elif response.status_code in [401, 403]:
                    return {"success": False, "error": f"Hunter.io authentication failed: {response.status_code}"}
                elif response.status_code == 422:
                    return {"success": False, "error": f"Invalid company name or domain: {company}"}
                else:
                    return {"success": False, "error": f"Hunter.io API returned {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": f"Error connecting to Hunter.io: {str(e)}"}

    async def generate_outreach_email(self, user_name: str, user_skills: List[str], job_title: str, company: str, recruiter_name: str = None) -> str:
        """
        Generates a personalized brief connecting outreach email using Gemini 2.0.
        """
        if not self.gemini_api_key:
            return "Hi,\n\nI recently came across the open role at your company and I'm very interested. Please let me know if we can connect.\n\nThanks,\nJob Seeker"

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=self.gemini_api_key,
            temperature=0.7
        )

        prompt_text = """
You are an expert career coach helping a candidate write a highly effective, concise cold-email to a recruiter.

Candidate Name: {user_name}
Candidate Top Skills: {user_skills}
Target Job Title: {job_title}
Target Company: {company}
Recruiter Name (if known): {recruiter_name}

Write a professional, short (less than 100 words), and engaging outreach email template.
Do not include subject line placeholders. 
Start directly with the greeting.
Be persuasive but very brief and respectful of their time.
"""
        prompt = PromptTemplate(
            input_variables=["user_name", "user_skills", "job_title", "company", "recruiter_name"],
            template=prompt_text
        )

        chain = prompt | llm

        try:
            skills_str = ", ".join(user_skills[:5]) if user_skills else "General technical skills"
            recruiter = recruiter_name if recruiter_name else "[Recruiter Name]"
            
            result = await chain.ainvoke({
                "user_name": user_name,
                "user_skills": skills_str,
                "job_title": job_title,
                "company": company,
                "recruiter_name": recruiter
            })
            
            return result.content.strip()
        except Exception as e:
            print(f"[HunterService] Error generating email: {e}")
            return f"Hi {recruiter_name or 'there'},\n\nI'm {user_name} and I recently came across the {job_title} role at {company}. I have expertise in {(','.join(user_skills[:3])) if user_skills else 'this field'} and would love to connect to discuss how I can add value to your team.\n\nBest regards,\n{user_name}"


def get_hunter_service() -> HunterService:
    return HunterService()
