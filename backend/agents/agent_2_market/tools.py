# backend/agents/agent_2_market/tools.py

"""
Agent 2: Market Sentinel - Helper Tools
1. JSearch (RapidAPI) -> Instant Jobs
2. Tavily -> Instant Hackathons & News
3. LangChain -> Embeddings
"""

import os
import re
import requests
from typing import Any, Literal
from datetime import datetime
from dotenv import load_dotenv

# --- THIRD PARTY IMPORTS ---
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Load environment variables
load_dotenv()

# Validate Critical Keys
if not os.getenv("GEMINI_API_KEY"):
    raise RuntimeError("GEMINI_API_KEY must be set in .env")

# =============================================================================
# 1. JSEARCH API (RapidAPI) - Primary Job Search (Instant)
# =============================================================================

def search_jsearch_jobs(query: str, num_results: int = 10) -> list[dict[str, Any]]:
    """Search for jobs using RapidAPI JSearch."""
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        print("[Market] RAPIDAPI_KEY not found, skipping JSearch")
        return []
    
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    params = {
        "query": query,
        "page": "1",
        "num_pages": "1",
        "date_posted": "month"
    }
    
    try:
        print(f"[Market] JSearch query: {query}")
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        raw_jobs = data.get("data", [])[:num_results]
        
        jobs = []
        for job in raw_jobs:
            jobs.append({
                "title": job.get("job_title", "Unknown Title"),
                "company": job.get("employer_name", "Unknown Company"),
                "link": job.get("job_apply_link") or job.get("job_google_link", ""),
                "summary": (job.get("job_description", "")[:500] + "...") if job.get("job_description") else "",
                "description": job.get("job_description", ""),
                "location": (job.get("job_city", "") + ", " + job.get("job_country", "")).strip(", "),
                "posted_at": job.get("job_posted_at_datetime_utc", ""),
                "type": "job",
                "source": "JSearch",
                "platform": job.get("job_publisher", "JSearch")
            })
        
        print(f"[Market] JSearch found {len(jobs)} jobs")
        return jobs
        
    except Exception as e:
        print(f"[Market] JSearch error: {str(e)}")
        return []

# =============================================================================
# 2. TAVILY API - Hackathons & News (Instant)
# =============================================================================

def search_tavily(
    query: str, 
    search_type: Literal["job", "hackathon", "news"] = "job",
    max_results: int = 5
) -> list[dict[str, Any]]:
    """Search using Tavily API for jobs, hackathons, or news."""
    try:
        from tavily import TavilyClient
        
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            print("[Market] TAVILY_API_KEY not found")
            return []
        
        client = TavilyClient(api_key=api_key)
        
        # Build specific queries
        if search_type == "hackathon":
            search_query = f"{query} site:devpost.com OR site:devfolio.co OR site:gitcoin.co"
        elif search_type == "news":
            search_query = query
        else:
            search_query = f"{query} (site:greenhouse.io OR site:lever.co)"
        
        # Configure search options
        search_kwargs = {"max_results": max_results}
        if search_type == "news":
            search_kwargs["search_depth"] = "advanced"
            search_kwargs["days"] = 3
        
        results = client.search(search_query, **search_kwargs)
        tavily_results = results.get("results", [])
        
        items = []
        for result in tavily_results:
            url = result.get("url", "")
            content = result.get("content", "")
            title = result.get("title", "")
            
            if search_type == "hackathon":
                bounty = extract_bounty_from_text(content)
                items.append({
                    "title": title,
                    "company": extract_platform_from_url(url),
                    "link": url,
                    "summary": content,
                    "description": content,
                    "type": "hackathon",
                    "source": "Tavily",
                    "platform": extract_platform_from_url(url),
                    "bounty_amount": bounty
                })
            elif search_type == "news":
                items.append({
                    "title": title,
                    "link": url,
                    "summary": content,
                    "description": content,
                    "source": extract_company_from_url(url),
                    "published_at": result.get("published_date", datetime.now().isoformat()),
                    "type": "news"
                })
            else:
                items.append({
                    "title": title,
                    "company": extract_company_from_url(url),
                    "link": url,
                    "summary": content,
                    "description": content,
                    "type": "job",
                    "source": "Tavily",
                    "platform": extract_platform_from_url(url)
                })
        
        return items
        
    except Exception as e:
        print(f"[Market] Tavily error: {str(e)}")
        return []

# =============================================================================
# 3. EMBEDDINGS & HELPERS
# =============================================================================

def generate_embedding(text: str) -> list[float]:
    """Generate embeddings using LangChain (Google GenAI)."""
    api_key = os.getenv("GEMINI_API_KEY")
    try:
        embeddings_model = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004", 
            google_api_key=api_key
        )
        return embeddings_model.embed_query(text)
    except Exception as e:
        raise Exception(f"Error generating embedding: {str(e)}")

def extract_bounty_from_text(text: str) -> float | None:
    patterns = [r'\$[\d,]+(?:k|K)?', r'[\d,]+\s*(?:USD|dollars?)', r'prize[:\s]+\$?[\d,]+']
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                amount_str = re.sub(r'[^\d.]', '', match.group())
                if 'k' in match.group().lower(): return float(amount_str) * 1000
                return float(amount_str) if amount_str else None
            except ValueError: continue
    return None

def extract_platform_from_url(url: str) -> str:
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        if "devpost" in domain: return "Devpost"
        if "devfolio" in domain: return "Devfolio"
        if "gitcoin" in domain: return "Gitcoin"
        return domain.replace("www.", "").split(".")[0].title()
    except Exception: return "Unknown"

def extract_company_from_url(url: str) -> str:
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        return domain.replace("www.", "").split(".")[0].title()
    except Exception: return "Unknown Company"