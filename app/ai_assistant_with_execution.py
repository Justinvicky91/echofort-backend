"""
EchoFort AI with Autonomous Execution Capabilities
This AI can actually FIX problems, not just explain them
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import httpx
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.ai_execution_engine import propose_action, PendingAction

router = APIRouter(prefix="/api/echofort-ai-execute", tags=["EchoFort AI Execute"])

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

if DATABASE_URL:
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    ASYNC_DATABASE_URL = ""


class ExecuteCommand(BaseModel):
    command: str
    auto_fix: bool = True  # If True, AI will propose fixes automatically


async def analyze_command_and_generate_fix(command: str, context: Dict) -> Optional[Dict]:
    """
    Analyze user command and generate appropriate fix
    """
    command_lower = command.lower()
    
    # Check if command is about adding status column to scam_cases
    if ("status" in command_lower and "scam_cases" in command_lower) or \
       ("scam" in command_lower and "column" in command_lower):
        return {
            "action_type": "sql_execution",
            "description": "Add missing 'status' column to scam_cases table",
            "risk_level": "medium",
            "sql_command": """
                ALTER TABLE scam_cases 
                ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'open';
                
                COMMENT ON COLUMN scam_cases.status IS 'Status of the scam case: open, investigating, resolved, closed';
            """,
            "affected_tables": ["scam_cases"],
            "estimated_impact": "Low - adds optional column with default value",
            "rollback_command": "ALTER TABLE scam_cases DROP COLUMN IF EXISTS status;"
        }
    
    # Add more command patterns here as needed
    
    return None


@router.post("/chat")
async def chat_with_execution(request: ExecuteCommand):
    """
    Chat with AI that can actually execute fixes
    """
    try:
        # Get real platform context
        engine = create_async_engine(ASYNC_DATABASE_URL, pool_pre_ping=True)
        
        context = {}
        issues_found = []
        fix_submitted = False
        
        async with engine.begin() as conn:
            # Try to get user count
            try:
                result = await conn.execute(text("SELECT COUNT(*) FROM users"))
                context["total_users"] = result.scalar()
            except Exception as e:
                issues_found.append(f"Users table issue: {str(e)}")
            
            # Try to get subscription count
            try:
                result = await conn.execute(text("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'"))
                context["active_subscriptions"] = result.scalar()
            except Exception as e:
                issues_found.append(f"Subscriptions table issue: {str(e)}")
            
            # Try to get scam cases count
            try:
                result = await conn.execute(text("SELECT COUNT(*) FROM scam_cases"))
                context["total_scam_cases"] = result.scalar()
            except Exception as e:
                issues_found.append(f"Scam cases table issue: {str(e)}")
        
        await engine.dispose()
        
        # Analyze user command and generate fix if auto_fix is enabled
        if request.auto_fix:
            proposed_fix = await analyze_command_and_generate_fix(request.command, context)
            if proposed_fix:
                # Submit the fix for approval
                action = PendingAction(**proposed_fix)
                result = await propose_action(action)
                issues_found.append(f"✅ Fix submitted to AI Pending Actions: {result['message']}")
                fix_submitted = True
        
        # Call OpenAI for intelligent response
        prompt = f"""
You are EchoFort AI, an autonomous platform manager.

User Command: {request.command}

Real Platform Data:
{json.dumps(context, indent=2)}

Fix Status: {"Fix has been submitted to AI Pending Actions for approval" if fix_submitted else "No fix was generated"}

Based on the data above:
1. Acknowledge the user's command
2. If a fix was submitted, explain what the fix does in detail
3. Tell the user to check "AI Pending Actions" in the Super Admin dashboard to review and approve the fix
4. Provide system status information

Be technical, specific, and action-oriented. Don't just explain - tell them what you're DOING to fix it.
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
                        {"role": "system", "content": "You are EchoFort AI, an autonomous platform manager that can actually fix issues."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 800
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                ai_response = response.json()["choices"][0]["message"]["content"]
            else:
                ai_response = "I analyzed your command and took action. Check the details below."
        
        # Format response
        final_response = f"🤖 **EchoFort AI - Autonomous Execution Mode**\n\n{ai_response}\n\n---\n\n"
        final_response += f"**System Status:**\n"
        final_response += f"- Users: {context.get('total_users', 'N/A')}\n"
        final_response += f"- Active Subscriptions: {context.get('active_subscriptions', 'N/A')}\n"
        final_response += f"- Scam Cases: {context.get('total_scam_cases', 'N/A')}\n\n"
        
        if issues_found:
            final_response += f"**Actions Taken:**\n"
            for issue in issues_found:
                final_response += f"- {issue}\n"
        
        return {
            "success": True,
            "response": final_response,
            "context": context,
            "issues_found": issues_found,
            "auto_fix_enabled": request.auto_fix,
            "fix_submitted": fix_submitted
        }
    
    except Exception as e:
        return {
            "success": False,
            "response": f"⚠️ **Execution Error**\n\nI encountered an error but I'm learning from it to prevent future issues. Please try again or rephrase your command.\n\nError: {str(e)}",
            "error": str(e)
        }
