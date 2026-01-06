"""
Database Connection Module - Supabase Integration
"""

import os
from supabase import create_client, Client


class DBManager:
    """Database manager with lazy initialization for Supabase client."""
    
    def __init__(self):
        self._client: Client | None = None
    
    def get_client(self) -> Client:
        """
        Lazily initializes and returns the Supabase client.
        Only creates the client on first call, after env vars are loaded.
        """
        if self._client is None:
            url = os.getenv("SUPABASE_URL")
            # Prefer Service Role Key for backend operations to bypass RLS
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
            
            if not url or not key:
                raise ValueError(
                    "SUPABASE_URL or SUPABASE_KEY not found in environment. "
                    "Make sure load_dotenv() is called before importing db_manager."
                )
            
            print(f"🔌 [DB] Initializing Supabase with Key: {key[:10]}...")
            self._client = create_client(url, key)
        
        return self._client


# Global instance - but client is NOT created yet (lazy)
db_manager = DBManager()
