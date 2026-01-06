"""
Agent 1 Perception - GitHub Watchdog (Event Stream Edition)
Analyzes GitHub user activity to verify skills using code evidence from recent commits.

This module scans a user's PUBLIC activity feed (Push Events) to extract
code patches and analyze them for technical skills.
"""

import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from github import Github

# --- LANGCHAIN IMPORTS ---
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

load_dotenv()

# File extensions we care about for skill analysis
CODE_EXTENSIONS = (
    '.py', '.js', '.ts', '.tsx', '.jsx',
    '.go', '.rs', '.java', '.cpp', '.c', '.h',
    '.rb', '.php', '.swift', '.kt', '.scala',
    '.sql', '.graphql', '.proto',
    '.yaml', '.yml', '.json', '.toml',
    '.sh', '.bash', '.zsh',
    '.ipynb', '.md'
)


def fetch_user_recent_activity(github_username: str, max_events: int = 10) -> Optional[Dict[str, Any]]:
    """
    Fetches recent public activity (Push Events) for a GitHub user
    and extracts code patches from their commits.
    
    Args:
        github_username: GitHub username to scan (e.g., "torvalds")
        max_events: Maximum number of events to process (default: 10)
    
    Returns:
        Dict with:
            - recent_code_context: Combined code patches for analysis
            - latest_commit_sha: SHA of the most recent commit (for caching)
            - repos_touched: List of repositories with activity
        Or None if no activity found
    """
    # === LIMITS TO PREVENT EXCESSIVE LLM COSTS ===
    MAX_CONTEXT_CHARS = 15000    # Max total context size (~15KB, ~4000 tokens)
    MAX_COMMITS_PER_REPO = 3      # Only analyze 3 most recent commits per repo
    MAX_FILES_PER_COMMIT = 5      # Only analyze 5 files per commit
    MAX_PATCH_SIZE = 1500         # Max chars per file patch
    
    token = os.getenv("GITHUB_ACCESS_TOKEN")
    if not token:
        print("⚠️ GITHUB_ACCESS_TOKEN missing - cannot fetch user activity")
        return None

    try:
        g = Github(token)
        user = g.get_user(github_username)
        
        # Fetch public events
        events = user.get_public_events()
        
        context_parts = []
        repos_touched = set()
        latest_commit_sha = None
        events_processed = 0
        current_context_size = 0
        
        for event in events:
            if events_processed >= max_events:
                break
            
            # Check if we've hit the context limit
            if current_context_size >= MAX_CONTEXT_CHARS:
                print(f"📊 Context limit reached ({current_context_size} chars), stopping collection")
                break
                
            # Only process PushEvents (commits)
            if event.type != "PushEvent":
                continue
                
            events_processed += 1
            repo_name = event.repo.name
            repos_touched.add(repo_name)
            
            payload = event.payload
            commits = payload.get("commits", [])
            
            # FALLBACK: If commits array is empty (common for web UI edits, merges, squashes),
            # fetch recent commits directly from the repository
            if not commits:
                print(f"📦 PushEvent has empty commits payload, fetching from repo: {repo_name}")
                try:
                    repo = g.get_repo(repo_name)
                    # Get limited recent commits from this repo
                    recent_commits = list(repo.get_commits()[:MAX_COMMITS_PER_REPO])
                    
                    for commit in recent_commits:
                        if current_context_size >= MAX_CONTEXT_CHARS:
                            break
                            
                        commit_sha = commit.sha
                        commit_message = commit.commit.message or ""
                        
                        # Track latest SHA for caching
                        if latest_commit_sha is None:
                            latest_commit_sha = commit_sha
                        
                        files_processed = 0
                        for file in commit.files:
                            if files_processed >= MAX_FILES_PER_COMMIT:
                                break
                            if current_context_size >= MAX_CONTEXT_CHARS:
                                break
                                
                            # Filter by code file extensions
                            if not file.filename.endswith(CODE_EXTENSIONS):
                                continue
                                
                            # Get the patch (diff)
                            if file.patch:
                                patch_text = (
                                    f"--- REPO: {repo_name} | FILE: {file.filename} ---\n"
                                    f"Commit: {commit_message[:100]}\n"
                                    f"Patch:\n{file.patch[:MAX_PATCH_SIZE]}"
                                )
                                context_parts.append(patch_text)
                                current_context_size += len(patch_text)
                                files_processed += 1
                            elif file.filename.endswith(".ipynb"):
                                nb_text = (
                                    f"--- REPO: {repo_name} | FILE: {file.filename} ---\n"
                                    f"Jupyter Notebook updated in commit: {commit_message[:100]}"
                                )
                                context_parts.append(nb_text)
                                current_context_size += len(nb_text)
                                files_processed += 1
                                
                except Exception as e:
                    print(f"⚠️ Could not fetch repo commits for {repo_name}: {e}")
                continue  # Move to next event after processing fallback
            
            # Normal flow: process commits from payload
            commits_processed = 0
            for commit_data in commits:
                if commits_processed >= MAX_COMMITS_PER_REPO:
                    break
                if current_context_size >= MAX_CONTEXT_CHARS:
                    break
                    
                commits_processed += 1
                commit_sha = commit_data.get("sha")
                commit_message = commit_data.get("message", "")
                
                # Track latest SHA for caching
                if latest_commit_sha is None:
                    latest_commit_sha = commit_sha
                
                # Try to get the full commit with file patches
                try:
                    repo = g.get_repo(repo_name)
                    full_commit = repo.get_commit(commit_sha)
                    
                    files_processed = 0
                    for file in full_commit.files:
                        if files_processed >= MAX_FILES_PER_COMMIT:
                            break
                        if current_context_size >= MAX_CONTEXT_CHARS:
                            break
                            
                        # Filter by code file extensions
                        if not file.filename.endswith(CODE_EXTENSIONS):
                            continue
                            
                        # Get the patch (diff)
                        if file.patch:
                            patch_text = (
                                f"--- REPO: {repo_name} | FILE: {file.filename} ---\n"
                                f"Commit: {commit_message[:100]}\n"
                                f"Patch:\n{file.patch[:MAX_PATCH_SIZE]}"
                            )
                            context_parts.append(patch_text)
                            current_context_size += len(patch_text)
                            files_processed += 1
                        elif file.filename.endswith(".ipynb"):
                            nb_text = (
                                f"--- REPO: {repo_name} | FILE: {file.filename} ---\n"
                                f"Jupyter Notebook updated in commit: {commit_message[:100]}"
                            )
                            context_parts.append(nb_text)
                            current_context_size += len(nb_text)
                            files_processed += 1
                            
                except Exception as e:
                    # Some commits might be in private repos or deleted
                    print(f"⚠️ Could not fetch commit {commit_sha[:7]}: {e}")
                    continue
        
        if not context_parts:
            print(f"⚠️ No code activity found for user: {github_username}")
            return None
        
        # Combine all patches into analysis context
        recent_code_context = "\n\n".join(context_parts)
        
        return {
            "recent_code_context": recent_code_context,
            "latest_commit_sha": latest_commit_sha,
            "repos_touched": list(repos_touched),
            "events_analyzed": events_processed
        }
        
    except Exception as e:
        print(f"❌ GitHub Events API Error: {e}")
        return None


def get_latest_commit_sha(github_username: str) -> Optional[str]:
    """
    Quick check to get just the latest commit SHA without full analysis.
    Used for efficient polling to detect new activity.
    """
    token = os.getenv("GITHUB_ACCESS_TOKEN")
    if not token:
        return None

    try:
        g = Github(token)
        user = g.get_user(github_username)
        events = user.get_public_events()
        
        for event in events:
            if event.type == "PushEvent":
                commits = event.payload.get("commits", [])
                if commits:
                    return commits[0].get("sha")
                
                # FALLBACK: If commits array is empty, fetch latest from repo
                repo_name = event.repo.name
                try:
                    repo = g.get_repo(repo_name)
                    latest_commit = list(repo.get_commits()[:1])
                    if latest_commit:
                        return latest_commit[0].sha
                except Exception as e:
                    print(f"⚠️ Could not fetch latest SHA from {repo_name}: {e}")
                    continue
        
        return None
        
    except Exception as e:
        print(f"❌ GitHub SHA Check Error: {e}")
        return None



def analyze_code_context(code_context: str) -> Optional[Dict[str, Any]]:
    """
    Uses LangChain + Gemini to extract skills from code context.
    
    Args:
        code_context: Combined code patches and file changes
        
    Returns:
        Dict with detected_skills list, each containing skill, level, evidence
    """
    import json
    import re
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️ GEMINI_API_KEY missing")
        return None
    
    # 1. Setup LLM with stricter settings
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.1,  # Lower temperature for more deterministic JSON output
        google_api_key=api_key
    )
    
    # 2. Strict prompt that ONLY returns JSON
    strict_prompt = """Analyze the code patches below and extract technical skills.

CODE PATCHES:
{code_context}

RESPOND WITH ONLY A JSON OBJECT. NO MARKDOWN. NO EXPLANATION. NO TEXT BEFORE OR AFTER.

Required JSON format:
{{"detected_skills": [
  {{"skill": "Python", "level": "advanced", "evidence": "FastAPI async patterns"}},
  {{"skill": "React", "level": "intermediate", "evidence": "Component hooks usage"}}
]}}

Rules:
- Return ONLY valid JSON, nothing else
- "skill": Technology name (Python, React, Docker, etc.)
- "level": One of "beginner", "intermediate", "advanced"
- "evidence": Brief 5-10 word description
- Maximum 10 skills
- Focus on concrete technologies visible in code"""

    try:
        print("[LangChain] Analyzing GitHub Activity Code Context...")
        
        # Direct LLM call without parser (more control)
        response = llm.invoke(strict_prompt.format(code_context=code_context[:12000]))
        raw_text = response.content.strip()
        
        # Try to parse as JSON directly
        try:
            result = json.loads(raw_text)
            if "detected_skills" in result:
                print(f"[LangChain] ✓ Detected {len(result['detected_skills'])} skills")
                return result
        except json.JSONDecodeError:
            pass
        
        # Fallback: Extract JSON from markdown code blocks if present
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_text, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                if "detected_skills" in result:
                    print(f"[LangChain] ✓ Extracted {len(result['detected_skills'])} skills from markdown")
                    return result
            except json.JSONDecodeError:
                pass
        
        # Final fallback: Find any JSON object in response
        json_match = re.search(r'\{[^{}]*"detected_skills"\s*:\s*\[.*?\]\s*\}', raw_text, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                print(f"[LangChain] ✓ Recovered {len(result.get('detected_skills', []))} skills")
                return result
            except json.JSONDecodeError:
                pass
        
        print(f"[LangChain] ⚠️ Could not parse JSON from response (length: {len(raw_text)})")
        return None
        
    except Exception as e:
        print(f"[LangChain] Analysis Error: {e}")
        return None


def extract_username_from_url(github_url: str) -> Optional[str]:
    """
    Extracts GitHub username from various URL formats.
    
    Supports:
        - https://github.com/username
        - https://github.com/username/
        - github.com/username
        - https://www.github.com/username
    
    Returns:
        Username string or None if invalid
    """
    if not github_url:
        return None
        
    # Clean the URL
    url = github_url.strip().rstrip("/")
    
    # Remove protocol and www
    url = url.replace("https://", "").replace("http://", "").replace("www.", "")
    
    # Should now be: github.com/username or github.com/username/repo
    if not url.startswith("github.com/"):
        return None
    
    parts = url.replace("github.com/", "").split("/")
    
    if parts and parts[0]:
        return parts[0]
    
    return None


# ============================================================================
# LEGACY FUNCTIONS (kept for backward compatibility)
# ============================================================================

def get_latest_user_activity(username_or_token: str):
    """
    LEGACY: Scans the authenticated user's repos for most recent activity.
    Kept for backward compatibility with existing code.
    """
    token = os.getenv("GITHUB_ACCESS_TOKEN")
    if not token: 
        return None

    try:
        g = Github(token)
        user = g.get_user()
        
        repos = user.get_repos(sort="updated", direction="desc")
        
        latest_repo = None
        try:
            latest_repo = repos[0]
        except IndexError:
            return None

        try:
            commits = latest_repo.get_commits()
            latest_commit_sha = commits[0].sha
        except:
            latest_commit_sha = "unknown"

        return {
            "repo_name": latest_repo.full_name,
            "repo_url": latest_repo.html_url,
            "last_updated": latest_repo.updated_at.isoformat(),
            "latest_commit_sha": latest_commit_sha
        }

    except Exception as e:
        print(f"❌ GitHub Activity Scan Error: {e}")
        return None


def fetch_and_analyze_github(github_url: str):
    """
    LEGACY: Analyzes a specific repository URL.
    Kept for backward compatibility.
    
    For new code, use fetch_user_recent_activity() + analyze_code_context() instead.
    """
    username = extract_username_from_url(github_url)
    
    if username:
        # Use new event-based approach
        activity = fetch_user_recent_activity(username)
        if activity and activity.get("recent_code_context"):
            return analyze_code_context(activity["recent_code_context"])
    
    # Fallback: Try to analyze as a repo URL
    token = os.getenv("GITHUB_ACCESS_TOKEN")
    if not token: 
        return None

    try:
        import base64
        g = Github(token)
        clean_url = github_url.rstrip("/")
        parts = clean_url.split("/")
        
        # Check if it's a repo URL (has at least user/repo)
        if len(parts) < 2:
            return None
            
        repo_name = f"{parts[-2]}/{parts[-1]}"
        repo = g.get_repo(repo_name)
        
        context_parts = []
        
        # Dependency Files
        dependency_files = ["requirements.txt", "environment.yml", "package.json", "pyproject.toml", "go.mod"]
        for dep_file in dependency_files:
            try:
                file_content = repo.get_contents(dep_file)
                decoded = base64.b64decode(file_content.content).decode("utf-8")
                context_parts.append(f"--- DEPENDENCY FILE: {dep_file} ---\n{decoded[:2000]}")
            except: 
                continue 

        # Recent Commits
        commits = repo.get_commits()[:10]
        for commit in commits:
            for file in commit.files:
                if file.filename.endswith(CODE_EXTENSIONS):
                    if file.patch:
                        context_parts.append(f"File: {file.filename}\nChange:\n{file.patch[:1500]}")

        if not context_parts:
            return None
            
        full_context = "\n\n".join(context_parts)
        return analyze_code_context(full_context)

    except Exception as e:
        print(f"❌ GitHub Fetch Error: {e}")
        return None
