Here is a professional, comprehensive `README.md` for **Agent 2: Market Sentinel**. You can place this file in the `backend/agents/agent_2_market/` directory so your team (or future you) understands exactly how it works.

---

# 📡 Agent 2: Market Sentinel

**Market Sentinel** is an autonomous intelligence agent designed to scan the external job market in real-time. It uses a **Hybrid Search Strategy** to fetch jobs, hackathons, and industry news instantly, store them in a database, and generate vector embeddings for semantic matching.

---

## 🚀 Features

* **Instant Job Search:** Fetches real-time job listings from across the web (LinkedIn, Indeed, Glassdoor, etc.) using JSearch.
* **Hackathon Discovery:** Scrapes major platforms (Devpost, Devfolio, Gitcoin) for active hackathons with prize bounties.
* **News Aggregation:** Retrieves the latest tech news relevant to the user's top skills.
* **Vector Embeddings:** Automatically generates AI embeddings for every job/hackathon and stores them in **Pinecone** for semantic search (RAG).
* **Smart Caching:** Saves all results to **Supabase** to build a persistent historical dataset.
* **Deduplication:** Prevents duplicate entries using unique link constraints.

---

## 🛠️ Tech Stack & APIs

| Component | Technology / Provider | Purpose |
| --- | --- | --- |
| **Jobs API** | **JSearch (RapidAPI)** | Primary source for real-time job listings. |
| **Search API** | **Tavily** | Search engine optimized for LLMs (used for Hackathons & News). |
| **Database** | **Supabase (PostgreSQL)** | Persistent storage for structured data. |
| **Vector DB** | **Pinecone** | Stores vector embeddings for semantic matching. |
| **Embeddings** | **Google Gemini** | Generates 768-dimension vectors via LangChain. |
| **Backend** | **FastAPI** | REST API framework. |

---

## ⚙️ Architecture

The agent follows a **Linear Execution Flow**:

1. **User Trigger:** The frontend sends a `POST /scan` request with the User's ID (via JWT).
2. **Profile Analysis:** The agent fetches the user's **Top Skill** and **Verified Skills** from Supabase.
3. **Smart Query Generation:**
* *Job Query:* "Junior {Skill} Developer"
* *Hackathon Query:* "{Skill} Hackathon 2026"
* *News Query:* "Latest news in {Skill} ecosystem"


4. **Parallel Execution:**
* **Tool A:** Calls JSearch API for jobs.
* **Tool B:** Calls Tavily API for hackathons.
* **Tool C:** Calls Tavily API for news.


5. **Data Processing:**
* **Storage:** Upserts clean data into Supabase (`jobs`, `market_news`).
* **Vectorization:** Generates embeddings for jobs/hackathons and pushes to Pinecone.


6. **Response:** Returns the structured JSON data to the user immediately.

---

## 📦 Setup & Configuration

### 1. Environment Variables

Ensure your `.env` file contains these keys:

```ini
# Database
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="ey..."  # Required for backend writes

# APIs
RAPIDAPI_KEY="your_rapidapi_key"    # For JSearch
TAVILY_API_KEY="tvly-..."           # For Hackathons/News
GEMINI_API_KEY="AIza..."            # For Embeddings

# Vector DB
PINECONE_API_KEY="pc..."
PINECONE_INDEX_NAME="career-flow-jobs"

```

### 2. Database Schema (Supabase)

The agent relies on two specific tables. Ensure these exist in your SQL Editor:

**Table: `jobs**`

```sql
create table public.jobs (
  id bigint generated always as identity primary key,
  title text not null,
  company text not null,
  link text unique,  -- Must be UNIQUE for deduplication
  summary text,
  type text,         -- 'job' or 'hackathon'
  bounty_amount text, -- For hackathons
  location text,
  platform text,
  created_at timestamp with time zone default timezone('utc'::text, now())
);

```

**Table: `market_news**`

```sql
create table public.market_news (
  id bigint generated always as identity primary key,
  title text not null,
  url text unique,   -- Must be UNIQUE for deduplication
  summary text,
  source text,
  published_at timestamp with time zone,
  created_at timestamp with time zone default timezone('utc'::text, now())
);

```

---

## 🔌 API Usage

### Endpoint: `POST /api/market/scan`

Triggers a fresh scan based on the logged-in user's profile.

**Headers:**

```http
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

```

**Response Example:**

```json
{
  "status": "success",
  "user_id": "550e8400-e29b...",
  "data": {
    "jobs": [
      {
        "title": "Junior Python Developer",
        "company": "Tech Corp",
        "link": "https://...",
        "type": "job"
      }
    ],
    "hackathons": [
      {
        "title": "Global AI Hackathon 2026",
        "link": "https://devpost.com/...",
        "bounty_amount": "50000.0",
        "type": "hackathon"
      }
    ],
    "stats": {
      "jobs_found": 10,
      "hackathons_found": 5,
      "vectors_saved": 15
    }
  }
}

```

---

## 📂 Project Structure

```text
backend/agents/agent_2_market/
├── router.py      # API Endpoint definitions (Controller)
├── service.py     # Business Logic (Orchestrator)
├── tools.py       # External API integrations (JSearch, Tavily, LangChain)
└── __init__.py

```

---

## 🧪 Testing

You can test this agent in isolation using the test script provided in the root directory:

```bash
python test_agent2.py

```

This script bypasses authentication (if configured) and prints a summary of the scan results to the console.