# backend/auth/dependencies.py
"""
JWT verification dependency for FastAPI
Verifies Supabase JWT tokens using RS256 algorithm
"""

from fastapi import Header, HTTPException, status
from jose import jwt
import httpx

SUPABASE_PROJECT_URL = "https://wbdlwopaghndjeknrbrm.supabase.co"
ALGORITHMS = ["RS256"]
AUDIENCE = "authenticated"

_cached_keys = None


async def get_jwks():
    """
    Fetch and cache JWKS (JSON Web Key Set) from Supabase.
    Keys are cached to avoid repeated network calls.
    """
    global _cached_keys
    if _cached_keys:
        return _cached_keys

    async with httpx.AsyncClient() as client:
        res = await client.get(f"{SUPABASE_PROJECT_URL}/auth/v1/keys")
        _cached_keys = res.json()["keys"]
        return _cached_keys


async def get_current_user(authorization: str = Header(None)):
    """
    FastAPI dependency to verify JWT and extract user info.
    
    Usage:
        @app.get("/protected")
        async def protected_route(user=Depends(get_current_user)):
            return {"user_id": user["sub"]}
    
    Returns:
        dict: JWT payload containing sub, email, app_metadata, etc.
    
    Raises:
        HTTPException: 401 if token is missing, invalid, or expired
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header"
        )

    try:
        token = authorization.split(" ")[1]
        jwks = await get_jwks()

        payload = jwt.decode(
            token,
            jwks,
            algorithms=ALGORITHMS,
            audience=AUDIENCE,
        )

        return payload  # contains sub, email, provider, etc.

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
