"""
Debug endpoint to test vault helper directly
Block 5 Step 8 debugging
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/debug/test-vault-helper")
async def test_vault_helper():
    """
    Test the vault helper directly with known parameters
    """
    import io
    import sys
    
    # Capture stdout to get print statements
    captured_output = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured_output
    
    try:
        from .block5_vault_helper import log_high_risk_to_vault
        
        # Test with high-risk email data
        evidence_id = await log_high_risk_to_vault(
            db=None,  # Will create own connection
            user_id="debug_user_999",
            evidence_type="email",
            content_category="harmful_extremist_content",
            violence_or_extremism_risk=10,
            tags=["extremism", "debug"],
            analysis_data={
                "test": "debug_endpoint",
                "sender_email": "debug@test.com",
                "subject": "Debug test",
                "body_preview": "This is a debug test"
            }
        )
        
        sys.stdout = old_stdout
        logs = captured_output.getvalue()
        
        return {
            "ok": True,
            "evidence_id": evidence_id,
            "message": "Vault helper executed successfully" if evidence_id else "Vault helper returned None",
            "logs": logs
        }
    
    except Exception as e:
        import traceback
        sys.stdout = old_stdout
        logs = captured_output.getvalue()
        
        return {
            "ok": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "logs": logs
        }
