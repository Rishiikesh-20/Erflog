# backend/agents/agent_2_market/cron.py

"""
Agent 2: Market Intelligence - Cron Job Entry Point

This module provides the entry point for the daily cron job execution.
It should be called once per day via a scheduler (e.g., cron, systemd timer,
cloud scheduler, etc.)

Usage:
    # Direct execution
    python -m agents.agent_2_market.cron
    
    # Or from project root
    python backend/agents/agent_2_market/cron.py
    
    # Or import and call
    from agents.agent_2_market.cron import run_daily_market_scan
    run_daily_market_scan()

Execution Guarantees:
- Idempotent (safe re-runs)
- Provider failures do not stop the entire run
- Structured logging only (no UI output)
- Deterministic and repeatable
"""

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

# Ensure the backend directory is in the path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Load environment variables before any other imports
from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")


def run_daily_market_scan() -> dict:
    """
    Execute the daily market intelligence scan.
    
    This function:
    1. Initializes the Market Intelligence Service
    2. Runs the daily scan
    3. Returns structured results
    
    Returns:
        Dictionary with scan results and statistics
    """
    from agents.agent_2_market.service import MarketIntelligenceService
    
    print("=" * 70)
    print("AGENT 2: MARKET INTELLIGENCE - DAILY CRON JOB")
    print(f"Execution Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)
    
    try:
        # Initialize service
        service = MarketIntelligenceService()
        
        # Run daily scan
        result = service.run_daily_scan()
        
        # Log results
        print("\n" + "=" * 70)
        print("EXECUTION SUMMARY")
        print("=" * 70)
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Jobs Stored: {result.get('jobs_stored', 0)}")
        print(f"Hackathons Stored: {result.get('hackathons_stored', 0)}")
        print(f"News Stored: {result.get('news_stored', 0)}")
        print(f"Vectors Stored: {result.get('vectors_stored', 0)}")
        
        if result.get('provider_errors'):
            print(f"\nProvider Errors:")
            for provider, error in result['provider_errors'].items():
                print(f"  - {provider}: {error}")
        
        print("=" * 70)
        
        return result
        
    except Exception as e:
        error_result = {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        print(f"\nCRITICAL ERROR: {str(e)}")
        return error_result


def main():
    """Main entry point for CLI execution."""
    result = run_daily_market_scan()
    
    # Exit with appropriate code
    if result.get("status") == "failed":
        sys.exit(1)
    elif result.get("status") == "partial_success":
        sys.exit(0)  # Partial success is still a success
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
