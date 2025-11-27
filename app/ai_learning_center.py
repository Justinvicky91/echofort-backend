"""
AI Learning Center Module
Handles conversation storage, decision tracking, daily digest generation, and learning from past interactions.
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_db_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def store_conversation_message(
    session_id: str,
    user_id: Optional[int],
    role: str,
    message_type: str,
    message_text: str,
    metadata: Dict[str, Any] = None
) -> int:
    """
    Store a conversation message in the database
    
    Args:
        session_id: Unique session identifier
        user_id: User ID (can be None for system messages)
        role: User role ('founder', 'admin', 'employee')
        message_type: Type of message ('user', 'assistant', 'system')
        message_text: The actual message text
        metadata: Additional metadata (tools_used, actions_created, etc.)
    
    Returns:
        Conversation ID
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO ai_conversations (session_id, user_id, role, message_type, message_text, message_metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (session_id, user_id, role, message_type, message_text, Json(metadata or {})))
        
        conversation_id = cur.fetchone()[0]
        conn.commit()
        return conversation_id
    finally:
        cur.close()
        conn.close()

def track_ai_decision(
    conversation_id: int,
    decision_type: str,
    decision_context: Dict[str, Any],
    confidence_score: Optional[float] = None
) -> int:
    """
    Track an AI decision for learning purposes
    
    Args:
        conversation_id: ID of the conversation where decision was made
        decision_type: Type of decision ('action_proposal', 'data_query', 'recommendation', 'alert')
        decision_context: Context of the decision (query, tools_used, reasoning, etc.)
        confidence_score: AI confidence in this decision (0.00 to 1.00)
    
    Returns:
        Decision ID
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO ai_decisions (conversation_id, decision_type, decision_context, confidence_score)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (conversation_id, decision_type, Json(decision_context), confidence_score))
        
        decision_id = cur.fetchone()[0]
        conn.commit()
        return decision_id
    finally:
        cur.close()
        conn.close()

def update_decision_outcome(
    decision_id: int,
    was_approved: bool,
    user_feedback: Optional[str] = None,
    outcome_data: Dict[str, Any] = None
):
    """
    Update the outcome of an AI decision after user review
    
    Args:
        decision_id: ID of the decision to update
        was_approved: Whether the decision was approved by the user
        user_feedback: Optional feedback from the user
        outcome_data: Additional outcome data (action_id, status, effectiveness, etc.)
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE ai_decisions
            SET was_approved = %s,
                user_feedback = %s,
                decision_outcome = %s,
                reviewed_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (was_approved, user_feedback, Json(outcome_data or {}), decision_id))
        
        conn.commit()
    finally:
        cur.close()
        conn.close()

def get_conversation_history(
    session_id: Optional[str] = None,
    user_id: Optional[int] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get conversation history for a session or user
    
    Args:
        session_id: Filter by session ID
        user_id: Filter by user ID
        limit: Maximum number of messages to return
    
    Returns:
        List of conversation messages
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        query = "SELECT * FROM ai_conversations WHERE 1=1"
        params = []
        
        if session_id:
            query += " AND session_id = %s"
            params.append(session_id)
        
        if user_id:
            query += " AND user_id = %s"
            params.append(user_id)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]
    finally:
        cur.close()
        conn.close()

def get_recent_decisions(
    decision_type: Optional[str] = None,
    was_approved: Optional[bool] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get recent AI decisions with optional filtering
    
    Args:
        decision_type: Filter by decision type
        was_approved: Filter by approval status
        limit: Maximum number of decisions to return
    
    Returns:
        List of decisions
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        query = "SELECT * FROM ai_decisions WHERE 1=1"
        params = []
        
        if decision_type:
            query += " AND decision_type = %s"
            params.append(decision_type)
        
        if was_approved is not None:
            query += " AND was_approved = %s"
            params.append(was_approved)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]
    finally:
        cur.close()
        conn.close()

def generate_daily_digest(date: Optional[datetime.date] = None) -> Dict[str, Any]:
    """
    Generate a daily digest of AI activity and insights
    
    Args:
        date: Date to generate digest for (defaults to yesterday)
    
    Returns:
        Daily digest data
    """
    if date is None:
        date = (datetime.now() - timedelta(days=1)).date()
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Get conversation stats
        cur.execute("""
            SELECT COUNT(*) as total_conversations,
                   COUNT(DISTINCT session_id) as unique_sessions
            FROM ai_conversations
            WHERE DATE(created_at) = %s
        """, (date,))
        conv_stats = dict(cur.fetchone())
        
        # Get decision stats
        cur.execute("""
            SELECT COUNT(*) as total_decisions,
                   SUM(CASE WHEN was_approved = TRUE THEN 1 ELSE 0 END) as approved,
                   SUM(CASE WHEN was_approved = FALSE THEN 1 ELSE 0 END) as rejected,
                   AVG(confidence_score) as avg_confidence
            FROM ai_decisions
            WHERE DATE(created_at) = %s
        """, (date,))
        decision_stats = dict(cur.fetchone())
        
        # Get top queries (simplified - in production, use NLP clustering)
        cur.execute("""
            SELECT message_text, COUNT(*) as count
            FROM ai_conversations
            WHERE DATE(created_at) = %s AND message_type = 'user'
            GROUP BY message_text
            ORDER BY count DESC
            LIMIT 5
        """, (date,))
        top_queries = [{"query": row["message_text"][:100], "count": row["count"]} for row in cur.fetchall()]
        
        # Use OpenAI to generate insights and recommendations
        prompt = f"""
        Analyze this AI system usage data for {date} and provide key insights and recommendations:
        
        - Total conversations: {conv_stats['total_conversations']}
        - Unique sessions: {conv_stats['unique_sessions']}
        - Total decisions: {decision_stats['total_decisions']}
        - Decisions approved: {decision_stats['approved']}
        - Decisions rejected: {decision_stats['rejected']}
        - Average confidence: {decision_stats['avg_confidence']:.2f if decision_stats['avg_confidence'] else 0}
        
        Top queries:
        {json.dumps(top_queries, indent=2)}
        
        Provide:
        1. 3-5 key insights about AI usage patterns
        2. 3-5 actionable recommendations for improving the platform
        
        Format as JSON: {{"insights": [{{"insight": "...", "category": "...", "importance": "high|medium|low"}}], "recommendations": [{{"recommendation": "...", "priority": "critical|high|medium|low", "reasoning": "..."}}]}}
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        ai_analysis = json.loads(response.choices[0].message.content)
        
        # Store digest in database
        cur.execute("""
            INSERT INTO ai_daily_digests (
                digest_date, total_conversations, total_decisions,
                decisions_approved, decisions_rejected,
                top_queries, key_insights, recommendations
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (digest_date) DO UPDATE SET
                total_conversations = EXCLUDED.total_conversations,
                total_decisions = EXCLUDED.total_decisions,
                decisions_approved = EXCLUDED.decisions_approved,
                decisions_rejected = EXCLUDED.decisions_rejected,
                top_queries = EXCLUDED.top_queries,
                key_insights = EXCLUDED.key_insights,
                recommendations = EXCLUDED.recommendations,
                generated_at = CURRENT_TIMESTAMP
            RETURNING *
        """, (
            date,
            conv_stats['total_conversations'],
            decision_stats['total_decisions'],
            decision_stats['approved'] or 0,
            decision_stats['rejected'] or 0,
            Json(top_queries),
            Json(ai_analysis.get('insights', [])),
            Json(ai_analysis.get('recommendations', []))
        ))
        
        digest = dict(cur.fetchone())
        conn.commit()
        return digest
    finally:
        cur.close()
        conn.close()

def get_daily_digest(date: Optional[datetime.date] = None) -> Optional[Dict[str, Any]]:
    """
    Get the daily digest for a specific date
    
    Args:
        date: Date to get digest for (defaults to yesterday)
    
    Returns:
        Daily digest data or None if not found
    """
    if date is None:
        date = (datetime.now() - timedelta(days=1)).date()
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT * FROM ai_daily_digests
            WHERE digest_date = %s
        """, (date,))
        
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        cur.close()
        conn.close()

def learn_from_patterns():
    """
    Analyze past interactions to identify and store learning patterns
    This runs periodically to improve AI responses over time
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Find common query patterns with high success rates
        cur.execute("""
            SELECT 
                d.decision_type,
                d.decision_context->>'query' as query_pattern,
                COUNT(*) as usage_count,
                AVG(CASE WHEN d.was_approved = TRUE THEN 100.0 ELSE 0.0 END) as success_rate,
                MAX(d.created_at) as last_used_at
            FROM ai_decisions d
            WHERE d.was_approved IS NOT NULL
            GROUP BY d.decision_type, d.decision_context->>'query'
            HAVING COUNT(*) >= 3
            ORDER BY success_rate DESC, usage_count DESC
            LIMIT 20
        """)
        
        patterns = cur.fetchall()
        
        for pattern in patterns:
            # Store or update learning pattern
            cur.execute("""
                INSERT INTO ai_learning_patterns (
                    pattern_type, pattern_data, success_rate, usage_count, last_used_at
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (pattern_type, (pattern_data->>'query_pattern'))
                DO UPDATE SET
                    success_rate = EXCLUDED.success_rate,
                    usage_count = EXCLUDED.usage_count,
                    last_used_at = EXCLUDED.last_used_at,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                pattern['decision_type'],
                Json({"query_pattern": pattern['query_pattern']}),
                pattern['success_rate'],
                pattern['usage_count'],
                pattern['last_used_at']
            ))
        
        conn.commit()
        return len(patterns)
    finally:
        cur.close()
        conn.close()
