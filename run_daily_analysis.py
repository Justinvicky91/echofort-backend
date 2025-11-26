#!/usr/bin/env python3
"""
Daily Analysis Cron Job Script
Block 8 Phase 3

This script is designed to be run by Railway cron job.
It triggers the AI analysis engine to run daily.

Railway Cron Configuration:
- Schedule: "0 2 * * *" (2 AM IST daily)
- Command: python3 run_daily_analysis.py
"""

import sys
import os

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.ai_analysis_engine import run_daily_analysis

if __name__ == "__main__":
    print("🚀 Starting Railway Cron Job: Daily AI Analysis")
    try:
        run_daily_analysis()
        print("✅ Cron job completed successfully")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Cron job failed: {e}")
        sys.exit(1)
