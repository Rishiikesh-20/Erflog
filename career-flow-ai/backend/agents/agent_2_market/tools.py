"""
Agent 2: Market Sentinel - Helper Tools for Job Search and Embeddings
This module provides tools for:
1. Searching jobs using Tavily API (targeting ATS platforms)
2. Scraping full job descriptions with trafilatura
3. Generating embeddings for job descriptions
"""

import os
from typing import Any
from dotenv import load_dotenv
from google import genai
import trafilatura

# Load environment variables
load_dotenv()

# Initialize Gemini client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY must be set in the environment or a .env file")

client = genai.Client(api_key=GEMINI_API_KEY)


def get_mock_jobs() -> list[dict[str, Any]]:
    """
    Return hardcoded mock job listings for fallback when Tavily fails.
    
    Returns:
        List of realistic job dictionaries
    """
    return [
        {
            "title": "Senior Python Developer",
            "company": "TechCorp Solutions",
            "link": "https://techcorp.example.com/jobs/senior-python-dev",
            "summary": "We are looking for a Senior Python Developer with 5+ years of experience in Django/FastAPI, cloud services (AWS/GCP), and database management. Experience with LLMs and AI systems is a plus.",
            "description": "We are looking for a Senior Python Developer with 5+ years of experience in Django/FastAPI, cloud services (AWS/GCP), and database management. Experience with LLMs and AI systems is a plus."
        },
        {
            "title": "AI/ML Engineer",
            "company": "StartupX AI",
            "link": "https://startupx.example.com/careers/ai-ml-engineer",
            "summary": "Join our AI team to build cutting-edge machine learning models. Required: Python, PyTorch/TensorFlow, experience with LangChain, and familiarity with vector databases like Pinecone.",
            "description": "Join our AI team to build cutting-edge machine learning models. Required: Python, PyTorch/TensorFlow, experience with LangChain, and familiarity with vector databases like Pinecone."
        },
        {
            "title": "Full Stack Software Engineer",
            "company": "InnovateTech Inc",
            "link": "https://innovatetech.example.com/jobs/fullstack-engineer",
            "summary": "Full Stack role requiring expertise in Python backend (FastAPI), React/Next.js frontend, PostgreSQL, and cloud deployment. Experience with REST APIs and microservices architecture preferred.",
            "description": "Full Stack role requiring expertise in Python backend (FastAPI), React/Next.js frontend, PostgreSQL, and cloud deployment. Experience with REST APIs and microservices architecture preferred."
        },
    ]


def scrape_job_description(url: str) -> str | None:
    """
    Scrape full job description from a URL using trafilatura.
    
    Args:
        url: The job posting URL to scrape
        
    Returns:
        Extracted text content or None if scraping fails
    """
    try:
        print(f"[Market] Scraping: {url}")
        downloaded = trafilatura.fetch_url(url)
        
        if not downloaded:
            print(f"[Market] Failed to fetch: {url}")
            return None
        
        text = trafilatura.extract(downloaded)
        
        if text and len(text.strip()) > 100:
            print(f"[Market] Scraped {len(text)} chars from {url}")
            return text.strip()
        else:
            print(f"[Market] Insufficient content from: {url}")
            return None
            
    except Exception as e:
        print(f"[Market] Scraping error for {url}: {str(e)}")
        return None


def search_jobs(query: str) -> list[dict[str, Any]]:
    """
    Search for jobs using Tavily API targeting ATS platforms,
    then scrape full descriptions with trafilatura.
    
    Args:
        query: Search query (e.g., "Python Developer")
        
    Returns:
        List of job dictionaries with full descriptions
    """
    try:
        from tavily import TavilyClient
        
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            print("[Market] TAVILY_API_KEY not found, using mock data")
            return get_mock_jobs()
        
        client = TavilyClient(api_key=api_key)
        
        # Target ATS platforms that are easy to scrape
        search_query = f"{query} (site:greenhouse.io OR site:lever.co OR site:ashbyhq.com)"
        print(f"[Market] Searching: {search_query}")
        
        results = client.search(search_query, max_results=5)
        
        # Transform results and scrape descriptions (top 3 only)
        jobs = []
        tavily_results = results.get("results", [])
        
        for i, result in enumerate(tavily_results):
            url = result.get("url", "")
            content = result.get("content", "")
            
            job = {
                "title": result.get("title", "Job Opening"),
                "company": extract_company_from_url(url),
                "link": url,
                "summary": content,  # Keep Tavily snippet for DB/preview
            }
            
            # Scrape full description for top 3 results only
            if i < 3 and url:
                scraped_description = scrape_job_description(url)
                
                # Use scraped content if available, otherwise fallback to Tavily snippet
                if scraped_description:
                    job["description"] = scraped_description
                else:
                    job["description"] = content  # Fallback to Tavily snippet
            else:
                job["description"] = content  # Fallback for results beyond top 3
            
            jobs.append(job)
        
        if not jobs:
            print("[Market] No results from Tavily, using mock data")
            return get_mock_jobs()
        
        print(f"[Market] Found {len(jobs)} jobs")
        return jobs
    
    except Exception as e:
        print(f"[Market] Error: {str(e)}")
        return get_mock_jobs()


def extract_company_from_url(url: str) -> str:
    """
    Extract a company name from a URL.
    
    Args:
        url: The URL string
        
    Returns:
        Extracted company name or "Unknown Company"
    """
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        # Remove www. and common TLDs
        company = domain.replace("www.", "").split(".")[0]
        return company.title() if company else "Unknown Company"
    except Exception:
        return "Unknown Company"


def generate_embedding(text: str) -> list[float]:
    """
    Generate embeddings for text using Google's embedding model.
    
    Args:
        text: Text to generate embedding for (e.g., job description)
        
    Returns:
        List of floats representing the embedding vector
        
    Raises:
        Exception: If embedding generation fails
    """
    try:
        # Use the official embedding model (768 dimensions)
        response = client.models.embed_content(
            model="text-embedding-004",
            contents=text,
        )
        
        # The embedding is in embeddings[0].values
        embedding = response.embeddings[0].values
        
        if not isinstance(embedding, list):
            raise ValueError("Embedding is not a list")
        
        return embedding
    
    except Exception as e:
        raise Exception(f"Error generating embedding: {str(e)}")
