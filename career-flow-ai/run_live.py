# ⚠️ LOAD DOTENV FIRST - before any other imports!
import os
from dotenv import load_dotenv

# Load environment variables from backend/.env FIRST
env_path = os.path.join(os.path.dirname(__file__), "backend", ".env")
load_dotenv(env_path)

# Debug: Verify env vars are loaded
print(f"DEBUG: SUPABASE_URL = {os.getenv('SUPABASE_URL')}")
print(f"DEBUG: SUPABASE_KEY = {os.getenv('SUPABASE_KEY')[:15]}..." if os.getenv('SUPABASE_KEY') else "DEBUG: SUPABASE_KEY = None")
print()

# NOW import backend modules (after dotenv is loaded)
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from agents.agent_4_operative.graph import run_agent4
from agents.agent_4_operative.tools import fetch_user_profile_by_uuid, build_resume_from_profile

# ==================== CONFIG ====================
# User UUID from Supabase profiles table
USER_UUID = "22c91dc9-4238-499b-a107-5b1abf3b919c"

JOB_DESCRIPTION = """
Full Stack Developer (Python + TypeScript) at Michael Page

Location: Bengaluru, Karnataka, India

Description:
Develop and maintain web applications using Python and TypeScript. 
Collaborate with cross-functional teams, ensure code quality, debug technical issues, 
and contribute to scalable system architectures.

Requirements:
- Strong proficiency in Python and TypeScript
- Experience with React.js and Node.js
- Knowledge of PostgreSQL and MongoDB
- Experience with Docker and AWS
- Understanding of RESTful APIs and microservices
"""


def main():
    print("=" * 60)
    print("🚀 AGENT 4 - APPLICATION OPERATIVE")
    print("=" * 60)
    print()
    
    try:
        # Fetch profile data from Supabase by UUID
        print(f"📡 Fetching profile for user: {USER_UUID}...")
        profile = fetch_user_profile_by_uuid(USER_UUID)
        
        # Build resume dict from profile
        user_profile = build_resume_from_profile(profile)
        
        print()
        print("📄 User Profile Loaded:")
        print(f"   Name: {user_profile.get('name', 'N/A')}")
        print(f"   Email: {user_profile.get('email', 'N/A')}")
        print(f"   Skills: {user_profile.get('skills', [])[:5]}...")
        print(f"   Experience Summary: {user_profile.get('experience_summary', 'N/A')[:50]}...")
        print()
        
        print("💼 Target Job:")
        print(f"   {JOB_DESCRIPTION[:150]}...")
        print()
        
        print("-" * 60)
        print("⚙️  Starting Agent 4 Workflow...")
        print("-" * 60)
        print()
        
        result = run_agent4(
            job_description=JOB_DESCRIPTION,
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
