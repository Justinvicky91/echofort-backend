# EchoFort Production Monitoring Setup Guide

## Overview

This document outlines the complete production monitoring setup for EchoFort, including error tracking, uptime monitoring, performance monitoring, and alerting.

---

## 1. Error Tracking with Sentry

### Setup

1. **Create Sentry Account:**
   - Visit https://sentry.io
   - Create new project: "echofort-backend"
   - Copy DSN (Data Source Name)

2. **Configure Environment Variables:**
   ```bash
   export SENTRY_DSN="https://your-dsn@sentry.io/project-id"
   export ENVIRONMENT="production"
   export RELEASE_VERSION="1.0.0"
   ```

3. **Install Sentry SDK:**
   ```bash
   pip install sentry-sdk[fastapi]
   ```

4. **Initialize in Application:**
   ```python
   from monitoring.sentry_config import init_sentry
   
   # In main.py
   init_sentry()
   ```

### Features Enabled

✅ **Error Tracking:**
- Automatic exception capture
- Stack traces with source code
- Breadcrumbs for debugging
- User context (without PII)

✅ **Performance Monitoring:**
- Transaction tracing (10% sample rate)
- Slow query detection
- API endpoint performance
- Database query profiling

✅ **Custom Error Categories:**
- API errors
- Payment errors
- AI/ML errors
- Database errors

✅ **DPDP Compliance:**
- No PII sent to Sentry
- Sanitized SQL queries
- Filtered breadcrumbs
- Before-send hooks

### Alert Configuration

**Critical Alerts:**
- Database connection failures
- Payment gateway errors
- Authentication system failures
- AI model failures

**Warning Alerts:**
- Slow API responses (>2s)
- High error rate (>5%)
- Memory usage >80%
- Database connection pool exhaustion

---

## 2. Uptime Monitoring

### Recommended Services

#### Option 1: UptimeRobot (Free)
- **URL:** https://uptimerobot.com
- **Features:** 50 monitors, 5-minute checks
- **Setup:**
  1. Create account
  2. Add monitor: https://api.echofort.ai/health
  3. Add monitor: https://echofort.ai
  4. Configure alert contacts (email, SMS, Slack)

#### Option 2: Pingdom (Paid)
- **URL:** https://pingdom.com
- **Features:** Global monitoring, 1-minute checks
- **Cost:** ~$15/month
- **Setup:**
  1. Create account
  2. Add uptime check for API
  3. Configure multi-location checks
  4. Set up alert integrations

#### Option 3: Better Uptime (Recommended)
- **URL:** https://betteruptime.com
- **Features:** Status page, on-call scheduling
- **Cost:** Free tier available
- **Setup:**
  1. Create account
  2. Add monitors for all critical endpoints
  3. Create public status page
  4. Configure incident management

### Endpoints to Monitor

**Critical (1-minute interval):**
- https://api.echofort.ai/health
- https://api.echofort.ai/test/ping

**Important (5-minute interval):**
- https://echofort.ai
- https://api.echofort.ai/legal/terms
- https://api.echofort.ai/openapi.json

**Database (5-minute interval):**
- Custom script to check PostgreSQL connection

### Custom Monitoring Script

Run the included uptime monitor:

```bash
cd /home/ubuntu/echofort-backend/monitoring
python uptime_config.py
```

Or run as systemd service:

```bash
sudo cp uptime-monitor.service /etc/systemd/system/
sudo systemctl enable uptime-monitor
sudo systemctl start uptime-monitor
```

---

## 3. Performance Monitoring

### Application Performance Monitoring (APM)

#### Sentry Performance
- Already configured in sentry_config.py
- Tracks transaction performance
- Identifies slow endpoints
- Database query profiling

#### New Relic (Alternative)
- **URL:** https://newrelic.com
- **Features:** Full APM suite
- **Cost:** Free tier available
- **Setup:**
  ```bash
  pip install newrelic
  newrelic-admin run-program gunicorn main:app
  ```

### Database Monitoring

**PostgreSQL Monitoring:**
```sql
-- Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check connection pool
SELECT count(*) as connections,
       state
FROM pg_stat_activity
GROUP BY state;
```

**Railway Dashboard:**
- Monitor CPU usage
- Monitor memory usage
- Monitor disk I/O
- Check connection count

### API Response Time Monitoring

**Target Metrics:**
- P50 (median): <200ms
- P95: <500ms
- P99: <1000ms

**Monitor with:**
- Sentry performance
- Custom middleware logging
- Railway metrics dashboard

---

## 4. Log Aggregation

### Option 1: Railway Logs
- Built-in log viewer
- Real-time streaming
- Search and filter
- Limited retention (7 days)

### Option 2: Papertrail (Recommended)
- **URL:** https://papertrailapp.com
- **Features:** Log aggregation, search, alerts
- **Cost:** Free tier (50MB/month)
- **Setup:**
  ```bash
  # Add to Railway environment
  PAPERTRAIL_HOST=logs.papertrailapp.com
  PAPERTRAIL_PORT=12345
  ```

### Option 3: Logtail
- **URL:** https://logtail.com
- **Features:** Modern log management
- **Cost:** Free tier available
- **Integration:** Python logging handler

### Log Levels

**Production Logging:**
- ERROR: All errors and exceptions
- WARNING: Slow queries, high memory
- INFO: Important events (auth, payments)
- DEBUG: Disabled in production

---

## 5. Alerting Configuration

### Alert Channels

**Primary:**
- Email: admin@echofort.ai
- SMS: +91-XXXXXXXXXX (for critical)

**Secondary:**
- Slack: #echofort-alerts channel
- Discord: Monitoring webhook
- PagerDuty: On-call rotation

### Alert Rules

#### Critical (Immediate)
- API down for >2 minutes
- Database connection failure
- Payment gateway failure
- Authentication system down
- Error rate >10%

#### High (5 minutes)
- API response time >2s
- Memory usage >90%
- Disk usage >90%
- Error rate >5%

#### Medium (15 minutes)
- API response time >1s
- Memory usage >80%
- High database connection count
- Error rate >2%

#### Low (1 hour)
- Slow queries detected
- High CPU usage
- Unusual traffic patterns

### Slack Integration

1. Create Slack webhook:
   ```
   https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   ```

2. Configure in environment:
   ```bash
   export ALERT_WEBHOOK_URL="https://hooks.slack.com/..."
   ```

3. Test alert:
   ```python
   from monitoring.uptime_config import UptimeMonitor
   monitor = UptimeMonitor()
   monitor.send_alert("Test alert", severity="info")
   ```

---

## 6. Security Monitoring

### Automated Security Scanning

**GitHub Actions (Already Configured):**
- Safety: Python dependency vulnerabilities
- Bandit: Security linter
- Runs on every push

**Additional Tools:**

#### Snyk
- **URL:** https://snyk.io
- **Features:** Dependency scanning, container scanning
- **Setup:** Connect GitHub repository

#### Dependabot
- **GitHub Feature:** Automatic dependency updates
- **Setup:** Enable in repository settings

### Security Alerts

**Monitor for:**
- Failed authentication attempts (>10/minute)
- Unusual API usage patterns
- SQL injection attempts
- XSS attempts
- DDoS attacks

**Implementation:**
```python
# Add middleware to track failed auth
@app.middleware("http")
async def security_monitor(request, call_next):
    # Track failed auth attempts
    # Alert on suspicious patterns
    return await call_next(request)
```

---

## 7. Business Metrics Monitoring

### Key Metrics to Track

**User Metrics:**
- New signups per day
- Active users (DAU/MAU)
- Subscription conversions
- Churn rate

**Revenue Metrics:**
- Daily revenue
- MRR (Monthly Recurring Revenue)
- ARPU (Average Revenue Per User)
- Payment success rate

**Product Metrics:**
- Scams detected per day
- False positive rate
- AI model accuracy
- Feature usage rates

**Technical Metrics:**
- API requests per minute
- Average response time
- Error rate
- Database query count

### Monitoring Dashboard

**Tools:**
- Grafana: Custom dashboards
- Metabase: Business intelligence
- Mixpanel: User analytics
- Amplitude: Product analytics

---

## 8. Status Page

### Public Status Page

**Recommended: Better Uptime**
- URL: status.echofort.ai
- Shows real-time status
- Historical uptime data
- Incident updates

**Components to Display:**
- API Status
- Website Status
- Mobile App Backend
- Payment Gateway
- Database

**Setup:**
1. Create Better Uptime account
2. Configure monitors
3. Create status page
4. Point subdomain: status.echofort.ai

### Incident Management

**Process:**
1. Incident detected (automated alert)
2. Create incident on status page
3. Investigate and fix
4. Update status page with progress
5. Mark as resolved
6. Post-mortem report

---

## 9. Monitoring Checklist

### Daily Checks
- [ ] Check Sentry for new errors
- [ ] Review API response times
- [ ] Check uptime percentage
- [ ] Review failed payment attempts
- [ ] Check database performance

### Weekly Checks
- [ ] Review slow query log
- [ ] Check disk usage trends
- [ ] Review security scan results
- [ ] Analyze traffic patterns
- [ ] Review user feedback

### Monthly Checks
- [ ] Review all monitoring costs
- [ ] Update alert thresholds
- [ ] Review incident reports
- [ ] Update monitoring documentation
- [ ] Conduct load testing

---

## 10. Cost Estimate

### Free Tier (Recommended for Start)

| Service | Plan | Cost | Features |
|---------|------|------|----------|
| Sentry | Free | $0 | 5K errors/month |
| Better Uptime | Free | $0 | 10 monitors |
| Railway Logs | Included | $0 | 7-day retention |
| GitHub Actions | Free | $0 | 2000 minutes/month |
| **Total** | | **$0/month** | |

### Paid Tier (For Scale)

| Service | Plan | Cost | Features |
|---------|------|------|----------|
| Sentry | Team | $26/month | 50K errors/month |
| Better Uptime | Pro | $20/month | Unlimited monitors |
| Papertrail | Pro | $7/month | 1GB logs/month |
| New Relic | Standard | $25/month | Full APM |
| **Total** | | **$78/month** | |

---

## 11. Implementation Steps

### Phase 1: Basic Monitoring (Week 1)
1. ✅ Set up Sentry error tracking
2. ✅ Configure uptime monitoring (Better Uptime)
3. ✅ Set up email alerts
4. ✅ Create basic status page

### Phase 2: Advanced Monitoring (Week 2)
1. ⚠️ Configure performance monitoring
2. ⚠️ Set up log aggregation (Papertrail)
3. ⚠️ Configure Slack alerts
4. ⚠️ Set up security scanning

### Phase 3: Business Metrics (Week 3)
1. ⚠️ Set up analytics dashboard
2. ⚠️ Configure business metric tracking
3. ⚠️ Create custom reports
4. ⚠️ Set up automated reports

### Phase 4: Optimization (Week 4)
1. ⚠️ Fine-tune alert thresholds
2. ⚠️ Optimize monitoring costs
3. ⚠️ Create runbooks for incidents
4. ⚠️ Train team on monitoring tools

---

## 12. Runbooks

### API Down Runbook

**Symptoms:**
- Health check endpoint returning errors
- Users unable to access API
- Uptime monitor alerts

**Investigation:**
1. Check Railway dashboard for service status
2. Check recent deployments
3. Review Sentry for errors
4. Check database connection
5. Check external dependencies

**Resolution:**
1. Rollback to last known good deployment
2. Restart service if needed
3. Scale up resources if needed
4. Update status page
5. Post-mortem after resolution

### High Error Rate Runbook

**Symptoms:**
- Sentry showing spike in errors
- Error rate >5%
- Multiple user reports

**Investigation:**
1. Check Sentry error dashboard
2. Identify common error patterns
3. Check recent code changes
4. Review affected endpoints
5. Check external API status

**Resolution:**
1. Fix critical bugs immediately
2. Deploy hotfix if needed
3. Rollback if necessary
4. Monitor error rate after fix
5. Document root cause

---

## 13. Contact Information

**On-Call Rotation:**
- Primary: CTO (Vigneshwaran J)
- Secondary: Backend Team Lead
- Tertiary: DevOps Engineer

**Escalation:**
- Level 1: Automated alerts
- Level 2: Email + SMS
- Level 3: Phone call
- Level 4: All hands on deck

**Emergency Contacts:**
- Railway Support: support@railway.app
- Sentry Support: support@sentry.io
- Database DBA: (if external)

---

*Last Updated: November 22, 2025*  
*Document Owner: DevOps Team*  
*Review Frequency: Monthly*
