"""
Threat Intelligence Scheduler - Block 15 v2
Sets up 12-hour cron job for automated threat intelligence scans
"""

import logging
import os
import psycopg2
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

from app.threat_intelligence_scanner import run_threat_intelligence_scan

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "echofort"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "")
    )


def start_threat_intel_scheduler():
    """
    Start the threat intelligence scheduler
    Runs scans every 12 hours (midnight and noon IST)
    Wrapped in try/except to prevent backend crashes
    """
    global scheduler
    
    try:
        if scheduler is not None:
            logger.warning("Threat Intelligence Scheduler already running")
            return
        
        logger.info("Starting Threat Intelligence Scheduler...")
        
        scheduler = BackgroundScheduler()
        
        # Schedule 12-hour scans
        # Cron: 0 0,12 * * * (midnight and noon every day)
        # IST = UTC+5:30, so we run at 18:30 and 6:30 UTC for midnight and noon IST
        scheduler.add_job(
            run_threat_intelligence_scan,
            trigger=CronTrigger(hour='6,18', minute=30),  # 12:00 AM and 12:00 PM IST
            id='threat_intel_12hour_scan',
            name='Threat Intelligence 12-Hour Scan',
            replace_existing=True,
            misfire_grace_time=3600  # Allow 1 hour grace period if server was down
        )
        
        # Daily statistics generation at 11:59 PM IST (18:29 UTC)
        scheduler.add_job(
            generate_daily_statistics,
            trigger=CronTrigger(hour=18, minute=29),
            id='threat_intel_daily_stats',
            name='Threat Intelligence Daily Statistics',
            replace_existing=True
        )
    
        scheduler.start()
        logger.info("✅ Threat Intelligence Scheduler started successfully")
        logger.info("📅 Scheduled jobs:")
        logger.info("  - 12-hour scans at 12:00 AM and 12:00 PM IST")
        logger.info("  - Daily statistics at 11:59 PM IST")
        
    except Exception as e:
        logger.error(f"❌ Failed to start Threat Intelligence Scheduler: {e}")
        logger.warning("⚠️ Backend will continue without scheduler")
        logger.warning("⚠️ Manual scans can still be triggered via API")
        # Don't raise - allow backend to continue


def stop_threat_intel_scheduler():
    """Stop the threat intelligence scheduler"""
    global scheduler
    
    try:
        if scheduler is not None:
            scheduler.shutdown()
            scheduler = None
            logger.info("Threat Intelligence Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")


def generate_daily_statistics():
    """Generate daily statistics for threat intelligence"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Call the database function to generate statistics
        cur.execute("SELECT generate_threat_intel_daily_stats(CURRENT_DATE)")
        conn.commit()
        
        cur.close()
        conn.close()
        
        logger.info("✅ Daily threat intelligence statistics generated")
        
    except Exception as e:
        logger.error(f"❌ Failed to generate daily statistics: {e}")


def get_scheduler_status():
    """Get current scheduler status"""
    global scheduler
    
    if scheduler is None:
        return {
            "running": False,
            "jobs": []
        }
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    return {
        "running": True,
        "jobs": jobs
    }
