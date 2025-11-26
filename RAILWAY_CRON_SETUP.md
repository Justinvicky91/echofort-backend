# Railway Cron Job Setup for AI Analysis Engine

## Overview

The AI Analysis Engine needs to run daily to:
1. Analyze platform metrics
2. Propose actions into the queue
3. Discover new threat patterns

This document explains how to set up the Railway cron job.

---

## Option 1: Railway Cron Job (Recommended)

Railway supports cron jobs natively. Follow these steps:

### Step 1: Create a New Service

1. Go to your Railway project dashboard
2. Click **"+ New"** → **"Empty Service"**
3. Name it: `echofort-ai-cron`

### Step 2: Connect to GitHub

1. In the new service, click **"Settings"**
2. Under **"Source"**, connect to the same GitHub repo: `Justinvicky91/echofort-backend`
3. Set **"Root Directory"**: `/` (same as main backend)

### Step 3: Configure Cron Schedule

1. In the service settings, find **"Cron Schedule"**
2. Enter: `0 2 * * *` (runs at 2 AM IST daily)
3. This translates to: "At 02:00 AM every day"

### Step 4: Set Start Command

1. In **"Settings"** → **"Deploy"** → **"Start Command"**
2. Enter: `python3 run_daily_analysis.py`

### Step 5: Add Environment Variables

The cron service needs the same environment variables as the main backend:

1. Go to **"Variables"** tab
2. Add these variables (copy from main backend service):
   - `DATABASE_URL` - PostgreSQL connection string
   - `OPENAI_API_KEY` - OpenAI API key
   - Any other required variables

### Step 6: Deploy

1. Click **"Deploy"**
2. Railway will build and deploy the cron service
3. It will run automatically at 2 AM IST every day

### Step 7: Test the Cron Job

To test without waiting for 2 AM:

1. Go to the cron service logs
2. Click **"Deployments"** → **"Trigger Deploy"**
3. Or use the manual trigger API endpoint (see below)

---

## Option 2: Manual Trigger via API (For Testing)

You can manually trigger the analysis engine via API:

### Trigger in Background (Non-blocking)

```bash
curl -X POST https://echofort.ai/admin/ai/analysis/trigger
```

### Run Synchronously (Blocks until complete)

```bash
curl -X POST https://echofort.ai/admin/ai/analysis/run-now
```

### Check Status

```bash
curl https://echofort.ai/admin/ai/analysis/status
```

---

## Option 3: External Cron Service (Alternative)

If Railway cron doesn't work, use an external service like **cron-job.org**:

1. Go to https://cron-job.org
2. Create a free account
3. Add a new cron job:
   - **URL**: `https://echofort.ai/admin/ai/analysis/trigger`
   - **Schedule**: Daily at 2 AM IST
   - **Method**: POST
4. Save and enable

---

## Monitoring & Logs

### View Cron Job Logs

1. Go to Railway dashboard → `echofort-ai-cron` service
2. Click **"Logs"** tab
3. You'll see output from each run:
   ```
   🤖 EchoFort AI Analysis Engine - Daily Run
   ⏰ Started at: 2025-11-26T02:00:00
   📊 Step 1: Gathering platform metrics...
   ✅ Metrics gathered
   🧠 Step 2: Analyzing platform health with AI...
   ✅ Analysis complete
   📝 Step 3: Inserting recommended actions into queue...
   ✅ 3 actions inserted into queue
   🔍 Step 4: Discovering new threat patterns...
   ✅ 5 patterns discovered
   📚 Step 5: Inserting patterns into library...
   ✅ 2 new patterns inserted into library
   ✅ Daily Analysis Complete
   ```

### Check Analysis Status via API

```bash
curl https://echofort.ai/admin/ai/analysis/status
```

Response:
```json
{
  "status": "operational",
  "last_analysis_run": "2025-11-26T02:00:00",
  "pending_actions": 5,
  "patterns_discovered_today": 2,
  "checked_at": "2025-11-26T10:30:00"
}
```

---

## Troubleshooting

### Cron Job Not Running

1. **Check Railway logs** for errors
2. **Verify environment variables** are set correctly
3. **Test manually** using the API trigger endpoint
4. **Check DATABASE_URL** is accessible from cron service

### OpenAI API Errors

1. **Verify OPENAI_API_KEY** is set
2. **Check API quota** at https://platform.openai.com
3. **Review error logs** in Railway

### Database Connection Issues

1. **Verify DATABASE_URL** format: `postgresql://user:pass@host:port/db`
2. **Check PostgreSQL is accessible** from Railway network
3. **Test connection** manually using `psql $DATABASE_URL`

---

## Cost Considerations

### Railway Cron Job

- **Free Tier**: 500 hours/month (plenty for daily cron)
- **Estimated Usage**: ~1 hour/month (2 minutes per day × 30 days)
- **Cost**: $0 (well within free tier)

### OpenAI API

- **Model**: gpt-4o-mini
- **Estimated Tokens per Run**: ~5,000 tokens
- **Cost per Run**: ~$0.01
- **Monthly Cost**: ~$0.30 (30 days)

**Total Monthly Cost**: ~$0.30

---

## Security Notes

1. ✅ **No user data is sent to OpenAI** - Only aggregated metrics
2. ✅ **No execution happens automatically** - Actions go to queue for approval
3. ✅ **Audit trail** - All actions logged with timestamps
4. ✅ **Environment variables** - API keys stored securely in Railway

---

## Next Steps

After setting up the cron job:

1. ✅ Deploy the backend with the new analysis engine
2. ✅ Set up Railway cron job
3. ✅ Test manually using API trigger
4. ✅ Monitor first automated run
5. ✅ Review proposed actions in Super Admin dashboard
6. ✅ Proceed to Phase 4: Safe Execution Engine

---

**Last Updated**: November 26, 2025  
**Author**: Manus AI Agent  
**Block**: 8 - Phase 3
