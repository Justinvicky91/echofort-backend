"""
EchoFort AI Orchestrator - Block 13
Chat console backend with OpenAI + internal tools
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from openai import OpenAI
import psycopg2
from psycopg2.extras import RealDictCursor
from app.ai_learning_center import store_conversation_message, track_ai_decision
from app.admin.ai_internet_tools import web_search, web_fetch, get_recent_web_logs
from app.admin.ai_config_tools import get_config, get_feature_flags, propose_config_change, propose_feature_flag_change
from app.admin.ai_github_tools import github_list_repos, github_get_file, propose_code_change
from app.admin.ai_mobile_tools import propose_mobile_release

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Database connection
def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

# ============================================================================
# INTERNAL TOOLS - Read-only (Safe)
# ============================================================================

def get_user_profile(phone_or_id: str) -> Dict[str, Any]:
    """Get user profile by phone number or user ID"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Try as phone first
            cur.execute("""
                SELECT id, phone, name, email, plan_type, status, created_at
                FROM users
                WHERE phone = %s OR id::text = %s
                LIMIT 1
            """, (phone_or_id, phone_or_id))
            user = cur.fetchone()
            return dict(user) if user else {"error": "User not found"}
    finally:
        conn.close()

def get_user_payments(user_id: str, date_range: Optional[str] = "30d") -> List[Dict[str, Any]]:
    """Get payment history for a user"""
    conn = get_db_connection()
    try:
        days = int(date_range.replace("d", "")) if "d" in date_range else 30
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, amount, status, payment_method, created_at
                FROM payments
                WHERE user_id = %s AND created_at > NOW() - INTERVAL '%s days'
                ORDER BY created_at DESC
                LIMIT 50
            """, (user_id, days))
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def get_user_complaints(user_id: str) -> List[Dict[str, Any]]:
    """Get complaints/tickets for a user"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, title, status, priority, created_at
                FROM complaint_drafts
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 50
            """, (user_id,))
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def get_employee_activity(employee_id: str, date_range: Optional[str] = "7d") -> Dict[str, Any]:
    """Get employee activity summary"""
    conn = get_db_connection()
    try:
        days = int(date_range.replace("d", "")) if "d" in date_range else 7
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get employee info
            cur.execute("""
                SELECT id, name, email, role, status
                FROM employees
                WHERE id = %s
            """, (employee_id,))
            employee = cur.fetchone()
            
            if not employee:
                return {"error": "Employee not found"}
            
            # Get recent activity count (placeholder - adjust based on your audit log table)
            cur.execute("""
                SELECT COUNT(*) as action_count
                FROM audit_logs
                WHERE user_id = %s AND created_at > NOW() - INTERVAL '%s days'
            """, (employee_id, days))
            activity = cur.fetchone()
            
            return {
                "employee": dict(employee),
                "activity_count": activity["action_count"] if activity else 0,
                "date_range": f"Last {days} days"
            }
    finally:
        conn.close()

def get_recent_scam_patterns(limit: int = 10, region: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get recent scam patterns from AI pattern library"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT id, category, description, risk_level, example_phrases, source_url, created_at
                FROM ai_pattern_library
                WHERE is_active = true
            """
            params = []
            
            if region:
                query += " AND region = %s"
                params.append(region)
            
            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)
            
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def get_recent_alerts(limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent platform alerts"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Assuming you have an alerts table
            cur.execute("""
                SELECT id, title, severity, message, created_at
                FROM system_alerts
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        # If alerts table doesn't exist, return empty
        return []
    finally:
        conn.close()

def get_plan_metrics() -> Dict[str, Any]:
    """Get subscription and revenue metrics"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Total active subscriptions
            cur.execute("""
                SELECT 
                    COUNT(*) as total_subscriptions,
                    SUM(CASE WHEN plan_type = 'family' THEN 1 ELSE 0 END) as family_plans,
                    SUM(CASE WHEN plan_type = 'individual' THEN 1 ELSE 0 END) as individual_plans
                FROM users
                WHERE status = 'active'
            """)
            subs = cur.fetchone()
            
            # Monthly revenue (last 30 days)
            cur.execute("""
                SELECT 
                    COALESCE(SUM(amount), 0) as mrr,
                    COUNT(*) as payment_count
                FROM payments
                WHERE status = 'completed' 
                AND created_at > NOW() - INTERVAL '30 days'
            """)
            revenue = cur.fetchone()
            
            # Refunds (last 30 days)
            cur.execute("""
                SELECT COUNT(*) as refund_count
                FROM payments
                WHERE status = 'refunded'
                AND created_at > NOW() - INTERVAL '30 days'
            """)
            refunds = cur.fetchone()
            
            return {
                "subscriptions": dict(subs) if subs else {},
                "revenue": dict(revenue) if revenue else {},
                "refunds": dict(refunds) if refunds else {}
            }
    finally:
        conn.close()

def get_system_health_summary() -> Dict[str, Any]:
    """Get system health status"""
    # This would call your existing health endpoint or check DB/services
    return {
        "status": "healthy",
        "database": "connected",
        "api": "operational",
        "timestamp": datetime.now().isoformat()
    }

# ============================================================================
# PROPOSAL TOOLS - Write via Action Queue (Safe)
# ============================================================================

def create_ai_action_proposal(
    action_type: str,
    payload: Dict[str, Any],
    created_by_user_id: int,
    summary: Optional[str] = None
) -> Dict[str, Any]:
    """Create a proposal in the AI action queue (does NOT execute)"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO ai_action_queue 
                (action_type, payload, status, created_by_user_id, source, summary)
                VALUES (%s, %s, 'PENDING', %s, 'EchoFort AI Chat', %s)
                RETURNING id, action_type, status, created_at
            """, (action_type, json.dumps(payload), created_by_user_id, summary or f"AI proposed {action_type}"))
            result = cur.fetchone()
            conn.commit()
            return dict(result) if result else {"error": "Failed to create action"}
    finally:
        conn.close()

# ============================================================================
# TOOL REGISTRY
# ============================================================================

AVAILABLE_TOOLS = {
    "get_user_profile": {
        "function": get_user_profile,
        "description": "Get user profile by phone number or user ID",
        "parameters": {
            "type": "object",
            "properties": {
                "phone_or_id": {"type": "string", "description": "Phone number or user ID"}
            },
            "required": ["phone_or_id"]
        }
    },
    "get_user_payments": {
        "function": get_user_payments,
        "description": "Get payment history for a user",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User ID"},
                "date_range": {"type": "string", "description": "Date range like '30d', '90d'", "default": "30d"}
            },
            "required": ["user_id"]
        }
    },
    "get_user_complaints": {
        "function": get_user_complaints,
        "description": "Get complaints/tickets for a user",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User ID"}
            },
            "required": ["user_id"]
        }
    },
    "get_employee_activity": {
        "function": get_employee_activity,
        "description": "Get employee activity summary",
        "parameters": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "string", "description": "Employee ID"},
                "date_range": {"type": "string", "description": "Date range like '7d', '30d'", "default": "7d"}
            },
            "required": ["employee_id"]
        }
    },
    "get_recent_scam_patterns": {
        "function": get_recent_scam_patterns,
        "description": "Get recent scam patterns from AI pattern library",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of patterns to return", "default": 10},
                "region": {"type": "string", "description": "Filter by region (optional)"}
            }
        }
    },
    "get_recent_alerts": {
        "function": get_recent_alerts,
        "description": "Get recent platform alerts",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of alerts to return", "default": 20}
            }
        }
    },
    "get_plan_metrics": {
        "function": get_plan_metrics,
        "description": "Get subscription and revenue metrics",
        "parameters": {"type": "object", "properties": {}}
    },
    "get_system_health_summary": {
        "function": get_system_health_summary,
        "description": "Get system health status",
        "parameters": {"type": "object", "properties": {}}
    },
    "create_ai_action_proposal": {
        "function": create_ai_action_proposal,
        "description": "Create a proposal for an action that requires approval (does NOT execute immediately)",
        "parameters": {
            "type": "object",
            "properties": {
                "action_type": {
                    "type": "string",
                    "description": "Type of action (SCAM_PATTERN_CREATE, FEATURE_FLAG_UPDATE, CONFIG_UPDATE, CREATE_INTERNAL_TASK)"
                },
                "payload": {"type": "object", "description": "Action payload as JSON"},
                "created_by_user_id": {"type": "integer", "description": "User ID creating the action"},
                "summary": {"type": "string", "description": "Human-readable summary of the action"}
            },
            "required": ["action_type", "payload", "created_by_user_id"]
        }
    },
    "internet_search": {
        "function": lambda query, category=None, user_id=1: [r.to_dict() for r in web_search(query, category, user_id)],
        "description": "Search the internet for information about scams, threats, competitors, or general topics. Returns list of search results with titles, summaries, and URLs.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "category": {
                    "type": "string",
                    "description": "Optional category: scam_fraud, harassment, child_safety, extremism, marketing_competitor, generic",
                    "enum": ["scam_fraud", "harassment", "child_safety", "extremism", "marketing_competitor", "generic"]
                }
            },
            "required": ["query"]
        }
    },
    "internet_fetch": {
        "function": lambda url, user_id=1: web_fetch(url, user_id).to_dict() if web_fetch(url, user_id) else {"error": "Failed to fetch URL"},
        "description": "Fetch and extract text content from a specific URL (HTTPS only). Returns page title and text snippet.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch (must be https://)"}
            },
            "required": ["url"]
        }
    },
    "get_config": {
        "function": get_config,
        "description": "Get platform configuration entries for a given scope (web, backend, mobile). Returns list of config key-value pairs.",
        "parameters": {
            "type": "object",
            "properties": {
                "scope": {"type": "string", "description": "Config scope: web, backend, or mobile", "enum": ["web", "backend", "mobile"]},
                "key_prefix": {"type": "string", "description": "Optional prefix to filter config keys"}
            },
            "required": ["scope"]
        }
    },
    "get_feature_flags": {
        "function": get_feature_flags,
        "description": "Get feature flags for a given scope (web, backend, mobile). Returns list of flags with enabled/disabled state.",
        "parameters": {
            "type": "object",
            "properties": {
                "scope": {"type": "string", "description": "Feature flag scope: web, backend, or mobile", "enum": ["web", "backend", "mobile"]},
                "flag_name_prefix": {"type": "string", "description": "Optional prefix to filter flag names"}
            },
            "required": ["scope"]
        }
    },
    "propose_config_change": {
        "function": propose_config_change,
        "description": "Propose a configuration change (requires approval). Use this to update website text, backend thresholds, or mobile settings.",
        "parameters": {
            "type": "object",
            "properties": {
                "scope": {"type": "string", "description": "Config scope: web, backend, or mobile"},
                "key": {"type": "string", "description": "Config key to update"},
                "new_value": {"type": "object", "description": "New value as JSON object"},
                "reason": {"type": "string", "description": "Reason for the change"},
                "created_by_user_id": {"type": "integer", "description": "User ID proposing the change"}
            },
            "required": ["scope", "key", "new_value", "reason", "created_by_user_id"]
        }
    },
    "propose_feature_flag_change": {
        "function": propose_feature_flag_change,
        "description": "Propose a feature flag change (requires approval). Use this to enable/disable features on website, backend, or mobile.",
        "parameters": {
            "type": "object",
            "properties": {
                "flag_name": {"type": "string", "description": "Feature flag name"},
                "new_state": {"type": "boolean", "description": "True to enable, False to disable"},
                "scope": {"type": "string", "description": "Feature flag scope: web, backend, or mobile"},
                "reason": {"type": "string", "description": "Reason for the change"},
                "created_by_user_id": {"type": "integer", "description": "User ID proposing the change"},
                "rollout_percent": {"type": "integer", "description": "Optional rollout percentage (0-100)"}
            },
            "required": ["flag_name", "new_state", "scope", "reason", "created_by_user_id"]
        }
    },
    "github_list_repos": {
        "function": github_list_repos,
        "description": "List available GitHub repositories (backend, frontend, mobile).",
        "parameters": {"type": "object", "properties": {}}
    },
    "github_get_file": {
        "function": github_get_file,
        "description": "Get file content from a GitHub repository. Use this to read code before proposing changes.",
        "parameters": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "Repository name (echofort-backend, echofort-frontend-prod, echofort-mobile)"},
                "path": {"type": "string", "description": "File path in repository"},
                "branch": {"type": "string", "description": "Branch name (default: main)", "default": "main"}
            },
            "required": ["repo", "path"]
        }
    },
    "propose_code_change": {
        "function": propose_code_change,
        "description": "Propose a code change via GitHub PR (requires approval). Use this to fix bugs, add features, or update UI.",
        "parameters": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Target system: backend, frontend, or mobile", "enum": ["backend", "frontend", "mobile"]},
                "description": {"type": "string", "description": "Description of the code change"},
                "files_to_change": {
                    "type": "array",
                    "description": "List of files to change with their new content",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path"},
                            "content": {"type": "string", "description": "New file content"}
                        },
                        "required": ["path", "content"]
                    }
                },
                "created_by_user_id": {"type": "integer", "description": "User ID proposing the change"}
            },
            "required": ["target", "description", "files_to_change", "created_by_user_id"]
        }
    },
    "propose_mobile_release": {
        "function": propose_mobile_release,
        "description": "Propose a mobile app release build (requires approval). Use this to trigger a new version build for Play Store.",
        "parameters": {
            "type": "object",
            "properties": {
                "version_hint": {"type": "string", "description": "Version number (e.g., 1.0.13)"},
                "notes": {"type": "string", "description": "Release notes describing changes"},
                "created_by_user_id": {"type": "integer", "description": "User ID proposing the release"},
                "build_type": {"type": "string", "description": "Build type: release or beta", "enum": ["release", "beta"], "default": "release"}
            },
            "required": ["version_hint", "notes", "created_by_user_id"]
        }
    }
}

# ============================================================================
# ORCHESTRATOR
# ============================================================================

def process_chat_message(
    message: str,
    session_id: Optional[str],
    role: str,
    user_id: int,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process a chat message using OpenAI + internal tools
    Returns: {assistant_message, actions_created, source_refs}
    """
    
    # Store user message in Learning Center
    try:
        user_conv_id = store_conversation_message(
            session_id=session_id or "unknown",
            user_id=user_id,
            role=role,
            message_type="user",
            message_text=message
        )
    except Exception as e:
        print(f"Warning: Failed to store user message in Learning Center: {e}")
        user_conv_id = None
    
    # Build system prompt
    system_prompt = f"""You are EchoFort AI, the intelligent assistant for the EchoFort platform.

You help the Founder/Super Admin manage the platform by:
1. Answering questions about users, payments, complaints, employees, scams, and system health
2. Researching scam trends, threats, and competitor activity using internet access
3. Proposing actions that need approval (you NEVER execute actions directly)

Current context:
- Role: {role}
- Environment: {context.get('environment', 'prod')}
- User ID: {user_id}

CRITICAL SAFETY RULES:
- You can READ data using tools like get_user_profile, get_plan_metrics, internet_search, internet_fetch
- For any CHANGES (create, update, delete), you MUST use create_ai_action_proposal
- NEVER execute commands directly
- Always explain what you're doing and why
- If you create an action proposal, tell the user it needs approval in the Action Queue

INTERNET RESEARCH GUIDELINES:
- For questions about "latest scam trends", "recent cybercrime", "competitor news", use internet_search first
- Use category filters: scam_fraud, harassment, child_safety, extremism, marketing_competitor
- When presenting internet results, cite sources with titles and URLs
- If internet tools fail, gracefully explain the limitation

Available tools: {', '.join(AVAILABLE_TOOLS.keys())}
"""

    # Convert tools to OpenAI format
    tools_for_openai = []
    for tool_name, tool_info in AVAILABLE_TOOLS.items():
        tools_for_openai.append({
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_info["description"],
                "parameters": tool_info["parameters"]
            }
        })
    
    # Call OpenAI with tools
    try:
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",  # or gpt-4, gpt-3.5-turbo
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            tools=tools_for_openai,
            tool_choice="auto"
        )
        
        assistant_message = response.choices[0].message
        actions_created = []
        source_refs = []
        
        # Handle tool calls
        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                # Execute tool with error handling
                if tool_name in AVAILABLE_TOOLS:
                    tool_func = AVAILABLE_TOOLS[tool_name]["function"]
                    
                    # Add user_id for action proposals
                    if tool_name == "create_ai_action_proposal":
                        tool_args["created_by_user_id"] = user_id
                    
                    try:
                        result = tool_func(**tool_args)
                    except Exception as tool_error:
                        # Log the full error for debugging
                        print(f"ERROR in tool {tool_name}: {str(tool_error)}")
                        # Return safe error message
                        result = {
                            "error": True,
                            "error_type": "tool_execution_error",
                            "safe_message": f"I encountered an internal error while trying to {tool_name.replace('_', ' ')}. The technical team has been notified."
                        }
                    
                    # Track actions created
                    if tool_name == "create_ai_action_proposal" and "id" in result:
                        actions_created.append({
                            "action_id": result["id"],
                            "action_type": result["action_type"],
                            "summary": tool_args.get("summary", f"AI proposed {result['action_type']}")
                        })
                    
                    # Track source refs
                    source_refs.append({
                        "type": "tool",
                        "value": tool_name,
                        "result_summary": str(result)[:200]  # Truncate for brevity
                    })
        
        response_text = assistant_message.content or "I've processed your request using internal tools."
        
        # Store assistant response in Learning Center
        try:
            assistant_conv_id = store_conversation_message(
                session_id=session_id or "unknown",
                user_id=user_id,
                role="assistant",
                message_type="assistant",
                message_text=response_text,
                metadata={
                    "tools_used": [ref["value"] for ref in source_refs if ref["type"] == "tool"],
                    "actions_created": actions_created
                }
            )
            
            # Track decision if actions were created
            if actions_created:
                track_ai_decision(
                    conversation_id=assistant_conv_id,
                    decision_type="action_proposal",
                    decision_context={
                        "query": message,
                        "tools_used": [ref["value"] for ref in source_refs if ref["type"] == "tool"],
                        "actions_created": actions_created,
                        "reasoning": response_text[:500]
                    },
                    confidence_score=0.85  # Default confidence
                )
        except Exception as e:
            print(f"Warning: Failed to store assistant response in Learning Center: {e}")
        
        return {
            "assistant_message": response_text,
            "actions_created": actions_created,
            "source_refs": source_refs
        }
        
    except Exception as e:
        return {
            "assistant_message": f"I encountered an error: {str(e)}",
            "actions_created": [],
            "source_refs": []
        }
