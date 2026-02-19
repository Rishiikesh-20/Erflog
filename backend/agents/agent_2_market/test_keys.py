import os
import sys
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

# Setup path and load env
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

load_dotenv(backend_dir / ".env")

# ANSI Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def print_result(service, status, message=""):
    if status == "PASS":
        print(f"[{GREEN}PASS{RESET}] {service:<15} {message}")
    else:
        print(f"[{RED}FAIL{RESET}] {service:<15} {message}")

def test_gemini():
    try:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return False, "Key not found"

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content("Ping")
        if response and response.text:
            return True, "OK"
        return False, "No response"
    except Exception as e:
        return False, str(e)

def test_jsearch():
    try:
        api_key = os.getenv("RAPIDAPI_KEY")
        if not api_key:
            return False, "Key not found"

        url = "https://jsearch.p.rapidapi.com/search"
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        params = {"query": "developer", "num_pages": "1", "page": "1"}
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            return True, f"OK - Response: {response.text[:100]}..."
        elif response.status_code == 429:
            return False, f"Rate limit exceeded - {response.text[:200]}"
        elif response.status_code == 403:
            return False, f"Invalid key or subscription - {response.text[:200]}"
        return False, f"Status {response.status_code} - {response.text[:200]}"
    except Exception as e:
        return False, str(e)

def test_tavily():
    try:
        # Check raw API valid first just in case sdk issue
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return False, "Key not found"

        payload = {
            "api_key": api_key,
            "query": "test",
            "search_depth": "basic",
            "max_results": 1
        }
        response = requests.post("https://api.tavily.com/search", json=payload, timeout=10)

        if response.status_code == 200:
            return True, f"OK - Response: {response.text[:100]}..."
        return False, f"Status {response.status_code} - {response.text[:200]}"
    except Exception as e:
        return False, str(e)

def test_serpapi():
    try:
        api_key = os.getenv("SERPAPI_KEY")
        if not api_key:
            return False, "Key not found"

        params = {
            "engine": "google_jobs",
            "q": "developer",
            "api_key": api_key
        }
        response = requests.get("https://serpapi.com/search.json", params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if "error" in data:
                return False, f"Error: {data['error']} - Response: {response.text[:200]}"
            return True, f"OK - Response: {response.text[:100]}..."
        return False, f"Status {response.status_code} - {response.text[:200]}"
    except Exception as e:
        return False, str(e)

def test_mantiks():
    try:
        api_key = os.getenv("MANTIKS_API_KEY")
        if not api_key:
            return False, "Key not found"

        url = "https://api.mantiks.io/company/search"
        headers = {
            "accept": "application/json",
            "X-API-KEY": api_key
        }
        params = {"job_title": "software engineer", "limit": 1, "job_age_in_days": 30, "job_location_ids": "1269750"}
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            return True, f"OK - Response: {response.text[:100]}..."
        return False, f"Status {response.status_code} - {response.text[:500]}"
    except Exception as e:
        return False, str(e)

def test_newsdata():
    try:
        api_key = os.getenv("NEWSDATA_API_KEY")
        if not api_key:
            return False, "Key not found"

        url = "https://newsdata.io/api/1/latest"
        params = {"apikey": api_key, "q": "technology"}
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                return True, f"OK - Response: {response.text[:100]}..."
            return False, f"API Status: {data.get('status')} - {response.text[:200]}"
        return False, f"Status {response.status_code} - {response.text[:200]}"
    except Exception as e:
        return False, str(e)

def test_supabase():
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            return False, "Credentials not found"

        supabase = create_client(url, key)
        # Just check connection by a lightweight call, e.g. auth user or empty select
        # Doing a select on 'profiles' with checking existence of table
        try:
            # We just want to see if we can query. Limit 1.
            supabase.table("profiles").select("*").limit(1).execute()
            return True, "OK"
        except Exception as query_err:
            return False, f"Connection Failed: {str(query_err)}"

    except Exception as e:
        return False, str(e)

def test_pinecone():
    try:
        from pinecone import Pinecone
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            return False, "Key not found"

        pc = Pinecone(api_key=api_key)
        indexes = pc.list_indexes()
        # If no error, we are good
        return True, f"OK ({len(indexes)} indexes)"
    except Exception as e:
        return False, str(e)

def main():
    print(f"\nRunning API Key Verification Check...\n")

    # Run tests
    results = [
        ("Gemini", test_gemini()),
        ("JSearch", test_jsearch()),
        ("Tavily", test_tavily()),
        ("SerpAPI", test_serpapi()),
        ("Mantiks", test_mantiks()),
        ("NewsData", test_newsdata()),
        ("Supabase", test_supabase()),
        ("Pinecone", test_pinecone())
    ]

    output_lines = []
    output_lines.append("-" * 50)
    success_count = 0
    for service, (success, msg) in results:
        status = "PASS" if success else "FAIL"
        line = f"[{status}] {service:<15} {msg}"
        print(line)
        output_lines.append(line)
        if success:
            success_count += 1
    output_lines.append("-" * 50)
    summary = f"Summary: {success_count}/{len(results)} Services Operational"
    print(summary)
    output_lines.append(summary)

    with open("test_results_detailed.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

if __name__ == "__main__":
    main()
