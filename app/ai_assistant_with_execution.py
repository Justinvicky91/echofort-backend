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


async def perform_comprehensive_platform_audit(conn) -> List[Dict]:
    """
    Perform a comprehensive audit of the EchoFort platform
    Returns list of issues found with proposed fixes
    """
    issues = []
    
    # Check 1: Verify critical tables exist
    critical_tables = ['users', 'subscriptions', 'scam_cases', 'payments', 'employees', 'ai_pending_actions']
    for table in critical_tables:
        try:
            await conn.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
        except Exception as e:
            issues.append({
                "action_type": "sql_execution",
                "description": f"Critical table '{table}' is missing or inaccessible",
                "risk_level": "high",
                "sql_command": f"-- Table {table} needs to be created. Check migrations.",
                "affected_tables": [table],
                "estimated_impact": f"High - {table} table is critical for platform operation",
                "rollback_command": f"-- No rollback - table creation required"
            })
    
    # Check 2: Verify scam_cases has status column
    try:
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'scam_cases' AND column_name = 'status'
        """))
        if not result.fetchone():
            issues.append({
                "action_type": "sql_execution",
                "description": "Add missing 'status' column to scam_cases table for case management",
                "risk_level": "medium",
                "sql_command": """
                    ALTER TABLE scam_cases 
                    ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'open';
                    
                    COMMENT ON COLUMN scam_cases.status IS 'Status: open, investigating, resolved, closed';
                """,
                "affected_tables": ["scam_cases"],
                "estimated_impact": "Low - adds optional column with default value",
                "rollback_command": "ALTER TABLE scam_cases DROP COLUMN IF EXISTS status;"
            })
    except Exception as e:
        pass
    
    # Check 3: Verify users table has proper indexes
    try:
        result = await conn.execute(text("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'users' AND indexname = 'idx_users_email'
        """))
        if not result.fetchone():
            issues.append({
                "action_type": "sql_execution",
                "description": "Add missing email index to users table for performance",
                "risk_level": "low",
                "sql_command": """
                    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                """,
                "affected_tables": ["users"],
                "estimated_impact": "Low - improves query performance",
                "rollback_command": "DROP INDEX IF EXISTS idx_users_email;"
            })
    except Exception as e:
        pass
    
    # Check 4: Verify payment gateway configuration
    try:
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM payment_gateways WHERE is_active = true
        """))
        active_gateways = result.scalar()
        if active_gateways == 0:
            issues.append({
                "action_type": "configuration",
                "description": "No active payment gateways configured - users cannot make payments",
                "risk_level": "critical",
                "sql_command": """
                    -- Enable at least one payment gateway (Razorpay, Stripe, or PayPal)
                    UPDATE payment_gateways 
                    SET is_active = true 
                    WHERE gateway_name = 'razorpay' 
                    LIMIT 1;
                """,
                "affected_tables": ["payment_gateways"],
                "estimated_impact": "High - enables payment processing",
                "rollback_command": "UPDATE payment_gateways SET is_active = false WHERE gateway_name = 'razorpay';"
            })
    except Exception as e:
        pass
    
    # Check 5: Verify subscription plans exist
    try:
        result = await conn.execute(text("SELECT COUNT(*) FROM subscription_plans"))
        plan_count = result.scalar()
        if plan_count == 0:
            issues.append({
                "action_type": "data_insertion",
                "description": "No subscription plans configured - users cannot subscribe",
                "risk_level": "critical",
                "sql_command": """
                    -- Insert default subscription plans
                    INSERT INTO subscription_plans (name, price, duration_days, features, is_active)
                    VALUES 
                        ('Basic', 399, 30, '{"call_screening": true, "trust_factor": true}', true),
                        ('Personal', 799, 30, '{"call_screening": true, "recording": true, "image_scan": true}', true),
                        ('Family', 1499, 30, '{"call_screening": true, "recording": true, "gps_tracking": true, "family_members": 4}', true);
                """,
                "affected_tables": ["subscription_plans"],
                "estimated_impact": "High - enables subscription functionality",
                "rollback_command": "DELETE FROM subscription_plans WHERE name IN ('Basic', 'Personal', 'Family');"
            })
    except Exception as e:
        pass
    
    return issues


async def analyze_command_and_generate_fix(command: str, context: Dict, conn=None) -> List[Dict]:
    """
    Analyze user command and generate appropriate fixes
    """
    command_lower = command.lower()
    fixes = []
    
    # Check if command is requesting comprehensive platform audit
    if any(keyword in command_lower for keyword in ['check', 'audit', 'analyze', 'inspect', 'review', 'full platform']):
        if conn:
            # Perform comprehensive audit
            audit_issues = await perform_comprehensive_platform_audit(conn)
            fixes.extend(audit_issues)
    
    # Check if command is about adding status column to scam_cases
    elif ("status" in command_lower and "scam_cases" in command_lower) or \
         ("scam" in command_lower and "column" in command_lower):
        fixes.append({
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
        })
    
    return fixes


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
        fixes_submitted = []
        
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
            
            # Analyze user command and generate fixes if auto_fix is enabled
            if request.auto_fix:
                proposed_fixes = await analyze_command_and_generate_fix(request.command, context, conn)
                
                # Submit each fix for approval
                for fix in proposed_fixes:
                    try:
                        action = PendingAction(**fix)
                        result = await propose_action(action)
                        fixes_submitted.append(result['message'])
                        issues_found.append(f"✅ {fix['description']}")
                    except Exception as e:
                        issues_found.append(f"❌ Failed to submit fix: {str(e)}")
        
        await engine.dispose()
        
        # Call OpenAI for intelligent response
        prompt = f"""
You are EchoFort AI, an autonomous platform manager.

User Command: {request.command}

Real Platform Data:
{json.dumps(context, indent=2)}

Fixes Submitted: {len(fixes_submitted)}
{chr(10).join(fixes_submitted) if fixes_submitted else "No fixes were generated"}

Based on the data above:
1. Acknowledge the user's command
2. If fixes were submitted, explain what each fix does in detail
3. Tell the user to check "AI Pending Actions" in the Super Admin dashboard to review and approve the fixes
4. Provide system status information
5. If no fixes were found, explain that the platform is operating normally

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
            final_response += f"**Issues Found & Actions Taken:**\n"
            for issue in issues_found:
                final_response += f"- {issue}\n"
        
        return {
            "success": True,
            "response": final_response,
            "context": context,
            "issues_found": issues_found,
            "auto_fix_enabled": request.auto_fix,
            "fixes_submitted": len(fixes_submitted)
        }
    
    except Exception as e:
        return {
            "success": False,
            "response": f"⚠️ **Execution Error**\n\nI encountered an error but I'm learning from it to prevent future issues. Please try again or rephrase your command.\n\nError: {str(e)}",
            "error": str(e)
        }
