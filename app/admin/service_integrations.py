"""
EchoFort Service Integration Module
Fetches real-time cost and usage data from Railway, OpenAI, and other services
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy import text
from datetime import datetime, timedelta
import httpx
import os
from ..rbac import guard_admin

router = APIRouter(prefix="/admin/integrations", tags=["Service Integrations"])

# Railway API Integration
async def fetch_railway_costs():
    """Fetch current month Railway hosting costs"""
    try:
        railway_token = os.getenv("RAILWAY_API_TOKEN")
        if not railway_token:
            return {"error": "Railway API token not configured", "cost": 0}
        
        # Railway GraphQL API
        url = "https://backboard.railway.app/graphql/v2"
        headers = {
            "Authorization": f"Bearer {railway_token}",
            "Content-Type": "application/json"
        }
        
        # Query for current usage
        query = """
        query {
          me {
            projects {
              edges {
                node {
                  name
                  estimatedUsage {
                    current
                    estimated
                  }
                }
              }
            }
          }
        }
        """
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={"query": query}, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                projects = data.get("data", {}).get("me", {}).get("projects", {}).get("edges", [])
                
                total_current = 0
                total_estimated = 0
                
                for project in projects:
                    node = project.get("node", {})
                    usage = node.get("estimatedUsage", {})
                    total_current += usage.get("current", 0) / 100  # Convert cents to dollars
                    total_estimated += usage.get("estimated", 0) / 100
                
                # Convert to INR (approximate rate: 1 USD = 83 INR)
                usd_to_inr = 83
                
                return {
                    "service": "railway",
                    "current_usage_usd": round(total_current, 2),
                    "current_usage_inr": round(total_current * usd_to_inr, 2),
                    "estimated_monthly_usd": round(total_estimated, 2),
                    "estimated_monthly_inr": round(total_estimated * usd_to_inr, 2),
                    "projects_count": len(projects),
                    "last_updated": datetime.now().isoformat()
                }
            else:
                return {"error": f"Railway API error: {response.status_code}", "cost": 0}
                
    except Exception as e:
        return {"error": str(e), "cost": 0}


# OpenAI API Integration
async def fetch_openai_usage():
    """Fetch OpenAI API usage and costs"""
    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            return {"error": "OpenAI API key not configured", "cost": 0}
        
        # OpenAI doesn't have a direct usage API, but we can track from our database
        # For now, return estimated based on token usage
        
        return {
            "service": "openai",
            "note": "OpenAI usage tracking via token consumption",
            "estimated_monthly_cost_usd": 0,  # Will be calculated from actual usage
            "estimated_monthly_cost_inr": 0,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"error": str(e), "cost": 0}


@router.get("/railway/costs", dependencies=[Depends(guard_admin)])
async def get_railway_costs(request: Request):
    """Get real-time Railway hosting costs"""
    costs = await fetch_railway_costs()
    return {"ok": True, "data": costs}


@router.get("/openai/usage", dependencies=[Depends(guard_admin)])
async def get_openai_usage(request: Request):
    """Get OpenAI API usage statistics"""
    usage = await fetch_openai_usage()
    return {"ok": True, "data": usage}


@router.get("/all-services/summary", dependencies=[Depends(guard_admin)])
async def get_all_services_summary(request: Request):
    """Get summary of all service costs"""
    try:
        railway = await fetch_railway_costs()
        openai = await fetch_openai_usage()
        
        # Get database-recorded costs
        db = request.app.state.db
        query = text("""
            SELECT 
                service,
                SUM(amount) as total_cost,
                COUNT(*) as transaction_count
            FROM infrastructure_costs
            WHERE date >= DATE_TRUNC('month', CURRENT_DATE)
            GROUP BY service
        """)
        
        rows = (await db.execute(query)).fetchall()
        recorded_costs = [dict(r._mapping) for r in rows]
        
        return {
            "ok": True,
            "live_data": {
                "railway": railway,
                "openai": openai
            },
            "recorded_costs": recorded_costs,
            "total_estimated_monthly_inr": railway.get("estimated_monthly_inr", 0) + openai.get("estimated_monthly_cost_inr", 0),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch service summary: {str(e)}")


@router.post("/sync-costs", dependencies=[Depends(guard_admin)])
async def sync_service_costs(request: Request):
    """Manually sync costs from all services to database"""
    try:
        db = request.app.state.db
        synced = []
        
        # Sync Railway costs
        railway = await fetch_railway_costs()
        if "error" not in railway:
            query = text("""
                INSERT INTO infrastructure_costs 
                (service, amount, billing_period, date, details, created_at)
                VALUES ('railway', :amount, 'daily', CURRENT_DATE, :details, NOW())
                ON CONFLICT (service, date) DO UPDATE SET amount = :amount, details = :details
                RETURNING cost_id
            """)
            
            import json
            await db.execute(query, {
                "amount": railway.get("current_usage_inr", 0),
                "details": json.dumps(railway)
            })
            synced.append("railway")
        
        # Sync OpenAI costs (if available)
        openai = await fetch_openai_usage()
        if "error" not in openai and openai.get("estimated_monthly_cost_inr", 0) > 0:
            query = text("""
                INSERT INTO infrastructure_costs 
                (service, amount, billing_period, date, details, created_at)
                VALUES ('openai', :amount, 'daily', CURRENT_DATE, :details, NOW())
                ON CONFLICT (service, date) DO UPDATE SET amount = :amount, details = :details
                RETURNING cost_id
            """)
            
            await db.execute(query, {
                "amount": openai.get("estimated_monthly_cost_inr", 0),
                "details": json.dumps(openai)
            })
            synced.append("openai")
        
        await db.commit()
        
        return {
            "ok": True,
            "message": "Costs synced successfully",
            "synced_services": synced,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(500, f"Failed to sync costs: {str(e)}")

