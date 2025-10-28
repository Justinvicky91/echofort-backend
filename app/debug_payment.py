"""Debug endpoint for payment gateway configuration"""
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import text
import json

router = APIRouter(prefix="/api/debug", tags=["Debug"])

@router.get("/payment-gateway-table")
async def check_payment_gateway_table(request: Request):
    """Check payment_gateways table structure"""
    try:
        db = request.app.state.db
        
        # Check if table exists
        result = await db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'payment_gateways'
            );
        """))
        exists = result.fetchone()[0]
        
        if not exists:
            return {
                "exists": False,
                "message": "Table payment_gateways does not exist"
            }
        
        # Get table structure
        result = await db.execute(text("""
            SELECT 
                column_name, 
                data_type, 
                is_nullable
            FROM information_schema.columns
            WHERE table_name = 'payment_gateways'
            ORDER BY ordinal_position;
        """))
        
        columns = [{"name": row[0], "type": row[1], "nullable": row[2]} for row in result.fetchall()]
        
        # Get record count
        result = await db.execute(text("SELECT COUNT(*) FROM payment_gateways;"))
        count = result.fetchone()[0]
        
        return {
            "exists": True,
            "columns": columns,
            "record_count": count,
            "message": "Table structure retrieved successfully"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "type": type(e).__name__
        }

@router.post("/test-payment-insert")
async def test_payment_insert(request: Request):
    """Test inserting a payment gateway record"""
    try:
        db = request.app.state.db
        
        # Try a simple insert
        test_data = {
            "name": "test_gateway",
            "enabled": True,
            "test_mode": True,
            "api_key": "test_api_key_encrypted",
            "secret_key": "test_secret_key_encrypted",
            "webhook_secret": "test_webhook_secret",
            "currencies": json.dumps(["INR", "USD"]),
            "regions": json.dumps(["India"]),
            "priority": 1,
            "admin_id": 1
        }
        
        # First, try to check what columns exist
        result = await db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns
            WHERE table_name = 'payment_gateways'
            ORDER BY ordinal_position;
        """))
        available_columns = [row[0] for row in result.fetchall()]
        
        return {
            "available_columns": available_columns,
            "test_data_keys": list(test_data.keys()),
            "message": "Ready to test insert - check if columns match"
        }
        
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
