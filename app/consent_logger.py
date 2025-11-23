"""
Consent Logging Module
Block 5 Legal & Safety Hardening
Tracks user consent to Terms & Privacy versions for DPDP compliance
"""

from datetime import datetime
from typing import Optional
import asyncio


async def log_user_consent(
    db,
    user_id: str,
    terms_version: str,
    privacy_version: str,
    consent_type: str,  # signup, plan_upgrade, feature_update
    consent_channel: str,  # mobile, web
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> int:
    """
    Log user consent to Terms & Privacy versions
    
    Args:
        db: Database connection
        user_id: User identifier
        terms_version: Version of Terms accepted (e.g., "2.0")
        privacy_version: Version of Privacy Policy accepted (e.g., "2.0")
        consent_type: Type of consent event
        consent_channel: Channel where consent was given
        ip_address: Optional IP address
        user_agent: Optional user agent string
    
    Returns:
        int: ID of the created consent log entry
    """
    
    def _insert():
        sql = """
        INSERT INTO user_consent_log 
        (user_id, terms_version, privacy_version, consent_type, consent_channel, ip_address, user_agent, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        
        # Use asyncio to run in thread pool
        import psycopg
        from os import getenv
        
        dsn = getenv("DATABASE_URL")
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    user_id,
                    terms_version,
                    privacy_version,
                    consent_type,
                    consent_channel,
                    ip_address,
                    user_agent,
                    datetime.utcnow()
                ))
                conn.commit()
                return cur.fetchone()[0]
    
    return await asyncio.to_thread(_insert)


async def get_latest_consent(db, user_id: str) -> Optional[dict]:
    """
    Get the latest consent record for a user
    
    Returns:
        dict with terms_version, privacy_version, timestamp, or None if no consent found
    """
    
    def _query():
        sql = """
        SELECT terms_version, privacy_version, consent_type, timestamp
        FROM user_consent_log
        WHERE user_id = %s
        ORDER BY timestamp DESC
        LIMIT 1
        """
        
        import psycopg
        from os import getenv
        
        dsn = getenv("DATABASE_URL")
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id,))
                row = cur.fetchone()
                if row:
                    return {
                        "terms_version": row[0],
                        "privacy_version": row[1],
                        "consent_type": row[2],
                        "timestamp": row[3].isoformat()
                    }
                return None
    
    return await asyncio.to_thread(_query)


# Current legal document versions (should match legal_texts/*.md)
CURRENT_TERMS_VERSION = "2.0"
CURRENT_PRIVACY_VERSION = "2.0"
