# backend/agents/agent_2_market/__init__.py

"""
Agent 2: Market Intelligence & Opportunity Aggregation

A backend-only autonomous agent that runs via cron job (once per day).
Collects, normalizes, deduplicates, and persists Jobs, Hackathons, and Tech News
for all users globally.

Modules:
- service: Main service class with business logic
- tools: External API integrations (JSearch, SerpAPI, Mantiks, Tavily, NewsData.io)
- schemas: Pydantic schemas for data validation
- router: FastAPI endpoints
- cron: Cron job entry point

Usage:
    # For cron execution
    from agents.agent_2_market.cron import run_daily_market_scan
    run_daily_market_scan()
    
    # For API usage
    from agents.agent_2_market.service import market_service
    result = market_service.run_daily_scan()
"""

from .service import market_service, MarketIntelligenceService
from .router import router
from .schemas import JobSchema, MarketNewsSchema, CronExecutionLog

__all__ = [
    "market_service",
    "MarketIntelligenceService",
    "router",
    "JobSchema",
    "MarketNewsSchema",
    "CronExecutionLog",
]