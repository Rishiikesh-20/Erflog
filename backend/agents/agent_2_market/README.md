# 📡 Agent 2: Market Intelligence & Opportunity Aggregation

**Market Intelligence Agent** is an autonomous backend agent that runs via cron job (once per day). It collects, normalizes, deduplicates, and persists Jobs, Hackathons, and Tech/Market News for **all users globally**.

---

## 🎯 Core Responsibilities

- **Global Market Scan:** Analyze all users' target roles and skills
- **Multi-Provider Aggregation:** Query JSearch, Mantiks, SerpAPI, Tavily, and NewsData.io
- **Data Normalization:** Unified schemas for jobs, hackathons, and news
- **Intelligent Storage:** Supabase (SQL) + Pinecone (Vector) with consistent IDs
- **Fair Coverage:** Serve all users equally without personalization bias

---

## 📊 Daily Collection Targets

| Category       | Target Count | Providers                    |
| -------------- | ------------ | ---------------------------- |
| **Jobs**       | 30           | JSearch, Mantiks, SerpAPI    |
| **Hackathons** | 10-20        | Tavily, SerpAPI              |
| **News**       | 10           | Tavily, NewsData.io, SerpAPI |

---

## 🛠️ Tech Stack & APIs

| Component      | Technology              | Purpose                              |
| -------------- | ----------------------- | ------------------------------------ |
| **Jobs API**   | JSearch (RapidAPI)      | Primary job listings                 |
| **Jobs API**   | Mantiks                 | Company & job intelligence           |
| **Jobs API**   | SerpAPI (Google Jobs)   | Specialized roles                    |
| **Hackathons** | Tavily                  | Hackathon discovery                  |
| **Hackathons** | SerpAPI (Google Search) | Platform-specific search             |
| **News**       | Tavily                  | Tech news aggregation                |
| **News**       | NewsData.io             | Industry news                        |
| **News**       | SerpAPI (Google News)   | Trending articles                    |
| **LLM**        | Google Gemini           | Role optimization & query generation |
| **Database**   | Supabase (PostgreSQL)   | Persistent storage                   |
| **Vector DB**  | Pinecone                | Semantic embeddings                  |
| **Embeddings** | Google GenAI            | 768-dimension vectors                |

⚠️ **Apify is NOT used** in this agent.

---

## ⚙️ Execution Flow

### Daily Cron Job Steps

```
Step 1: Aggregate Global User Context
    └── Collect all users' target_roles and skills from profiles
    └── Create global unique role and skill sets

Step 2: Role Optimization via LLM (Gemini)
    └── Select at most 5 distinct roles for maximum coverage
    └── Prefer high-demand roles with good hiring volume

Step 3: Provider Allocation Strategy
    └── JSearch → Frontend, Backend, Web, Mobile roles
    └── Mantiks → Security, Enterprise, Cloud roles
    └── SerpAPI → Web3, AI/ML, Data roles

Step 4: Job Collection (30 jobs)
    └── 10 jobs per provider
    └── LLM-generated search queries
    └── Normalize to unified schema

Step 5: Hackathon Collection (10-20)
    └── Tavily + SerpAPI
    └── Target: Devpost, Devfolio, MLH, Gitcoin
    └── Extract prize/bounty amounts

Step 6: News Collection (10)
    └── Tavily + NewsData.io + SerpAPI
    └── Tech/Market trends
    └── Industry news

Step 7-9: Normalization & Deduplication
    └── Generate consistent UUIDs
    └── Deduplicate by link (jobs) or url (news)
    └── Same ID in Supabase AND Pinecone

Step 10: Storage
    └── Supabase: jobs, market_news tables
    └── Pinecone: __default__ namespace
```

---

## 📁 Module Structure

```
agent_2_market/
├── __init__.py      # Package exports
├── cron.py          # Cron job entry point
├── router.py        # FastAPI endpoints
├── schemas.py       # Pydantic data schemas
├── service.py       # Main business logic
├── tools.py         # External API integrations
└── README.md        # This file
```

---

## 🗃️ Database Schemas

### Jobs Table (jobs & hackathons)

```sql
jobs (
  id UUID PRIMARY KEY,
  title TEXT NOT NULL,
  company TEXT,
  location TEXT,
  link TEXT UNIQUE NOT NULL,
  description TEXT,
  summary TEXT,
  source TEXT,
  posted_at TIMESTAMPTZ,
  expiration_date TIMESTAMPTZ,
  platform TEXT,
  remote_policy TEXT,
  bounty_amount NUMERIC,
  type TEXT NOT NULL,  -- "job" | "hackathon"
  created_at TIMESTAMPTZ DEFAULT NOW()
)
```

### Market News Table

```sql
market_news (
  id UUID PRIMARY KEY,
  title TEXT NOT NULL,
  url TEXT UNIQUE NOT NULL,
  source TEXT,
  summary TEXT,
  published_at TIMESTAMPTZ,
  topics TEXT[],
  created_at TIMESTAMPTZ DEFAULT NOW()
)
```

---

## 🚀 Usage

### Cron Job (Recommended)

```bash
# Direct execution
python -m agents.agent_2_market.cron

# Or from backend directory
cd backend
python -m agents.agent_2_market.cron
```

### API Endpoint

```bash
# Daily cron (internal, requires CRON_SECRET)
curl -X POST http://localhost:8000/api/market/cron \
  -H "X-Cron-Secret: your-secret-key"

# User-triggered scan (requires JWT)
curl -X POST http://localhost:8000/api/market/scan \
  -H "Authorization: Bearer <jwt_token>"

# Get statistics
curl http://localhost:8000/api/market/stats
```

### Python Import

```python
from agents.agent_2_market.cron import run_daily_market_scan
from agents.agent_2_market.service import market_service

# Run daily scan
result = run_daily_market_scan()

# Or use service directly
result = market_service.run_daily_scan()
```

---

## 🔑 Environment Variables

```env
# Required
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
GEMINI_API_KEY=AIza...

# Job Providers
RAPIDAPI_KEY=xxx           # For JSearch
SERPAPI_KEY=xxx            # For SerpAPI
MANTIKS_API_KEY=xxx        # For Mantiks

# News/Hackathon Providers
TAVILY_API_KEY=tvly-xxx
NEWSDATA_API_KEY=xxx

# Vector Database
PINECONE_API_KEY=xxx
PINECONE_INDEX_NAME=career-flow-jobs

# Security (Optional)
CRON_SECRET=your-cron-secret
```

---

## ✅ Execution Guarantees

| Guarantee             | Description                               |
| --------------------- | ----------------------------------------- |
| ✅ Idempotent         | Safe to re-run multiple times             |
| ✅ Provider Isolation | One provider failure doesn't stop the run |
| ✅ Deduplication      | No duplicate entries by link/url          |
| ✅ Consistent IDs     | Same UUID in Supabase AND Pinecone        |
| ✅ Fair Coverage      | Global scan for all users                 |
| ✅ Structured Logs    | Silent execution with structured output   |

---

## 📈 Monitoring

The cron job returns structured results:

```json
{
  "status": "success",
  "jobs_stored": 30,
  "hackathons_stored": 15,
  "news_stored": 10,
  "vectors_stored": 55,
  "provider_errors": {},
  "timestamp": "2026-01-04T00:00:00Z"
}
```

Possible statuses:

- `success`: All operations completed
- `partial_success`: Some providers failed but data was collected
- `failed`: Critical error occurred

---

## 🔧 Cron Schedule (Example)

```cron
# Run daily at 2 AM UTC
0 2 * * * cd /path/to/backend && python -m agents.agent_2_market.cron >> /var/log/market_agent.log 2>&1
```

---

## 📝 Notes

1. **Rate Limits:** Each provider has rate limits. The agent distributes queries to stay within limits.
2. **LLM Usage:** Gemini is only used for query generation and role optimization, never for fetching external data.
3. **No User Personalization:** This agent serves all users equally with a global market scan.
4. **Vector Namespace:** All vectors are stored in the `__default__` namespace with `type` metadata for filtering.
