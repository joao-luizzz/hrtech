# Pre-Production Deployment Checklist

**Phase:** 4 - Quality, Compliance & Deployment  
**Checklist Version:** 1.0  
**Last Updated:** 2025-03-30

---

## 🔒 Security Review

**HTTPS & Certificates:**
- [ ] SSL certificate valid and renewed (check expiry date)
- [ ] Certificate chain complete and trusted

**Security Headers:**
- [ ] `DEBUG=False` in production settings
- [ ] `SECURE_HSTS_SECONDS` set to 31536000 (1 year)
- [ ] `SECURE_SSL_REDIRECT=True` enforced
- [ ] `X_FRAME_OPTIONS='DENY'` configured
- [ ] `SESSION_COOKIE_SECURE=True` enforced
- [ ] `CSRF_COOKIE_SECURE=True` enforced
- [ ] Content Security Policy headers configured

**Secrets Management:**
- [ ] `SECRET_KEY` rotated and unique per environment
- [ ] `ALLOWED_HOSTS` configured for production domain
- [ ] CSRF_TRUSTED_ORIGINS includes production domain
- [ ] No hardcoded credentials in code (verified via `grep -r "password\|api_key" core/ --include="*.py" | grep -v "test_"`)

---

## 📊 Database

**Infrastructure:**
- [ ] PostgreSQL 15+ running on Render or equivalent
- [ ] Automatic backups configured (daily)
- [ ] Read-only replica configured (if expecting >100 concurrent users)

**Configuration:**
- [ ] `DATABASE_URL` environment variable set and accessible
- [ ] Connection pooling enabled (`CONN_MAX_AGE=600`)
- [ ] Connection pool size appropriate for load (default: 5-20)
- [ ] Timeouts configured (connection, query, transaction)

**Migrations:**
- [ ] All migrations created and tested in staging
- [ ] Migration scripts run: `python manage.py migrate` (verified)
- [ ] No data loss in migration (tested with backup restore)
- [ ] Rollback procedure documented and tested

**Backup & Recovery:**
- [ ] Database backup tested (restore and verify InterviewQuestion table)
- [ ] Backup location documented and accessible
- [ ] Point-in-time recovery (PITR) enabled if available
- [ ] Disaster recovery plan reviewed with team

---

## 🔑 Secrets & Environment Variables

**OpenAI Configuration:**
- [ ] `OPENAI_API_KEY` loaded from environment (not in code)
- [ ] OpenAI account has sufficient quota (check API usage dashboard)
- [ ] OpenAI model specified: `gpt-4o-mini` (or chosen model)
- [ ] Timeout configured: `OPENAI_TIMEOUT_SECONDS=15`

**Neo4j Configuration:**
- [ ] `NEO4J_URI` set to production Aura endpoint
- [ ] `NEO4J_USER` and `NEO4J_PASSWORD` loaded from environment
- [ ] Neo4j connection tested (query skill gaps for test candidate)
- [ ] Connection pool configured for production load

**Database Configuration:**
- [ ] `DATABASE_URL` set and accessible from Render
- [ ] Database credentials NOT in version control

**AWS S3 (CV Storage):**
- [ ] `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` loaded from environment
- [ ] S3 bucket configured with encryption at rest
- [ ] S3 bucket lifecycle rules configured (delete old CVs after N days)
- [ ] Presigned URL expiration set appropriately

**Redis (Caching):**
- [ ] `REDIS_URL` configured (if using cache)
- [ ] Redis connection tested
- [ ] Key eviction policy configured (e.g., `maxmemory-policy allkeys-lru`)

**Email (Notifications):**
- [ ] Email backend configured (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`)
- [ ] Sender email address verified

**Render Deployment:**
- [ ] `RENDER_DEPLOY_HOOK` configured (for CI/CD)

**Sentry Error Tracking:**
- [ ] `SENTRY_DSN` set for error tracking
- [ ] Sentry project created and verified
- [ ] Alert rules configured (e.g., >5 errors/hour)

---

## 🪵 Logging & Monitoring

**Application Logging:**
- [ ] Logs directed to `/var/log/django/` or Render logging service
- [ ] Interview Assistant logs filtered by `[Interview]` prefix
- [ ] Log rotation configured (daily, keep 30 days)
- [ ] LGPD audit logging verified (no PII in logs)

**Error Tracking:**
- [ ] Sentry DSN configured and verified
- [ ] Error notifications configured (email/Slack)
- [ ] Alert threshold set (e.g., 50+ errors/hour)

**Performance Monitoring:**
- [ ] APM tool configured (optional: New Relic, DataDog)
- [ ] Response time tracked and alerted if >5s (P95)
- [ ] Database query performance tracked

**Health Checks:**
- [ ] Health check endpoint available: `GET /health` returns 200
- [ ] Database connectivity checked in health endpoint
- [ ] External service connectivity checked (OpenAI, Neo4j, S3)

---

## 🚀 Deployment Testing

**Code Quality:**
- [ ] Code reviewed by at least one team member
- [ ] Linting passed: `flake8 core/ --count --select=E9,F63,F7,F82 --show-source --statistics`
- [ ] No hardcoded credentials or secrets

**Test Execution:**
- [ ] Unit tests pass: `python manage.py test core.tests` ✓
- [ ] Coverage at 80%+: `pytest --cov` ✓
- [ ] E2E tests pass: `pytest core/tests/test_interview_end_to_end.py -v` ✓ (20+ tests)
- [ ] Performance tests pass: `pytest core/tests/test_interview_performance.py -v` ✓
- [ ] LGPD audit passes: `python manage.py audit_lgpd_compliance` ✓

**Staging Deployment:**
- [ ] Code deployed to staging environment
- [ ] Staging environment mirrors production (same DB engine, same external services)
- [ ] All endpoints return 200 (health check, admin, API endpoints)
- [ ] Mocked OpenAI works in staging
- [ ] Candidate profile page loads with interview questions button (staff user)
- [ ] Generate questions flow works end-to-end in staging
- [ ] Error handling verified in staging (forced timeout, rate limit)

**Database Migrations in Staging:**
- [ ] Migrations applied successfully to staging DB
- [ ] No data loss or corruption detected
- [ ] Rollback tested (revert migration, re-apply)

**Static Files:**
- [ ] Static files collected: `python manage.py collectstatic --noinput`
- [ ] CSS/JS files compressed and minified (if applicable)
- [ ] CDN or cloud storage configured for static assets

**Environment Variable Validation:**
- [ ] All production environment variables set and verified
- [ ] No hardcoded defaults for production secrets
- [ ] Secrets verified in Render dashboard (not showing in logs)

---

## 🔄 Rollback Procedure

**Pre-Deployment:**
- [ ] Rollback plan documented (see DEPLOYMENT_RUNBOOK.md)
- [ ] Database backup taken and verified
- [ ] Rollback script tested locally

**Deployment:**
- [ ] Reverse migration script prepared
- [ ] Previous version tagged in Git: `git tag v3.9-stable`

**Post-Deployment (if needed):**
- [ ] Rollback procedures executable without manual intervention
- [ ] Team alerted on rollback (Slack/Email configured)
- [ ] Incident review scheduled

---

## ✅ Final Verification

**Production Readiness:**
- [ ] All security checks passed ✓
- [ ] All database checks passed ✓
- [ ] All secrets configured ✓
- [ ] All monitoring configured ✓
- [ ] All tests passing ✓
- [ ] Staging deployment verified ✓

**Pre-Launch Smoke Tests (in staging):**
- [ ] Homepage loads and is responsive
- [ ] Django admin accessible at `/admin/`
- [ ] Candidate search functionality works
- [ ] Interview questions button visible for staff user
- [ ] Generate questions endpoint returns 200 (mocked OpenAI)
- [ ] Error page friendly (no stack traces to end users)
- [ ] HTTPS enforced (redirect HTTP → HTTPS)
- [ ] Rate limiting configured (optional: 5 generations per candidate per day)

**Compliance Verification:**
- [ ] LGPD audit passes (0 violations): `python manage.py audit_lgpd_compliance` ✓
- [ ] No PII in logs (spot check: `grep -r "email\|cpf\|name" logs/`)
- [ ] Access control enforced (`@staff_required` decorator active)
- [ ] Audit trail present (created_by, created_at fields)

---

## 📋 Deployment Approval Sign-Off

**Approvers Required:**

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Engineering Lead | ________________ | ✓ | __________ |
| Security Review | ________________ | ✓ | __________ |
| Compliance/Legal | ________________ | ✓ | __________ |
| Product Manager | ________________ | ✓ | __________ |

---

## 🕐 Deployment Details

**Deployment Window:**  
Date/Time (UTC): ________________  
Duration (estimated): __________ minutes  
Expected Downtime: __________ minutes (0 if blue-green)

**Rollback Window:**  
If issues detected within __________ minutes, rollback to v3.9-stable

**Communication Plan:**
- [ ] Status page updated
- [ ] Team notified via Slack
- [ ] On-call engineer assigned
- [ ] Customer notification template prepared (if applicable)

**On-Call Contact:**  
Name: ________________  
Phone: ________________  
Slack: ________________

---

## 📝 Additional Notes

**Deployment Checklist Completion:**

Total Items: 51  
Completed: ___/51 (____%)

**Sign-Off:**

I have verified that all items on this checklist are complete and production is ready for deployment.

**Completed by:** ________________ (name & title)  
**Date:** ________________  
**Time:** ________________ (UTC)

---

**Document Version:** 1.0  
**Last Updated:** 2025-03-30  
**Next Review:** After deployment (first week)

**Reference Documents:**
- DEPLOYMENT_RUNBOOK.md (step-by-step deployment guide)
- LGPD_COMPLIANCE.md (compliance verification)
- PERFORMANCE_BASELINE.md (performance targets)
- Security hardening configuration in core/settings.py
