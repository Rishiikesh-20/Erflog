# backend/agents/agent_2_market/schemas.py

"""
Agent 2: Market Intelligence - Data Schemas
Unified schemas for Jobs, Hackathons, and Market News.
"""

import uuid
from datetime import datetime, date
from typing import Optional, Literal, Union
from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Job / Hackathon Schema (Unified)
# =============================================================================

class JobSchema(BaseModel):
    """
    Unified schema for jobs and hackathons.
    Matches Supabase 'jobs' table exactly.
    """
    title: str
    company: str = "Unknown"
    location: str = ""
    link: str
    description: str = ""
    summary: str = ""
    source: str = ""
    posted_at: Optional[Union[date, datetime, str]] = None  # DB: date
    expiration_date: Optional[Union[date, datetime, str]] = None  # DB: date
    platform: str = "Unknown"
    remote_policy: Optional[str] = None
    bounty_amount: Optional[str] = None  # DB: text (not float)
    type: Literal["job", "hackathon"] = "job"

    @field_validator('summary', mode='before')
    @classmethod
    def truncate_summary(cls, v: str) -> str:
        if v and len(v) > 1000:
            return v[:1000]
        return v or ""

    @field_validator('description', mode='before')
    @classmethod
    def truncate_description(cls, v: str) -> str:
        if v and len(v) > 5000:
            return v[:5000]
        return v or ""

    def to_supabase_dict(self) -> dict:
        """Convert to Supabase-compatible dictionary (without 'id' - auto-generated)."""
        data = {
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "link": self.link,
            "description": self.description,
            "summary": self.summary,
            "source": self.source,
            "platform": self.platform,
            "type": self.type,
        }
        # posted_at: DB expects date (YYYY-MM-DD)
        if self.posted_at:
            if isinstance(self.posted_at, datetime):
                data["posted_at"] = self.posted_at.date().isoformat()
            elif isinstance(self.posted_at, date):
                data["posted_at"] = self.posted_at.isoformat()
            elif isinstance(self.posted_at, str):
                data["posted_at"] = self.posted_at[:10]  # Take YYYY-MM-DD
        # expiration_date: DB expects date (YYYY-MM-DD)
        if self.expiration_date:
            if isinstance(self.expiration_date, datetime):
                data["expiration_date"] = self.expiration_date.date().isoformat()
            elif isinstance(self.expiration_date, date):
                data["expiration_date"] = self.expiration_date.isoformat()
            elif isinstance(self.expiration_date, str):
                data["expiration_date"] = self.expiration_date[:10]
        if self.remote_policy:
            data["remote_policy"] = self.remote_policy
        # bounty_amount: DB expects text
        if self.bounty_amount:
            data["bounty_amount"] = str(self.bounty_amount)
        return data

    def to_pinecone_metadata(self) -> dict:
        """Convert to Pinecone metadata."""
        return {
            "item_id": self.link,  # Use link as unique identifier
            "type": self.type,
            "title": self.title,
            "company": self.company,
            "link": self.link,
            "summary": self.summary[:500] if self.summary else "",
            "source": self.source,
            "platform": self.platform,
        }


# =============================================================================
# Market News Schema
# =============================================================================

class MarketNewsSchema(BaseModel):
    """
    Schema for market/tech news.
    Matches Supabase 'market_news' table exactly.
    """
    title: str
    url: str
    source: str = ""
    summary: str = ""
    published_at: Optional[Union[datetime, str]] = None
    topics: list[str] = Field(default_factory=list)
    user_id: Optional[str] = None  # DB: uuid (nullable)

    @field_validator('summary', mode='before')
    @classmethod
    def truncate_summary(cls, v: str) -> str:
        if v and len(v) > 1000:
            return v[:1000]
        return v or ""

    def to_supabase_dict(self) -> dict:
        """Convert to Supabase-compatible dictionary (without 'id' - auto-generated)."""
        data = {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "summary": self.summary,
            "topics": self.topics,
        }
        if self.published_at:
            if isinstance(self.published_at, datetime):
                data["published_at"] = self.published_at.isoformat()
            elif isinstance(self.published_at, str):
                data["published_at"] = self.published_at
        if self.user_id:
            data["user_id"] = self.user_id
        return data

    def to_pinecone_metadata(self) -> dict:
        """Convert to Pinecone metadata."""
        return {
            "item_id": self.url,  # Use URL as unique identifier
            "type": "news",
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "summary": self.summary[:500] if self.summary else "",
            "topics": self.topics[:5] if self.topics else [],
        }


# =============================================================================
# Cron Execution Log Schema
# =============================================================================

class CronExecutionLog(BaseModel):
    """Schema for tracking cron execution history."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: Literal["running", "success", "partial_failure", "failed"] = "running"
    jobs_collected: int = 0
    hackathons_collected: int = 0
    news_collected: int = 0
    provider_errors: dict = Field(default_factory=dict)
    roles_processed: list[str] = Field(default_factory=list)
    skills_processed: list[str] = Field(default_factory=list)


# =============================================================================
# Provider Allocation Schema
# =============================================================================

class ProviderAllocation(BaseModel):
    """Schema for provider-role allocation."""
    jsearch: list[str] = Field(default_factory=list)
    mantiks: list[str] = Field(default_factory=list)
    serpapi: list[str] = Field(default_factory=list)

    def get_all_roles(self) -> list[str]:
        """Get all allocated roles."""
        return self.jsearch + self.mantiks + self.serpapi


# =============================================================================
# LLM Response Schemas
# =============================================================================

class OptimizedRolesResponse(BaseModel):
    """Schema for LLM role optimization response."""
    roles: list[str] = Field(max_length=5)
    reasoning: str = ""


class GeneratedQueries(BaseModel):
    """Schema for LLM-generated search queries."""
    job_queries: list[str] = Field(default_factory=list)
    hackathon_queries: list[str] = Field(default_factory=list)
    news_queries: list[str] = Field(default_factory=list)
