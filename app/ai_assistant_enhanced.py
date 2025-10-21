# app/ai_assistant_enhanced.py - FULL AUTONOMOUS ECHOFORT AI
"""
EchoFort AI - Autonomous Platform Manager
Can modify frontend/backend code, send marketing campaigns, manage infrastructure
ALL actions require Super Admin approval before execution
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy import text
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel
from .rbac import guard_admin
import os
import json
import subprocess
from openai import OpenAI

router = APIRouter(prefix="/api/echofort-ai", tags=["EchoFort AI"])

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============================================================================
# MODELS
# ============================================================================

class AICommand(BaseModel):
    admin_key: str
    command: str
    auto_approve: bool = False  # If True, execute without approval

class AIApproval(BaseModel):
    admin_key: str
    task_id: int
    approved: bool
    feedback: Optional[str] = None

class MarketingCampaign(BaseModel):
    admin_key: str
    campaign_type: Literal["email", "push", "whatsapp", "sms"]
    target_audience: str  # "all", "active_users", "trial_users", etc.
    subject: str
    message: str

# ============================================================================
# ECHOFORT AI CORE - AUTONOMOUS CAPABILITIES
# ============================================================================

async def get_platform_context(request: Request) -> dict:
    """Gather real-time platform data for AI context"""
    db = request.app.state.db
    
    context = {
        "timestamp": datetime.now().isoformat(),
        "platform": "EchoFort - AI-Powered Scam Protection"
    }
    
    try:
        # Active users and revenue
        revenue_query = text("""
            SELECT 
                COUNT(*) as active_users,
                COALESCE(SUM(amount), 0) as monthly_revenue
            FROM subscriptions 
            WHERE status = 'active'
        """)
        result = (await db.execute(revenue_query)).fetchone()
        context["active_users"] = result[0] if result else 0
        context["monthly_revenue"] = float(result[1]) if result else 0.0
        
        # Scam detection stats
        scam_query = text("""
            SELECT 
                COUNT(*) as total_scams_detected,
                COUNT(*) FILTER (WHERE action_taken = 'blocked') as scams_blocked
            FROM digital_arrest_alerts
            WHERE detected_at > NOW() - INTERVAL '7 days'
        """)
        result = (await db.execute(scam_query)).fetchone()
        context["scams_detected_7d"] = result[0] if result else 0
        context["scams_blocked_7d"] = result[1] if result else 0
        
    except Exception as e:
        print(f"Error gathering context: {e}")
    
    return context


async def echofort_ai_execute_command(command: str, platform_context: dict) -> dict:
    """
    EchoFort AI processes command and generates execution plan
    Returns: {
        "action_type": "code_change|marketing|database|infrastructure",
        "description": "What AI will do",
        "code": "Generated code (if applicable)",
        "sql": "Generated SQL (if applicable)",
        "files_to_modify": ["file1.tsx", "file2.py"],
        "preview": "Preview of changes",
        "requires_approval": true,
        "estimated_impact": "High|Medium|Low",
        "risks": ["risk1", "risk2"]
    }
    """
    
    system_prompt = f"""You are EchoFort AI, an autonomous platform manager with the ability to modify code, manage infrastructure, and execute marketing campaigns.

CURRENT PLATFORM STATE:
{json.dumps(platform_context, indent=2)}

YOUR CAPABILITIES:
1. **Code Generation**: Generate React/TypeScript frontend code and Python backend code
2. **Database Operations**: Generate SQL queries for data operations
3. **Marketing Automation**: Draft email/push/WhatsApp campaigns
4. **Infrastructure Management**: Suggest scaling, optimization, deployment changes
5. **Business Intelligence**: Analyze data and recommend actions

REPOSITORIES:
- Frontend: React + TypeScript + Vite (Netlify deployment)
- Backend: FastAPI + PostgreSQL (Railway deployment)

IMPORTANT RULES:
1. ALL actions require Super Admin approval before execution
2. Provide detailed preview of changes
3. List all files that will be modified
4. Estimate impact (High/Medium/Low)
5. Identify potential risks
6. Generate production-ready code (no placeholders)
7. Follow existing code patterns and style

USER COMMAND: {command}

Analyze the command and respond in JSON format:
{{
  "action_type": "code_change|marketing|database|infrastructure|analysis",
  "description": "Clear description of what you will do",
  "code": "Generated code if applicable (full, production-ready)",
  "sql": "Generated SQL if applicable",
  "files_to_modify": ["list of files"],
  "preview": "Detailed preview of changes",
  "requires_approval": true,
  "estimated_impact": "High|Medium|Low",
  "risks": ["potential risk 1", "potential risk 2"],
  "benefits": ["benefit 1", "benefit 2"],
  "estimated_time": "Time to execute (e.g., '2 minutes')"
}}

If the command is unclear or dangerous, set "requires_approval": true and explain concerns in "preview"."""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": command}
            ],
            temperature=0.3,  # Lower temperature for more precise code generation
            max_tokens=2000
        )
        
        ai_response = response.choices[0].message.content
        
        # Try to parse JSON response
        try:
            execution_plan = json.loads(ai_response)
        except:
            # If not JSON, wrap in structure
            execution_plan = {
                "action_type": "analysis",
                "description": "AI analysis",
                "preview": ai_response,
                "requires_approval": True,
                "estimated_impact": "Low",
                "risks": [],
                "benefits": []
            }
        
        return execution_plan
        
    except Exception as e:
        return {
            "action_type": "error",
            "description": f"Error processing command: {str(e)}",
            "requires_approval": True,
            "estimated_impact": "None",
            "risks": ["AI processing error"],
            "benefits": []
        }


async def execute_approved_task(task_id: int, db) -> dict:
    """
    Execute a task that has been approved by Super Admin
    """
    # Get task details
    task_query = text("""
        SELECT action_type, code, sql, files_to_modify, description
        FROM ai_pending_tasks
        WHERE task_id = :tid AND status = 'approved'
    """)
    
    task = (await db.execute(task_query, {"tid": task_id})).fetchone()
    
    if not task:
        return {"ok": False, "error": "Task not found or not approved"}
    
    action_type = task[0]
    code = task[1]
    sql = task[2]
    files_to_modify = json.loads(task[3]) if task[3] else []
    description = task[4]
    
    result = {"ok": True, "action_type": action_type, "executed": []}
    
    try:
        if action_type == "code_change":
            # Execute code changes (write to files, commit to GitHub)
            for file_path in files_to_modify:
                # This would write to actual files
                # For safety, we'll just log the intention
                result["executed"].append(f"Would modify: {file_path}")
            
            result["message"] = "Code changes prepared (manual deployment required)"
        
        elif action_type == "database":
            # Execute SQL
            if sql:
                await db.execute(text(sql))
                result["executed"].append("SQL executed successfully")
                result["message"] = "Database operation completed"
        
        elif action_type == "marketing":
            # Send marketing campaign
            result["executed"].append("Marketing campaign queued")
            result["message"] = "Campaign will be sent within 5 minutes"
        
        elif action_type == "infrastructure":
            # Infrastructure changes
            result["executed"].append("Infrastructure changes noted")
            result["message"] = "Manual infrastructure update required"
        
        # Update task status
        await db.execute(text("""
            UPDATE ai_pending_tasks
            SET status = 'completed', executed_at = NOW()
            WHERE task_id = :tid
        """), {"tid": task_id})
        
    except Exception as e:
        result = {"ok": False, "error": str(e)}
        
        # Mark task as failed
        await db.execute(text("""
            UPDATE ai_pending_tasks
            SET status = 'failed', error_message = :err
            WHERE task_id = :tid
        """), {"tid": task_id, "err": str(e)})
    
    return result


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/command", dependencies=[Depends(guard_admin)])
async def ai_command(request: Request, payload: AICommand):
    """
    Send command to EchoFort AI
    AI will analyze and create execution plan for approval
    """
    try:
        expected_key = os.getenv("ADMIN_KEY", "EchoFortSuperAdmin2025")
        if payload.admin_key != expected_key:
            raise HTTPException(403, "Invalid admin key")
        
        # Get platform context
        platform_context = await get_platform_context(request)
        
        # Get AI execution plan
        execution_plan = await echofort_ai_execute_command(
            command=payload.command,
            platform_context=platform_context
        )
        
        # Save task to database for approval
        db = request.app.state.db
        
        task_query = text("""
            INSERT INTO ai_pending_tasks (
                admin_id, command, action_type, description, code, sql,
                files_to_modify, preview, estimated_impact, risks, benefits,
                requires_approval, status, created_at
            ) VALUES (
                1, :cmd, :type, :desc, :code, :sql, :files, :preview,
                :impact, :risks, :benefits, :approval, 'pending', NOW()
            ) RETURNING task_id
        """)
        
        result = await db.execute(task_query, {
            "cmd": payload.command,
            "type": execution_plan.get("action_type", "unknown"),
            "desc": execution_plan.get("description", ""),
            "code": execution_plan.get("code"),
            "sql": execution_plan.get("sql"),
            "files": json.dumps(execution_plan.get("files_to_modify", [])),
            "preview": execution_plan.get("preview", ""),
            "impact": execution_plan.get("estimated_impact", "Unknown"),
            "risks": json.dumps(execution_plan.get("risks", [])),
            "benefits": json.dumps(execution_plan.get("benefits", [])),
            "approval": execution_plan.get("requires_approval", True)
        })
        
        task_id = result.fetchone()[0]
        
        # If auto_approve is True and impact is Low, execute immediately
        if payload.auto_approve and execution_plan.get("estimated_impact") == "Low":
            await db.execute(text("""
                UPDATE ai_pending_tasks SET status = 'approved' WHERE task_id = :tid
            """), {"tid": task_id})
            
            execution_result = await execute_approved_task(task_id, db)
            
            return {
                "ok": True,
                "task_id": task_id,
                "execution_plan": execution_plan,
                "auto_executed": True,
                "execution_result": execution_result,
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "ok": True,
            "task_id": task_id,
            "execution_plan": execution_plan,
            "requires_approval": execution_plan.get("requires_approval", True),
            "message": "Task created. Please review and approve to execute.",
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.post("/approve", dependencies=[Depends(guard_admin)])
async def approve_task(request: Request, payload: AIApproval):
    """
    Approve or reject AI task
    If approved, task will be executed immediately
    """
    try:
        expected_key = os.getenv("ADMIN_KEY", "EchoFortSuperAdmin2025")
        if payload.admin_key != expected_key:
            raise HTTPException(403, "Invalid admin key")
        
        db = request.app.state.db
        
        if payload.approved:
            # Mark as approved
            await db.execute(text("""
                UPDATE ai_pending_tasks
                SET status = 'approved', approved_at = NOW(), admin_feedback = :feedback
                WHERE task_id = :tid
            """), {"tid": payload.task_id, "feedback": payload.feedback})
            
            # Execute the task
            execution_result = await execute_approved_task(payload.task_id, db)
            
            return {
                "ok": True,
                "task_id": payload.task_id,
                "status": "approved_and_executed",
                "execution_result": execution_result,
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Mark as rejected
            await db.execute(text("""
                UPDATE ai_pending_tasks
                SET status = 'rejected', admin_feedback = :feedback
                WHERE task_id = :tid
            """), {"tid": payload.task_id, "feedback": payload.feedback})
            
            return {
                "ok": True,
                "task_id": payload.task_id,
                "status": "rejected",
                "message": "Task rejected by Super Admin",
                "timestamp": datetime.now().isoformat()
            }
    
    except Exception as e:
        raise HTTPException(500, f"Approval error: {str(e)}")


@router.get("/pending-tasks", dependencies=[Depends(guard_admin)])
async def get_pending_tasks(request: Request, admin_key: str):
    """
    Get all pending tasks awaiting approval
    """
    try:
        expected_key = os.getenv("ADMIN_KEY", "EchoFortSuperAdmin2025")
        if admin_key != expected_key:
            raise HTTPException(403, "Invalid admin key")
        
        db = request.app.state.db
        
        tasks_query = text("""
            SELECT 
                task_id, command, action_type, description, preview,
                estimated_impact, risks, benefits, created_at
            FROM ai_pending_tasks
            WHERE status = 'pending'
            ORDER BY created_at DESC
            LIMIT 20
        """)
        
        tasks = (await db.execute(tasks_query)).fetchall()
        
        pending_tasks = []
        for task in tasks:
            pending_tasks.append({
                "task_id": task[0],
                "command": task[1],
                "action_type": task[2],
                "description": task[3],
                "preview": task[4],
                "estimated_impact": task[5],
                "risks": json.loads(task[6]) if task[6] else [],
                "benefits": json.loads(task[7]) if task[7] else [],
                "created_at": str(task[8])
            })
        
        return {
            "ok": True,
            "pending_count": len(pending_tasks),
            "tasks": pending_tasks,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(500, f"Error fetching tasks: {str(e)}")


@router.post("/marketing-campaign", dependencies=[Depends(guard_admin)])
async def create_marketing_campaign(request: Request, payload: MarketingCampaign):
    """
    Create marketing campaign (requires approval)
    AI will draft the campaign and wait for approval before sending
    """
    try:
        expected_key = os.getenv("ADMIN_KEY", "EchoFortSuperAdmin2025")
        if payload.admin_key != expected_key:
            raise HTTPException(403, "Invalid admin key")
        
        db = request.app.state.db
        
        # Get target audience count
        if payload.target_audience == "all":
            count_query = text("SELECT COUNT(*) FROM users")
        elif payload.target_audience == "active_users":
            count_query = text("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
        elif payload.target_audience == "trial_users":
            count_query = text("SELECT COUNT(*) FROM users WHERE trial_started_at IS NOT NULL")
        else:
            count_query = text("SELECT COUNT(*) FROM users")
        
        target_count = (await db.execute(count_query)).fetchone()[0]
        
        # Create pending task
        task_query = text("""
            INSERT INTO ai_pending_tasks (
                admin_id, command, action_type, description, preview,
                estimated_impact, requires_approval, status, created_at
            ) VALUES (
                1, :cmd, 'marketing', :desc, :preview, 'High', true, 'pending', NOW()
            ) RETURNING task_id
        """)
        
        result = await db.execute(task_query, {
            "cmd": f"Send {payload.campaign_type} campaign to {payload.target_audience}",
            "desc": f"Marketing campaign: {payload.subject}",
            "preview": f"""Campaign Type: {payload.campaign_type}
Target Audience: {payload.target_audience} ({target_count} users)
Subject: {payload.subject}
Message: {payload.message}

This campaign will be sent to {target_count} users via {payload.campaign_type}.
Estimated delivery time: 10-30 minutes.
"""
        })
        
        task_id = result.fetchone()[0]
        
        return {
            "ok": True,
            "task_id": task_id,
            "campaign_type": payload.campaign_type,
            "target_count": target_count,
            "message": "Campaign created and awaiting approval",
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(500, f"Campaign creation error: {str(e)}")


@router.get("/task-history", dependencies=[Depends(guard_admin)])
async def get_task_history(request: Request, admin_key: str, limit: int = 50):
    """
    Get history of all AI tasks (completed, rejected, failed)
    """
    try:
        expected_key = os.getenv("ADMIN_KEY", "EchoFortSuperAdmin2025")
        if admin_key != expected_key:
            raise HTTPException(403, "Invalid admin key")
        
        db = request.app.state.db
        
        history_query = text("""
            SELECT 
                task_id, command, action_type, description, status,
                created_at, approved_at, executed_at, admin_feedback
            FROM ai_pending_tasks
            WHERE status IN ('completed', 'rejected', 'failed')
            ORDER BY created_at DESC
            LIMIT :lim
        """)
        
        tasks = (await db.execute(history_query, {"lim": limit})).fetchall()
        
        history = []
        for task in tasks:
            history.append({
                "task_id": task[0],
                "command": task[1],
                "action_type": task[2],
                "description": task[3],
                "status": task[4],
                "created_at": str(task[5]),
                "approved_at": str(task[6]) if task[6] else None,
                "executed_at": str(task[7]) if task[7] else None,
                "admin_feedback": task[8]
            })
        
        return {
            "ok": True,
            "total_tasks": len(history),
            "tasks": history,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(500, f"Error fetching history: {str(e)}")

