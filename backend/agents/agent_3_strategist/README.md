# Agent 3 - The Strategist (Career Coach)

**Agent 3** allows the system to "Think". It doesn't just match keywords; it understands the semantic gap between a candidate and a target role, then builds a plan to close it.

## Features

- **Semantic Matching** - Retrieves jobs from Pinecone that semantically match the user's profile, not just keyword hits.
- **Tier Classification**:
  - **Tier A (Ready)**: ≥80% Match. No roadmap needed.
  - **Tier B (Improvement)**: <80% Match. Learning roadmap generated.
- **Gap Analysis & Roadmaps** - For jobs below 80% match, uses Gemini to identify missing skills and generates a **3-Day Learning Roadmap** with DAG visualization.
- **Application Text Generation** - Pre-generates copy-paste ready responses for ALL jobs (cover letters, why join, etc.)

---

## Architecture

### Orchestration with LangGraph

The new orchestrator (`orchestrator.py`) uses LangGraph to coordinate:

1. **Job Enrichment Node**: For each of 10 matched jobs:

   - If score < 80%: Generate learning roadmap (DAG with nodes/edges)
   - For ALL jobs: Generate application text (cover letter, why join, etc.)

2. **Finalization Node**: Compile stats and prepare data for storage

### Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     DAILY CRON JOB                                  │
│                                                                     │
│  For each user:                                                     │
│  ┌─────────────────┐     ┌─────────────────┐     ┌───────────────┐ │
│  │  Fetch User     │────▶│  Query Pinecone │────▶│  10 Jobs      │ │
│  │  Embedding      │     │  (3 namespaces) │     │  10 Hackathons│ │
│  └─────────────────┘     └─────────────────┘     │  5 News       │ │
│                                                   └───────┬───────┘ │
│                                                           │         │
│                          ┌────────────────────────────────┘         │
│                          ▼                                          │
│                ┌──────────────────────┐                             │
│                │   ORCHESTRATOR       │                             │
│                │   (LangGraph)        │                             │
│                │                      │                             │
│                │  For each job:       │                             │
│                │  ├─ score < 80%?     │                             │
│                │  │  └─ Gen Roadmap   │                             │
│                │  └─ Gen App Text     │                             │
│                └──────────┬───────────┘                             │
│                           │                                         │
│                           ▼                                         │
│                ┌──────────────────────┐                             │
│                │   Store in          │                             │
│                │   today_data table  │                             │
│                └──────────────────────┘                             │
│                                                                     │
│  ✅ ALL PROCESSING COMPLETE - NO FURTHER PROCESSING UNTIL NEXT DAY  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Structure

### today_data JSON

```json
{
  "jobs": [
    {
      "id": "123",
      "score": 0.75,
      "title": "Software Engineer",
      "company": "TechCorp",
      "needs_improvement": true,
      "roadmap": {
        "missing_skills": ["Kubernetes", "GraphQL"],
        "graph": {
          "nodes": [
            {"id": "n1", "label": "K8s Basics", "day": 1, "type": "concept"},
            {"id": "n2", "label": "Deploy App", "day": 2, "type": "practice"},
            {"id": "n3", "label": "CI/CD Pipeline", "day": 3, "type": "project"}
          ],
          "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"}
          ]
        },
        "resources": {...}
      },
      "application_text": {
        "why_this_company": "...",
        "why_this_role": "...",
        "cover_letter_opening": "...",
        "cover_letter_body": "...",
        "cover_letter_closing": "...",
        "key_achievements": ["...", "..."],
        "questions_for_interviewer": ["...", "..."]
      }
    }
  ],
  "hackathons": [...],
  "news": [...],
  "hot_skills": [...],
  "stats": {
    "jobs_count": 10,
    "jobs_with_roadmap": 6,
    "high_match_jobs": 4
  }
}
```

---

## API Endpoints

### Get All Jobs (with roadmaps & application text)

```
GET /api/strategist/jobs
Authorization: Bearer <jwt>

Response:
{
  "status": "success",
  "jobs": [...],
  "count": 10,
  "stats": {
    "high_match": 4,
    "needs_improvement": 6,
    "with_roadmap": 6
  }
}
```

### Get Roadmap for Specific Job

```
GET /api/strategist/jobs/{job_id}/roadmap
Authorization: Bearer <jwt>
```

### Get Application Text for Specific Job

```
GET /api/strategist/jobs/{job_id}/application
Authorization: Bearer <jwt>
```

### Trigger Cron (Admin)

```
POST /api/strategist/cron
X-Cron-Secret: <secret>
```

---

## Running the Cron Job

```bash
# Direct execution
python -m agents.agent_3_strategist.cron

# Or via FastAPI endpoint (requires CRON_SECRET)
curl -X POST http://localhost:8000/api/strategist/cron \
  -H "X-Cron-Secret: your-secret"
```
