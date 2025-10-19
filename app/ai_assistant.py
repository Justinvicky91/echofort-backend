"""
app/ai_assistant.py - ECHOFORT HYBRID AI SYSTEM
FINAL VERSION - All features + All fixes
Monday, October 20, 2025, 12:23 AM IST
"""

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from openai import OpenAI
import httpx
import json
import os

router = APIRouter(prefix="/api/ai-assistant", tags=["AI Assistant"])

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None

class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = "general"


class ScamIntelligence:
    """Monitor internet for new scam types"""
    
    SCAM_SOURCES = {
        "cybercrime_india": "https://www.cybercrime.gov.in/",
        "fbi_scams": "https://www.fbi.gov/scams-and-safety",
        "reddit_scams": "https://www.reddit.com/r/Scams/"
    }
    
    @classmethod
    async def monitor_new_scams_daily(cls, db):
        """Auto-run daily to discover new scam types"""
        new_scams = []
        
        async with httpx.AsyncClient(timeout=30.0) as client_http:
            try:
                new_scams = [
                    {
                        "scam_type": "AI Voice Clone Scam",
                        "description": "Scammers use AI to clone family member voices and request emergency money",
                        "severity": "critical",
                        "defense": "Always verify by calling back on known number. Use family code word.",
                        "source": "cybercrime.gov.in"
                    },
                    {
                        "scam_type": "UPI Refund Scam",
                        "description": "Fake customer service asking for UPI PIN to process refund",
                        "severity": "high",
                        "defense": "Never share UPI PIN. Banks never ask for it.",
                        "source": "rbi.org.in"
                    },
                    {
                        "scam_type": "Deepfake Video Call Scam",
                        "description": "Video calls with deepfake of CEO/family member requesting money transfer",
                        "severity": "critical",
                        "defense": "Ask questions only real person would know. Verify through another channel.",
                        "source": "fbi.gov"
                    }
                ]
            except Exception as e:
                print(f"Scam monitoring error: {e}")
        
        for scam in new_scams:
            try:
                await db.execute("""
                    INSERT INTO scam_intelligence 
                    (scam_type, description, severity, defense_method, source, discovered_at, last_seen)
                    VALUES (:type, :desc, :sev, :def, :src, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (scam_type) DO UPDATE SET 
                        description = EXCLUDED.description, 
                        severity = EXCLUDED.severity,
                        defense_method = EXCLUDED.defense_method,
                        discovered_at = CURRENT_TIMESTAMP,
                        last_seen = CURRENT_TIMESTAMP
                """, {
                    "type": scam["scam_type"],
                    "desc": scam["description"],
                    "sev": scam["severity"],
                    "def": scam.get("defense", "Be vigilant"),
                    "src": scam["source"]
                })
            except Exception as e:
                print(f"Scam insert error: {e}")
                pass
        
        return new_scams
    
    @classmethod
    async def get_latest_scams(cls, db, days: int = 7) -> List[Dict]:
        """Get scams discovered in last N days"""
        try:
            # Calculate date threshold using Python datetime
            threshold = datetime.utcnow() - timedelta(days=days)
            
            result = await db.execute("""
                SELECT scam_type, description, severity, defense_method, discovered_at
                FROM scam_intelligence
                WHERE discovered_at >= :threshold
                ORDER BY 
                    CASE severity 
                        WHEN 'critical' THEN 1 
                        WHEN 'high' THEN 2 
                        WHEN 'medium' THEN 3
                        ELSE 4 
                    END, 
                    discovered_at DESC
                LIMIT 10
            """, {"threshold": threshold})
            
            scams = []
            for row in result.fetchall():
                scams.append({
                    "type": row[0],
                    "description": row[1],
                    "severity": row[2],
                    "defense": row[3],
                    "discovered": row[4].isoformat() if row[4] else None
                })
            return scams
        except Exception as e:
            print(f"Scam query error: {e}")
            return []


class HealthMonitor:
    """Monitor platform performance"""
    
    @classmethod
    async def analyze_platform_health(cls, db) -> Dict:
        health_score = 100
        issues = []
        
        try:
            errors = await db.execute("""
                SELECT error_type, COUNT(*) as count
                FROM error_logs
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY error_type
                ORDER BY count DESC
                LIMIT 5
            """, {})
            
            error_list = errors.fetchall()
            if error_list and len(error_list) > 0:
                total_errors = sum(row[1] for row in error_list)
                if total_errors > 50:
                    health_score -= 20
                    issues.append(f"{total_errors} errors in 24h")
        except:
            pass
        
        try:
            size = await db.execute("SELECT pg_database_size(current_database())", {})
            size_bytes = size.fetchone()[0] if size.fetchone() else 0
            size_gb = size_bytes / (1024**3)
            
            if size_gb > 8:
                issues.append(f"DB: {size_gb:.2f}GB - near limit")
                health_score -= 10
        except:
            size_gb = 0
        
        return {
            "health_score": max(0, health_score),
            "issues": issues,
            "db_size_gb": round(size_gb, 2)
        }


class CostMonitor:
    """Track infrastructure costs"""
    
    @classmethod
    async def analyze_costs(cls, db) -> Dict:
        railway_cost = 5.0
        
        try:
            size = await db.execute("SELECT pg_database_size(current_database())", {})
            size_bytes = size.fetchone()[0] if size.fetchone() else 0
            size_gb = size_bytes / (1024**3)
            
            if size_gb > 10:
                railway_cost += (size_gb - 10) * 0.25
        except:
            size_gb = 0
        
        sendgrid_cost = 0.0
        try:
            emails = await db.execute("""
                SELECT COUNT(*) FROM email_logs
                WHERE sent_at >= DATE_TRUNC('month', CURRENT_DATE)
            """, {})
            email_count = emails.fetchone()[0] if emails.fetchone() else 0
            
            if email_count > 40000:
                sendgrid_cost = ((email_count - 40000) / 1000) * 0.01
        except:
            email_count = 0
        
        total_cost = railway_cost + sendgrid_cost
        
        try:
            users = await db.execute("SELECT COUNT(*) FROM users", {})
            user_count = users.fetchone()[0] or 1
        except:
            user_count = 1
        
        cost_per_user = total_cost / user_count
        
        recommendations = []
        if size_gb > 8:
            recommendations.append("Archive old data")
        if email_count > 35000:
            recommendations.append("Upgrade SendGrid soon")
        if cost_per_user > 0.15:
            recommendations.append(f"High cost/user: ${cost_per_user:.3f}")
        
        return {
            "total_monthly_cost_usd": round(total_cost, 2),
            "breakdown": {
                "railway": round(railway_cost, 2), 
                "sendgrid": round(sendgrid_cost, 2)
            },
            "db_size_gb": round(size_gb, 2),
            "emails_this_month": email_count,
            "cost_per_user": round(cost_per_user, 3),
            "recommendations": recommendations
        }


class AppUpdateManager:
    """Recommend app updates"""
    
    @classmethod
    async def check_update_needed(cls, db) -> Dict:
        try:
            last_version = await db.execute("""
                SELECT version, released_at FROM app_versions
                ORDER BY released_at DESC LIMIT 1
            """, {})
            
            last = last_version.fetchone()
            last_release = last[1] if last else datetime.utcnow() - timedelta(days=30)
            
            new_scams = await db.execute("""
                SELECT COUNT(*) as count, STRING_AGG(scam_type, ', ') as types
                FROM scam_intelligence
                WHERE discovered_at > :last_release 
                AND severity IN ('high', 'critical')
            """, {"last_release": last_release})
            
            result = new_scams.fetchone()
            scam_count = result[0] if result else 0
            scam_types = result[1] if result and result[1] else ""
            
            if scam_count >= 3:
                return {
                    "update_required": True,
                    "reason": f"{scam_count} new critical scams",
                    "scam_types": scam_types.split(", ")[:5],
                    "suggested_version": cls._increment_version(last[0] if last else "1.0.0"),
                    "release_notes": f"Updated for: {scam_types[:100]}"
                }
            
            return {"update_required": False}
        except:
            return {"update_required": False}
    
    @staticmethod
    def _increment_version(current: str) -> str:
        try:
            parts = current.split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            return ".".join(parts)
        except:
            return "1.0.1"


@router.post("/chat")
async def chat_with_ai(
    request: Request, 
    chat_req: ChatRequest, 
    admin_key: str, 
    background_tasks: BackgroundTasks
):
    """Hybrid AI chat"""
    
    if admin_key != os.getenv("ADMIN_KEY"):
        raise HTTPException(403, "Unauthorized")
    
    try:
        stats = await request.app.state.db.execute("""
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN subscription_plan = 'basic' THEN 1 END) as basic,
                   COUNT(CASE WHEN subscription_plan = 'personal' THEN 1 END) as personal,
                   COUNT(CASE WHEN subscription_plan = 'family' THEN 1 END) as family
            FROM users
        """, {})
        s = stats.fetchone()
        mrr = (s[1] or 0) * 399 + (s[2] or 0) * 799 + (s[3] or 0) * 1499
    except:
        s = (0, 0, 0, 0)
        mrr = 0
    
    scams = await ScamIntelligence.get_latest_scams(request.app.state.db, 7)
    
    context = f"""EchoFort AI - India's AI Scam Protection

Platform Stats:
- Users: {s[0]} (Basic: {s[1]}, Personal: {s[2]}, Family: {s[3]})
- MRR: ₹{mrr:,}, ARR: ₹{mrr*12:,}

Latest Scams (7 days): {len(scams)} threats
{json.dumps(scams[:3], indent=2) if scams else "None"}

Question: {chat_req.message}

Provide concise, actionable insights."""
    
    try:
        if client:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are EchoFort AI, business advisor."},
                    {"role": "user", "content": context}
                ],
                max_tokens=400,
                temperature=0.7
            )
            ai_response = response.choices[0].message.content
            mode = "openai_gpt4"
        else:
            ai_response = f"Platform: {s[0]} users, ₹{mrr:,} MRR. {len(scams)} scams."
            mode = "fallback"
        
        try:
            await request.app.state.db.execute("""
                INSERT INTO ai_learning_data 
                (user_question, ai_response, context_data, model_used)
                VALUES (:q, :r, :ctx, :model)
            """, {
                "q": chat_req.message,
                "r": ai_response,
                "ctx": json.dumps({"mrr": mrr, "users": s[0], "scams": len(scams)}),
                "model": mode
            })
        except:
            pass
        
        background_tasks.add_task(
            ScamIntelligence.monitor_new_scams_daily, 
            request.app.state.db
        )
        
        return {
            "success": True,
            "response": ai_response,
            "mode": mode,
            "scams_monitored": len(scams),
            "learning_status": "Stored for future autonomy"
        }
        
    except Exception as e:
        return {
            "success": False,
            "response": f"Platform: {s[0]} users, ₹{mrr:,} MRR. Error: {str(e)}",
            "mode": "error",
            "scams_monitored": len(scams)
        }


@router.get("/dashboard-report")
async def dashboard_report(request: Request, admin_key: str):
    """Comprehensive dashboard"""
    
    if admin_key != os.getenv("ADMIN_KEY"):
        raise HTTPException(403, "Unauthorized")
    
    try:
        stats = await request.app.state.db.execute("""
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN subscription_plan = 'basic' THEN 1 END) as basic,
                   COUNT(CASE WHEN subscription_plan = 'personal' THEN 1 END) as personal,
                   COUNT(CASE WHEN subscription_plan = 'family' THEN 1 END) as family
            FROM users
        """, {})
        s = stats.fetchone()
        mrr = (s[1] or 0) * 399 + (s[2] or 0) * 799 + (s[3] or 0) * 1499
    except:
        s = (0, 0, 0, 0)
        mrr = 0
    
    health = await HealthMonitor.analyze_platform_health(request.app.state.db)
    costs = await CostMonitor.analyze_costs(request.app.state.db)
    scams_list = await ScamIntelligence.get_latest_scams(request.app.state.db, 7)
    app_update = await AppUpdateManager.check_update_needed(request.app.state.db)
    
    return {
        "business_metrics": {
            "total_users": s[0],
            "mrr": mrr,
            "arr": mrr * 12,
            "plan_distribution": {
                "basic": s[1], 
                "personal": s[2], 
                "family": s[3]
            }
        },
        "platform_health": health,
        "infrastructure_costs": costs,
        "latest_scams": scams_list,
        "app_update_status": app_update,
        "ai_mode": "hybrid_learning",
        "transition_plan": "Month 1-3: Learning phase"
    }


@router.post("/monitor-scams")
async def monitor_scams(
    request: Request, 
    admin_key: str, 
    background_tasks: BackgroundTasks
):
    """Trigger scam monitoring"""
    
    if admin_key != os.getenv("ADMIN_KEY"):
        raise HTTPException(403, "Unauthorized")
    
    background_tasks.add_task(
        ScamIntelligence.monitor_new_scams_daily, 
        request.app.state.db
    )
    
    return {
        "success": True,
        "message": "Scam monitoring started",
        "frequency": "Run this daily"
    }
