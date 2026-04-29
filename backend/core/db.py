"""
Database Connection Module - Supabase Integration

Includes:
- Lazy Supabase client initialisation
- Retry-decorated helpers for fragile external writes
- Dual-write helper (Supabase + Pinecone) with rollback
"""

import os
import logging
from supabase import create_client, Client
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = logging.getLogger("DB")


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


# =============================================================================
# RETRY-DECORATED HELPERS
# =============================================================================

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def supabase_upsert(table: str, data: dict, on_conflict: str = "id") -> dict:
    """
    Upsert a row into Supabase with automatic retry + exponential backoff.

    Args:
        table: Target table name.
        data: Row data as a dict.
        on_conflict: Column(s) to use for conflict resolution.

    Returns:
        The upserted row data from Supabase.
    """
    client = db_manager.get_client()
    result = client.table(table).upsert(data, on_conflict=on_conflict).execute()
    return result.data


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def supabase_insert(table: str, data: dict) -> dict:
    """
    Insert a row into Supabase with automatic retry + exponential backoff.
    """
    client = db_manager.get_client()
    result = client.table(table).insert(data).execute()
    return result.data


# =============================================================================
# DUAL-WRITE HELPER  (Supabase → Pinecone)
# =============================================================================

def dual_write(
    table: str,
    row_data: dict,
    pinecone_index,
    vector_id: str,
    vector_values: list[float],
    vector_metadata: dict,
    namespace: str = "",
    on_conflict: str = "id",
) -> dict:
    """
    Transactional dual-write: Supabase first, then Pinecone.

    If the Pinecone upsert fails, the Supabase row is deleted (best-effort
    rollback) so the two stores stay in sync.

    Args:
        table: Supabase table name.
        row_data: Dict of column values.
        pinecone_index: An initialised Pinecone Index object.
        vector_id: ID for the Pinecone vector.
        vector_values: Embedding values.
        vector_metadata: Metadata dict attached to the vector.
        namespace: Pinecone namespace.
        on_conflict: Supabase conflict column.

    Returns:
        Dict with keys ``supabase`` and ``pinecone`` containing their
        respective response payloads.
    """
    # Step 1: Write to Supabase
    sb_result = supabase_upsert(table, row_data, on_conflict)

    # Step 2: Write to Pinecone
    try:
        pc_result = pinecone_index.upsert(
            vectors=[
                {
                    "id": vector_id,
                    "values": vector_values,
                    "metadata": vector_metadata,
                }
            ],
            namespace=namespace,
        )
    except Exception as pc_err:
        # Best-effort rollback: remove the Supabase row
        logger.error(f"Pinecone upsert failed, rolling back Supabase row: {pc_err}")
        try:
            row_id = row_data.get("id") or (sb_result[0].get("id") if sb_result else None)
            if row_id:
                db_manager.get_client().table(table).delete().eq("id", row_id).execute()
                logger.info(f"Supabase rollback succeeded for id={row_id}")
        except Exception as rb_err:
            logger.error(f"Supabase rollback also failed: {rb_err}")
        raise pc_err

    return {"supabase": sb_result, "pinecone": pc_result}
