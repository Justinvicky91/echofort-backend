"""
Block 5: Evidence Vault Helper
Handles automatic logging of high-risk content to evidence_vault
"""

from sqlalchemy import text
from datetime import datetime, timedelta
import json


async def log_high_risk_to_vault(
    db,
    user_id: str,
    evidence_type: str,  # "image", "email", "sms", "voice"
    content_category: str,
    violence_or_extremism_risk: int,
    tags: list,
    analysis_data: dict,
    threshold: int = 7
):
    """
    Log high-risk content to evidence_vault when threshold is exceeded
    
    Args:
        db: Database connection (if None, will create one from DATABASE_URL)
        user_id: User ID (or "anonymous" if not available)
        evidence_type: Type of evidence (image, email, sms, voice)
        content_category: AI-predicted category
        violence_or_extremism_risk: Risk score 0-10
        tags: List of tags
        analysis_data: Full analysis results (stored as JSONB)
        threshold: Minimum risk score to trigger vault logging (default: 7)
    
    Returns:
        evidence_id if logged, None otherwise
    """
    # Only log if risk exceeds threshold
    if violence_or_extremism_risk < threshold:
        return None
    
    # Create database connection if not provided
    created_connection = False
    if db is None:
        import os
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url:
            print("❌ Block 5: DATABASE_URL not set, cannot log to vault")
            return None
        
        # Convert postgres:// to postgresql:// for async
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif not database_url.startswith("postgresql+asyncpg://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        engine = create_async_engine(database_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        db = async_session()
        created_connection = True
    
    try:
        # Generate evidence ID
        import secrets
        evidence_id = f"EVD-{secrets.token_hex(6).upper()}"
        
        # Determine case_type based on content_category
        case_type_map = {
            "harmful_extremist_content": "harmful_extremism",
            "self_harm_risk": "self_harm",
            "scam_fraud": "scam",
            "harassment_abuse": "harassment"
        }
        case_type = case_type_map.get(content_category, "unknown")
        
        # Calculate retention expiry (7 years for legal compliance)
        retention_expiry = datetime.utcnow() + timedelta(days=7*365)
        
        # Create EchoFort seal
        seal = f"""
╔══════════════════════════════════════════╗
║         🛡️ ECHOFORT EVIDENCE 🛡️          ║
║  Evidence ID: {evidence_id}           ║
║  Type: {evidence_type.upper()}                    ║
║  Risk: {violence_or_extremism_risk}/10                       ║
║  Sealed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC         ║
║  AI PREDICTION - NOT LEGAL LABEL         ║
╚══════════════════════════════════════════╝
        """.strip()
        
        # Insert into evidence_vault
        query = text("""
            INSERT INTO evidence_vault (
                evidence_id, user_id, evidence_type,
                scam_type, threat_level,
                content_category, violence_or_extremism_risk, tags,
                ai_analysis, echofort_seal, retention_expiry,
                created_at
            ) VALUES (
                :evidence_id, :user_id, :evidence_type,
                :case_type, :threat_level,
                :content_category, :violence_risk, :tags,
                :ai_analysis, :seal, :retention_expiry,
                NOW()
            )
            RETURNING id
        """)
        
        result = await db.execute(query, {
            "evidence_id": evidence_id,
            "user_id": user_id or "anonymous",
            "evidence_type": evidence_type,
            "case_type": case_type,
            "threat_level": violence_or_extremism_risk,
            "content_category": content_category,
            "violence_risk": violence_or_extremism_risk,
            "tags": json.dumps(tags),
            "ai_analysis": json.dumps(analysis_data),
            "seal": seal,
            "retention_expiry": retention_expiry
        })
        
        await db.commit()
        
        vault_id = result.fetchone()[0]
        print(f"✅ Block 5: High-risk content logged to vault - Evidence ID: {evidence_id}, Vault ID: {vault_id}")
        
        return evidence_id
        
    except Exception as e:
        print(f"❌ Block 5: Failed to log to vault: {e}")
        if db:
            await db.rollback()
        return None
    finally:
        # Close connection if we created it
        if created_connection and db:
            await db.close()
