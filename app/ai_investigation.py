"""
AI Investigation Module
Handles case management, evidence linking, and investigation workflows
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import json

def get_db_connection():
    """Get database connection"""
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    return conn

def generate_case_number():
    """Generate unique case number (format: CASE-YYYYMMDD-XXXX)"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"CASE-{today}-"
    
    # Find the highest case number for today
    cur.execute("""
        SELECT case_number FROM investigation_cases 
        WHERE case_number LIKE %s 
        ORDER BY case_number DESC LIMIT 1
    """, (f"{prefix}%",))
    
    result = cur.fetchone()
    if result:
        last_num = int(result[0].split('-')[-1])
        new_num = last_num + 1
    else:
        new_num = 1
    
    cur.close()
    conn.close()
    
    return f"{prefix}{new_num:04d}"

def create_investigation_case(title, description, case_type, priority="medium", 
                             victim_user_id=None, suspect_phone=None, suspect_name=None, 
                             suspect_details=None, created_by=None):
    """Create a new investigation case"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    case_number = generate_case_number()
    suspect_details_json = json.dumps(suspect_details or {})
    
    cur.execute("""
        INSERT INTO investigation_cases 
        (case_number, title, description, case_type, priority, victim_user_id, 
         suspect_phone, suspect_name, suspect_details, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """, (case_number, title, description, case_type, priority, victim_user_id,
          suspect_phone, suspect_name, suspect_details_json, created_by))
    
    case = cur.fetchone()
    case_id = case['id']
    
    # Add timeline event
    cur.execute("""
        INSERT INTO investigation_timeline 
        (case_id, event_type, event_description, created_by)
        VALUES (%s, 'created', %s, %s)
    """, (case_id, f"Case created: {title}", created_by))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return dict(case)

def get_investigation_cases(status=None, case_type=None, limit=50, offset=0):
    """Get list of investigation cases with optional filters"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    query = "SELECT * FROM investigation_cases WHERE 1=1"
    params = []
    
    if status:
        query += " AND status = %s"
        params.append(status)
    
    if case_type:
        query += " AND case_type = %s"
        params.append(case_type)
    
    query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    cur.execute(query, params)
    cases = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return [dict(case) for case in cases]

def get_case_details(case_id):
    """Get full case details including timeline, evidence, and notes"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get case
    cur.execute("SELECT * FROM investigation_cases WHERE id = %s", (case_id,))
    case = cur.fetchone()
    
    if not case:
        cur.close()
        conn.close()
        return None
    
    # Get timeline
    cur.execute("""
        SELECT * FROM investigation_timeline 
        WHERE case_id = %s ORDER BY created_at DESC
    """, (case_id,))
    timeline = cur.fetchall()
    
    # Get evidence
    cur.execute("""
        SELECT * FROM investigation_evidence 
        WHERE case_id = %s ORDER BY added_at DESC
    """, (case_id,))
    evidence = cur.fetchall()
    
    # Get notes
    cur.execute("""
        SELECT * FROM investigation_notes 
        WHERE case_id = %s ORDER BY created_at DESC
    """, (case_id,))
    notes = cur.fetchall()
    
    # Get actions
    cur.execute("""
        SELECT * FROM ai_investigation_actions 
        WHERE case_id = %s ORDER BY created_at DESC
    """, (case_id,))
    actions = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return {
        "case": dict(case),
        "timeline": [dict(t) for t in timeline],
        "evidence": [dict(e) for e in evidence],
        "notes": [dict(n) for n in notes],
        "actions": [dict(a) for a in actions]
    }

def update_case_status(case_id, new_status, updated_by=None, resolution_summary=None):
    """Update case status and add timeline event"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Update case
    if new_status in ['resolved', 'closed'] and resolution_summary:
        cur.execute("""
            UPDATE investigation_cases 
            SET status = %s, resolved_at = CURRENT_TIMESTAMP, resolution_summary = %s
            WHERE id = %s
            RETURNING *
        """, (new_status, resolution_summary, case_id))
    else:
        cur.execute("""
            UPDATE investigation_cases 
            SET status = %s
            WHERE id = %s
            RETURNING *
        """, (new_status, case_id))
    
    case = cur.fetchone()
    
    # Add timeline event
    cur.execute("""
        INSERT INTO investigation_timeline 
        (case_id, event_type, event_description, created_by)
        VALUES (%s, 'status_change', %s, %s)
    """, (case_id, f"Status changed to: {new_status}", updated_by))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return dict(case)

def add_evidence_to_case(case_id, evidence_type, evidence_description, 
                        evidence_id=None, evidence_metadata=None, added_by=None):
    """Link evidence to a case"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    metadata_json = json.dumps(evidence_metadata or {})
    
    cur.execute("""
        INSERT INTO investigation_evidence 
        (case_id, evidence_type, evidence_id, evidence_description, evidence_metadata, added_by)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING *
    """, (case_id, evidence_type, evidence_id, evidence_description, metadata_json, added_by))
    
    evidence = cur.fetchone()
    
    # Add timeline event
    cur.execute("""
        INSERT INTO investigation_timeline 
        (case_id, event_type, event_description, created_by)
        VALUES (%s, 'evidence_added', %s, %s)
    """, (case_id, f"Evidence added: {evidence_type} - {evidence_description}", added_by))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return dict(evidence)

def add_note_to_case(case_id, note_text, note_type="general", created_by=None):
    """Add a note to a case"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        INSERT INTO investigation_notes 
        (case_id, note_text, note_type, created_by)
        VALUES (%s, %s, %s, %s)
        RETURNING *
    """, (case_id, note_text, note_type, created_by))
    
    note = cur.fetchone()
    
    # Add timeline event
    cur.execute("""
        INSERT INTO investigation_timeline 
        (case_id, event_type, event_description, created_by)
        VALUES (%s, 'note_added', %s, %s)
    """, (case_id, f"Note added: {note_type}", created_by))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return dict(note)

def propose_investigation_action(case_id, action_type, action_description, 
                                action_data=None, proposed_by="ai"):
    """Propose an AI investigation action (requires human approval)"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    action_data_json = json.dumps(action_data or {})
    
    cur.execute("""
        INSERT INTO ai_investigation_actions 
        (case_id, action_type, action_description, action_data, proposed_by)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING *
    """, (case_id, action_type, action_description, action_data_json, proposed_by))
    
    action = cur.fetchone()
    
    # Add timeline event
    cur.execute("""
        INSERT INTO investigation_timeline 
        (case_id, event_type, event_description, created_by)
        VALUES (%s, 'action_proposed', %s, NULL)
    """, (case_id, f"AI proposed action: {action_type}"))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return dict(action)

def approve_investigation_action(action_id, approved_by):
    """Approve an AI investigation action"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        UPDATE ai_investigation_actions 
        SET status = 'approved', approved_by = %s, approved_at = CURRENT_TIMESTAMP
        WHERE id = %s
        RETURNING *
    """, (approved_by, action_id))
    
    action = cur.fetchone()
    
    if action:
        # Add timeline event
        cur.execute("""
            INSERT INTO investigation_timeline 
            (case_id, event_type, event_description, created_by)
            VALUES (%s, 'action_approved', %s, %s)
        """, (action['case_id'], f"Action approved: {action['action_type']}", approved_by))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return dict(action) if action else None

def get_investigation_statistics(days=30):
    """Get investigation statistics for the last N days"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT * FROM investigation_statistics 
        WHERE stat_date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY stat_date DESC
    """, (days,))
    
    stats = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return [dict(s) for s in stats]

def generate_daily_investigation_stats():
    """Generate daily investigation statistics"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    yesterday = (datetime.now() - timedelta(days=1)).date()
    
    # Calculate statistics
    cur.execute("""
        SELECT 
            COUNT(*) as total_cases,
            SUM(CASE WHEN DATE(created_at) = %s THEN 1 ELSE 0 END) as cases_opened,
            SUM(CASE WHEN DATE(resolved_at) = %s THEN 1 ELSE 0 END) as cases_resolved,
            AVG(CASE WHEN resolved_at IS NOT NULL 
                THEN EXTRACT(EPOCH FROM (resolved_at - created_at))/3600 
                ELSE NULL END) as avg_resolution_time_hours
        FROM investigation_cases
        WHERE created_at <= %s
    """, (yesterday, yesterday, yesterday))
    
    stats = cur.fetchone()
    
    # Get cases by type
    cur.execute("""
        SELECT case_type, COUNT(*) as count
        FROM investigation_cases
        WHERE created_at <= %s
        GROUP BY case_type
    """, (yesterday,))
    
    cases_by_type = {row['case_type']: row['count'] for row in cur.fetchall()}
    
    # Get evidence count
    cur.execute("""
        SELECT COUNT(*) as evidence_count
        FROM investigation_evidence
        WHERE DATE(added_at) = %s
    """, (yesterday,))
    
    evidence_count = cur.fetchone()['evidence_count']
    
    # Get AI actions
    cur.execute("""
        SELECT 
            COUNT(*) as proposed,
            SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved
        FROM ai_investigation_actions
        WHERE DATE(created_at) = %s
    """, (yesterday,))
    
    ai_actions = cur.fetchone()
    
    # Insert statistics
    cur.execute("""
        INSERT INTO investigation_statistics 
        (stat_date, total_cases, cases_opened, cases_resolved, cases_by_type, 
         avg_resolution_time_hours, evidence_items_collected, ai_actions_proposed, ai_actions_approved)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (stat_date) DO UPDATE SET
            total_cases = EXCLUDED.total_cases,
            cases_opened = EXCLUDED.cases_opened,
            cases_resolved = EXCLUDED.cases_resolved,
            cases_by_type = EXCLUDED.cases_by_type,
            avg_resolution_time_hours = EXCLUDED.avg_resolution_time_hours,
            evidence_items_collected = EXCLUDED.evidence_items_collected,
            ai_actions_proposed = EXCLUDED.ai_actions_proposed,
            ai_actions_approved = EXCLUDED.ai_actions_approved
        RETURNING *
    """, (yesterday, stats['total_cases'], stats['cases_opened'], stats['cases_resolved'],
          json.dumps(cases_by_type), stats['avg_resolution_time_hours'], 
          evidence_count, ai_actions['proposed'], ai_actions['approved']))
    
    result = cur.fetchone()
    
    conn.commit()
    cur.close()
    conn.close()
    
    return dict(result)
