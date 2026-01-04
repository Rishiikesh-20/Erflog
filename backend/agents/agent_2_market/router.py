# backend/agents/agent_2_market/router.py

from fastapi import APIRouter, Depends, HTTPException
from auth.dependencies import get_current_user
from .service import market_service

router = APIRouter(prefix="/api/market", tags=["Agent 2: Market"])

# --- PRODUCTION MODE (SECURE) ---
@router.post("/scan")
async def market_scan(user: dict = Depends(get_current_user)):
    """
    Run a hybrid market scan (Protected).
    """
    user_id = user["sub"]  # Gets real User ID from JWT
    
    try:
        print(f"[Market Router] Running market scan for user: {user_id}")
        result = market_service.run_market_scan(user_id)
        
        return {
            "status": "success",
            "user_id": user_id,
            "data": result
        }
        
    except Exception as e:
        print(f"[Market Router] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Market scan failed: {str(e)}")