import os
from dotenv import load_dotenv
from pinecone import Pinecone
from google import genai

# Load environment variables from .env
load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
INDEX_NAME = os.getenv("INDEX_NAME", "ai-verse")

if not PINECONE_API_KEY or not GEMINI_API_KEY:
    raise RuntimeError("PINECONE_API_KEY and GEMINI_API_KEY must be set in the environment or a .env file")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)
client = genai.Client(api_key=GEMINI_API_KEY)

def search_jobs(query_text: str, top_k: int = 5):
    """
    1. Converts user text (resume/skills) into a Vector.
    2. Queries Pinecone for similar jobs.
    3. Returns the list of matches with metadata.
    """
    print(f"🔍 Agent 3: Searching for matches for '{query_text[:30]}...'")

    try:
        response = client.models.embed_content(
            model="text-embedding-004",  # 768 dimensions
            contents=query_text,
        )
        user_vector = response.embeddings[0].values

        search_results = index.query(
            vector=user_vector,
            top_k=top_k,
            include_metadata=True
        )
        
        matches = []
        for match in search_results['matches']:
            matches.append({
                "id": match['id'],
                "score": match['score'], 
                "title": match['metadata'].get('title', 'Unknown Role'),
                "company": match['metadata'].get('company_name', 'Unknown Company'),
                "description": match['metadata'].get('description', ''),
                "link": match['metadata'].get('link_to_apply', '#')
            })
        
        return matches

    except Exception as e:
        print(f"❌ Error in Agent 3: {e}")
        return []