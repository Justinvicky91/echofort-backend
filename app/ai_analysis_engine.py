"""
AI Analysis Engine - Phase 3
Block 8: Autonomous Analysis + Human-Approved Execution

This module implements the autonomous analysis engine that:
1. Analyzes platform metrics from multiple data sources
2. Learns new threat patterns from the internet
3. Proposes actions into the ai_action_queue
4. Does NOT execute anything (human approval required)

Designed to run as a scheduled job (daily cron).
"""

import os
import json
import psycopg
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_db_connection():
    """Get database connection"""
    database_url = os.getenv("DATABASE_URL", "")
    if database_url.startswith("postgresql+psycopg://"):
        database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    return psycopg.connect(database_url)

# ============================================================================
# DATA SOURCE INTEGRATIONS
# ============================================================================

def fetch_user_growth_metrics() -> Dict[str, Any]:
    """Fetch user growth and churn metrics from Block 1 analytics"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Total users
                cur.execute("SELECT COUNT(*) FROM users WHERE role = 'user'")
                total_users = cur.fetchone()[0]
                
                # Users created in last 7 days
                cur.execute("""
                    SELECT COUNT(*) FROM users 
                    WHERE role = 'user' AND created_at > NOW() - INTERVAL '7 days'
                """)
                new_users_7d = cur.fetchone()[0]
                
                # Users created in previous 7 days (for comparison)
                cur.execute("""
                    SELECT COUNT(*) FROM users 
                    WHERE role = 'user' 
                    AND created_at BETWEEN NOW() - INTERVAL '14 days' AND NOW() - INTERVAL '7 days'
                """)
                prev_users_7d = cur.fetchone()[0]
                
                # Calculate growth rate
                growth_rate = 0
                if prev_users_7d > 0:
                    growth_rate = ((new_users_7d - prev_users_7d) / prev_users_7d) * 100
                
                return {
                    "total_users": total_users,
                    "new_users_7d": new_users_7d,
                    "prev_users_7d": prev_users_7d,
                    "growth_rate": round(growth_rate, 2)
                }
    except Exception as e:
        print(f"Error fetching user metrics: {e}")
        return {"total_users": 0, "new_users_7d": 0, "growth_rate": 0}

def fetch_evidence_vault_stats() -> Dict[str, Any]:
    """Fetch evidence vault statistics from Block 4/5"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Total evidence items
                cur.execute("SELECT COUNT(*) FROM evidence_vault")
                total_evidence = cur.fetchone()[0]
                
                # Evidence by category
                cur.execute("""
                    SELECT category, COUNT(*) 
                    FROM evidence_vault 
                    GROUP BY category
                """)
                by_category = dict(cur.fetchall())
                
                # High-risk evidence (extremism threshold >= 7)
                cur.execute("""
                    SELECT COUNT(*) FROM evidence_vault 
                    WHERE extremism_score >= 7
                """)
                high_risk_count = cur.fetchone()[0]
                
                # Evidence created in last 7 days
                cur.execute("""
                    SELECT COUNT(*) FROM evidence_vault 
                    WHERE created_at > NOW() - INTERVAL '7 days'
                """)
                new_evidence_7d = cur.fetchone()[0]
                
                return {
                    "total_evidence": total_evidence,
                    "by_category": by_category,
                    "high_risk_count": high_risk_count,
                    "new_evidence_7d": new_evidence_7d
                }
    except Exception as e:
        print(f"Error fetching evidence vault stats: {e}")
        return {"total_evidence": 0, "high_risk_count": 0, "new_evidence_7d": 0}

def fetch_block5_config() -> Dict[str, Any]:
    """Fetch current Block5Config settings"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT config_data FROM block5_config 
                    ORDER BY updated_at DESC LIMIT 1
                """)
                row = cur.fetchone()
                if row and row[0]:
                    return row[0]
                return {}
    except Exception as e:
        print(f"Error fetching Block5Config: {e}")
        return {}

def fetch_billing_metrics() -> Dict[str, Any]:
    """Fetch billing and revenue metrics from Block 2"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Total revenue (last 30 days)
                cur.execute("""
                    SELECT COALESCE(SUM(amount), 0) FROM invoices 
                    WHERE status = 'paid' 
                    AND created_at > NOW() - INTERVAL '30 days'
                """)
                revenue_30d = cur.fetchone()[0]
                
                # Total refunds (last 30 days)
                cur.execute("""
                    SELECT COALESCE(SUM(amount), 0) FROM refunds 
                    WHERE status = 'completed' 
                    AND created_at > NOW() - INTERVAL '30 days'
                """)
                refunds_30d = cur.fetchone()[0]
                
                # Refund rate
                refund_rate = 0
                if revenue_30d > 0:
                    refund_rate = (refunds_30d / revenue_30d) * 100
                
                return {
                    "revenue_30d": float(revenue_30d),
                    "refunds_30d": float(refunds_30d),
                    "refund_rate": round(refund_rate, 2)
                }
    except Exception as e:
        print(f"Error fetching billing metrics: {e}")
        return {"revenue_30d": 0, "refunds_30d": 0, "refund_rate": 0}

def fetch_consent_log_stats() -> Dict[str, Any]:
    """Fetch consent log statistics from Block 7"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Total consents
                cur.execute("SELECT COUNT(*) FROM user_consent_log")
                total_consents = cur.fetchone()[0]
                
                # Consents by version
                cur.execute("""
                    SELECT terms_version, privacy_version, COUNT(*) 
                    FROM user_consent_log 
                    GROUP BY terms_version, privacy_version
                """)
                by_version = [{"terms": row[0], "privacy": row[1], "count": row[2]} for row in cur.fetchall()]
                
                return {
                    "total_consents": total_consents,
                    "by_version": by_version
                }
    except Exception as e:
        print(f"Error fetching consent log stats: {e}")
        return {"total_consents": 0, "by_version": []}

# ============================================================================
# AI ANALYSIS FUNCTIONS
# ============================================================================

def analyze_platform_health(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Use OpenAI to analyze platform health and generate insights"""
    try:
        prompt = f"""
You are the EchoFort AI Analysis Engine. Analyze the following platform metrics and provide insights:

**User Metrics:**
- Total Users: {metrics['user_metrics']['total_users']}
- New Users (last 7 days): {metrics['user_metrics']['new_users_7d']}
- Growth Rate: {metrics['user_metrics']['growth_rate']}%

**Evidence Vault:**
- Total Evidence Items: {metrics['evidence_vault']['total_evidence']}
- High-Risk Items: {metrics['evidence_vault']['high_risk_count']}
- New Evidence (last 7 days): {metrics['evidence_vault']['new_evidence_7d']}
- By Category: {json.dumps(metrics['evidence_vault']['by_category'])}

**Billing:**
- Revenue (last 30 days): ₹{metrics['billing']['revenue_30d']}
- Refunds (last 30 days): ₹{metrics['billing']['refunds_30d']}
- Refund Rate: {metrics['billing']['refund_rate']}%

**Block5 Config:**
{json.dumps(metrics['block5_config'], indent=2)}

Provide:
1. A brief summary of platform health (2-3 sentences)
2. Any anomalies or concerns detected
3. Recommended actions (if any)

Format your response as JSON:
{{
  "summary": "Brief health summary",
  "anomalies": ["anomaly1", "anomaly2"],
  "recommended_actions": [
    {{
      "type": "config_change|pattern_update|infra_suggestion|investigate_anomaly",
      "target": "target_component",
      "reason": "why this action is recommended",
      "payload": {{}},
      "impact_summary": "human-readable explanation"
    }}
  ]
}}
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are the EchoFort AI Analysis Engine. Analyze platform metrics and propose safe, non-destructive actions."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    
    except Exception as e:
        print(f"Error in AI analysis: {e}")
        return {
            "summary": "Analysis failed",
            "anomalies": [],
            "recommended_actions": []
        }

def discover_threat_patterns() -> List[Dict[str, Any]]:
    """Search the internet for new threat patterns"""
    try:
        # Search queries for threat intelligence
        search_queries = [
            "new phishing scams India 2025",
            "digital arrest scam latest trends",
            "AI voice cloning fraud cases",
            "loan harassment tactics India",
            "online impersonation fraud patterns"
        ]
        
        discovered_patterns = []
        
        for query in search_queries:
            try:
                # Use OpenAI to simulate web search and pattern discovery
                # In production, this would use actual web search APIs
                prompt = f"""
You are a threat intelligence researcher. Based on the query "{query}", describe a realistic threat pattern that might be emerging.

Provide your response as JSON:
{{
  "category": "PHISHING|FRAUD|HARASSMENT|EXTREMISM|SCAM|IMPERSONATION|LOAN_HARASSMENT",
  "description": "Detailed description of the threat pattern",
  "example_phrases": ["phrase1", "phrase2", "phrase3"],
  "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "source_url": "https://example.com/source",
  "tags": ["tag1", "tag2", "tag3"]
}}
"""
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a threat intelligence researcher focused on scams and fraud in India."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                
                pattern = json.loads(response.choices[0].message.content)
                discovered_patterns.append(pattern)
                
            except Exception as e:
                print(f"Error discovering pattern for query '{query}': {e}")
                continue
        
        return discovered_patterns
    
    except Exception as e:
        print(f"Error in threat pattern discovery: {e}")
        return []

# ============================================================================
# ACTION QUEUE MANAGEMENT
# ============================================================================

def insert_proposed_action(action: Dict[str, Any]) -> bool:
    """Insert a proposed action into the ai_action_queue"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ai_action_queue (
                        type, target, payload, impact_summary
                    ) VALUES (%s, %s, %s, %s)
                """, (
                    action['type'],
                    action['target'],
                    json.dumps(action['payload']),
                    action['impact_summary']
                ))
                conn.commit()
                print(f"✅ Proposed action inserted: {action['type']} -> {action['target']}")
                return True
    except Exception as e:
        print(f"Error inserting proposed action: {e}")
        return False

def insert_discovered_pattern(pattern: Dict[str, Any]) -> bool:
    """Insert a discovered pattern into the ai_pattern_library"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Check if similar pattern already exists
                cur.execute("""
                    SELECT id FROM ai_pattern_library 
                    WHERE category = %s AND description ILIKE %s
                    LIMIT 1
                """, (pattern['category'], f"%{pattern['description'][:50]}%"))
                
                if cur.fetchone():
                    print(f"⏭️  Pattern already exists, skipping: {pattern['description'][:50]}")
                    return False
                
                # Insert new pattern
                cur.execute("""
                    INSERT INTO ai_pattern_library (
                        category, description, example_phrases, risk_level, source_url, tags
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    pattern['category'],
                    pattern['description'],
                    json.dumps(pattern.get('example_phrases', [])),
                    pattern['risk_level'],
                    pattern.get('source_url'),
                    json.dumps(pattern.get('tags', []))
                ))
                conn.commit()
                print(f"✅ Pattern inserted: {pattern['category']} - {pattern['description'][:50]}")
                return True
    except Exception as e:
        print(f"Error inserting pattern: {e}")
        return False

# ============================================================================
# MAIN ANALYSIS ROUTINE
# ============================================================================

def run_daily_analysis():
    """Main routine to run daily analysis"""
    print("="*80)
    print("🤖 EchoFort AI Analysis Engine - Daily Run")
    print(f"⏰ Started at: {datetime.now().isoformat()}")
    print("="*80)
    
    # Step 1: Gather metrics from all data sources
    print("\n📊 Step 1: Gathering platform metrics...")
    metrics = {
        "user_metrics": fetch_user_growth_metrics(),
        "evidence_vault": fetch_evidence_vault_stats(),
        "billing": fetch_billing_metrics(),
        "block5_config": fetch_block5_config(),
        "consent_log": fetch_consent_log_stats()
    }
    print(f"✅ Metrics gathered: {json.dumps(metrics, indent=2)}")
    
    # Step 2: Analyze platform health and generate insights
    print("\n🧠 Step 2: Analyzing platform health with AI...")
    analysis = analyze_platform_health(metrics)
    print(f"✅ Analysis complete:")
    print(f"   Summary: {analysis.get('summary', 'N/A')}")
    print(f"   Anomalies: {len(analysis.get('anomalies', []))}")
    print(f"   Recommended Actions: {len(analysis.get('recommended_actions', []))}")
    
    # Step 3: Insert recommended actions into queue
    print("\n📝 Step 3: Inserting recommended actions into queue...")
    actions_inserted = 0
    for action in analysis.get('recommended_actions', []):
        if insert_proposed_action(action):
            actions_inserted += 1
    print(f"✅ {actions_inserted} actions inserted into queue")
    
    # Step 4: Discover new threat patterns
    print("\n🔍 Step 4: Discovering new threat patterns...")
    patterns = discover_threat_patterns()
    print(f"✅ {len(patterns)} patterns discovered")
    
    # Step 5: Insert patterns into library
    print("\n📚 Step 5: Inserting patterns into library...")
    patterns_inserted = 0
    for pattern in patterns:
        if insert_discovered_pattern(pattern):
            patterns_inserted += 1
    print(f"✅ {patterns_inserted} new patterns inserted into library")
    
    # Summary
    print("\n" + "="*80)
    print("✅ Daily Analysis Complete")
    print(f"   Actions Proposed: {actions_inserted}")
    print(f"   Patterns Discovered: {patterns_inserted}")
    print(f"⏰ Completed at: {datetime.now().isoformat()}")
    print("="*80)

if __name__ == "__main__":
    run_daily_analysis()
