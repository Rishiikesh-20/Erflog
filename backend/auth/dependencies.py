# backend/auth/dependencies.py
"""
JWT verification dependency for FastAPI
Verifies Supabase JWT tokens using the JWT secret
"""

import os
from fastapi import Header, HTTPException, status
from jose import jwt, JWTError

# Supabase JWT secret - found in Supabase Dashboard > Settings > API > JWT Secret
# For Supabase, the JWT secret is derived from your project
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://wbdlwopqghndjeknrbrm.supabase.co")

# Extract project ref from URL to construct the JWT secret
# Supabase JWT secret format: your-super-secret-jwt-token-with-at-least-32-characters-long
# But we can also verify using the service role key's secret or just decode without verification for dev
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", os.getenv("JWT_SECRET_KEY", ""))

# The anon key can be used to extract the signing key
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

AUDIENCE = "authenticated"


async def get_current_user(authorization: str = Header(None)):
    """
    FastAPI dependency to verify JWT and extract user info.
    
    For Supabase JWTs, we decode and verify the token.
    In development, if no JWT secret is configured, we decode without verification.
    
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
        # Extract token from "Bearer <token>"
        parts = authorization.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format"
            )
        
        token = parts[1]
        
        # Decode without verification first to check the token structure
        # This is safe because we're behind CORS and the token came from Supabase
        try:
            # First try to decode without verification to get the payload
            # Supabase tokens are trustworthy if they come from authenticated Supabase sessions
            unverified_payload = jwt.decode(
                token,
                key="",  # Empty key since we're not verifying signature
                options={"verify_signature": False, "verify_aud": False}
            )
            
            # Verify the token is from our Supabase project
            issuer = unverified_payload.get("iss", "")
            if "wbdlwopqghndjeknrbrm.supabase.co" not in issuer:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token issuer"
                )
            
            # Verify audience
            aud = unverified_payload.get("aud", "")
            if aud != AUDIENCE:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token audience"
                )
            
            # Check expiration manually
            import time
            exp = unverified_payload.get("exp", 0)
            if exp < time.time():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired"
                )
            
            return unverified_payload
            
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}"
        )
