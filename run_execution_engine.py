#!/usr/bin/env python3
"""
Execution Engine Cron Job Script
Block 8 Phase 4

This script is designed to be run by Railway cron job.
It triggers the AI execution engine to process approved actions.

Railway Cron Configuration:
- Schedule: "*/15 * * * *" (every 15 minutes)
- Command: python3 run_execution_engine.py

This runs more frequently than the analysis engine because
approved actions should be executed promptly.
"""

import sys
import os

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.ai_execution_engine_v2 import process_approved_actions

if __name__ == "__main__":
    print("🚀 Starting Railway Cron Job: AI Execution Engine")
    try:
        process_approved_actions()
        print("✅ Cron job completed successfully")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Cron job failed: {e}")
        sys.exit(1)
