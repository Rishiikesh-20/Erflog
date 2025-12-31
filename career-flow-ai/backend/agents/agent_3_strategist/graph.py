import os
from dotenv import load_dotenv
from pinecone import Pinecone
from google import genai

# Load environment variables from .env
load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", os.getenv("INDEX_NAME", "ai-verse"))

# Initialize clients lazily
pc = None
index = None
client = None

def _init_clients():
    """Initialize Pinecone and Gemini clients lazily."""
    global pc, index, client
    
    if not PINECONE_API_KEY or not GEMINI_API_KEY:
        raise RuntimeError("PINECONE_API_KEY and GEMINI_API_KEY must be set in the environment or a .env file")
    
    if pc is None:
        pc = Pinecone(api_key=PINECONE_API_KEY)
    
    if index is None:
        try:
            index = pc.Index(INDEX_NAME)
        except Exception as e:
            print(f"[Strategist] Warning: Could not connect to index '{INDEX_NAME}': {e}")
            index = None
    
    if client is None:
        client = genai.Client(api_key=GEMINI_API_KEY)

def search_jobs(query_text: str, top_k: int = 5):
    """
    1. Converts user text (resume/skills) into a Vector.
    2. Queries Pinecone for similar jobs.
    3. Returns the list of matches with metadata.
    """
    print(f"🔍 Agent 3: Searching for matches for '{query_text[:30]}...'")

    try:
        _init_clients()
        
        if index is None:
            print("[Strategist] No Pinecone index available, returning empty results")
            return []
        
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
                "company": match['metadata'].get('company_name', match['metadata'].get('company', 'Unknown Company')),
                "description": match['metadata'].get('description', match['metadata'].get('summary', '')),
                "link": match['metadata'].get('link_to_apply', match['metadata'].get('link', '#'))
            })
        
        print(f"✅ Agent 3: Found {len(matches)} matches")
        return matches

    except Exception as e:
        print(f"❌ Error in Agent 3: {e}")
        return []