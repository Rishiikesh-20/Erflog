# backend/agents/agent_2_market/tools.py

"""
Agent 2: Market Intelligence - External Provider Tools

Data Providers:
- Jobs: JSearch (RapidAPI), Mantiks, SerpAPI
- Hackathons: Tavily, SerpAPI
- News: Tavily, NewsData.io, SerpAPI

⚠️ Apify is NOT used anywhere in this agent.
"""

import os
import re
import json
import requests
from typing import Any, Literal, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv

# --- THIRD PARTY IMPORTS ---
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Validate Critical Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY must be set in .env")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)


# =============================================================================
# 1. JSEARCH API (RapidAPI) - Primary Job Search
# =============================================================================

def search_jsearch_jobs(
    query: str, 
    num_results: int = 10,
    country: str = "in",
    date_posted: str = "month"
) -> list[dict[str, Any]]:
    """
    Search for jobs using RapidAPI JSearch.
    
    Args:
        query: Job search query (e.g., "Frontend Developer")
        num_results: Maximum number of results to return
        country: Country code for job search
        date_posted: Filter by date posted (all, today, 3days, week, month)
    
    Returns:
        List of normalized job dictionaries
    """
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        print("[JSearch] RAPIDAPI_KEY not found, skipping")
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
        "country": country,
        "date_posted": date_posted
    }
    
    try:
        print(f"[JSearch] Query: {query}")
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        
        data = response.json()
        raw_jobs = data.get("data", [])[:num_results]
        
        jobs = []
        for job in raw_jobs:
            # Build location string
            city = job.get("job_city", "")
            state = job.get("job_state", "")
            country_name = job.get("job_country", "")
            location_parts = [p for p in [city, state, country_name] if p]
            location = ", ".join(location_parts)
            
            # Parse posted date
            posted_at = None
            if job.get("job_posted_at_timestamp"):
                try:
                    posted_at = datetime.fromtimestamp(
                        job["job_posted_at_timestamp"], 
                        tz=timezone.utc
                    ).isoformat()
                except:
                    pass
            
            # Determine remote policy
            remote_policy = None
            if job.get("job_is_remote"):
                remote_policy = "remote"
            elif "hybrid" in str(job.get("job_employment_type", "")).lower():
                remote_policy = "hybrid"
            
            jobs.append({
                "title": job.get("job_title", "Unknown Title"),
                "company": job.get("employer_name", "Unknown Company"),
                "link": job.get("job_apply_link") or job.get("job_google_link", ""),
                "description": job.get("job_description", ""),
                "summary": _truncate_text(job.get("job_description", ""), 500),
                "location": location,
                "posted_at": posted_at,
                "remote_policy": remote_policy,
                "type": "job",
                "source": "JSearch",
                "platform": job.get("job_publisher", "JSearch"),
            })
        
        print(f"[JSearch] Found {len(jobs)} jobs")
        return jobs
        
    except requests.exceptions.RequestException as e:
        print(f"[JSearch] Request error: {str(e)}")
        return []
    except Exception as e:
        print(f"[JSearch] Error: {str(e)}")
        return []


# =============================================================================
# 2. SERPAPI (Google Jobs) - Job Search
# =============================================================================

def search_serpapi_jobs(
    query: str,
    num_results: int = 10,
    location: str = "India"
) -> list[dict[str, Any]]:
    """
    Search for jobs using SerpAPI Google Jobs engine.
    
    Args:
        query: Job search query
        num_results: Maximum results to return
        location: Location for job search
    
    Returns:
        List of normalized job dictionaries
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        print("[SerpAPI] SERPAPI_KEY not found, skipping")
        return []
    
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_jobs",
        "q": query,
        "location": location,
        "hl": "en",
        "gl": "in",
        "api_key": api_key
    }
    
    try:
        print(f"[SerpAPI Jobs] Query: {query}")
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        
        data = response.json()
        raw_jobs = data.get("jobs_results", [])[:num_results]
        
        jobs = []
        for job in raw_jobs:
            # Extract link from related_links
            link = ""
            related_links = job.get("related_links", [])
            if related_links:
                link = related_links[0].get("link", "")
            
            # Parse extensions for remote policy
            extensions = job.get("extensions", [])
            remote_policy = None
            for ext in extensions:
                ext_lower = ext.lower()
                if "remote" in ext_lower:
                    remote_policy = "remote"
                elif "hybrid" in ext_lower:
                    remote_policy = "hybrid"
            
            jobs.append({
                "title": job.get("title", "Unknown Title"),
                "company": job.get("company_name", "Unknown Company"),
                "link": link,
                "description": job.get("description", ""),
                "summary": _truncate_text(job.get("description", ""), 500),
                "location": job.get("location", ""),
                "remote_policy": remote_policy,
                "type": "job",
                "source": "SerpAPI",
                "platform": job.get("via", "Google Jobs"),
            })
        
        print(f"[SerpAPI Jobs] Found {len(jobs)} jobs")
        return jobs
        
    except requests.exceptions.RequestException as e:
        print(f"[SerpAPI Jobs] Request error: {str(e)}")
        return []
    except Exception as e:
        print(f"[SerpAPI Jobs] Error: {str(e)}")
        return []


# =============================================================================
# 3. MANTIKS API - Company & Job Intelligence
# =============================================================================

def search_mantiks_jobs(
    job_title: str,
    num_results: int = 10,
    location_id: Optional[str] = "1269750"  # India location ID
) -> list[dict[str, Any]]:
    """
    Search for jobs using Mantiks Company Search API.
    
    Args:
        job_title: Job title to search for
        num_results: Maximum results to return
        location_id: Mantiks location ID (optional)
    
    Returns:
        List of normalized job dictionaries
    """
    api_key = os.getenv("MANTIKS_API_KEY")
    if not api_key:
        print("[Mantiks] MANTIKS_API_KEY not found, skipping")
        return []
    
    url = "https://api.mantiks.io/company/search"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    params = {
        "job_title": job_title,
        "limit": num_results
    }
    
    if location_id:
        params["job_location_ids"] = location_id
    
    try:
        print(f"[Mantiks] Query: {job_title}")
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        
        data = response.json()
        companies = data.get("companies", [])
        
        jobs = []
        for company in companies:
            company_name = company.get("name", "Unknown Company")
            company_jobs = company.get("jobs", [])
            
            for job in company_jobs[:3]:  # Max 3 jobs per company
                # Parse salary
                salary_info = job.get("salary", {})
                salary_str = ""
                if salary_info:
                    min_sal = salary_info.get("min", 0)
                    max_sal = salary_info.get("max", 0)
                    sal_type = salary_info.get("type", "YEARLY")
                    if min_sal and max_sal:
                        salary_str = f"${min_sal:,} - ${max_sal:,} {sal_type}"
                
                jobs.append({
                    "title": job.get("job_title", "Unknown Title"),
                    "company": company_name,
                    "link": job.get("job_board_url", ""),
                    "description": f"Job at {company_name}. {salary_str}".strip(),
                    "summary": f"Position at {company_name}. {salary_str}".strip(),
                    "location": job.get("location", ""),
                    "posted_at": job.get("date_creation"),
                    "type": "job",
                    "source": "Mantiks",
                    "platform": job.get("job_board", "LinkedIn"),
                })
                
                if len(jobs) >= num_results:
                    break
            
            if len(jobs) >= num_results:
                break
        
        print(f"[Mantiks] Found {len(jobs)} jobs")
        return jobs
        
    except requests.exceptions.RequestException as e:
        print(f"[Mantiks] Request error: {str(e)}")
        return []
    except Exception as e:
        print(f"[Mantiks] Error: {str(e)}")
        return []


# =============================================================================
# 4. TAVILY API - Hackathons & News Search
# =============================================================================

def search_tavily_hackathons(
    query: str,
    max_results: int = 10
) -> list[dict[str, Any]]:
    """
    Search for hackathons using Tavily API.
    
    Args:
        query: Search query for hackathons
        max_results: Maximum results to return
    
    Returns:
        List of normalized hackathon dictionaries
    """
    try:
        from tavily import TavilyClient
        
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            print("[Tavily Hackathons] TAVILY_API_KEY not found")
            return []
        
        client = TavilyClient(api_key=api_key)
        
        # Target hackathon platforms specifically - India focused
        search_query = f"{query} hackathon India site:devpost.com OR site:devfolio.co OR site:gitcoin.co OR site:hackerearth.com OR site:mlh.io OR site:unstop.com"
        
        print(f"[Tavily Hackathons] Query: {query}")
        results = client.search(
            search_query, 
            max_results=max_results,
            search_depth="advanced"
        )
        
        hackathons = []
        for result in results.get("results", []):
            url = result.get("url", "")
            content = result.get("content", "")
            title = result.get("title", "")
            
            # Extract bounty/prize amount
            bounty = _extract_bounty_from_text(content)
            
            hackathons.append({
                "title": title,
                "company": _extract_platform_from_url(url),
                "link": url,
                "description": content,
                "summary": _truncate_text(content, 500),
                "type": "hackathon",
                "source": "Tavily",
                "platform": _extract_platform_from_url(url),
                "bounty_amount": bounty,
            })
        
        print(f"[Tavily Hackathons] Found {len(hackathons)} hackathons")
        return hackathons
        
    except ImportError:
        print("[Tavily] tavily-python package not installed")
        return []
    except Exception as e:
        print(f"[Tavily Hackathons] Error: {str(e)}")
        return []


def search_tavily_news(
    query: str,
    max_results: int = 5,
    days: int = 7
) -> list[dict[str, Any]]:
    """
    Search for tech/market news using Tavily API.
    
    Args:
        query: Search query for news
        max_results: Maximum results to return
        days: Number of days to look back
    
    Returns:
        List of normalized news dictionaries
    """
    try:
        from tavily import TavilyClient
        
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            print("[Tavily News] TAVILY_API_KEY not found")
            return []
        
        client = TavilyClient(api_key=api_key)
        
        # Add India focus to news search
        india_query = f"{query} India"
        print(f"[Tavily News] Query: {india_query}")
        results = client.search(
            india_query,
            max_results=max_results,
            search_depth="advanced",
            days=days
        )
        
        news_items = []
        for result in results.get("results", []):
            url = result.get("url", "")
            
            # Parse published date
            published_at = None
            if result.get("published_date"):
                try:
                    published_at = result["published_date"]
                except:
                    pass
            
            news_items.append({
                "title": result.get("title", ""),
                "url": url,
                "summary": _truncate_text(result.get("content", ""), 500),
                "source": _extract_domain_from_url(url),
                "published_at": published_at,
                "topics": [],  # Will be enriched by LLM if needed
            })
        
        print(f"[Tavily News] Found {len(news_items)} news articles")
        return news_items
        
    except ImportError:
        print("[Tavily] tavily-python package not installed")
        return []
    except Exception as e:
        print(f"[Tavily News] Error: {str(e)}")
        return []


# =============================================================================
# 5. SERPAPI - Hackathon Search (Google Search)
# =============================================================================

def search_serpapi_hackathons(
    query: str,
    num_results: int = 10
) -> list[dict[str, Any]]:
    """
    Search for hackathons using SerpAPI Google Search.
    
    Args:
        query: Search query for hackathons
        num_results: Maximum results to return
    
    Returns:
        List of normalized hackathon dictionaries
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        print("[SerpAPI Hackathons] SERPAPI_KEY not found, skipping")
        return []
    
    url = "https://serpapi.com/search.json"
    
    # Target hackathon platforms - India focused
    search_query = f"{query} hackathon India (site:devpost.com OR site:devfolio.co OR site:mlh.io OR site:unstop.com OR site:hackerearth.com)"
    
    params = {
        "engine": "google",
        "q": search_query,
        "num": num_results,
        "api_key": api_key
    }
    
    try:
        print(f"[SerpAPI Hackathons] Query: {query}")
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        
        data = response.json()
        organic_results = data.get("organic_results", [])[:num_results]
        
        hackathons = []
        for result in organic_results:
            url = result.get("link", "")
            snippet = result.get("snippet", "")
            
            bounty = _extract_bounty_from_text(snippet)
            
            hackathons.append({
                "title": result.get("title", ""),
                "company": _extract_platform_from_url(url),
                "link": url,
                "description": snippet,
                "summary": _truncate_text(snippet, 500),
                "type": "hackathon",
                "source": "SerpAPI",
                "platform": _extract_platform_from_url(url),
                "bounty_amount": bounty,
            })
        
        print(f"[SerpAPI Hackathons] Found {len(hackathons)} hackathons")
        return hackathons
        
    except requests.exceptions.RequestException as e:
        print(f"[SerpAPI Hackathons] Request error: {str(e)}")
        return []
    except Exception as e:
        print(f"[SerpAPI Hackathons] Error: {str(e)}")
        return []


# =============================================================================
# 6. NEWSDATA.IO API - News Search
# =============================================================================

def search_newsdata_news(
    query: str,
    num_results: int = 10,
    country: str = "in",
    language: str = "en"
) -> list[dict[str, Any]]:
    """
    Search for news using NewsData.io API.
    
    Args:
        query: Search query for news
        num_results: Maximum results to return
        country: Country code
        language: Language code
    
    Returns:
        List of normalized news dictionaries
    """
    api_key = os.getenv("NEWSDATA_API_KEY")
    if not api_key:
        print("[NewsData] NEWSDATA_API_KEY not found, skipping")
        return []
    
    url = "https://newsdata.io/api/1/latest"
    params = {
        "apikey": api_key,
        "q": query,
        "country": country,
        "language": language,
        "category": "technology,business"
    }
    
    try:
        print(f"[NewsData] Query: {query}")
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") != "success":
            print(f"[NewsData] API returned status: {data.get('status')}")
            return []
        
        articles = data.get("results", [])[:num_results]
        
        news_items = []
        for article in articles:
            # Parse published date
            published_at = None
            if article.get("pubDate"):
                try:
                    published_at = article["pubDate"]
                except:
                    pass
            
            # Extract topics from keywords and category
            topics = []
            if article.get("keywords"):
                topics.extend(article["keywords"][:5])
            if article.get("category"):
                topics.extend(article["category"][:3])
            topics = list(set(topics))[:5]  # Dedupe and limit
            
            news_items.append({
                "title": article.get("title", ""),
                "url": article.get("link", ""),
                "summary": _truncate_text(article.get("description", ""), 500),
                "source": article.get("source_id", "Unknown"),
                "published_at": published_at,
                "topics": topics,
            })
        
        print(f"[NewsData] Found {len(news_items)} news articles")
        return news_items
        
    except requests.exceptions.RequestException as e:
        print(f"[NewsData] Request error: {str(e)}")
        return []
    except Exception as e:
        print(f"[NewsData] Error: {str(e)}")
        return []


# =============================================================================
# 7. SERPAPI - News Search (Google News)
# =============================================================================

def search_serpapi_news(
    query: str,
    num_results: int = 5
) -> list[dict[str, Any]]:
    """
    Search for news using SerpAPI Google News engine.
    
    Args:
        query: Search query for news
        num_results: Maximum results to return
    
    Returns:
        List of normalized news dictionaries
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        print("[SerpAPI News] SERPAPI_KEY not found, skipping")
        return []
    
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_news",
        "q": f"{query} India",
        "gl": "in",
        "hl": "en",
        "api_key": api_key
    }
    
    try:
        print(f"[SerpAPI News] Query: {query}")
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        
        data = response.json()
        news_results = data.get("news_results", [])[:num_results]
        
        news_items = []
        for article in news_results:
            news_items.append({
                "title": article.get("title", ""),
                "url": article.get("link", ""),
                "summary": _truncate_text(article.get("snippet", ""), 500),
                "source": article.get("source", {}).get("name", "Unknown"),
                "published_at": article.get("date"),
                "topics": [],
            })
        
        print(f"[SerpAPI News] Found {len(news_items)} news articles")
        return news_items
        
    except requests.exceptions.RequestException as e:
        print(f"[SerpAPI News] Request error: {str(e)}")
        return []
    except Exception as e:
        print(f"[SerpAPI News] Error: {str(e)}")
        return []


# =============================================================================
# 8. GEMINI LLM - Query Generation & Role Optimization
# =============================================================================

def optimize_roles_with_llm(
    roles: list[str],
    skills: list[str],
    max_roles: int = 5
) -> list[str]:
    """
    Use Gemini to optimize and select the best roles for maximum coverage.
    
    Args:
        roles: List of all user target roles
        skills: List of all user skills
        max_roles: Maximum number of roles to return
    
    Returns:
        List of optimized roles (1-5)
    """
    if not roles:
        return ["Software Developer"]
    
    if len(roles) <= max_roles:
        return roles
    
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""You are a job market analyst. Given these target roles and skills from multiple users, 
select at most {max_roles} distinct job roles that best cover all users collectively.

Target Roles: {json.dumps(roles)}
Skills: {json.dumps(skills[:30])}  # Limit skills for context

Rules:
1. Return only roles from the provided list
2. Maximize coverage across different users
3. Prefer high-demand roles with good hiring volume
4. Return 1 to {max_roles} roles maximum
5. Roles must be distinct (no duplicates)

Return ONLY a JSON array of role strings, nothing else.
Example: ["Frontend Developer", "Data Scientist", "DevOps Engineer"]
"""
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Parse JSON response
        if response_text.startswith("[") or "{" in response_text:
            # Extract JSON from response (might have markdown or extra text)
            json_start = response_text.find("[")
            json_end = response_text.rfind("]") + 1
            if json_start >= 0 and json_end > json_start:
                try:
                    json_text = response_text[json_start:json_end]
                    optimized_roles = json.loads(json_text)
                    if isinstance(optimized_roles, list) and optimized_roles:
                        # Don't validate against original list - LLM might clean/normalize names
                        print(f"[LLM] Optimized roles: {optimized_roles}")
                        return optimized_roles[:max_roles]
                except json.JSONDecodeError as e:
                    print(f"[LLM] JSON parse error: {e}")
        
        # Fallback: return first N roles
        print("[LLM] Could not parse response, using fallback")
        return roles[:max_roles]
        
    except Exception as e:
        print(f"[LLM] Role optimization error: {str(e)}")
        return roles[:max_roles]


def generate_search_queries_with_llm(
    roles: list[str],
    skills: list[str],
    query_type: Literal["jobs", "hackathons", "news"]
) -> list[str]:
    """
    Use Gemini to generate optimized search queries.
    
    Args:
        roles: List of target roles
        skills: List of skills
        query_type: Type of queries to generate
    
    Returns:
        List of search query strings
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        type_prompts = {
            "jobs": f"""Generate {min(5, len(roles))} optimized job search queries for these roles and skills.
Roles: {json.dumps(roles)}
Skills: {json.dumps(skills[:20])}

Rules:
- Each query should be 2-5 words
- Include role name and relevant skill
- Make queries specific and searchable
- Focus on high-demand positions

Return ONLY a JSON array of query strings.""",

            "hackathons": f"""Generate 3-5 hackathon search queries based on these skills and roles.
Roles: {json.dumps(roles)}
Skills: {json.dumps(skills[:20])}

Rules:
- Include terms like "hackathon", "challenge", "competition"
- Focus on 2026 and upcoming events
- Include technology-specific terms
- Make queries specific to hackathon platforms

Return ONLY a JSON array of query strings.""",

            "news": f"""Generate 3-5 tech news search queries based on these skills and technologies.
Skills: {json.dumps(skills[:20])}
Roles: {json.dumps(roles)}

Rules:
- Focus on industry trends and market news
- Include terms like "latest", "trends", "2026"
- Target technology ecosystem news
- Make queries broad enough to find relevant articles

Return ONLY a JSON array of query strings."""
        }
        
        prompt = type_prompts.get(query_type, type_prompts["jobs"])
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Parse JSON response
        if response_text.startswith("["):
            queries = json.loads(response_text)
            if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
                print(f"[LLM] Generated {query_type} queries: {queries}")
                return queries[:5]
        
        # Fallback queries
        fallback = {
            "jobs": [f"{role} developer" for role in roles[:3]],
            "hackathons": [f"{skills[0] if skills else 'programming'} hackathon 2026"],
            "news": [f"{skills[0] if skills else 'technology'} industry trends 2026"]
        }
        return fallback.get(query_type, [])
        
    except Exception as e:
        print(f"[LLM] Query generation error: {str(e)}")
        # Return basic fallback queries
        if query_type == "jobs":
            return [f"{role}" for role in roles[:3]]
        elif query_type == "hackathons":
            return ["tech hackathon 2026", "developer challenge 2026"]
        else:
            return ["technology trends 2026", "tech industry news"]


def allocate_roles_to_providers(roles: list[str]) -> dict[str, list[str]]:
    """
    Intelligently allocate roles to job providers.
    
    Strategy:
    - JSearch: Best for common tech roles (Frontend, Backend, Full Stack)
    - SerpAPI: Best for specialized/emerging roles (Web3, AI/ML)
    - Mantiks: Best for security and enterprise roles
    
    Args:
        roles: List of roles to allocate
    
    Returns:
        Dictionary with provider allocations
    """
    allocation = {
        "jsearch": [],
        "mantiks": [],
        "serpapi": []
    }
    
    # Define provider strengths
    jsearch_keywords = ["frontend", "backend", "full stack", "fullstack", "web", "mobile", "react", "node", "python", "javascript"]
    mantiks_keywords = ["security", "cyber", "enterprise", "cloud", "devops", "sre", "infrastructure"]
    serpapi_keywords = ["web3", "blockchain", "ai", "ml", "machine learning", "data", "analyst", "scientist"]
    
    for role in roles:
        role_lower = role.lower()
        
        # Check which provider is best suited
        jsearch_score = sum(1 for kw in jsearch_keywords if kw in role_lower)
        mantiks_score = sum(1 for kw in mantiks_keywords if kw in role_lower)
        serpapi_score = sum(1 for kw in serpapi_keywords if kw in role_lower)
        
        if mantiks_score >= jsearch_score and mantiks_score >= serpapi_score and mantiks_score > 0:
            allocation["mantiks"].append(role)
        elif serpapi_score >= jsearch_score and serpapi_score > 0:
            allocation["serpapi"].append(role)
        else:
            # Default to JSearch for general roles
            allocation["jsearch"].append(role)
    
    # Ensure balanced distribution: If Mantiks has 0 roles, redistribute
    if roles and len(allocation["mantiks"]) == 0 and len(roles) >= 3:
        # Move one role from jsearch or serpapi to mantiks for diversity
        if allocation["jsearch"]:
            allocation["mantiks"].append(allocation["jsearch"].pop())
        elif allocation["serpapi"]:
            allocation["mantiks"].append(allocation["serpapi"].pop())
    
    # Ensure at least one provider has roles if we have any
    if roles and not any(allocation.values()):
        allocation["jsearch"] = roles[:2]
    
    print(f"[Allocation] JSearch: {allocation['jsearch']}, Mantiks: {allocation['mantiks']}, SerpAPI: {allocation['serpapi']}")
    return allocation


# =============================================================================
# 9. EMBEDDINGS
# =============================================================================

def generate_embedding(text: str) -> list[float]:
    """
    Generate embeddings using Google GenAI.
    
    Args:
        text: Text to generate embedding for
    
    Returns:
        List of embedding floats (768 dimensions)
    """
    api_key = os.getenv("GEMINI_API_KEY")
    try:
        embeddings_model = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004", 
            google_api_key=api_key
        )
        return embeddings_model.embed_query(text)
    except Exception as e:
        raise Exception(f"Error generating embedding: {str(e)}")


# =============================================================================
# 10. HELPER FUNCTIONS
# =============================================================================

def _truncate_text(text: str, max_length: int) -> str:
    """Truncate text to max length with ellipsis."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def _extract_bounty_from_text(text: str) -> Optional[float]:
    """Extract prize/bounty amount from text."""
    if not text:
        return None
    
    patterns = [
        r'\$[\d,]+(?:k|K)?',
        r'[\d,]+\s*(?:USD|dollars?)',
        r'prize[:\s]+\$?[\d,]+',
        r'[\d,]+\s*(?:in prizes|prize pool)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                amount_str = re.sub(r'[^\d.]', '', match.group())
                if 'k' in match.group().lower():
                    return float(amount_str) * 1000
                if amount_str:
                    return float(amount_str)
            except ValueError:
                continue
    return None


def _extract_platform_from_url(url: str) -> str:
    """Extract platform name from URL."""
    if not url:
        return "Unknown"
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        
        platform_map = {
            "devpost": "Devpost",
            "devfolio": "Devfolio",
            "gitcoin": "Gitcoin",
            "hackerearth": "HackerEarth",
            "mlh": "MLH",
            "hackathon.io": "Hackathon.io",
        }
        
        for key, name in platform_map.items():
            if key in domain:
                return name
        
        return domain.replace("www.", "").split(".")[0].title()
    except Exception:
        return "Unknown"


def _extract_domain_from_url(url: str) -> str:
    """Extract clean domain name from URL."""
    if not url:
        return "Unknown"
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        return domain.replace("www.", "")
    except Exception:
        return "Unknown"


def _extract_company_from_url(url: str) -> str:
    """Extract company name from URL."""
    if not url:
        return "Unknown Company"
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        return domain.replace("www.", "").split(".")[0].title()
    except Exception:
        return "Unknown Company"


# =============================================================================
# LEGACY COMPATIBILITY FUNCTIONS
# =============================================================================

def search_tavily(
    query: str, 
    search_type: Literal["job", "hackathon", "news"] = "job",
    max_results: int = 5
) -> list[dict[str, Any]]:
    """Legacy function for backward compatibility."""
    if search_type == "hackathon":
        return search_tavily_hackathons(query, max_results)
    elif search_type == "news":
        return search_tavily_news(query, max_results)
    else:
        # For jobs, use JSearch instead
        return search_jsearch_jobs(query, max_results)


def extract_bounty_from_text(text: str) -> Optional[float]:
    """Legacy wrapper for _extract_bounty_from_text."""
    return _extract_bounty_from_text(text)


def extract_platform_from_url(url: str) -> str:
    """Legacy wrapper for _extract_platform_from_url."""
    return _extract_platform_from_url(url)


def extract_company_from_url(url: str) -> str:
    """Legacy wrapper for _extract_company_from_url."""
    return _extract_company_from_url(url)