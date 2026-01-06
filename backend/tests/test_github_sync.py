import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load env vars first
load_dotenv()

from agents.agent_1_perception.service import agent1_service

async def test_github_sync():
    print("🚀 Starting GitHub Watchdog Service Test...")
    
    # 1. Setup Test Data
    # Use a real public repo that has code (e.g., this project or a popular one)
    test_github_url = "https://github.com/Rishiikesh-20/EdgeMind-PdM" 
    
    # Use the same dummy ID from your resume test so we update that profile
    test_user_id = "11111111-1111-1111-1111-111111111111" 
    
    try:
        # 2. Call the Service directly
        print(f"   Analyzing Repo: {test_github_url}...")
        result = await agent1_service.run_github_watchdog(
            user_id=test_user_id,
            github_url=test_github_url
        )
        
        if result:
            print("\n✅ Sync Successful!")
            print("------------------------------------------------")
            print(f"Analysis Raw: {result.get('analysis')}")
            print("------------------------------------------------")
            print(f"Updated Skills List: {result.get('updated_skills')}")
        else:
            print("\n❌ Sync Failed: Returned None (Check logs for API errors)")
        
    except Exception as e:
        print(f"\n❌ Test Crashed: {e}")

if __name__ == "__main__":
    asyncio.run(test_github_sync())