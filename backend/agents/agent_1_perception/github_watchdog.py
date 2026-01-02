# backend/agents/agent_1_perception/github_watchdog.py

import os
import json
import base64
import google.generativeai as genai
from dotenv import load_dotenv
from github import Github

load_dotenv()

# Configure Google AI
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# Fail-safe model list
MODELS_TO_TRY = [
    "gemini-2.5-flash"
]

def get_latest_user_activity(username_or_token: str):
    """
    Scans the user's GitHub profile to find the ONE repository 
    that was updated most recently.
    """
    token = os.getenv("GITHUB_ACCESS_TOKEN")
    if not token: return None

    try:
        g = Github(token)
        user = g.get_user() # Uses the token's user
        
        # Get repos sorted by 'updated', most recent first
        # limit=1 because we only care about what you are doing RIGHT NOW
        repos = user.get_repos(sort="updated", direction="desc")
        
        latest_repo = None
        try:
            latest_repo = repos[0]
        except IndexError:
            return None

        # Get latest commit SHA to check for changes
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
    # ... (Keep your existing fetch_and_analyze_github code EXACTLY as it was in the previous step) ...
    # ... Copy the entire function from the previous "Final Smarter" version ...
    # ... Just ensure this file HAS the new get_latest_user_activity function above ...
    
    # RE-PASTING THE LOGIC FOR COMPLETENESS:
    token = os.getenv("GITHUB_ACCESS_TOKEN")
    if not token: return None

    try:
        g = Github(token)
        clean_url = github_url.rstrip("/")
        parts = clean_url.split("/")
        repo_name = f"{parts[-2]}/{parts[-1]}"
        repo = g.get_repo(repo_name)
        
        context_parts = []
        
        # 1. Dependency Files
        dependency_files = ["requirements.txt", "environment.yml", "package.json", "pyproject.toml"]
        for dep_file in dependency_files:
            try:
                file_content = repo.get_contents(dep_file)
                decoded = base64.b64decode(file_content.content).decode("utf-8")
                context_parts.append(f"--- DEPENDENCY FILE: {dep_file} ---\n{decoded[:2000]}")
            except: continue 

        # 2. Recent Commits
        commits = repo.get_commits()[:10]
        for commit in commits:
            for file in commit.files:
                if file.filename.endswith(('.py', '.js', '.ts', '.tsx', '.go', '.rs', '.java', '.cpp', '.ipynb')):
                    if file.patch:
                        context_parts.append(f"File: {file.filename}\nChange:\n{file.patch[:1500]}")
                    elif file.filename.endswith(".ipynb"):
                        context_parts.append(f"File: {file.filename} (Jupyter Notebook updated)")

        if not context_parts: return None
        full_context = "\n\n".join(context_parts)
        return _analyze_robustly(full_context)

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def _analyze_robustly(code_context: str):
    # ... (Keep existing robust analysis logic) ...
    # COPY THE _analyze_robustly function from previous step here
    prompt = f"""
    You are a Technical Skill Auditor.
    CODE CONTEXT: {code_context}
    TASK: Identify skills. Prioritize dependency files. Output JSON.
    OUTPUT JSON FORMAT: {{ "detected_skills": [ {{ "skill": "Pandas", "level": "Int", "evidence": "req.txt" }} ] }}
    """
    for model_name in MODELS_TO_TRY:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return json.loads(response.text.replace("```json", "").replace("```", "").strip())
        except: continue
    return None