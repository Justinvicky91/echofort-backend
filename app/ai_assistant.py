# app/ai_assistant.py - REAL OPENAI INTEGRATION
"""
EchoFort AI - Self-Evolving Platform Intelligence
Super Admin Only - Uses OpenAI GPT-4 for autonomous platform management
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
from .rbac import guard_admin
import os
import json
from openai import OpenAI

router = APIRouter(prefix="/api/ai-assistant", tags=["AI Assistant"])

# Lazy OpenAI client initialization (only when needed)
_client = None

def get_openai_client():
    """Lazy load OpenAI client to avoid startup crashes"""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(500, "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.")
        _client = OpenAI(api_key=api_key)
    return _client

class AICommand(BaseModel):
    admin_key: str
    command: str
    context: Optional[dict] = None

class AIChatMessage(BaseModel):
    admin_key: str
    message: str
    include_platform_data: bool = True

class ScamUpdate(BaseModel):
    scam_type: str
    description: str
    severity: int  # 1-10
    source: str
    keywords: list

# ============================================================================
# ECHOFORT AI CORE - OpenAI GPT-4 Integration
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
        
        # Scam detection stats (last 7 days)
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
        
        # Infrastructure costs (current month)
        cost_query = text("""
            SELECT COALESCE(SUM(amount), 0) 
            FROM infrastructure_costs
            WHERE EXTRACT(MONTH FROM date) = EXTRACT(MONTH FROM NOW())
        """)
        result = (await db.execute(cost_query)).fetchone()
        context["monthly_costs"] = float(result[0]) if result else 0.0
        
        # User growth (last 30 days)
        growth_query = text("""
            SELECT COUNT(*) FROM users
            WHERE created_at > NOW() - INTERVAL '30 days'
        """)
        result = (await db.execute(growth_query)).fetchone()
        context["new_users_30d"] = result[0] if result else 0
        
        # Calculate profit
        context["monthly_profit"] = context["monthly_revenue"] - context["monthly_costs"]
        
    except Exception as e:
        print(f"Error gathering platform context: {e}")
        context["error"] = "Partial data available"
    
    return context


async def echofort_ai_chat(message: str, platform_context: dict, conversation_history: List[dict] = None) -> str:
    """
    EchoFort AI - OpenAI GPT-4 powered intelligent assistant
    Learns from platform data and provides autonomous insights
    """
    
    # System prompt - EchoFort AI personality and capabilities
    system_prompt = f"""You are EchoFort AI, an advanced self-evolving artificial intelligence that manages and optimizes the EchoFort scam protection platform.

PLATFORM OVERVIEW:
EchoFort is India's first AI-powered scam protection platform that protects users from digital arrest scams, investment frauds, and cyber threats. The platform uses call screening, GPS tracking, screen time monitoring, and family protection features.

YOUR CAPABILITIES:
1. Business Intelligence: Analyze revenue, costs, profit, and provide financial insights
2. User Analytics: Monitor user growth, churn, engagement, and subscription patterns
3. Threat Intelligence: Track scam patterns, detection rates, and emerging threats
4. System Optimization: Suggest infrastructure improvements, cost reductions, scaling strategies
5. Predictive Analytics: Forecast revenue, user growth, and threat trends
6. Autonomous Decision Making: After 6 months of learning, make platform decisions independently
7. Customer Management: Analyze customer behavior, satisfaction, and retention
8. Risk Assessment: Identify business risks, security vulnerabilities, and compliance issues

CURRENT PLATFORM DATA:
{json.dumps(platform_context, indent=2)}

YOUR PERSONALITY:
- Professional, intelligent, and proactive
- Data-driven and analytical
- Forward-thinking and strategic
- Honest about limitations and uncertainties
- Focused on platform growth and user protection

YOUR GOALS:
1. Maximize platform revenue and profitability
2. Protect users from scams effectively
3. Optimize operational costs
4. Scale infrastructure efficiently
5. Provide actionable insights to Super Admin
6. Learn and evolve continuously

RESPONSE GUIDELINES:
- Provide specific numbers and data-driven insights
- Suggest concrete actions, not just observations
- Highlight risks and opportunities
- Be concise but comprehensive
- Use professional business language
- Include confidence levels for predictions (e.g., "85% confident")

Remember: You are the autonomous brain of EchoFort. Think strategically and act decisively."""

    # Build conversation messages
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history if available
    if conversation_history:
        messages.extend(conversation_history[-10:])  # Last 10 messages for context
    
    # Add current user message
    messages.append({"role": "user", "content": message})
    
    try:
        # Call OpenAI GPT-4
        response = get_openai_client().chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
            presence_penalty=0.6,
            frequency_penalty=0.3
        )
        
        ai_response = response.choices[0].message.content
        return ai_response
        
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return f"EchoFort AI encountered an error: {str(e)}. Please check OpenAI API key and try again."


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/chat", dependencies=[Depends(guard_admin)])
async def ai_chat(request: Request, payload: AIChatMessage):
    """
    Chat with EchoFort AI - Super Admin Only
    Real OpenAI GPT-4 integration for intelligent platform management
    """
    try:
        # Verify admin key
        expected_key = os.getenv("ADMIN_KEY", "EchoFortSuperAdmin2025")
        if payload.admin_key != expected_key:
            raise HTTPException(403, "Invalid admin key")
        
        # Gather platform context
        platform_context = {}
        if payload.include_platform_data:
            platform_context = await get_platform_context(request)
        
        # Get conversation history from database
        try:
            history_query = text("""
                SELECT message, response FROM ai_interactions
                WHERE admin_id = 1
                ORDER BY timestamp DESC
                LIMIT 5
            """)
            history_rows = (await request.app.state.db.execute(history_query)).fetchall()
            
            conversation_history = []
            for row in reversed(history_rows):
                conversation_history.append({"role": "user", "content": row[0]})
                conversation_history.append({"role": "assistant", "content": row[1]})
        except:
            conversation_history = []
        
        # Get AI response from OpenAI GPT-4
        ai_response = await echofort_ai_chat(
            message=payload.message,
            platform_context=platform_context,
            conversation_history=conversation_history
        )
        
        # Log interaction to database
        try:
            log_query = text("""
                INSERT INTO ai_interactions (admin_id, message, response, timestamp)
                VALUES (1, :msg, :resp, NOW())
            """)
            await request.app.state.db.execute(log_query, {
                "msg": payload.message,
                "resp": ai_response
            })
        except Exception as e:
            print(f"Failed to log interaction: {e}")
        
        return {
            "ok": True,
            "response": ai_response,
            "platform_data": platform_context if payload.include_platform_data else None,
            "timestamp": datetime.now().isoformat(),
            "ai_status": "EchoFort AI Online - Self-Evolution Active"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "message": "EchoFort AI encountered an error",
            "timestamp": datetime.now().isoformat()
        }


@router.get("/dashboard", dependencies=[Depends(guard_admin)])
async def ai_dashboard(request: Request, admin_key: str):
    """
    AI-generated dashboard with real-time insights
    Uses OpenAI for intelligent analysis and recommendations
    """
    try:
        expected_key = os.getenv("ADMIN_KEY", "EchoFortSuperAdmin2025")
        if admin_key != expected_key:
            raise HTTPException(403, "Invalid admin key")
        
        # Get platform context
        platform_context = await get_platform_context(request)
        
        # Ask AI to analyze the dashboard data
        analysis_prompt = f"""Analyze the current platform metrics and provide:
1. Overall health score (0-100)
2. Top 3 opportunities for growth
3. Top 3 risks or concerns
4. Revenue forecast for next month
5. Recommended actions for Super Admin

Current metrics:
{json.dumps(platform_context, indent=2)}"""
        
        ai_analysis = await echofort_ai_chat(
            message=analysis_prompt,
            platform_context=platform_context,
            conversation_history=[]
        )
        
        return {
            "ok": True,
            "timestamp": datetime.now().isoformat(),
            "metrics": platform_context,
            "ai_analysis": ai_analysis,
            "ai_status": "EchoFort AI - Autonomous Monitoring Active"
        }
    
    except Exception as e:
        raise HTTPException(500, f"AI dashboard error: {str(e)}")


@router.post("/predict", dependencies=[Depends(guard_admin)])
async def ai_predict(request: Request, payload: dict):
    """
    AI-powered predictions using OpenAI
    Predict revenue, user growth, scam trends, etc.
    """
    try:
        admin_key = payload.get("admin_key")
        prediction_type = payload.get("type")  # "revenue", "users", "scams", "churn"
        timeframe = payload.get("timeframe", "30_days")
        
        expected_key = os.getenv("ADMIN_KEY", "EchoFortSuperAdmin2025")
        if admin_key != expected_key:
            raise HTTPException(403, "Invalid admin key")
        
        # Get platform context
        platform_context = await get_platform_context(request)
        
        # Get historical data
        db = request.app.state.db
        
        if prediction_type == "revenue":
            history_query = text("""
                SELECT 
                    DATE_TRUNC('day', created_at) as date,
                    SUM(amount) as daily_revenue
                FROM subscriptions
                WHERE created_at > NOW() - INTERVAL '90 days'
                GROUP BY DATE_TRUNC('day', created_at)
                ORDER BY date DESC
                LIMIT 30
            """)
        elif prediction_type == "users":
            history_query = text("""
                SELECT 
                    DATE_TRUNC('day', created_at) as date,
                    COUNT(*) as daily_signups
                FROM users
                WHERE created_at > NOW() - INTERVAL '90 days'
                GROUP BY DATE_TRUNC('day', created_at)
                ORDER BY date DESC
                LIMIT 30
            """)
        else:
            history_query = text("""
                SELECT 
                    DATE_TRUNC('day', detected_at) as date,
                    COUNT(*) as daily_scams
                FROM digital_arrest_alerts
                WHERE detected_at > NOW() - INTERVAL '90 days'
                GROUP BY DATE_TRUNC('day', detected_at)
                ORDER BY date DESC
                LIMIT 30
            """)
        
        try:
            history_rows = (await db.execute(history_query)).fetchall()
            historical_data = [{"date": str(row[0]), "value": float(row[1])} for row in history_rows]
        except:
            historical_data = []
        
        # Ask AI to make prediction
        prediction_prompt = f"""Based on the historical data and current platform metrics, predict the {prediction_type} for the next {timeframe}.

Current Platform Metrics:
{json.dumps(platform_context, indent=2)}

Historical Data (last 30 days):
{json.dumps(historical_data, indent=2)}

Provide:
1. Predicted value for next {timeframe}
2. Confidence level (0-100%)
3. Key factors influencing the prediction
4. Potential risks or opportunities
5. Recommended actions

Format your response as JSON with these fields:
{{
  "predicted_value": <number>,
  "confidence": <0-100>,
  "trend": "increasing|decreasing|stable",
  "factors": ["factor1", "factor2", ...],
  "risks": ["risk1", "risk2", ...],
  "opportunities": ["opp1", "opp2", ...],
  "recommendations": ["action1", "action2", ...]
}}"""
        
        ai_prediction = await echofort_ai_chat(
            message=prediction_prompt,
            platform_context=platform_context,
            conversation_history=[]
        )
        
        # Try to parse JSON response
        try:
            prediction_data = json.loads(ai_prediction)
        except:
            prediction_data = {"raw_response": ai_prediction}
        
        return {
            "ok": True,
            "prediction_type": prediction_type,
            "timeframe": timeframe,
            "prediction": prediction_data,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(500, f"Prediction error: {str(e)}")


@router.post("/learn", dependencies=[Depends(guard_admin)])
async def ai_learn(request: Request, payload: dict):
    """
    AI learns from feedback and platform events
    Stores learning data for continuous improvement
    """
    try:
        feedback_type = payload.get("type")
        data = payload.get("data")
        
        learn_query = text("""
            INSERT INTO ai_learning 
            (feedback_type, data, timestamp)
            VALUES (:type, :data, NOW())
            RETURNING learning_id
        """)
        
        result = await request.app.state.db.execute(learn_query, {
            "type": feedback_type,
            "data": json.dumps(data)
        })
        
        learning_id = result.fetchone()[0]
        
        return {
            "ok": True,
            "learning_id": learning_id,
            "message": "EchoFort AI has learned from this feedback",
            "ai_status": "Continuously learning and evolving",
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(500, f"Learning error: {str(e)}")


@router.get("/status", dependencies=[Depends(guard_admin)])
async def ai_status(request: Request, admin_key: str):
    """
    Get EchoFort AI status and learning progress
    """
    try:
        expected_key = os.getenv("ADMIN_KEY", "EchoFortSuperAdmin2025")
        if admin_key != expected_key:
            raise HTTPException(403, "Invalid admin key")
        
        db = request.app.state.db
        
        # Get AI interaction count
        interaction_count = (await db.execute(text(
            "SELECT COUNT(*) FROM ai_interactions"
        ))).fetchone()[0]
        
        # Get learning data count
        learning_count = (await db.execute(text(
            "SELECT COUNT(*) FROM ai_learning"
        ))).fetchone()[0]
        
        # Calculate days since first interaction
        first_interaction = (await db.execute(text(
            "SELECT MIN(timestamp) FROM ai_interactions"
        ))).fetchone()[0]
        
        days_active = 0
        if first_interaction:
            days_active = (datetime.now() - first_interaction).days
        
        # Calculate learning progress (6 months = 180 days to full autonomy)
        learning_progress = min(100, (days_active / 180) * 100)
        
        return {
            "ok": True,
            "ai_name": "EchoFort AI",
            "status": "online",
            "openai_model": "gpt-4",
            "total_interactions": interaction_count,
            "total_learning_events": learning_count,
            "days_active": days_active,
            "learning_progress": round(learning_progress, 2),
            "autonomy_level": "supervised" if learning_progress < 100 else "autonomous",
            "capabilities": [
                "Business Intelligence",
                "Predictive Analytics",
                "Threat Detection",
                "System Optimization",
                "Customer Management",
                "Risk Assessment",
                "Autonomous Decision Making (after 6 months)"
            ],
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(500, f"Status error: {str(e)}")

