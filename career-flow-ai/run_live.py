import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from dotenv import load_dotenv

# Load environment variables from backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))

from agents.agent_4_operative.graph import run_agent4
from agents.agent_4_operative.tools import fetch_user_profile_from_db

# ==================== CONFIG ====================
USE_DATABASE = True # Set to True to fetch from Pinecone/Supabase
USER_ID = "your-user-id-here"  # Replace with actual user_id from Agent 1

# ==================== MOCK DATA ====================

MOCK_USER_PROFILE = {
    "name": "Karthik Ganesan",
    "email": "karthik@example.com",
    "phone": "+1 (555) 123-4567",
    "location": "San Francisco, CA",
    "linkedin": "https://linkedin.com/in/karthikganesan",
    "github": "https://github.com/karthikg",
    "summary": "Full-stack developer with 5 years of experience building scalable web applications. Proficient in Python, JavaScript, and cloud technologies. Passionate about AI and automation.",
    "experience": [
        {
            "title": "Senior Software Engineer",
            "company": "TechStartup Inc",
            "location": "San Francisco, CA",
            "start_date": "Jan 2022",
            "end_date": "Present",
            "bullets": [
                "Led development of microservices architecture serving 1M+ users",
                "Implemented CI/CD pipelines reducing deployment time by 60%",
                "Mentored team of 4 junior developers"
            ]
        },
        {
            "title": "Software Engineer",
            "company": "WebAgency Co",
            "location": "New York, NY",
            "start_date": "Jun 2019",
            "end_date": "Dec 2021",
            "bullets": [
                "Built RESTful APIs using Python and FastAPI",
                "Developed React frontend components for e-commerce platform",
                "Optimized database queries improving performance by 40%"
            ]
        }
    ],
    "education": [
        {
            "degree": "B.S. Computer Science",
            "institution": "UC Berkeley",
            "location": "Berkeley, CA",
            "graduation_date": "May 2019",
            "gpa": "3.7"
        }
    ],
    "skills": [
        "Python", "JavaScript", "TypeScript", "React", "FastAPI",
        "PostgreSQL", "MongoDB", "Docker", "Kubernetes", "AWS",
        "Git", "CI/CD", "Agile", "REST APIs", "GraphQL"
    ],
    "certifications": [
        {"name": "AWS Solutions Architect", "issuer": "Amazon", "date": "2023"},
        {"name": "Google Cloud Professional", "issuer": "Google", "date": "2022"}
    ]
}

MOCK_JOB_DESCRIPTION = """
Senior Backend Engineer at TechCorp

About the Role:
We are looking for a Senior Backend Engineer to join our Platform team. You will be 
responsible for designing and building scalable microservices that power our AI-driven 
product recommendations engine.

Requirements:
- 5+ years of experience in backend development
- Strong proficiency in Python and FastAPI/Django
- Experience with distributed systems and microservices architecture
- Hands-on experience with Kubernetes and Docker
- Familiarity with machine learning pipelines is a plus
- Experience with PostgreSQL and Redis
- Strong understanding of RESTful API design
- Excellent problem-solving and communication skills

Nice to have:
- Experience with LangChain or similar AI frameworks
- Knowledge of vector databases (Pinecone, Weaviate)
- Contributions to open source projects

Benefits:
- Competitive salary ($180k - $220k)
- Remote-first culture
- Health, dental, and vision insurance
- 401k matching
- Unlimited PTO
"""

# ==================== RUN THE AGENT ====================

def main():
    print("=" * 60)
    print("🚀 AGENT 4 - APPLICATION OPERATIVE")
    print("=" * 60)
    print()
    
    print("📄 User Profile:")
    print(f"   Name: {MOCK_USER_PROFILE['name']}")
    print(f"   Email: {MOCK_USER_PROFILE['email']}")
    print()
    
    print("💼 Target Job:")
    print(f"   {MOCK_JOB_DESCRIPTION[:100]}...")
    print()
    
    print("-" * 60)
    print("⚙️  Starting Agent 4 Workflow...")
    print("-" * 60)
    print()
    
    try:
        # Choose data source
        if USE_DATABASE:
            print("📡 Fetching profile from Pinecone/Supabase...")
            user_profile = fetch_user_profile_from_db(USER_ID)
        else:
            print("🧪 Using local mock data...")
            user_profile = MOCK_USER_PROFILE
        
        # Run the agent
        result = run_agent4(
            job_description=MOCK_JOB_DESCRIPTION,
            user_profile=user_profile
        )
        
        print()
        print("=" * 60)
        print("✅ WORKFLOW COMPLETE!")
        print("=" * 60)
        print()
        print(f"📝 Rewritten Content Keys: {list(result.get('rewritten_content', {}).keys())}")
        print(f"📄 PDF Generated: {result.get('pdf_path', 'N/A')}")
        print(f"📧 Recruiter Email: {result.get('recruiter_email', 'N/A')}")
        print(f"📊 Application Status: {result.get('application_status', 'N/A')}")
        print()
        
        if result.get('pdf_path'):
            print(f"👉 Open your PDF at: {result['pdf_path']}")
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ WORKFLOW FAILED!")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
