# Agent 3 - The Strategist (Career Coach)

**Agent 3** allows the system to "Think". It doesn't just match keywords; it understands the semantic gap between a candidate and a target role, then builds a plan to close it.

## Features

- **Semantic Matching** - Retrieves jobs from Pinecone that semantically match the user's profile, not just keyword hits.
- **Tier Classification**:
    - **Tier A (Ready)**: >85% Match. Auto-apply recommended.
    - **Tier B (Reach)**: 40-85% Match. Learning required.
    - **Tier C (Low)**: <40% Match. Discard.
- **Gap Analysis & Roadmaps** - For Tier B jobs, it uses Gemini to identify missing skills and generates a **3-Day Micro-Learning Roadmap** with resources.

---

## Workflow

```mermaid
graph TD
    User[User Profile] -->|Vector Search| Pinecone
    Pinecone -->|Candidates| Classifier
    Classifier -->|Tier A| Apply[Ready to Apply]
    Classifier -->|Tier B| Gap[Gap Analysis]
    Gap -->|Gemini| Roadmap[Generate Learning Roadmap]
    Classifier -->|Tier C| Discord[Ignore]
```

## API usage

**Endpoint**: `/api/generate-strategy`

**Request**:
```json
{
  "query": "Full stack developer with Python and React experience"
}
```

**Response**:
Returns a "Strategy Report" containing matched jobs, their calculated Tiers, and (for Tier B) a detailed learning roadmap.
