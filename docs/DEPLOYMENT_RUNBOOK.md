# Production Deployment Runbook

**Version:** 1.0  
**Last Updated:** 2025-03-30  
**Owner:** Engineering Team  
**Duration:** ~15 minutes (maintenance window not required if blue-green deployment used)

---

## Overview

This runbook provides step-by-step instructions for deploying the AI Interview Assistant (Phase 4) to production. It includes pre-deployment verification, deployment steps, verification procedures, rollback options, and 24-hour monitoring guidelines.

**Deployment Philosophy:**
- Zero downtime preferred (blue-green or rolling deployment)
- All checks automated and tested in staging first
- Rollback procedures ready before deployment
- Comprehensive monitoring during first 24 hours

---

## Pre-Deployment (5 minutes)

### 1. Final Verification

Before touching production, run all checks locally to ensure readiness:

```bash
# Verify test suite passes
cd /home/joao/hrtech
source venv/bin/activate
pytest --cov --cov-report=term-missing 2>&1 | tail -5

# Expected output:
# TOTAL ... 80%+
# All tests pass, 0 failures
```

```bash
# Verify E2E tests pass
pytest core/tests/test_interview_end_to_end.py -v 2>&1 | tail -10

# Expected output:
# ======= 20+ passed =======
```

```bash
# Verify LGPD audit passes
python manage.py audit_lgpd_compliance 2>&1 | tail -5

# Expected output:
# Status: PASS
# Violations Found: 0
```

```bash
# Verify no pending migrations
python manage.py makemigrations --dry-run 2>&1

# Expected output:
# No changes detected in app 'core'
```

### 2. Database Backup

**On Render or your hosting provider:**

```bash
# Connect to production database
psql postgresql://user:pass@db.render.com:5432/hrtech_prod

# Create backup with timestamp
BACKUP_FILE="hrtech_prod_backup_$(date +%Y%m%d_%H%M%S).sql"
pg_dump -h db.render.com -U user hrtech_prod > $BACKUP_FILE

# Verify backup size (should be >50MB for complete data)
ls -lh $BACKUP_FILE

# Expected output:
# -rw-r--r-- 1 user user 245M Mar 30 14:23 hrtech_prod_backup_20250330_142300.sql
```

**Store backup securely:**
```bash
# Upload to S3 backup bucket
aws s3 cp $BACKUP_FILE s3://hrtech-backups/postgres/ --sse AES256

# Document backup metadata
echo "Backup: $BACKUP_FILE" >> deployment_backups.txt
echo "Size: $(du -h $BACKUP_FILE | cut -f1)" >> deployment_backups.txt
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> deployment_backups.txt
```

### 3. Deploy to Staging First

Test in staging environment before production:

```bash
# Deploy to staging branch
git push staging  # or equivalent CI/CD pipeline

# Wait for Render to build and deploy (2-3 minutes)
# Monitor: Render > Deployments > Latest

# Verify staging endpoint responds
curl -X GET https://staging.yourdomain.com/health -v

# Expected output:
# < HTTP/1.1 200 OK
# {"status": "ok"}
```

```bash
# Test with staging admin user (in browser)
# Visit: https://staging.yourdomain.com/admin
# Login with test credentials
# Navigate to candidate profile
# Verify "Generate Interview Questions" button is visible
# Click button and verify loading spinner appears
# Wait 5 seconds for mocked response (should show questions)
```

If any issue appears in staging, **STOP** and debug before proceeding to production.

---

## Deployment Steps (5-10 minutes)

### Step 1: Create Release Tag

```bash
# On your local machine, verify you're on main branch
git branch -v  # Should show "* main"
git log --oneline | head -1  # Confirm latest commit

# Create annotated tag
git tag -a v4.0-production \
  -m "Phase 4: Quality & Deployment - Interview Assistant Final
  
  - 80%+ test coverage verified
  - LGPD compliance audit: PASS
  - Performance baseline established
  - Security hardening complete
  - E2E test suite: 20+ tests passing
  - Ready for production deployment"

# Verify tag
git tag -l -n5 v4.0-production

# Push tag to remote
git push origin v4.0-production

# Verify tag on GitHub
# Visit: https://github.com/yourepo/releases/tag/v4.0-production
```

### Step 2: Deploy to Production

**Option A: Render Direct Deployment (Recommended)**

```bash
# Push to main branch (triggers automatic deployment via GitHub integration)
git push origin main

# Render automatically detects new commit and starts deployment
# Monitor deployment progress:
# 1. Visit Render dashboard: https://dashboard.render.com
# 2. Select your service
# 3. Click "Deployments"
# 4. Monitor the "Building" → "Deploying" → "Live" status
# 5. Expected duration: 2-3 minutes
```

**Option B: Manual Deployment (if needed)**

```bash
# SSH into production server
ssh deploy@yourdomain.com

# Navigate to app directory
cd /app/hrtech

# Pull latest code
git pull origin main
git checkout v4.0-production  # Ensure we're on the right tag

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Clear cache (optional)
python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Restart application server
systemctl restart gunicorn
# or
sudo systemctl restart hrtech-app

# Verify service is running
systemctl status gunicorn
```

### Step 3: Verify Production Deployment (3-5 minutes)

```bash
# 1. Check health endpoint
curl -X GET https://yourdomain.com/health -v

# Expected output:
# < HTTP/1.1 200 OK
# Content-Length: 16
# {"status": "ok"}
```

```bash
# 2. Check Django admin loads
curl -X GET https://yourdomain.com/admin/ -v 2>&1 | head -20

# Expected output:
# < HTTP/1.1 200 OK
# < Content-Type: text/html
# (HTML login page follows)
```

```bash
# 3. Check interview questions endpoint accessible
# (This will return 403 since not authenticated, but confirms endpoint exists)
curl -X POST https://yourdomain.com/api/vaga/1/candidates/550e8400-e29b-41d4-a716-446655440000/generate-questions/ \
  -H "Content-Type: application/json" \
  -v 2>&1 | head -20

# Expected output:
# < HTTP/1.1 302 Found  (redirect to login)
# or
# < HTTP/1.1 403 Forbidden  (no CSRF token, not staff)
# NOT: < HTTP/1.1 500 Internal Server Error
```

```bash
# 4. Check logs for errors (last 50 lines)
tail -50 /var/log/django/interview_assistant.log | grep -i "error\|critical"

# Expected output:
# (no ERROR or CRITICAL entries, only INFO)

# If errors found, check details:
tail -200 /var/log/django/interview_assistant.log | tail -100
```

```bash
# 5. Monitor error tracking (Sentry)
# Visit: https://sentry.io > Projects > HR Tech ATS
# Check "Issues" tab for new errors
# Expected: 0 new critical errors

# Common errors during deployment:
# - 404 on missing template: check TEMPLATES setting
# - 500 on database query: check DATABASE_URL
# - 403 on API: expected (not authenticated)
# - 502 Bad Gateway: service still starting (wait 30s and retry)
```

### Step 4: Smoke Test (5-10 minutes)

**From a browser (logged in as admin):**

1. **Homepage loads:**  
   Visit: `https://yourdomain.com/`  
   ✓ Page loads without errors  
   ✓ Navigation menu visible  
   ✓ No 404 or 500 errors  

2. **Django admin accessible:**  
   Visit: `https://yourdomain.com/admin/`  
   ✓ Login page loads  
   ✓ Login with production credentials  
   ✓ Admin dashboard displays  

3. **Candidate profile with interview questions:**  
   Navigate to: `/admin/core/candidato/` (or equivalent)  
   Select a test candidate  
   ✓ Candidate profile loads  
   ✓ "Generate Interview Questions" button visible (if staff user)  

4. **Generate questions flow:**  
   Click: "Generate Interview Questions" button  
   ✓ Loading spinner appears immediately  
   ✓ Request sent to API (check browser Network tab)  
   ✓ Questions appear after 5 seconds (mocked OpenAI)  
   ✓ No JavaScript errors in console  

5. **Regenerate workflow:**  
   Click: "Regenerate" button  
   ✓ Confirmation dialog appears  
   ✓ Confirm regeneration  
   ✓ Old questions replaced with new ones  
   ✓ Audit trail updated (verify in admin)  

6. **Browser console:**  
   Open: DevTools (F12) → Console tab  
   ✓ No JavaScript errors  
   ✓ No 404 errors for CSS/JS files  
   ✓ No CORS errors  

7. **Application logs:**  
   Check: `tail -50 /var/log/django/interview_assistant.log`  
   ✓ No CRITICAL or ERROR entries  
   ✓ INFO entries showing question generation  
   ✓ All timestamps recent  

**If all smoke tests pass:**  
✅ **Deployment is SUCCESSFUL**

---

## Rollback Procedure (5-10 minutes)

If production breaks after deployment, perform these steps immediately.

### Emergency Rollback - Option 1: Render Quick Rollback

```bash
# Visit Render dashboard
# 1. Navigate to: https://dashboard.render.com > Services > your-service
# 2. Click: "Deployments" tab
# 3. Find: previous stable deployment (before v4.0)
# 4. Click: "Redeploy" button
# 5. Wait: 2-3 minutes for rollback to complete

# Verify rollback succeeded
curl -X GET https://yourdomain.com/health

# Expected: 200 OK within 3 minutes
```

### Emergency Rollback - Option 2: Git Rollback

```bash
# Identify last known good commit
git log --oneline | head -10
# Example output:
# 3a5f7c1 test(phase-4): coverage config and E2E tests ← Known good
# a2b1c0d feat: add interview service
# ...

# Reset to previous commit
git reset --hard 3a5f7c1

# Force push to revert (⚠️ Use with caution!)
git push -f origin main

# Render will automatically redeploy from the previous commit
# Monitor: https://dashboard.render.com > Deployments
# Expected: Deployment completes in 2-3 minutes

# Verify health
curl -X GET https://yourdomain.com/health
```

### Emergency Rollback - Option 3: Database Restore

If database migrations caused the issue:

```bash
# SSH to production
ssh deploy@yourdomain.com

# Stop application to prevent writes
systemctl stop gunicorn

# Restore from backup (created in Pre-Deployment)
psql postgresql://user:pass@db.render.com:5432/hrtech_prod < hrtech_prod_backup_20250330_142300.sql

# Verify data restored
psql -c "SELECT COUNT(*) FROM core_interviewquestion;" \
  postgresql://user:pass@db.render.com:5432/hrtech_prod

# Should show count matching pre-deployment

# Apply any necessary migrations again
python manage.py migrate

# Restart application
systemctl start gunicorn

# Verify health
curl -X GET https://yourdomain.com/health
```

### Post-Rollback Actions

1. **Notify Team:**
   ```bash
   # Send Slack message
   curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
     -H 'Content-Type: application/json' \
     -d '{
       "text": "🚨 Production rolled back to v3.9-stable due to [issue description]",
       "channel": "#deployments"
     }'
   ```

2. **Create Incident Report:**
   - What went wrong
   - Why tests didn't catch it
   - Root cause analysis
   - Preventive measures

3. **Fix Issue Locally:**
   - Identify root cause
   - Add test coverage for the issue
   - Fix code
   - Verify all tests pass

4. **Re-deploy After Fix:**
   - Follow deployment steps again
   - Deploy to staging first
   - Verify smoke tests
   - Deploy to production

---

## Monitoring After Deployment (First 24 Hours)

### Immediate Monitoring (0-1 hour)

**Every 5 minutes:**
- [ ] Health check returns 200: `curl https://yourdomain.com/health`
- [ ] Admin page loads: `curl https://yourdomain.com/admin/`
- [ ] Error logs clean: `tail -50 /var/log/django/ | grep -i error`

**Every 15 minutes:**
- [ ] No critical errors in Sentry (check dashboard)
- [ ] API response times healthy (check APM if available)
- [ ] Database connections stable (<10/max)

### Hourly Monitoring (1-24 hours)

**Checklist:**
- [ ] No CRITICAL errors in logs (Sentry dashboard)
- [ ] API response times healthy (<5s P95 for generation, <100ms for cached)
- [ ] Database connection pool healthy (connections <20/max)
- [ ] OpenAI API calls succeeding (log 100+ successful generations)
- [ ] Staff users generating questions without errors (spot check 5+ candidates)
- [ ] No 500 errors (check error logs)

### Daily Monitoring (Day 1 Complete)

- [ ] Zero 500 errors in production logs
- [ ] Questions loading for all recruiters (spot check 5+ candidates)
- [ ] LGPD audit still passes: `python manage.py audit_lgpd_compliance`
- [ ] No database locks or slow queries (>1s)
- [ ] All expected features working:
  - [ ] Question generation (first time)
  - [ ] Question caching (repeat requests)
  - [ ] Question regeneration
  - [ ] Permission checks (non-staff rejected)
  - [ ] Error handling (timeouts, API errors)

### Post-Deployment Sign-Off

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPLOYMENT SIGN-OFF
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Deployment completed successfully at: 2025-03-30T14:30:00Z

Version Deployed: v4.0-production
Deployed by: ________________
Verified by: ________________

First 24h Monitoring Results:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- [ ] ✓ No critical errors detected
- [ ] ✓ API response times healthy
- [ ] ✓ LGPD audit passed (0 violations)
- [ ] ✓ All smoke tests passed
- [ ] ✓ Recruiters using feature successfully
- [ ] ✓ No database corruption
- [ ] ✓ Performance baseline maintained

Status: ✅ APPROVED FOR PRODUCTION

This feature is now live and ready for end-user use.
```

---

## Troubleshooting

### Problem: 500 Internal Server Error on `/api/vaga/*/candidates/*/generate-questions/`

**Diagnosis:**
```bash
tail -50 /var/log/django/interview_assistant.log | grep -A5 "ERROR\|CRITICAL"
```

**Common Causes:**

1. **OPENAI_API_KEY not set or invalid:**
   ```bash
   # Check environment variable
   echo $OPENAI_API_KEY
   
   # Fix: Add to Render environment
   # Render > Environment > Add "OPENAI_API_KEY=sk-..."
   ```

2. **Database connection failed:**
   ```bash
   # Check DATABASE_URL
   psql $DATABASE_URL -c "SELECT 1;"
   
   # Fix: Verify PostgreSQL is running and accessible
   ```

3. **Permission decorator issue:**
   ```bash
   # Verify user.is_staff = True in admin
   python manage.py shell
   >>> from django.contrib.auth import get_user_model
   >>> User = get_user_model()
   >>> User.objects.filter(is_staff=True).count()
   1  # Should show at least one staff user
   ```

4. **Template not found:**
   ```bash
   # Check template paths in settings
   # Ensure 'core/partials/interview_questions_display.html' exists
   ls -la /app/hrtech/templates/core/partials/
   ```

**Fix:**
```bash
# Restart application after fixing environment
systemctl restart gunicorn

# Verify health
curl -X GET https://yourdomain.com/health

# If still failing, check detailed logs
journalctl -u gunicorn -n 100 --no-pager
```

### Problem: CSRF Token Mismatch

**Error Message:**
```
CSRF verification failed. Request aborted.
Reason given for failure: CSRF token missing or incorrect.
```

**Cause:** Browser cookies not secure in HTTPS environment

**Fix:**
```python
# In core/settings.py, verify these are set:
if not DEBUG:
    CSRF_COOKIE_SECURE = True  # HTTPS only
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True

# Restart application
systemctl restart gunicorn
```

### Problem: OpenAI API Timeout

**Error Message:**
```
TimeoutError: OpenAI API call exceeded 15 seconds
```

**Cause:** Network latency, OpenAI service degradation, or API overload

**Expected Behavior (correct):**
- User sees error message: "Generation took too long. Try again."
- User can click "Try Again" button to retry
- No database corruption (question not partially saved)

**Verify:**
```bash
# Check OpenAI status page
curl https://status.openai.com/api/v2/status.json | jq .

# Look for: "operational": true

# If OpenAI is down, monitor status page for updates
# No action needed — automatic retry in code handles this
```

### Problem: Database Locked

**Error Message:**
```
django.db.utils.IntegrityError: database is locked
```

**Cause:** Concurrent writes exceeding SQLite capabilities (if using SQLite in production — don't!)

**Fix:**
```bash
# Switch to PostgreSQL (recommended for production)
# Update DATABASE_URL to use PostgreSQL

# If already PostgreSQL, check for long-running queries
psql $DATABASE_URL -c "
  SELECT pid, usename, application_name, query, query_start
  FROM pg_stat_activity
  WHERE query != '<idle>'
  ORDER BY query_start DESC;
"

# Kill long-running queries if necessary
# psql $DATABASE_URL -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid != pg_backend_pid() AND query_start < now() - interval '10 minutes';"
```

### Problem: Memory Leak (Memory Usage Growing)

**Diagnosis:**
```bash
# Monitor memory usage
top -p $(pgrep -f gunicorn | head -1)

# If memory grows over hours, could be:
# 1. Large Django cache not evicted
# 2. Database connection not closed
# 3. External API response not freed
```

**Fix:**
```bash
# Restart application to clear memory
systemctl restart gunicorn

# If recurring, add memory limits
# Update systemd service:
# /etc/systemd/system/gunicorn.service
# Add: MemoryMax=512M
systemctl daemon-reload
systemctl restart gunicorn
```

---

## Deployment Checklist

**Before Deployment:**
- [ ] All tests passing (unit, E2E, performance)
- [ ] LGPD audit passes (0 violations)
- [ ] Staging deployment successful
- [ ] Database backup created and verified
- [ ] Team notified of deployment window

**During Deployment:**
- [ ] Tag created in Git
- [ ] Code pushed to production
- [ ] Deployment monitoring active
- [ ] Health check passing
- [ ] Smoke tests successful

**After Deployment:**
- [ ] All smoke tests passed
- [ ] No CRITICAL errors in logs
- [ ] API response times healthy
- [ ] LGPD audit passed
- [ ] Team notified of success
- [ ] Incident response plan reviewed
- [ ] Monitoring dashboard active

**Sign-Off:**
- [ ] Engineering Lead: ________________
- [ ] Operations: ________________
- [ ] Product Manager: ________________

---

## Reference Documents

- **DEPLOYMENT_CHECKLIST.md** — Pre-deployment verification items
- **LGPD_COMPLIANCE.md** — Compliance audit results
- **PERFORMANCE_BASELINE.md** — Performance targets and results
- **Security Configuration** — core/settings.py (HSTS, CSP, CSRF, etc.)

---

**Document Version:** 1.0  
**Last Updated:** 2025-03-30  
**Next Review:** After deployment (first week)  
**Owner:** Engineering Team  
**Revision History:**

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-03-30 | Initial deployment runbook |
