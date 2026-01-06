# Create a file named: backend/run_with_mock_auth.py
import sys
import os
from pathlib import Path

# Add parent directory to path so we can import from backend root
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
from main import app
from auth.dependencies import get_current_user

# 1. Define the Mock Override
async def mock_get_current_user():
    return {"sub": "11111111-1111-1111-1111-111111111111", "email": "test@example.com"}

# 2. Apply Override
app.dependency_overrides[get_current_user] = mock_get_current_user

if __name__ == "__main__":
    print("⚠️  SERVER RUNNING IN TEST MODE (AUTH BYPASSED) ⚠️")
    uvicorn.run(app, host="0.0.0.0", port=8000)