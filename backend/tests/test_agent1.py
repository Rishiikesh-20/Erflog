import requests
import uuid
import os
import sys
from pathlib import Path

# Config (update with your local)
BASE_URL = "http://localhost:8000"  # Adjust if prefixed, e.g., /agent1

# Define path to your existing local file
# This assumes 'test_resume.pdf' is in the SAME folder as this script
CURRENT_DIR = Path(__file__).parent
PDF_FILENAME = "test_resume.pdf"
PDF_PATH = CURRENT_DIR / PDF_FILENAME

# Mock user (bypass auth—hardcode in service/router for tests)
TEST_USER_ID = str(uuid.uuid4())

# Helper: Multipart upload for PDF
def upload_resume(pdf_path):
    if not pdf_path.exists():
        print(f"❌ Error: File not found at {pdf_path}")
        print("Please ensure 'test_resume.pdf' is in the same directory.")
        sys.exit(1)

    print(f"📂 Reading resume from: {pdf_path}")
    
    with open(pdf_path, 'rb') as f:
        # Note: We send the filename as 'test-resume.pdf' to the server
        files = {'file': (pdf_path.name, f, 'application/pdf')}
        
        # Mock auth header (Ensure your backend is running in Mock Mode or use real Token)
        headers = {'Authorization': f'Bearer mock-jwt-for-{TEST_USER_ID}'} 
        
        try:
            response = requests.post(f"{BASE_URL}/api/perception/upload-resume", files=files, headers=headers)
            response.raise_for_status() # Raise error for 400/500 codes
        except requests.exceptions.HTTPError as e:
            print(f"❌ Upload Failed: {e}")
            print(f"Server Response: {response.text}")
            sys.exit(1)
            
    return response.json()

# =============================================================================
# TESTS START HERE
# =============================================================================

# Step 1: Upload Resume
print("=== Testing Resume Upload ===")
upload_result = upload_resume(PDF_PATH)
print("✅ Upload Success!")
print(f"User ID: {TEST_USER_ID}")
print(f"Data: {upload_result}")  

# Step 2: Onboard GitHub (PATCH)
print("\n=== Testing Onboarding ===")
onboard_data = {"github_url": "https://github.com/octocat", "target_roles": ["Software Engineer"]}
response = requests.patch(
    f"{BASE_URL}/api/perception/onboarding",
    json=onboard_data,
    headers={'Authorization': f'Bearer mock-jwt-for-{TEST_USER_ID}'}
)
print(response.json()) 

# Step 3: Sync GitHub
print("\n=== Testing GitHub Sync ===")
sync_response = requests.post(
    f"{BASE_URL}/api/perception/sync-github",
    headers={'Authorization': f'Bearer mock-jwt-for-{TEST_USER_ID}'}
)
print(sync_response.json())

# Step 4: Watchdog Poll (Simulate new activity)
print("\n=== Testing Watchdog Poll ===")
poll_data = {"last_known_sha": "abc123"}  # Fake old SHA
poll_response = requests.post(
    f"{BASE_URL}/api/perception/watchdog/check",
    json=poll_data,
    headers={'Authorization': f'Bearer mock-jwt-for-{TEST_USER_ID}'}
)
print(poll_response.json())

# Step 5: Generate & Submit Quiz
print("\n=== Testing Quiz ===")
# We assume the resume or github sync found "Python" or similar. 
# If not, change "Python" below to a skill that actually exists in your resume.
SKILL_TO_TEST = "Python" 

quiz_req = {"skill_name": SKILL_TO_TEST, "level": "intermediate"}
quiz_resp = requests.post(
    f"{BASE_URL}/api/perception/verify/quiz",
    json=quiz_req,
    headers={'Authorization': f'Bearer mock-jwt-for-{TEST_USER_ID}'}
)

if quiz_resp.status_code != 200:
    print(f"⚠️ Quiz generation failed. Server said: {quiz_resp.text}")
    print("Skipping submission...")
else:
    quiz_data = quiz_resp.json()
    print(quiz_data)

    # Submit (Using the cheat field 'correct_index' returned by our stateless backend)
    # In a real app, the user wouldn't see 'correct_index'
    correct_idx = quiz_data["quiz"]["correct_index"]
    
    submit_data = {
        "quiz_id": quiz_data["quiz"]["quiz_id"],
        "skill_name": SKILL_TO_TEST,
        "answer_index": correct_idx,  # Force correct answer
        "expected_correct_index": correct_idx
    }
    submit_resp = requests.post(
        f"{BASE_URL}/api/perception/verify/submit",
        json=submit_data,
        headers={'Authorization': f'Bearer mock-jwt-for-{TEST_USER_ID}'}
    )
    print(submit_resp.json()) 

# Step 6: Fetch Profile
print("\n=== Testing Profile Fetch ===")
profile_resp = requests.get(
    f"{BASE_URL}/api/perception/profile",
    headers={'Authorization': f'Bearer mock-jwt-for-{TEST_USER_ID}'}
)
print(profile_resp.json())

print("\n=== All Tests Complete! ===")