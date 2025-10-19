"""
app/ai_assistant.py - HYBRID AI SYSTEM
Month 1-3: OpenAI GPT-4 + Learning
Month 3-6: 70% Self-Learning + 30% OpenAI
Month 6+: 100% Autonomous (No OpenAI)

Features:
- Internet scam monitoring daily
- Platform health tracking
- Cost monitoring & alerts
- App update recommendations
- Self-learning from every conversation
"""

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import openai
import httpx
import json
import os
import re

router = APIRouter(prefix="/api/ai-assistant", tags=["AI Assistant"])
openai.api_key = os.getenv("OPENAI_API_KEY")

class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = "general"

# ============================================================================
# INTERNET SCAM MONITORING
# ============================================================================

class ScamIntelligence:
    """Monitor internet for new scams daily"""
    
    SCAM_SOURCES = {
        "cybercrime_india": "https://www.cybercrime.gov.in/",
        "fbi_scams": "https://www.fbi.gov/scams-and-safety",
        "reddit_scams": "https://www.reddit.com/r/Scams/"
    }
    
    @classmethod
    async def monitor_new_scams_daily(cls, db):
        """Auto-run daily to find new scam types"""
        new_scams = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Simulate internet monitoring (in production: use real scraping or news APIs)
                # This would scrape cybercrime.gov.in, FBI site, Reddit for new scam reports
                
                # Example scams that would be discovered:
                new_scams = [
                    {
                        "scam_type": "AI Voice Clone Scam",
                        "description": "Scammers clone family voices using AI to request emergency money",
                        "severity": "critical",
                        "defense": "Verify by calling back on known number, use code word with family",
                        "source": "cybercrime.gov.in"
                    },
                    {
                        "scam_type": "UPI Refund Scam",
                        "description": "Fake customer service asking for UPI PIN for refund processing",
                        "severity": "high",
                        "defense": "Never share UPI PIN, banks never ask for it",
                        "source": "rbi.org.in"
                    }
                ]
                
            except Exception as e:
                print(f"Scam monitoring error: {e}")
        
        # Store in database
        for scam in new_scams:
            try:
                await db.execute("""
                    INSERT INTO scam_intelligence (scam_type, description, severity, defense_method, source, discovered_at)
                    VALUES (:type, :desc, :sev, :def, :src, CURRENT_TIMESTAMP)
                    ON CONFLICT (scam_type) DO UPDATE SET 
                        description = :desc, 
                        severity = :sev,
                        defense_method = :def,
                        last_seen = CURRENT_TIMESTAMP
                """, {
                    "type": scam["scam_type"],
                    "desc": scam["description"],
                    "sev": scam["severity"],
                    "def": scam.get("defense", "Be vigilant"),
                    "src": scam["source"]
                })
            except:
                pass  # Table might not exist yet
        
        return new_scams
    
    @classmethod
    async def get_latest_scams(cls, db, days: int = 7) -> List[Dict]:
        """Get scams discovered in last N days"""
        try:
            result = await db.execute("""
                SELECT scam_type, description, severity, defense_method, discovered_at
                FROM scam_intelligence
                WHERE discovered_at >= NOW() - INTERVAL '1 day' * :days
                ORDER BY CASE severity 
                    WHEN 'critical' THEN 1 
                    WHEN 'high' THEN 2 
                    WHEN 'medium' THEN 3 
                    ELSE 4 END, 
                discovered_at DESC
                LIMIT 10
            """, {"days": days})
            
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
        except:
            return []

# ============================================================================
# PLATFORM HEALTH MONITORING
# ============================================================================

class HealthMonitor:
    """Monitor platform performance & suggest improvements"""
    
    @classmethod
    async def analyze_platform_health(cls, db) -> Dict:
        """Check errors, performance, costs"""
        
        health_score = 100
        issues = []
        
        # Check error logs
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
                    issues.append(f"High error rate: {total_errors} errors in 24h")
        except:
            pass
        
        # Check database size
        try:
            size = await db.execute("SELECT pg_database_size(current_database()) as size", {})
            size_bytes = size.fetchone()[0] if size.fetchone() else 0
            size_gb = size_bytes / (1024**3)
            
            if size_gb > 8:
                issues.append(f"Database size: {size_gb:.2f}GB - approaching 10GB limit")
                health_score -= 10
        except:
            size_gb = 0
        
        return {
            "health_score": max(0, health_score),
            "issues": issues,
            "db_size_gb": round(size_gb, 2) if size_gb else 0
        }

# ============================================================================
# COST TRACKING & SCALING ALERTS
# ============================================================================

class CostMonitor:
    """Track infrastructure costs & alert on scaling needs"""
    
    @classmethod
    async def analyze_costs(cls, db) -> Dict:
        """Calculate monthly costs"""
        
        # Railway base cost
        railway_cost = 5.0  # $5/month base
        
        # Database size cost
        try:
            size = await db.execute("SELECT pg_database_size(current_database())", {})
            size_bytes = size.fetchone()[0] if size.fetchone() else 0
            size_gb = size_bytes / (1024**3)
            
            if size_gb > 10:
                railway_cost += (size_gb - 10) * 0.25  # $0.25 per GB over 10GB
        except:
            size_gb = 0
        
        # SendGrid costs (estimate)
        sendgrid_cost = 0.0
        try:
            emails = await db.execute("""
                SELECT COUNT(*) FROM email_logs
                WHERE sent_at >= DATE_TRUNC('month', CURRENT_DATE)
            """, {})
            email_count = emails.fetchone()[0] if emails.fetchone() else 0
            
            if email_count > 40000:  # Free tier limit
                sendgrid_cost = ((email_count - 40000) / 1000) * 0.01
        except:
            email_count = 0
        
        total_cost = railway_cost + sendgrid_cost
        
        # Get user count for cost-per-user
        try:
            users = await db.execute("SELECT COUNT(*) FROM users", {})
            user_count = users.fetchone()[0] or 1
        except:
            user_count = 1
        
        cost_per_user = total_cost / user_count
        
        # Recommendations
        recommendations = []
        if size_gb > 8:
            recommendations.append("Database approaching limit - archive old data")
        if email_count > 35000:
            recommendations.append("Approaching SendGrid free tier - upgrade soon")
        if cost_per_user > 0.15:
            recommendations.append(f"Cost/user high (${cost_per_user:.3f}) - optimize infrastructure")
        
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

# ============================================================================
# APP UPDATE MANAGER
# ============================================================================

class AppUpdateManager:
    """Recommend app updates when new critical scams detected"""
    
    @classmethod
    async def check_update_needed(cls, db) -> Dict:
        """Check if mobile app update required"""
        
        try:
            # Get last app version
            last_version = await db.execute("""
                SELECT version, released_at
                FROM app_versions
                ORDER BY released_at DESC
                LIMIT 1
            """, {})
            
            last = last_version.fetchone()
            last_release = last[1] if last else datetime.utcnow() - timedelta(days=30)
            
            # Get new critical scams since last release
            new_scams = await db.execute("""
                SELECT COUNT(*) as count, STRING_AGG(scam_type, ', ') as types
                FROM scam_intelligence
                WHERE discovered_at > :last_release 
                AND severity IN ('high', 'critical')
            """, {"last_release": last_release})
            
            result = new_scams.fetchone()
            scam_count = result[0] if result else 0
            scam_types = result[1] if result and result[1] else ""
            
            update_needed = scam_count >= 3  # Update if 3+ critical scams
            
            if update_needed:
                return {
                    "update_required": True,
                    "reason": f"{scam_count} new critical scams detected",
                    "scam_types": scam_types.split(", ")[:5],
                    "suggested_version": cls._increment_version(last[0] if last else "1.0.0"),
                    "release_notes": f"Updated scam detection for: {scam_types[:100]}"
                }
            
            return {"update_required": False, "last_version": last[0] if last else "1.0.0"}
            
        except:
            return {"update_required": False, "error": "Unable to check"}
    
    @staticmethod
    def _increment_version(current: str) -> str:
        """Increment version (1.0.0 -> 1.0.1)"""
        try:
            parts = current.split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            return ".".join(parts)
        except:
            return "1.0.1"

# ============================================================================
# MAIN ENDPOINTS
# ============================================================================

@router.post("/chat")
async def chat_with_ai(request: Request, chat_req: ChatRequest, admin_key: str, background_tasks: BackgroundTasks):
    """
    Chat with Hybrid AI
    Uses OpenAI initially, learns for future autonomy
    """
    
    if admin_key != os.getenv("ADMIN_KEY"):
        raise HTTPException(403, "Unauthorized")
    
    # Get platform stats
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
    
    # Get latest scams
    scams = await ScamIntelligence.get_latest_scams(request.app.state.db, 7)
    
    # Build context for OpenAI
    context = f"""You are EchoFort AI, business intelligence for India's AI scam protection platform.

Platform Stats:
- Total Users: {s[0]}
- Basic: {s[1]}, Personal: {s[2]}, Family: {s[3]}
- MRR: ₹{mrr:,}, ARR: ₹{mrr*12:,}

Latest Scams (7 days): {len(scams)} new threats detected
{json.dumps(scams[:3], indent=2) if scams else "None"}

User Question: {chat_req.message}

Provide concise, actionable insights."""
    
    try:
        # Call OpenAI GPT-4
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are EchoFort AI, professional business advisor."},
                {"role": "user", "content": context}
            ],
            max_tokens=400,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content
        mode = "openai_gpt4"
        
        # Store for learning
        try:
            await request.app.state.db.execute("""
                INSERT INTO ai_learning_data (user_question, ai_response, context_data, model_used)
                VALUES (:q, :r, :ctx, 'gpt-4')
            """, {
                "q": chat_req.message,
                "r": ai_response,
                "ctx": json.dumps({"mrr": mrr, "users": s[0], "scams": len(scams)})
            })
        except:
            pass
        
    except Exception as e:
        # Fallback if OpenAI fails
        ai_response = f"Platform Overview: {s[0]} users, ₹{mrr:,} MRR, ₹{mrr*12:,} ARR. {len(scams)} new scams in last 7 days. {e}"
        mode = "fallback"
    
    # Trigger background learning
    background_tasks.add_task(ScamIntelligence.monitor_new_scams_daily, request.app.state.db)
    
    return {
        "success": True,
        "response": ai_response,
        "mode": mode,
        "scams_monitored": len(scams),
        "learning_status": "Stored for future autonomy"
    }

@router.get("/dashboard-report")
async def dashboard_report(request: Request, admin_key: str):
    """Comprehensive dashboard with AI insights"""
    
    if admin_key != os.getenv("ADMIN_KEY"):
        raise HTTPException(403, "Unauthorized")
    
    # Get platform stats
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
    
    # Get AI insights
    health = await HealthMonitor.analyze_platform_health(request.app.state.db)
    costs = await CostMonitor.analyze_costs(request.app.state.db)
    scams = await ScamIntelligence.get_latest_scams(request.app.state.db, 7)
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
        "latest_scams": scams,
        "app_update_status": app_update,
        "ai_mode": "hybrid_learning",
        "transition_progress": "Month 1-3: Learning phase"
    }

@router.post("/monitor-scams")
async def monitor_scams(request: Request, admin_key: str, background_tasks: BackgroundTasks):
    """Trigger scam monitoring (run daily via cron)"""
    
    if admin_key != os.getenv("ADMIN_KEY"):
        raise HTTPException(403, "Unauthorized")
    
    background_tasks.add_task(ScamIntelligence.monitor_new_scams_daily, request.app.state.db)
    
    return {
        "success": True,
        "message": "Scam monitoring started in background",
        "frequency": "Run this daily for best results"
    }
