"""
Quick schema checker
"""
from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(prefix="/api/debug", tags=["Debug"])

@router.get("/invoices-schema")
async def check_invoices_schema(request: Request):
    """Check invoices table schema"""
    try:
        db = request.app.state.db
        
        # Get column information
        result = (await db.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'invoices'
            ORDER BY ordinal_position
        """))).fetchall()
        
        columns = []
        for row in result:
            columns.append({
                "name": row[0],
                "type": row[1],
                "nullable": row[2]
            })
        
        return {
            "ok": True,
            "table": "invoices",
            "columns": columns
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }
