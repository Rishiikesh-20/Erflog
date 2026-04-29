# Career Flow AI - Backend

A hybrid AI backend for career analysis, market aggregation, roadmap generation, resume tailoring, interviews, and coding practice.

## Project Structure

- **core/**: Shared logic and state management
  - `state.py`: LangGraph State definitions
  - `db.py`: Database connections (Supabase)
  
- **agents/**: Modular agent implementations
  - `agent_1_perception`: PDF and document analysis
  - `agent_2_market`: Market research and web scraping
  - `agent_3_strategist`: Strategic planning and recommendations
  - `agent_4_operative`: Resume tailoring and application support
  - `agent_5_mock_interview`: Voice/text interview bot
  - `agent_6_leetcode`: Problem recommendations and progress tracking
  - `worker.py`: ARQ background worker for scheduled market scan and strategist jobs

## Setup

1. Create a `.env` file from `.env.example`:
   \`\`\`bash
   cp .env.example .env
   \`\`\`

2. Install dependencies:
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`

3. Set up your API keys in \`.env\`

4. Run the API:
   \`\`\`bash
   python main.py
   \`\`\`

5. Run the worker for scheduled background jobs:
   \`\`\`bash
   arq worker.WorkerSettings
   \`\`\`

## API Endpoints

- \`GET /\`: API overview
- \`GET /health\`: Health check
- \`GET /api/me\`: Current authenticated user
- \`/api/perception/*\`: Resume, onboarding, profile, GitHub sync
- \`/api/market/*\`: Market scan and stats
- \`/api/strategist/*\`: Today data, refresh, dashboard, saved-job roadmap helpers
- \`/agent4/*\`: Resume tailoring and application assistance
- \`/api/interview/*\`: Mock interview flows
- \`/api/leetcode/*\`: Problem recommendations and progress

## Technologies

- FastAPI: Web framework
- LangGraph: Agent orchestration
- Langchain: LLM integration
- Google Generative AI: AI models
- Supabase: Database backend
- Tavily: Web search capability
