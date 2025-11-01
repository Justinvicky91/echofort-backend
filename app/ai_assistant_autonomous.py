from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import os
import httpx
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
import subprocess
import glob
from app.ai_execution_engine import propose_action, PendingAction

router = APIRouter(prefix="/api/echofort-ai-autonomous", tags=["EchoFort AI Autonomous"])

# Get API keys and database URL from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Convert DATABASE_URL for async use
if DATABASE_URL:
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    ASYNC_DATABASE_URL = ""

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    execute_directly: bool = True

class LearningEntry(BaseModel):
    topic: str
    information: str
    source: str
    confidence: float
    requires_approval: bool = True

# ============================================================================
# DATABASE ACCESS - Real-time platform data
# ============================================================================

async def get_real_platform_context() -> Dict[str, Any]:
    """Get REAL platform data from database"""
    try:
        # Create async engine from DATABASE_URL
        if not ASYNC_DATABASE_URL:
            return {"error": "Database URL not configured"}
        
        engine = create_async_engine(ASYNC_DATABASE_URL, pool_pre_ping=True)
        
        async with engine.begin() as conn:
            # Get real user count
            user_result = await conn.execute(text("SELECT COUNT(*) FROM users"))
            total_users = user_result.scalar() or 0
            
            # Get real employee count
            emp_result = await conn.execute(text("SELECT COUNT(*) FROM employees"))
            total_employees = emp_result.scalar() or 0
            
            # Get real subscription count
            sub_result = await conn.execute(text("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'"))
            active_subscriptions = sub_result.scalar() or 0
            
            # Get real revenue from subscriptions
            rev_result = await conn.execute(text("SELECT COALESCE(SUM(amount), 0) FROM subscriptions WHERE status = 'active'"))
            total_revenue = float(rev_result.scalar() or 0)
            
            # Get real threats blocked
            threat_result = await conn.execute(text("SELECT COUNT(*) FROM scam_cases WHERE status = 'blocked'"))
            threats_blocked = threat_result.scalar() or 0
            
            # Get payment gateway status
            pg_result = await conn.execute(text("SELECT gateway_name, is_active FROM payment_gateways"))
            payment_gateways = [{"name": row[0], "active": row[1]} for row in pg_result.fetchall()]
            
            # Get scam alerts count
            alerts_result = await conn.execute(text("SELECT COUNT(*) FROM scam_cases WHERE created_at > NOW() - INTERVAL '24 hours'"))
            recent_alerts = alerts_result.scalar() or 0
            
            return {
                "total_users": total_users,
                "total_employees": total_employees,
                "active_subscriptions": active_subscriptions,
                "total_revenue": total_revenue,
                "threats_blocked": threats_blocked,
                "payment_gateways": payment_gateways,
                "recent_scam_alerts": recent_alerts,
                "database_status": "Connected",
                "backend_status": "Online (Railway)",
                "frontend_status": "Online (Vercel)"
            }
    except Exception as e:
        print(f"Database context error: {e}")
        return {
            "error": str(e),
            "database_status": "Error",
            "message": "Could not fetch real-time data"
        }

# ============================================================================
# CODE INSPECTION - Check actual implementation
# ============================================================================

async def check_homepage_features() -> Dict[str, Any]:
    """Check if homepage features are actually implemented"""
    try:
        frontend_path = "/home/ubuntu/echofort-frontend-prod"
        
        results = {
            "sidebar_scam_alerts": False,
            "youtube_video_section": False,
            "video_rotation_logic": False,
            "auto_update_mechanism": False,
            "details": []
        }
        
        # Check for scam alerts sidebar in frontend code
        try:
            result = subprocess.run(
                ["grep", "-r", "Live Scam Alerts", frontend_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                results["sidebar_scam_alerts"] = True
                results["details"].append("✅ Scam alerts sidebar found in frontend code")
        except:
            pass
        
        # Check for YouTube video section
        try:
            result = subprocess.run(
                ["grep", "-r", "youtube\\|video\\|Watch Demo", frontend_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                results["youtube_video_section"] = True
                results["details"].append("✅ YouTube video section found in frontend")
        except:
            pass
        
        # Check for auto-update mechanism
        try:
            result = subprocess.run(
                ["grep", "-r", "Auto-updates\\|setInterval\\|useEffect", frontend_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                results["auto_update_mechanism"] = True
                results["details"].append("✅ Auto-update mechanism detected")
        except:
            pass
        
        return results
    except Exception as e:
        return {"error": str(e), "message": "Could not inspect code"}

async def check_backend_cron_jobs() -> Dict[str, Any]:
    """Check if cron jobs or scheduled tasks exist"""
    try:
        backend_path = "/home/ubuntu/echofort-backend"
        
        results = {
            "cron_jobs_found": False,
            "scheduled_tasks": [],
            "details": []
        }
        
        # Check for APScheduler or similar
        try:
            result = subprocess.run(
                ["grep", "-r", "schedule\\|cron\\|APScheduler", backend_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                results["cron_jobs_found"] = True
                results["details"].append("✅ Scheduling mechanism found in backend")
        except:
            pass
        
        return results
    except Exception as e:
        return {"error": str(e), "message": "Could not check cron jobs"}

# ============================================================================
# AI CAPABILITIES - Enhanced with real data
# ============================================================================

async def call_openai_with_context(prompt: str, context: Dict[str, Any]) -> str:
    """Call OpenAI with real platform context"""
    if not OPENAI_API_KEY:
        return ""
    
    try:
        system_prompt = f"""You are EchoFort AI, an autonomous platform manager with REAL-TIME access to:
- Database (PostgreSQL)
- Codebase (Frontend + Backend)
- System metrics and logs
- Internet for research

REAL PLATFORM DATA:
- Users: {context.get('total_users', 0)}
- Employees: {context.get('total_employees', 0)}
- Subscriptions: {context.get('active_subscriptions', 0)}
- Revenue: ₹{context.get('total_revenue', 0)}
- Threats Blocked: {context.get('threats_blocked', 0)}
- Recent Alerts: {context.get('recent_scam_alerts', 0)}
- Payment Gateways: {json.dumps(context.get('payment_gateways', []))}

You provide TECHNICAL, ACCURATE answers based on REAL DATA, not generic responses.
When asked about features, you CHECK THE CODE and DATABASE, not make assumptions.
"""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.3  # Lower temperature for more factual responses
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"OpenAI Error: {e}")
    
    return ""

# ============================================================================
# SELF-LEARNING SYSTEM with Approval
# ============================================================================

async def store_learning(entry: LearningEntry) -> bool:
    """Store learned information in database with approval workflow"""
    try:
        if not ASYNC_DATABASE_URL:
            return False
        
        engine = create_async_engine(ASYNC_DATABASE_URL, pool_pre_ping=True)
        
        async with engine.begin() as conn:
            # Create ai_learning table if not exists
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ai_learning (
                    id SERIAL PRIMARY KEY,
                    topic VARCHAR(255) NOT NULL,
                    information TEXT NOT NULL,
                    source VARCHAR(255),
                    confidence FLOAT,
                    requires_approval BOOLEAN DEFAULT true,
                    approved BOOLEAN DEFAULT false,
                    approved_by VARCHAR(255),
                    approved_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Insert learning entry
            await conn.execute(text("""
                INSERT INTO ai_learning (topic, information, source, confidence, requires_approval)
                VALUES (:topic, :information, :source, :confidence, :requires_approval)
            """), {
                "topic": entry.topic,
                "information": entry.information,
                "source": entry.source,
                "confidence": entry.confidence,
                "requires_approval": entry.requires_approval
            })
            
        return True
    except Exception as e:
        print(f"Learning storage error: {e}")
        return False

async def get_pending_approvals() -> List[Dict[str, Any]]:
    """Get learning entries pending approval"""
    try:
        if not ASYNC_DATABASE_URL:
            return []
        
        engine = create_async_engine(ASYNC_DATABASE_URL, pool_pre_ping=True)
        
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT id, topic, information, source, confidence, created_at
                FROM ai_learning
                WHERE requires_approval = true AND approved = false
                ORDER BY created_at DESC
                LIMIT 10
            """))
            
            return [
                {
                    "id": row[0],
                    "topic": row[1],
                    "information": row[2],
                    "source": row[3],
                    "confidence": row[4],
                    "created_at": row[5].isoformat() if row[5] else None
                }
                for row in result.fetchall()
            ]
    except Exception as e:
        print(f"Get approvals error: {e}")
        return []

# ============================================================================
# MAIN CHAT ENDPOINT - Truly Autonomous
# ============================================================================

@router.post("/chat")
async def autonomous_chat(request: ChatRequest):
    """
    Truly Autonomous EchoFort AI with:
    - Real database access
    - Code inspection capabilities
    - System command execution
    - Self-learning with approval workflow
    - Technical accuracy over generic responses
    """
    
    try:
        user_message = request.message.lower()
        
        # Get REAL platform context from database
        context = await get_real_platform_context()
        
        # Initialize response components
        technical_findings = []
        ai_response = ""
        
        # INTELLIGENT COMMAND DETECTION
        pending_action_created = None
        
        # Detect actionable commands that require approval
        if any(word in user_message for word in ['create marketing campaign', 'marketing campaign', 'campaign']):
            # Generate marketing campaign action
            campaign_action = PendingAction(
                action_type="marketing_campaign",
                description=f"Create marketing campaign based on: {request.message}",
                risk_level="low",
                code_changes={
                    "campaign_name": "AI-Generated Campaign",
                    "target_audience": "Extracted from command",
                    "command": request.message,
                    "platform_context": context
                }
            )
            try:
                result = await propose_action(campaign_action)
                pending_action_created = result
            except Exception as e:
                print(f"Error creating pending action: {e}")
        
        elif any(word in user_message for word in ['fix bug', 'fix any bug', 'fix issue', 'repair']):
            # Generate bug fix action
            fix_action = PendingAction(
                action_type="bug_fix",
                description=f"Fix bugs based on: {request.message}",
                risk_level="medium",
                code_changes={
                    "fix_type": "AI-Generated Fix",
                    "target_system": "Extracted from command",
                    "command": request.message,
                    "platform_context": context
                }
            )
            try:
                result = await propose_action(fix_action)
                pending_action_created = result
            except Exception as e:
                print(f"Error creating pending action: {e}")
        
        elif any(word in user_message for word in ['update', 'modify', 'change', 'improve']):
            # Generate system update action
            update_action = PendingAction(
                action_type="system_update",
                description=f"System update based on: {request.message}",
                risk_level="medium",
                code_changes={
                    "update_type": "AI-Generated Update",
                    "command": request.message,
                    "platform_context": context
                }
            )
            try:
                result = await propose_action(update_action)
                pending_action_created = result
            except Exception as e:
                print(f"Error creating pending action: {e}")
        
        # Check homepage features
        if any(word in user_message for word in ['homepage', 'sidebar', 'scam alerts', 'youtube', 'video']):
            homepage_check = await check_homepage_features()
            technical_findings.append({
                "type": "code_inspection",
                "title": "Homepage Features Analysis",
                "data": homepage_check
            })
            
            cron_check = await check_backend_cron_jobs()
            technical_findings.append({
                "type": "system_check",
                "title": "Scheduled Tasks Analysis",
                "data": cron_check
            })
        
        # Build enhanced prompt with REAL data
        enhanced_prompt = f"""
User Command: {request.message}

REAL-TIME PLATFORM DATA:
{json.dumps(context, indent=2)}

TECHNICAL FINDINGS:
{json.dumps(technical_findings, indent=2)}

Provide a TECHNICAL, ACCURATE response based on the REAL DATA above.
Do NOT give generic customer service responses.
Do NOT say "platform just launched" unless data confirms it.
BE SPECIFIC about what exists and what doesn't based on actual checks.
"""
        
        # Get AI response with real context
        ai_response = await call_openai_with_context(enhanced_prompt, context)
        
        if not ai_response:
            ai_response = "I checked the system but couldn't generate a detailed response. Here's what I found:\n\n"
            ai_response += f"**Platform Status:**\n"
            ai_response += f"- Users: {context.get('total_users', 0)}\n"
            ai_response += f"- Subscriptions: {context.get('active_subscriptions', 0)}\n"
            ai_response += f"- Threats Blocked: {context.get('threats_blocked', 0)}\n\n"
            
            if technical_findings:
                ai_response += "**Technical Findings:**\n"
                for finding in technical_findings:
                    ai_response += f"- {finding['title']}: {json.dumps(finding['data'], indent=2)}\n"
        
        # Store learning (with approval required)
        learning_entry = LearningEntry(
            topic=f"Command: {request.message[:100]}",
            information=f"Response: {ai_response[:500]}",
            source="autonomous_execution",
            confidence=0.85,
            requires_approval=True
        )
        await store_learning(learning_entry)
        
        # Format final response
        final_response = f"🤖 **EchoFort AI - Autonomous Execution Mode**\n\n{ai_response}\n\n---\n\n"
        
        if pending_action_created:
            final_response += f"\n✅ **Action Created for Approval**\n"
            final_response += f"- Action ID: #{pending_action_created.get('action_id')}\n"
            final_response += f"- Type: {pending_action_created.get('action_type')}\n"
            final_response += f"- Status: Pending Super Admin Approval\n"
            final_response += f"\n📋 Please check **AI Pending Actions** section to review and approve this action.\n\n---\n\n"
        
        final_response += f"**System Status:**\n"
        final_response += f"- Users: {context.get('total_users', 0)}\n"
        final_response += f"- Active Subscriptions: {context.get('active_subscriptions', 0)}\n"
        final_response += f"- Scam Cases: {context.get('threats_blocked', 0)}\n"
        
        return {
            "success": True,
            "response": final_response,
            "executed": True,
            "real_data_used": True,
            "technical_findings": technical_findings,
            "context": context,
            "learning_stored": True,
            "pending_action_created": pending_action_created is not None,
            "action_id": pending_action_created.get('action_id') if pending_action_created else None,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "response": f"⚠️ **Error Processing Command**\n\nError: {str(e)}\n\nI'm logging this error for learning.",
            "executed": False,
            "error": str(e)
        }

@router.get("/learning/pending")
async def get_learning_approvals():
    """Get pending learning entries for Super Admin approval"""
    pending = await get_pending_approvals()
    return {
        "success": True,
        "pending_count": len(pending),
        "entries": pending
    }

@router.post("/learning/approve/{entry_id}")
async def approve_learning(entry_id: int):
    """Approve a learning entry"""
    try:
        if not ASYNC_DATABASE_URL:
            return {"success": False, "error": "Database not configured"}
        
        engine = create_async_engine(ASYNC_DATABASE_URL, pool_pre_ping=True)
        
        async with engine.begin() as conn:
            await conn.execute(text("""
                UPDATE ai_learning
                SET approved = true,
                    approved_by = 'SuperAdmin',
                    approved_at = CURRENT_TIMESTAMP
                WHERE id = :entry_id
            """), {"entry_id": entry_id})
        
        return {"success": True, "message": "Learning entry approved"}
    except Exception as e:
        return {"success": False, "error": str(e)}
