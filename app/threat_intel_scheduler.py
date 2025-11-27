"""
Threat Intelligence Scheduler - Block 15
Sets up 12-hour cron job for automated threat intelligence scans
"""

import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

from app.threat_intelligence_scanner import run_scheduled_scan

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def start_threat_intel_scheduler():
    """
    Start the threat intelligence scheduler
    Runs scans every 12 hours (midnight and noon IST)
    """
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler already running")
        return
    
    scheduler = AsyncIOScheduler()
    
    # Schedule 12-hour scans
    # Cron: 0 0,12 * * * (midnight and noon every day)
    # IST = UTC+5:30, so we run at 18:30 and 6:30 UTC for midnight and noon IST
    scheduler.add_job(
        run_scheduled_scan,
        trigger=CronTrigger(hour='6,18', minute=30),  # 12:00 AM and 12:00 PM IST
        id='threat_intel_12hour_scan',
        name='Threat Intelligence 12-Hour Scan',
        replace_existing=True,
        misfire_grace_time=3600  # Allow 1 hour grace period if server was down
    )
    
    # Optional: Daily statistics generation at 11:59 PM IST (18:29 UTC)
    scheduler.add_job(
        generate_daily_statistics,
        trigger=CronTrigger(hour=18, minute=29),
        id='threat_intel_daily_stats',
        name='Threat Intelligence Daily Statistics',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Threat Intelligence Scheduler started")
    logger.info("Next scan scheduled at: 12:00 AM and 12:00 PM IST (6:30 AM and 6:30 PM UTC)")


def stop_threat_intel_scheduler():
    """Stop the threat intelligence scheduler"""
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("Threat Intelligence Scheduler stopped")


async def generate_daily_statistics():
    """Generate daily statistics for threat intelligence"""
    from app.database import get_db
    from sqlalchemy import text
    
    db = next(get_db())
    try:
        query = text("SELECT generate_threat_intel_daily_stats(CURRENT_DATE)")
        db.execute(query)
        db.commit()
        logger.info("Daily threat intelligence statistics generated")
    except Exception as e:
        logger.error(f"Failed to generate daily statistics: {e}")
    finally:
        db.close()


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


# For manual testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Starting Threat Intelligence Scheduler...")
    start_threat_intel_scheduler()
    
    print("\nScheduler Status:")
    status = get_scheduler_status()
    print(f"Running: {status['running']}")
    print(f"Jobs: {len(status['jobs'])}")
    for job in status['jobs']:
        print(f"  - {job['name']}: Next run at {job['next_run_time']}")
    
    print("\nPress Ctrl+C to stop...")
    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        stop_threat_intel_scheduler()
        print("Scheduler stopped")
