import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import UploadFile
from agents.agent_1_perception.service import agent1_service

# Mock an UploadFile object (since we aren't using a real HTTP request)
class MockUploadFile(UploadFile):
    def __init__(self, filename):
        self.filename = filename
        self.file = open(filename, "rb")

    async def read(self, size: int = -1):
        return self.file.read(size)

async def test_agent_1():
    print("🧪 Starting Agent 1 Service Test...")
    
    # 1. Create a dummy file object
    mock_file = MockUploadFile("test_resume.pdf")
    
    try:
        # 2. Call the Service directly
        # We pass a specific ID so we can easily find it in the DB later
        test_user_id = "11111111-1111-1111-1111-111111111111" 
        
        result = await agent1_service.process_resume_upload(
            file=mock_file, 
            user_id=test_user_id
        )
        
        print("\n✅ Service Execution Successful!")
        print(f"User ID: {result['user_id']}")
        print(f"Name Extracted: {result.get('name')}")
        print(f"Skills Found: {result.get('skills')}")
        print(f"Resume URL: {result.get('resume_url')}")
        
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
    finally:
        mock_file.file.close()

if __name__ == "__main__":
    # Load env vars if needed (dotenv)
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(test_agent_1())