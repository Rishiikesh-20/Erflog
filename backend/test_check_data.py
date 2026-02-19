"""Check what's actually stored in today_data for the user."""
import os
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

s = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
r = s.table("today_data").select("data_json, updated_at").eq(
    "user_id", "483287fc-427a-4b4a-9b8a-2036282348ca"
).execute()

if not r.data:
    print("NO DATA FOUND")
else:
    row = r.data[0]
    print(f"updated_at: {row['updated_at']}")
    data = row["data_json"]
    print(f"generated_at: {data.get('generated_at', 'MISSING')}")
    jobs = data.get("jobs", [])
    print(f"\nJobs ({len(jobs)}):")
    for j in jobs:
        title = j.get("title", "?")[:50]
        score = j.get("score", "N/A")
        mp = j.get("match_percentage", "MISSING")
        sem = j.get("semantic_score", "N/A")
        print(f"  {title:50s}  score={score!s:>8}  match_pct={mp!s:>8}  semantic={sem!s:>8}")
