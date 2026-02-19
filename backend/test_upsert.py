"""
Temporary test: directly test the today_data upsert, bypassing the full cron.
Run with: python test_upsert.py
"""
import os
import json
import traceback
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
USER_ID = "483287fc-427a-4b4a-9b8a-2036282348ca"

print(f"URL: {SUPABASE_URL[:40]}...")
print(f"KEY: {SUPABASE_KEY[:10]}...")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 1. Read current state
print("\n[1] Current row in today_data:")
try:
    r = supabase.table("today_data").select("user_id, updated_at").eq("user_id", USER_ID).execute()
    print("   ", r.data)
except Exception as e:
    print("   ERROR:", e)

# 2. Try upsert with a minimal test payload
print("\n[2] Attempting upsert...")
try:
    updated_at = datetime.now(timezone.utc).isoformat()
    test_data = {
        "jobs": [],
        "hackathons": [],
        "news": [],
        "hot_skills": [],
        "generated_at": updated_at,
        "stats": {"test": True}
    }
    # JSON round-trip to ensure serializability (same as fixed service.py)
    json_safe = json.loads(json.dumps(test_data, default=str))

    payload = {
        "user_id": USER_ID,
        "data_json": json_safe,
        "updated_at": updated_at,
    }
    response = supabase.table("today_data").upsert(payload, on_conflict="user_id").execute()
    print("   Response data:", response.data)
    print("   ✅ UPSERT SUCCEEDED")
except Exception as e:
    print("   ❌ UPSERT FAILED:", e)
    traceback.print_exc()

# 3. Read again to confirm
print("\n[3] Row after upsert:")
try:
    r = supabase.table("today_data").select("user_id, updated_at").eq("user_id", USER_ID).execute()
    print("   ", r.data)
except Exception as e:
    print("   ERROR:", e)
