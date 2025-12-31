import os
import json
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY must be set in the environment or a .env file")

client = genai.Client(api_key=GEMINI_API_KEY)

def generate_gap_roadmap(user_skills_text: str, job_description: str):
    """
    Generates a 3-Day Micro-Learning Plan to bridge the gap.
    """
    print("🚧 Generating Roadmap...")
    
    prompt = f"""
    You are an expert Technical Career Coach and Curriculum Designer.
    
    TASK:
    Perform a Gap Analysis between the User's Skills and the Job Description.
    Identify the top 3 missing critical skills.
    Create a "3-Day Micro-Roadmap" to learn these specific missing skills.
    
    INPUTS:
    User Skills: "{user_skills_text}"
    Target Job: "{job_description}"
    
    REQUIREMENTS:
    1. Be specific (don't say "Learn Python", say "Learn FastAPI Dependency Injection").
    2. Provide REAL documentation links (Official Docs).
    3. Provide YouTube Search queries for finding tutorials.
    4. Output MUST be valid JSON.
    
    OUTPUT JSON FORMAT:
    {{
      "missing_skills": ["Skill 1", "Skill 2"],
      "roadmap": [
        {{
          "day": 1,
          "topic": "Title of the day",
          "tasks": ["Task 1", "Task 2"],
          "resources": [
             {{ "name": "Official Docs", "url": "https://..." }},
             {{ "name": "YouTube Tutorial", "url": "https://www.youtube.com/results?search_query=..." }}
          ]
        }},
        ... (Day 2 and Day 3)
      ]
    }}
    
    RETURN ONLY JSON. NO MARKDOWN.
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        # Clean the response (remove ```json if present)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"❌ Roadmap Generation Failed: {e}")
        # Fallback Roadmap for Demo safety
        return {
            "missing_skills": ["Advanced Concepts"],
            "roadmap": [
                {"day": 1, "topic": "Review Requirements", "tasks": ["Read Docs"], "resources": []}
            ]
        }