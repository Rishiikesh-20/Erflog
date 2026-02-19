"""
Test: Generate user embedding with gemini-embedding-001
and check cosine similarity against jobs in Pinecone.
Compare with the stored embedding-001 vector.
"""
import os
from dotenv import load_dotenv
load_dotenv()
from pinecone import Pinecone
from google import genai

USER_ID = "483287fc-427a-4b4a-9b8a-2036282348ca"

# Setup
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
idx = pc.Index("ai-verse")
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# 1. Get user profile text
from supabase import create_client
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
profile = sb.table("profiles").select(
    "skills, target_roles, experience_summary, education"
).eq("user_id", USER_ID).single().execute()
p = profile.data
skills = p.get("skills", []) or []
roles = p.get("target_roles", []) or []
exp = p.get("experience_summary", "") or ""
edu = p.get("education", "") or ""
profile_text = f"Skills: {', '.join(skills) if isinstance(skills, list) else skills}\nTarget Roles: {', '.join(roles) if isinstance(roles, list) else roles}\nExperience: {exp}\nEducation: {edu}"

print(f"Profile text ({len(profile_text)} chars): {profile_text[:200]}...")

# 2. Generate embedding with gemini-embedding-001
resp = client.models.embed_content(model="gemini-embedding-001", contents=profile_text)
new_vec = resp.embeddings[0].values
print(f"\ngemini-embedding-001 vector: {len(new_vec)} dims, first 3: {new_vec[:3]}")

# 3. Get the stored embedding-001 vector
stored = idx.fetch(ids=[USER_ID], namespace="users")
stored_vec = stored.vectors[USER_ID].values
print(f"Stored embedding-001 vector: {len(stored_vec)} dims, first 3: {stored_vec[:3]}")

# 4. Query jobs with BOTH vectors and compare
print("\n" + "="*70)
print("COMPARISON: Stored embedding-001 vs Fresh gemini-embedding-001")
print("="*70)

for label, vec in [("stored embedding-001", stored_vec), ("fresh gemini-embedding-001", new_vec)]:
    q = idx.query(vector=vec, top_k=5, include_metadata=True, namespace="")
    print(f"\n--- {label} ---")
    for m in q.get("matches", []):
        title = m.get("metadata", {}).get("title", "?")[:50]
        score = m.get("score", 0)
        print(f"  {score:.4f}  {title}")
