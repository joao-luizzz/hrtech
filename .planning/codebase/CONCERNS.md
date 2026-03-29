# Codebase Concerns

**Analysis Date:** 2025-01-15

## Critical Issues

### 1. Bare Exception Handlers - Silent Failures

**Issue:** Multiple broad `except Exception:` handlers throughout codebase suppress errors without proper recovery.

**Files:**
- `core/matching.py` - lines 349, 418
- `core/neo4j_connection.py` - lines 135, 164  
- `core/tasks.py` - lines 241, 341, 373, 427, 435
- `core/views.py` - lines 169, 513, 580, 845, 882, 944

**Impact:**
- Errors are logged but execution continues, potentially leaving system in inconsistent state
- In `neo4j_connection.py:135` and `neo4j_connection.py:164`, query failures return empty lists instead of failing
- In `tasks.py:435`, exception is re-raised without context, making Celery retry semantics unclear
- Production logs will miss critical integration failures (OpenAI, Neo4j, S3)

**Fix approach:**
- Replace broad `except Exception` with specific exception types (ValidationError, ConnectionError, TimeoutError, etc.)
- For critical paths (matching.py, tasks.py), implement circuit breaker pattern
- In neo4j_connection.py, propagate exceptions instead of returning empty results
- Add exhaustive exception handlers with distinct retry/fallback strategies per exception type

---

### 2. Unvalidated CSV Text Truncation - Data Loss

**Issue:** CVs are truncated at 15,000 characters without checking if meaningful content was lost.

**File:** `core/tasks.py` - line 254
```python
return texto[:15000]  # Hard limit, no warning or validation
```

**Impact:**
- Candidates with lengthy CVs lose skill information mid-extraction
- GPT-4o-mini receives incomplete context, producing wrong skill inferences
- No audit trail of truncation - matching results are unexplicable to candidates
- Violates LGPD requirement for data processing transparency

**Fix approach:**
- Log truncation as warning with candidate UUID and character count lost
- Implement progressive sampling strategy (extract key sections: summary, experience, skills)
- Add configuration threshold (e.g., warn at 80% of limit)
- Store original text length in database for audit
- Return error status if truncation exceeds threshold, requiring human review

---

### 3. Celery Task Failure Handling - Race Condition

**Issue:** After max retries, task catches DoesNotExist but may race with cascade delete.

**File:** `core/tasks.py` - lines 417-432
```python
except Candidato.DoesNotExist:
    logger.error(f"Candidato {candidato_id} não encontrado")
    
# Later, after MaxRetriesExceededError:
except MaxRetriesExceededError:
    try:
        candidato = Candidato.objects.get(pk=candidato_id)
        candidato.status_cv = Candidato.StatusCV.ERRO
        candidato.save(update_fields=['status_cv', 'updated_at'])
    except Exception as status_error:  # Bare exception - what if it's cascade deleted?
        logger.exception("Falha ao atualizar status para ERRO...")
```

**Impact:**
- If Candidato is deleted between max_retries and status update, job silently disappears
- Admin cannot identify failed CV processing jobs
- S3 CV may remain orphaned if cleanup wasn't triggered
- No metric available for monitoring failed vs. abandoned jobs

**Fix approach:**
- Move status update BEFORE max_retries in task chain (use initial state capture)
- Add separate "CV Processing Audit" table to track all attempts independent of Candidato
- Implement cleanup job to detect orphaned CVs (S3 keys without corresponding Candidato)
- Use transaction.atomic() to ensure consistency

---

### 4. Neo4j Connection Not Closed Properly

**Issue:** Neo4j singleton driver in `core/neo4j_connection.py` is created but never closed gracefully.

**File:** `core/neo4j_connection.py` - lines 74-97

**Impact:**
- Connection leaks on Django shutdown (though Gunicorn forcefully terminates)
- In long-running Celery workers, connection pool may exhaust (50 max connections by config, line 46)
- No cleanup on settings reload or test teardown
- Health checks don't verify Neo4j connectivity before routing traffic

**Fix approach:**
- Implement Django app ready() signal to register shutdown handler
- Add `django.dispatch` signal to close driver on `django.core.signals.request_finished` for web, but NOT for Celery (workers need persistent connection)
- Add health check endpoint `/health/neo4j/` before matching operations
- Configure connection pool monitoring - log warnings when pool utilization > 80%
- In tests, use fixture-level teardown to close connection

---

## High-Priority Issues

### 5. Race Condition in CV Upload Rate Limiting

**Issue:** Cache increment in rate limiter is not atomic with initial check.

**File:** `core/services/cv_upload_service.py` - lines 74-84
```python
def _is_rate_limited(cache_key: str, limit: int, timeout_seconds: int) -> bool:
    if cache.add(cache_key, 1, timeout=timeout_seconds):  # Key didn't exist
        return False  # First request succeeds
    
    try:
        current_count = cache.incr(cache_key)  # Race window here
    except ValueError:
        cache.set(cache_key, 1, timeout=timeout_seconds)
        current_count = 1
    
    return current_count > limit
```

**Impact:**
- Two concurrent requests can both increment before checking limit
- Allows one extra request per race window (~1-2ms on Redis)
- With 20 max requests per IP, distributed attack could bypass limits
- Email rate limit (5 max) is easily bypassed by concurrent submissions

**Fix approach:**
- Use Lua scripting in Redis (atomic operation) if using RedisCache
- Implement server-side Celery rate limiting as fallback
- Log suspected abuse (multiple rate-limit violations from same IP within 1 minute)
- Add IP-based temporary block after 3 violations (10 minute cooldown)

---

### 6. Unhandled Async OpenAI API Failures

**Issue:** OpenAI API errors are retried with insufficient exponential backoff strategy.

**File:** `core/tasks.py` - lines 366-375
```python
except (RateLimitError, APIConnectionError, APITimeoutError) as e:
    logger.warning("Erro transiente OpenAI (%s). Reagendando retry.", type(e).__name__)
    raise self.retry(exc=e)  # Default retry with countdown=60 globally

except ValidationError as e:
    logger.warning(f"Validação Pydantic falhou: {e.error_count()} erros")
    raise self.retry(exc=e, countdown=30)  # Same countdown for validation error

except Exception as e:
    logger.error(f"Erro na chamada OpenAI: {type(e).__name__}")
    raise self.retry(exc=e, countdown=60)  # Same countdown for unknown errors
```

**Impact:**
- RateLimitError gets same 60s retry as generic exception - will retry into 429 again
- ValidationError (bad data, not transient) retried with 30s countdown - wastes resources
- No distinction between quota exhaustion (needs human intervention) and timeout
- Max retries = 3 (line 293) means after 3 minutes + 18s retries, job dies without alert
- Candidate never notified that skill extraction failed (status never updated to ERRO)

**Fix approach:**
- Implement exponential backoff: retry 1 @ 10s, retry 2 @ 30s, retry 3 @ 120s
- Catch RateLimitError separately - don't retry if quota_reset_seconds > 3600 (require manual trigger)
- Never retry ValidationError - mark job as ERRO immediately and log schema mismatch
- Add circuit breaker: if 5 RateLimitErrors in 1 minute, pause queue for 5 minutes
- Send admin email alert when quota exhausted

---

### 7. Missing Input Validation on Job IDs and UUIDs

**Issue:** URL parameters accepting candidato_id, vaga_id are not validated before database queries.

**Files:**
- `core/views.py` - lines 209 (status_cv_htmx), 564 (detalhe_candidato_match), 630 (mover_kanban)
- `core/matching.py` - line 392 (dados.get('candidato_id'))

**Impact:**
- Invalid UUID format passed to database causes 500 error instead of 404
- Example: `/api/candidato/not-a-uuid/` triggers unhandled exception
- No early rejection of obviously invalid IDs
- Potential for information leakage via error messages (if DEBUG=True in production)

**Fix approach:**
- Add UUID validation decorator or middleware
- In views: use custom get_object_or_404 that validates UUID format first
- Return 400 (Bad Request) for malformed IDs, not 500 (Internal Server Error)
- Add request parameter validation schema (Pydantic or Django forms)

---

### 8. Insufficient Cypher Query Parameterization

**Issue:** While most queries use parameters, dynamically constructed skill names could be vulnerable.

**File:** `core/matching.py` - lines 304-350 (Cypher query construction)
```python
# SKILL HANDLING:
parametros = {
    'todas_skills': todas_skills,
    'skills_obrigatorias': nomes_obrigatorias,
    'skills_desejaveis': nomes_desejaveis,
}
```

While these are passed as parameters, the query itself constructs lists in Cypher. If skill names contain special characters or Cypher keywords, could cause injection.

**Impact:**
- Low risk because skills come from validated JSON payload initially
- But if Neo4j schema ever changes or if UI allows special chars, injection becomes possible
- No input sanitization on skill names before Cypher serialization

**Fix approach:**
- Add explicit allowlist for skill name characters (a-zA-Z0-9, space, dash, hash, plus, dot)
- Reject skill names with parentheses, quotes, or Unicode punctuation
- Add Cypher injection test cases to test suite
- Use Neo4j driver's parameter binding exclusively (current code does this correctly)

---

### 9. Ghost Job Detection Not Reliable

**Issue:** CV processing status marked as "ghost job" if not updated in 30 minutes, but no automated cleanup.

**File:** `core/views.py` - lines 251-276 (dashboard_rh)
```python
ghost_job_minutes = getattr(settings, 'CV_GHOST_JOB_MINUTES', 30)
ghost_job_cutoff = timezone.now() - timedelta(minutes=ghost_job_minutes)

jobs_fantasmas_qs = Candidato.objects.filter(
    status_cv__in=processing_statuses,
    updated_at__lt=ghost_job_cutoff,
).order_by('updated_at')

# Stats only - no automatic cleanup
stats['jobs_fantasmas'] = jobs_fantasmas_qs.count()
```

**Impact:**
- Admins see ghost jobs in dashboard but cannot auto-kill them
- If Celery worker dies, CVs remain in PROCESSANDO forever
- No mechanism to requeue jobs or notify users their upload failed
- Can accumulate hundreds of stalled jobs over time

**Fix approach:**
- Create management command `python manage.py cleanup_ghost_jobs` to reset status to ERRO
- Add Celery Beat task to run daily: detect ghost jobs, email user, clean up S3
- Add manual action in admin interface: "Reset processing jobs" button
- Implement exponential backoff: warn at 30min, force reset at 60min, delete S3 at 90min

---

### 10. Matching Algorithm Doesn't Handle Tie-Breaking Consistently

**Issue:** When multiple candidates have identical scores, ranking is non-deterministic.

**File:** `core/matching.py` - lines 200-230 (comment describes tie-breaking)
```python
# Critérios de desempate:
#     1. Disponibilidade imediata
#     2. Menor gap de senioridade
#     3. Data de cadastro mais recente
```

But implementation doesn't strictly enforce ordering. Line 868 sorts by:
```python
return engine.executar_matching(
    vaga_id=vaga_id,
    limite=limite,
)
```

No sort order is applied in `executar_matching` - results depend on Neo4j query order.

**Impact:**
- Same job's candidates ranked differently on reruns
- Users see inconsistent results if they refresh page
- Impossible to explain why candidate A is ranked above candidate B to recruiter
- Fails LGPD requirement for algorithm explainability

**Fix approach:**
- Explicitly sort by: disponivel (DESC), abs(gap_senioridade), created_at (DESC)
- Add deterministic tiebreaker: candidato_id (UUID order) as final sort
- Store sort key in AuditoriaMatch.detalhes_calculo for reproducibility
- Add integration test: verify same ranking across multiple runs

---

## Medium-Priority Issues

### 11. No Timeout on File Download from S3

**Issue:** CV download from S3 in tasks has no timeout configured.

**File:** `core/services/s3_service.py` - line 100+
```python
# No timeout specified in boto3 client
self.client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=self.region
)
```

**Impact:**
- If S3 is slow or network stalls, task hangs until Celery hard timeout (5 minutes, line 224)
- Could tie up worker thread for minutes
- No distinction between slow S3 and unreachable S3

**Fix approach:**
- Configure boto3 config: `Config(connect_timeout=10, read_timeout=30)`
- Wrap S3 operations in explicit timeout context
- Catch `ConnectionError` and `socket.timeout` separately from other errors
- Log S3 latency metrics for monitoring

---

### 12. Logging May Leak Sensitive Data

**Issue:** While CV text is masked before OpenAI, other sensitive data may be logged.

**File:** `core/tasks.py` - lines 156-180 (comment says "LGPD" but implementation incomplete)
```python
# LGPD: Mascarar CPF, RG, datas ANTES de enviar para OpenAI

# Regex patterns exist for CPF, RG masking
# But original texto_bruto is logged in exception handlers
```

And: `core/tasks.py` - line 254
```python
return texto[:15000]  # This text might be logged if exception occurs
```

**Impact:**
- If pdfplumber fails, error context may include CV text fragment
- If OpenAI API validation fails, request JSON is logged with unmasked text
- Logs are often aggregated to central system (CloudWatch, DataDog) - LGPD violation
- Could expose candidate's SSN, personal address, etc.

**Fix approach:**
- Never log CV text or structured extracts
- In exception handlers, log only metadata: file_size, page_count, extraction_duration
- Use logger.exception() only for non-sensitive errors
- Implement log masking regex for patterns: CPF, RG, dates, email (catch what slips through)

---

### 13. No Explicit Transaction Management in Matching

**Issue:** Matching results saved to PostgreSQL but Neo4j write can fail without rollback.

**File:** `core/matching.py` - lines 834-835
```python
with transaction.atomic():
    AuditoriaMatch.objects.bulk_create(auditorias)
```

But Neo4j save happens before:
```python
# Line 794-810: Skills saved to Neo4j BEFORE transaction
salvar_habilidades_neo4j(...)

# Line 834: Only PostgreSQL is wrapped in transaction
with transaction.atomic():
    AuditoriaMatch.objects.bulk_create(auditorias)
```

**Impact:**
- If Neo4j write succeeds but PostgreSQL bulk_create fails, data is inconsistent
- Audits in PostgreSQL won't exist but skills are in Neo4j
- Matching results can't be replayed or explained
- No rollback mechanism if one of two writes fails

**Fix approach:**
- Move Neo4j write INSIDE transaction.atomic() context
- Create custom transaction manager that coordinates both databases
- Add "audit created" check before returning results
- Implement compensating transaction: if PostgreSQL fails, delete Neo4j nodes

---

### 14. Email Service Not Configured for Production

**Issue:** Email backend defaults to console output; SMTP may not be tested.

**File:** `hrtech/settings.py` - lines 114-123
```python
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')  # Empty default
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
```

**Impact:**
- If EMAIL_HOST_USER is not set in .env, silent failure (empty string used)
- No test coverage for email delivery (services/email_service.py has no tests)
- Candidates never notified of match results or stage changes
- Admin emails for quota exhaustion never sent

**Fix approach:**
- Require EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in non-DEBUG mode
- Add email delivery test: send test email on startup
- Log email send failures prominently
- Implement fallback: if SMTP fails, queue to Redis for retry
- Add email service tests with mock SMTP

---

### 15. Admin Interface Not Secured

**Issue:** Django admin is exposed at default `/admin/` with customization but no extra hardening.

**File:** `hrtech/settings.py` - lines 56-57
```python
'admin_interface',  # Custom admin UI
'colorfield',
```

**Impact:**
- Brute force attacks on `/admin/login/` not rate limited
- No 2FA or IP whitelisting
- Admin interface shows sensitive URLs and structure
- No audit log for admin actions

**Fix approach:**
- Move admin to non-standard path: `X-Admin-Path` header or random URL
- Add rate limiting to login: 3 attempts per IP per 10 minutes
- Implement 2FA via django-two-factor-auth
- Enable admin action logging with django-auditlog
- Add IP whitelist for admin access in production

---

## Low-Priority Issues

### 16. Matching Senioridade Gap Calculation May Have Off-By-One

**File:** `core/matching.py` - line 103 (map of senioridade to value)
```python
SENIORIDADE_MAP = {
    'junior': 1,
    'pleno': 2,
    'senior': 3,
}
```

Usage in gap calculation is unclear (not shown in extracted lines). If candidate is "junior" and job is "senior", gap should be 2 levels, not 1.

**Impact:** Low - affects only gap analysis display, not matching score. But could confuse recruiters.

**Fix approach:** Add test case: `gap_senior_vs_junior should be 2`, ensure calculation matches

---

### 17. Celery Worker Without Process Supervision

**File:** `Procfile` - line 2
```
worker: celery -A hrtech worker -l INFO -Q default,openai
```

Running Celery directly without supervisor (systemd, daemontools, etc.). On Render, this is acceptable, but:

**Impact:** If worker crashes, no automatic restart. Dashboard shows stale job counts.

**Fix approach:** Use Render's Process Types correctly. Consider Heroku-style restart policies or Kubernetes liveness probe.

---

### 18. Test Coverage Incomplete

**Issue:** 90 total test methods but many areas untested.

**Files:** 
- `core/tests/test_backend_validations.py` - mostly view integration tests
- `core/tests/test_pipeline_mock.py` - mocked Celery tests
- Missing: email_service.py tests, s3_service.py real integration tests, neo4j edge cases

**Impact:** Low risk for critical path but edge cases in Neo4j schema changes, S3 downtime, email failures are untested.

**Fix approach:** Add tests for:
- S3 service: upload failure, download timeout, presigned URL expiration
- Email service: SMTP connection error, invalid recipient, attachment too large
- Neo4j: connection loss, query timeout, skill name with special characters

---

### 19. No Monitoring/Alerting Infrastructure

**Issue:** No APM, metrics, or alerting configured.

**Impact:**
- Can't detect matching algorithm slowdowns until users complain
- OpenAI API quota exhaustion discovered manually
- Neo4j query performance regressions invisible
- Celery task failures accumulate silently

**Fix approach:** Add:
- Sentry for error tracking (free tier covers basics)
- CloudWatch/Datadog for metrics (task duration, queue depth, Neo4j latency)
- Alerting: email on > 5 task failures in 1 hour, matching avg duration > 5 seconds

---

### 20. Documentation Gaps

**Issue:** Critical features have inline comments but no architecture docs.

**Missing:**
- Neo4j schema documentation (what nodes exist, what SIMILAR_A relationships mean)
- Matching algorithm proof (why weights are 60/25/15, not 50/30/20)
- API contracts (what fields are required in CV upload payload)
- Deployment runbook (how to scale Celery, migrate databases)

**Impact:** Medium - onboarding new developers is slow, troubleshooting is guess-work.

**Fix approach:** Create:
- `docs/neo4j_schema.md` - node types, indexes, query patterns
- `docs/matching_algorithm.md` - justification for weights and decay factors
- `docs/deployment.md` - scaling, backups, recovery
- `docs/api.md` - auto-generated from Pydantic schemas

---

## Security Considerations

### Authentication & Authorization

**Current State:**
- Uses django-allauth for auth (good)
- Role-based access control via Profile.role (good)
- Decorator-based authorization on views (correct usage in most cases)

**Gaps:**
- No CSRF token validation on some AJAX endpoints (CSRF_PROTECT present but `require_POST` checked)
- Session timeout not configured - defaults to 2 weeks
- No rate limiting on login attempts
- Superuser bypass in decorators (lines 37-38 in decorators.py) could be exploited if account is compromised

**Recommendation:** Set SESSION_COOKIE_AGE = 86400 (1 day), add login rate limiting, remove superuser bypass or require 2FA for superuser.

---

### Data Privacy (LGPD)

**Current State:**
- CV text is masked before OpenAI (good)
- Presigned URLs with 15-minute TTL for S3 access (good)
- ON_DELETE=SET_NULL for foreign keys to preserve audit history (good)

**Gaps:**
- Logs may contain PII (addressed in issue #12)
- No data retention policy (CVs stored indefinitely)
- No mechanism for candidate to request data deletion
- Matching scores not explained to candidates

**Recommendation:** Add GDPR/LGPD request handler, implement data retention schedule (delete CVs after 12 months), add "explain match" feature.

---

### API Security

**Current State:**
- No public API - all endpoints require authentication
- File upload validates PDF headers (good)
- File size limit 10MB (reasonable)

**Gaps:**
- Rate limiting by email is easily bypassed (addressed in issue #5)
- No API key authentication for future integrations
- No CORS headers configured (not needed now but will be needed if frontend moves to separate domain)

**Recommendation:** Add API versioning, implement proper rate limiting, pre-configure CORS for future expansion.

---

## Infrastructure Concerns

### Celery Queue Reliability

**Issue:** Using Redis as both broker and backend. If Redis goes down, all tasks are lost.

**Impact:**
- CVs uploaded during Redis downtime are lost
- No queue persistence
- Failure recovery requires manual database cleanup

**Recommendation:** Evaluate PostgreSQL broker (django-celery-beat) or cloud-hosted RabbitMQ for production.

---

### Neo4j Connection Pool Exhaustion

**Risk:** 50 max connections configured. Under high load (> 25 simultaneous Celery tasks + web requests), connection pool exhausts.

**Recommendation:** Monitor pool utilization, consider dynamic scaling to 100 for production.

---

### Database Performance

**Risk:** No indexes on frequently queried fields:
- `Candidato.email` is unique but not indexed (PostgreSQL auto-indexes unique constraints)
- `Candidato.status_cv` used in filters but no index
- `AuditoriaMatch.vaga` used in rankings but no select_related in all places

**Recommendation:** Add indexes for `status_cv`, add select_related for all AuditoriaMatch queries.

---

## Summary of Critical Path Issues

**Most urgent to fix (blocks production deployment):**
1. Issue #2: CV text truncation (data loss)
2. Issue #3: Celery task failure race condition
3. Issue #6: OpenAI retry strategy (cost overrun risk)
4. Issue #9: Ghost job detection (stuck jobs accumulate)

**High impact, medium effort:**
1. Issue #1: Bare exception handlers
2. Issue #4: Neo4j connection cleanup
3. Issue #12: Logging sensitive data

**Must address before scaling:**
1. Issue #5: Rate limiting race condition
2. Issue #7: Missing input validation
3. Issue #13: Transaction management (data consistency)

---

*Concerns audit: 2025-01-15*
