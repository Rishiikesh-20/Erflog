import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
ENDPOINT = "/api/market/scan"
URL = f"{BASE_URL}{ENDPOINT}"

def test_agent_2():
    print(f"\n🚀 Starting Agent 2 Test on: {URL}")
    print("--------------------------------------------------")

    try:
        # 1. Measure Response Time
        start_time = time.time()
        
        # Send POST Request (No auth needed since we are using the test endpoint)
        print("📡 Sending request...")
        response = requests.post(URL)
        
        duration = time.time() - start_time
        print(f"⏱️  Response received in {duration:.2f} seconds")

        # 2. Check Status Code
        if response.status_code == 200:
            print("✅ Status Code: 200 OK")
            
            data = response.json()
            
            # 3. Validate Response Structure
            if "status" in data and data["status"] == "success":
                result = data.get("data", {})
                stats = result.get("stats", {})
                queries = result.get("queries_used", {})
                
                print("\n📊 SCAN RESULTS SUMMARY:")
                print(f"   - User ID Used:    {data.get('user_id')}")
                print(f"   - Job Query:       {queries.get('job_query')}")
                print(f"   - Jobs Found:      {stats.get('jobs_found')} (JSearch)")
                print(f"   - Hackathons:      {stats.get('hackathons_found')} (Tavily)")
                print(f"   - News Items:      {stats.get('news_found')} (Tavily)")
                print(f"   - Vectors Saved:   {stats.get('vectors_saved')} (Pinecone)")

                # 4. Print Data Samples
                print("\n🔍 DATA SAMPLES:")
                
                # Check Jobs
                jobs = result.get("jobs", [])
                if jobs:
                    print(f"   ✅ First Job: '{jobs[0]['title']}' at '{jobs[0]['company']}'")
                    print(f"      Link: {jobs[0]['link']}")
                else:
                    print("   ⚠️  No Jobs found (Check RAPIDAPI_KEY or query)")

                # Check Hackathons
                hackathons = result.get("hackathons", [])
                if hackathons:
                    print(f"   ✅ First Hackathon: '{hackathons[0]['title']}'")
                    print(f"      Link: {hackathons[0]['link']}")
                else:
                    print("   ⚠️  No Hackathons found (Check TAVILY_API_KEY)")

                # Check News
                news = result.get("news", [])
                if news:
                    print(f"   ✅ First News: '{news[0]['title']}'")
                else:
                    print("   ℹ️  No News found (This is common if Tavily strict search is used)")

            else:
                print("❌ API returned failure status.")
                print(json.dumps(data, indent=2))

        else:
            print(f"❌ Error: Status Code {response.status_code}")
            print("Response:", response.text)

    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the server.")
        print("   -> Is 'uvicorn main:app --reload' running?")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

if __name__ == "__main__":
    test_agent_2()