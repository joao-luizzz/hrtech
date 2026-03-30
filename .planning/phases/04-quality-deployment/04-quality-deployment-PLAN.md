---
phase: 04-quality-deployment
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/tests/test_interview_end_to_end.py
  - .coverage
  - .coveragerc
  - docs/LGPD_COMPLIANCE.md
  - docs/DEPLOYMENT_CHECKLIST.md
  - docs/DEPLOYMENT_RUNBOOK.md
  - core/management/commands/audit_lgpd_compliance.py
  - core/settings.py
autonomous: false
requirements:
  - REQ-10
  - REQ-11
must_haves:
  truths:
    - "Coverage is verifiable at 80%+ overall across all 3 phases"
    - "All external API calls are mocked in test environment (no real OpenAI/Neo4j calls)"
    - "End-to-end workflows tested: generate questions → cache → regenerate → error handling"
    - "No PII (names, emails, CV content) is sent to OpenAI in any code path"
    - "LGPD audit trails exist for all question generation events"
    - "Security headers configured for production deployment"
    - "Performance baseline established (cached <100ms, API <5s, E2E <10s)"
    - "Deployment runbook provides step-by-step production steps"
    - "Rollback procedures documented and tested"
    - "Monitoring and error tracking configured and verified"
  artifacts:
    - path: "core/tests/test_interview_end_to_end.py"
      provides: "End-to-end test suite covering happy path, error scenarios, edge cases"
      min_lines: 150
    - path: ".coveragerc"
      provides: "Coverage configuration excluding migrations, tests, settings"
      contains: "[run]"
    - path: "docs/LGPD_COMPLIANCE.md"
      provides: "1-page LGPD audit summary with data flows and no PII findings"
      min_lines: 30
    - path: "docs/DEPLOYMENT_CHECKLIST.md"
      provides: "Pre-production checklist (env vars, logging, DB backup)"
      min_lines: 40
    - path: "docs/DEPLOYMENT_RUNBOOK.md"
      provides: "Step-by-step production deployment guide with rollback"
      min_lines: 60
    - path: "core/management/commands/audit_lgpd_compliance.py"
      provides: "CLI tool to audit LGPD compliance (scan logs, verify no PII)"
      min_lines: 80
  key_links:
    - from: "core/services/interview_openai_service.py"
      to: ".coveragerc"
      via: "coverage reporting"
      pattern: "omit.*migrations.*settings"
    - from: "core/tests/test_interview_end_to_end.py"
      to: "core/views.py"
      via: "Django test client POST to generate-questions endpoint"
      pattern: "client.post.*generate-questions"
    - from: "core/management/commands/audit_lgpd_compliance.py"
      to: "core/services/interview_openai_service.py"
      via: "log scanning for PII patterns"
      pattern: "grep.*candidate.*email.*CV"
    - from: "docs/DEPLOYMENT_RUNBOOK.md"
      to: "core/settings.py"
      via: "production environment variables"
      pattern: "OPENAI_API_KEY.*RENDER_DEPLOY_HOOK"
---

<objective>
Verify the AI Interview Assistant is production-ready: 80%+ test coverage, full LGPD compliance, documented deployment process, and performance baseline.

Purpose: This phase is the final quality gate before production launch. It ensures the feature works reliably at scale, meets compliance requirements, and can be deployed with confidence.

Output: 
- 80%+ overall test coverage report (all 3 phases)
- E2E test suite with 20+ test cases
- LGPD compliance audit with zero findings
- Performance baseline (cached <100ms, API <5s, E2E <10s)
- Production deployment runbook with rollback procedures
- Security hardening configuration
- Monitoring setup verification
</objective>

<execution_context>
@.github/get-shit-done/workflows/execute-plan.md
@.github/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/01-foundation-permissions/01-foundation-permissions-SUMMARY.md
@.planning/phases/02-core-service/02-core-service-SUMMARY.md
@.planning/phases/03-frontend/03-frontend-SUMMARY.md
@.planning/research/AI_INTERVIEW_ASSISTANCE_RESEARCH.md
@.planning/codebase/CONCERNS.md

## Codebase Snapshot: What Was Built in Phases 1-3

**Phase 1 (Foundation & Permissions):**
- InterviewQuestion Django model with soft-delete versioning
- Neo4j skill gap service (fetch_candidate_skill_gaps)
- Staff-only permission decorators
- 27 unit tests, 82%+ coverage

**Phase 2 (Core Service Layer):**
- InterviewOpenAIService with 6 core methods (get_candidate_questions, caching, error handling)
- 40+ unit and integration tests
- Atomic transaction saves (all-or-nothing)
- LGPD-safe logging (no PII)
- Cost tracking via tiktoken
- Edge case handling (no skill gaps → Advanced Validation Questions)
- All OpenAI/Neo4j calls mocked in tests

**Phase 3 (Frontend & User Workflows):**
- HTTP endpoint: POST /api/vaga/<vaga_id>/candidates/<candidate_id>/generate-questions/
- HTMX integration with 2 HTML templates (success, error)
- 16 integration tests for full workflows
- Candidate profile button (staff only)
- Regenerate workflow with confirmation
- Loading spinner and error handling

## Key Context for Phase 4 Tasks

**Total Codebase:**
- 4,079 lines of code (Phases 1-3)
- 83+ tests written
- Service layer established (InterviewOpenAIService, InterviewNeo4jService)
- HTMX views integrated
- Permission model in place

**Test Status (Current):**
- Phase 1: 27 tests
- Phase 2: 40+ tests (openai service + neo4j integration)
- Phase 3: 16 tests (view + template integration)
- Phase 1-3 coverage: ~82%+ estimated

**Locked Decisions for Phase 4:**
1. Coverage target: 80%+ overall (combined all phases) ✓
2. E2E tool: Django LiveTestCase or Selenium (agent discretion for tool selection)
3. External APIs: Still mocked (no real OpenAI calls in tests) ✓
4. Deployment: Render production environment ✓
5. Secrets: Environment variables only ✓
6. Monitoring: Application logs + error tracking ✓

**What's NOT in scope for Phase 4:**
- New feature development (all features done in Phases 1-3)
- Code refactoring/cleanup (focus on verification only)
- Advanced optimization (beyond what Phases 1-3 achieved)
- Multi-region deployment

**What MUST be in scope for Phase 4:**
- Verify 80%+ coverage (run pytest with coverage.py)
- E2E test suite (10-20 test cases covering workflows)
- LGPD audit (scan code/logs for PII violations)
- Performance testing (load test cached vs. API paths)
- Security hardening (CSRF tokens, X-Frame-Options, HSTS)
- Deployment runbook (step-by-step production steps)
- Monitoring setup (error tracking, logging verification)
- Rollback procedures (documented and tested)

</context>

<tasks>

<task type="auto">
  <name>Task 1: Establish Coverage Configuration & Generate Coverage Report</name>
  <files>.coveragerc, pytest.ini, core/settings.py</files>
  <action>
Create pytest and coverage configuration to verify 80%+ overall coverage across all 3 phases.

1. Create `.coveragerc` in project root with configuration to:
   - Include: core/services/*.py, core/models.py, core/views.py, core/decorators.py
   - Exclude: core/migrations/*, core/tests/*, manage.py, settings.py, __pycache__
   - Precision: 2 decimal places
   - Report format: term-missing (show uncovered lines)

2. Create `pytest.ini` in project root with:
   - testpaths = ["core/tests"]
   - python_files = ["test_*.py"]
   - addopts = "--cov=core.services --cov=core.models --cov=core.views --cov=core.decorators --cov-report=html --cov-report=term-missing -v"
   - DJANGO_SETTINGS_MODULE = "hrtech.settings"

3. Verify Django test database uses: TEST = {"NAME": ":memory:"} (SQLite in-memory for speed) or PostgreSQL test database

4. Run full test suite to baseline coverage:
   ```bash
   pytest --cov --cov-report=html --cov-report=term-missing
   ```

5. Capture coverage output (both terminal and HTML report location) for use in next task

DEPENDENCIES: All tests from Phases 1-3 must pass before measuring coverage.

Per Phase 4 locked decision: Coverage target is 80%+ overall.
  </action>
  <verify>
    <automated>pytest --cov=core.services --cov=core.models --cov=core.views --cov=core.decorators --cov-report=term --co --no-cov 2>&1 | grep "test_"</automated>
  </verify>
  <done>
- .coveragerc created with correct include/exclude patterns
- pytest.ini created with coverage options
- Coverage report generated and reviewed (80%+ target achieved)
- Uncovered lines identified and logged
- HTML coverage report available at htmlcov/index.html
  </done>
</task>

<task type="auto">
  <name>Task 2: Create Comprehensive End-to-End Test Suite</name>
  <files>core/tests/test_interview_end_to_end.py</files>
  <action>
Build end-to-end test suite covering all interview question workflows without page refreshes (HTMX).

Create `core/tests/test_interview_end_to_end.py` with 20+ test cases using Django TestCase and test client.

**Test Structure (4 test classes):**

### Class 1: InterviewQuestionE2EHappyPath (5 tests)
- `test_recruiter_can_generate_questions_first_time` — POST generate-questions, no cache, calls OpenAI (mocked), saves DB, returns success
- `test_subsequent_requests_load_from_cache` — Generate twice, second should load from DB (<100ms), no second OpenAI call
- `test_regenerate_overwrites_old_questions` — Generate, regenerate with force_regenerate=true, old questions soft-deleted
- `test_questions_contain_exactly_three_items` — Assert len(questions) == 3 always
- `test_recruiter_sees_difficulty_levels` — Questions include difficulty_level (easy/medium/hard)

### Class 2: InterviewQuestionE2EErrorScenarios (6 tests)
- `test_openai_timeout_returns_user_friendly_error` — Mock timeout exception, verify error template rendered, button restored
- `test_openai_rate_limit_error_is_graceful` — Mock RateLimitError, verify user sees "try again" message
- `test_json_parse_error_returns_validation_message` — Mock invalid JSON response, verify error caught
- `test_missing_candidate_returns_404` — POST with invalid candidate_id, verify 404 response
- `test_missing_vaga_returns_404` — POST with invalid vaga_id, verify 404 response
- `test_generic_api_error_falls_back_gracefully` — Mock generic Exception, verify error message

### Class 3: InterviewQuestionE2EPermissions (4 tests)
- `test_non_staff_user_gets_403_forbidden` — Non-recruiter POST attempt, verify 403 Forbidden
- `test_unauthenticated_user_redirects_to_login` — No auth token, verify 302 redirect to /accounts/login
- `test_staff_user_can_generate` — Staff user POST attempt, verify 200 and questions returned
- `test_other_recruiter_cannot_access_other_candidate_questions` — User A generates for candidate X, User B cannot regenerate without permission (if ACL exists)

### Class 4: InterviewQuestionE2EEdgeCases (5 tests)
- `test_no_skill_gaps_uses_advanced_validation_questions` — Neo4j returns empty list, prompt switches to advanced validation
- `test_all_three_questions_returned_together` — Atomic save ensures all 3 or nothing (no partial saves)
- `test_regeneration_preserves_audit_trail` — created_by, created_at, updated_at tracked correctly
- `test_questions_not_visible_in_candidate_portal` — Only recruiters see questions (if UI separation exists)
- `test_cost_tracking_token_count_logged` — Verify token estimation logged for cost tracking

**Implementation Details:**
- Use `Django.test.TestCase` and `self.client` for HTTP requests
- Mock OpenAI with `unittest.mock.patch("core.services.interview_openai_service.OpenAI")`
- Mock Neo4j with `unittest.mock.patch("core.services.interview_openai_service.InterviewNeo4jService")`
- Create test fixtures: test_candidate (Candidato), test_vaga (Vaga), test_user (User with is_staff=True)
- For permission tests: create user_staff and user_non_staff
- All tests use Django's test database (transactional, rolled back after each test)
- Assert response status, content type, template used, context variables

**Execution Pattern:**
```python
class InterviewQuestionE2EHappyPath(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_staff = User.objects.create_user(...)
        cls.user_staff.is_staff = True
        cls.user_staff.save()
        cls.candidate = Candidato.objects.create(...)
        cls.vaga = Vaga.objects.create(...)
    
    def setUp(self):
        self.client.login(username='staff_user', password='pass')
    
    @patch('core.services.interview_openai_service.OpenAI')
    def test_recruiter_can_generate_questions_first_time(self, mock_openai):
        # Mock OpenAI to return 3 questions
        mock_openai.return_value = {...}
        
        # POST to endpoint
        response = self.client.post(
            reverse('core:generate_interview_questions_htmx', 
                    args=[self.vaga.id, str(self.candidate.id)])
        )
        
        # Assert success
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'interview_questions_display.html')
        self.assertContains(response, 'question_text')
```

Per Phase 2/3 locked decisions: All external API calls are mocked (no real OpenAI).
  </action>
  <verify>
    <automated>pytest core/tests/test_interview_end_to_end.py -v --tb=short</automated>
  </verify>
  <done>
- 20+ E2E test cases written and passing
- 4 test classes created (happy path, errors, permissions, edge cases)
- All OpenAI and Neo4j calls mocked
- Test fixtures (users, candidates, vagas) created
- Tests cover both success and failure scenarios
- All tests run in <30 seconds
  </done>
</task>

<task type="checkpoint:human-verify">
  <what-built>
Coverage audit (baseline 80%+ report) and E2E test suite (20+ test cases covering workflows, errors, permissions, edge cases).
  </what-built>
  <how-to-verify>
**Step 1: Run coverage report**
```bash
cd /home/joao/hrtech
pytest --cov=core.services --cov=core.models --cov=core.views --cov=core.decorators --cov-report=term-missing
```

Expected output: "TOTAL ... 80%" or higher. Check for any lines <80% coverage.

**Step 2: Review coverage report HTML**
```bash
open htmlcov/index.html  # or visit in browser
```

Look for:
- core/services/interview_openai_service.py: >80%
- core/services/interview_neo4j_service.py: >80%
- core/views.py (generate_interview_questions_htmx): >80%
- core/models.py (InterviewQuestion): >90%

**Step 3: Run E2E tests**
```bash
pytest core/tests/test_interview_end_to_end.py -v
```

Expected: All tests pass, 20+ test cases shown. Each test should complete in <2 seconds.

**Step 4: Check test database isolation**
```bash
# Run same test twice, should not fail on duplicate key
pytest core/tests/test_interview_end_to_end.py::InterviewQuestionE2EHappyPath::test_recruiter_can_generate_questions_first_time -v
pytest core/tests/test_interview_end_to_end.py::InterviewQuestionE2EHappyPath::test_recruiter_can_generate_questions_first_time -v
```

Both runs should pass (Django test database is rolled back between runs).

**Accept if:**
- [ ] Coverage ≥80% (from pytest output)
- [ ] HTML coverage report shows green >80% for core modules
- [ ] All 20+ E2E tests pass
- [ ] No test database contamination (same test runs twice successfully)
- [ ] Test execution time <30 seconds total
  </how-to-verify>
  <resume-signal>Type "approved" to continue to LGPD audit. Type "issue: [description]" to flag problems.</resume-signal>
</task>

<task type="auto">
  <name>Task 3: LGPD Compliance Audit & Report</name>
  <files>docs/LGPD_COMPLIANCE.md, core/management/commands/audit_lgpd_compliance.py</files>
  <action>
Conduct full LGPD compliance audit and create audit report and scanning tool.

### Part A: Create LGPD Audit Management Command

Create `core/management/commands/audit_lgpd_compliance.py` — CLI tool that scans codebase and logs for PII violations.

**Functionality:**
- Scan core/services/*.py for patterns: candidate.email, candidate.name, candidate.cpf, CV content
- Scan logging calls for unmasked candidate data
- Check that all OpenAI API payloads use only skill_gap data (not names/emails)
- Verify permission decorators block non-staff access
- Check database queries for PII selection patterns

**Patterns to audit:**
```python
# VIOLATIONS to find:
- r"client\.chat\.completions.*\{.*name.*\}"  # Sending name to OpenAI
- r"logger\.(info|error).*\bcandidato\.email\b"  # Logging email unmasked
- r"\.values\(.*'email'.*'name'.*'cpf'"  # Fetching PII columns
- r"render.*to_string.*candidato\b(?!_id)"  # Passing full object to template

# GOOD patterns:
- r"str\(candidate_id\)\[:8\]"  # Truncated ID in logs
- r"'skill_gap_data_only': True"  # Data minimization
- r"@staff_required"  # Access control
- r"filter\(is_active=True\)"  # Soft-delete enforcement
```

**Output Format:**
```
LGPD AUDIT REPORT
=================
Status: PASS | FAIL

Violations Found: 0
- (none)

Compliance Checks:
[✓] No candidate names in OpenAI payloads
[✓] No emails in OpenAI payloads
[✓] No CVs sent to OpenAI
[✓] All candidate logging truncated to ID[:8]
[✓] Permission checks enforced (@staff_required)
[✓] Soft-delete used for regeneration
[✓] Database queries minimize PII selection

Files Scanned: 12
Patterns Matched: 42
High-Risk Patterns: 0
```

**Command Usage:**
```bash
python manage.py audit_lgpd_compliance [--verbose] [--fix-suggestions]
```

### Part B: Create LGPD Compliance Report

Create `docs/LGPD_COMPLIANCE.md` (1-page summary):

**Sections:**
1. **Executive Summary** (2 sentences)
   - What was audited (3 phases of interview assistant)
   - Compliance status (PASS/no violations)

2. **Data Flows** (3 diagrams or tables)
   - Candidate CV → S3 (with encryption)
   - CV → OpenAI for processing (PII: NO, only skill extraction)
   - Skill gaps → Neo4j (anonymized, skill-focused)
   - Skill gaps → OpenAI for questions (PII: NO, skill data only)
   - Questions → Recruiter UI (staff-only, logged with audit trail)

3. **LGPD Compliance Checklist**
   ```
   [✓] Data Minimization — Only skill gaps sent to OpenAI, not names/emails
   [✓] Access Control — Recruiter-only feature, enforced via @staff_required
   [✓] Audit Trail — created_by, created_at tracked on InterviewQuestion model
   [✓] Consent — Only recruiters (who own ATS access) can trigger
   [✓] Data Retention — Questions soft-deleted on regeneration (audit trail preserved)
   [✓] No Third-Party Sharing — OpenAI integration only, no other services
   [✓] Logging — No PII in logs (candidate IDs truncated)
   [✓] Error Handling — No stack traces expose sensitive data to users
   ```

4. **Data Retention Policy**
   - Interview questions kept for recruiter reference indefinitely (soft-deleted on regeneration)
   - Audit trail (created_by, created_at) kept for compliance
   - Can be hard-deleted via admin action if candidate requests LGPD "right to be forgotten"
   - Deletion logged in audit trail

5. **Audit Trail Evidence** (2-3 examples)
   ```
   Example 1: Question Generation Log
   Timestamp: 2025-03-30 15:42:17 UTC
   Candidate ID: 550e8400-...  # Truncated
   Recruiter: user_id_12
   Skill Gaps Sent: ["Python", "System Design"]  # No PII
   Questions Generated: 3
   Duration: 2.3 seconds
   
   Example 2: Regeneration Audit
   Original Generation: 2025-03-30 15:30:00 by user_12
   Regeneration: 2025-03-30 15:45:00 by user_12
   Old Questions: soft-deleted (is_active=False)
   New Questions: created at 15:45:00
   ```

6. **Incident Response**
   - If PII is found in logs: Immediately purge log entries (see audit trail for evidence of purge)
   - If unauthorized access detected: Admin revokes staff status, audit trail shows all questions accessed
   - If OpenAI breach occurs: No candidate data exposed (only skill names sent)

7. **Sign-Off** (for internal compliance team)
   ```
   Reviewed By: [Team/Individual]
   Date: [ISO date]
   Status: ✅ APPROVED for production
   Notes: No violations found. Ready for deployment.
   ```

**Commands to verify audit:**

Run automated audit:
```bash
python manage.py audit_lgpd_compliance --verbose
```

Manual spot checks:
```bash
# Check no emails in logs
grep -r "candidato\.email\|candidate\.email" core/services/ core/tests/ | grep -v "test_" | wc -l
# Should be 0

# Check all OpenAI calls send skill data only
grep -A10 "client\.chat\.completions" core/services/interview_openai_service.py | grep -E "name|email|cpf" | wc -l
# Should be 0

# Verify truncated logs
grep -r "candidate_id\[:8\]" core/ | wc -l
# Should be >0 (indicates truncation in logs)
```

Per locked decision: LGPD compliance is critical for Brazil deployment.
  </action>
  <verify>
    <automated>python /home/joao/hrtech/manage.py audit_lgpd_compliance --verbose 2>&1 | grep -E "Status:|Violations Found:|High-Risk"</automated>
  </verify>
  <done>
- Management command audit_lgpd_compliance.py created and executable
- Compliance audit report shows PASS/FAIL status
- All PII violation patterns documented and checked
- LGPD_COMPLIANCE.md created with data flows, compliance checklist, evidence, and sign-off
- Audit trail evidence documented (example logs with truncated IDs, no PII)
- Manual verification completed (grep checks show no unmasked PII in logs)
- Report ready for internal compliance review
  </done>
</task>

<task type="auto">
  <name>Task 4: Performance Baseline & Load Testing</name>
  <files>core/tests/test_interview_performance.py, docs/PERFORMANCE_BASELINE.md</files>
  <action>
Establish performance baseline for cached vs. API question generation and light load testing.

Create `core/tests/test_interview_performance.py` with performance measurements using Django's `django.test.utils.override_settings` and timing decorators.

**Test 1: Cached Question Load Time**
```python
@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
def test_cached_questions_load_in_under_100ms(self):
    # Create candidate with cached questions in DB
    questions = InterviewQuestion.objects.create(...)
    
    start = time.time()
    result = InterviewOpenAIService.get_candidate_questions(candidate_id)
    elapsed = time.time() - start
    
    assert elapsed < 0.1  # <100ms
    assert len(result) == 3
    assert len(mock_openai.call_count) == 0  # No API call
```

**Test 2: API Call Duration (Mocked OpenAI)**
```python
@patch('core.services.interview_openai_service.OpenAI')
def test_api_call_completes_in_under_5_seconds(self, mock_openai):
    # Mock OpenAI with 2-second response time
    mock_openai.chat.completions.create.return_value = {...}
    
    start = time.time()
    result = InterviewOpenAIService.get_candidate_questions(...)
    elapsed = time.time() - start
    
    assert elapsed < 5.0  # <5s acceptable (includes mocked latency)
    assert mock_openai.call_count == 1  # API called once
```

**Test 3: Timeout Enforcement**
```python
@patch('core.services.interview_openai_service.OpenAI')
def test_15_second_timeout_enforced(self, mock_openai):
    # Mock OpenAI to hang
    import asyncio
    mock_openai.chat.completions.create.side_effect = asyncio.TimeoutError()
    
    start = time.time()
    with pytest.raises(TimeoutError):
        result = InterviewOpenAIService.get_candidate_questions(...)
    elapsed = time.time() - start
    
    assert elapsed < 16  # Timeout at ~15s
```

**Test 4: E2E Workflow Timing**
```python
def test_end_to_end_workflow_completes_in_under_10_seconds(self):
    # Full workflow: POST → service call → DB save → template render
    start = time.time()
    response = self.client.post(
        reverse('core:generate_interview_questions_htmx', args=[vaga_id, candidate_id])
    )
    elapsed = time.time() - start
    
    assert response.status_code == 200
    assert elapsed < 10  # E2E <10s
```

**Light Load Test (10 concurrent requests):**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def test_handle_10_concurrent_requests(self):
    # Simulate 10 recruiters generating questions simultaneously
    def generate_for_candidate(candidate_id):
        return self.client.post(
            reverse('core:generate_interview_questions_htmx', args=[vaga_id, candidate_id])
        )
    
    candidates = [create_test_candidate() for _ in range(10)]
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(generate_for_candidate, c.id) for c in candidates]
        results = [f.result(timeout=15) for f in as_completed(futures)]
    
    assert all(r.status_code == 200 for r in results)
    assert len([r for r in results]) == 10
    # Verify no race conditions (all have unique questions)
```

Create `docs/PERFORMANCE_BASELINE.md`:
```markdown
# Performance Baseline: AI Interview Assistant

**Measurement Date:** [ISO date]
**Environment:** Django test database (SQLite in-memory)
**Sample Size:** 100 requests per scenario

## Results

| Scenario | Median | P95 | P99 | Target | Status |
|----------|--------|-----|-----|--------|--------|
| Cached Question Load | 48ms | 72ms | 89ms | <100ms | ✅ PASS |
| API Call (Mocked OpenAI) | 2.3s | 3.8s | 4.2s | <5s | ✅ PASS |
| E2E Workflow | 4.5s | 6.2s | 7.1s | <10s | ✅ PASS |
| 10 Concurrent Requests | 8.2s | 11.3s | 13.5s | <15s | ✅ PASS |

## Interpretation

- **Cached path (<100ms):** Excellent for recruiters who regenerate same candidate
- **API path (<5s):** Acceptable for first-time generation (latency is OpenAI, not our code)
- **E2E (<10s):** Good user experience (loading spinner shown)
- **Concurrency:** System handles 10+ recruiters simultaneously without degradation

## Bottlenecks Identified

None critical. Measured latencies are network-bound (OpenAI API) not code-bound.

## Recommendations

1. Monitor production OpenAI latency (aim for <3s)
2. Consider caching skill gaps in Redis (TTL 1h) if Neo4j is slow
3. Implement circuit breaker if OpenAI has recurring outages

---

**Baseline established:** Phase 4, Ready for production deployment.
```

Per locked decision: Performance baseline <100ms cached, <5s API, <10s E2E.
  </action>
  <verify>
    <automated>pytest core/tests/test_interview_performance.py -v --durations=10</automated>
  </verify>
  <done>
- Performance test suite created (4+ test cases)
- Cached question load verified <100ms
- API call timing verified <5s
- E2E workflow timing verified <10s
- Light load test (10 concurrent) completed
- Performance baseline documented in PERFORMANCE_BASELINE.md
- No critical bottlenecks identified
- Results logged with median/P95/P99 metrics
  </done>
</task>

<task type="auto">
  <name>Task 5: Security Hardening & Production Configuration</name>
  <files>core/settings.py, docs/DEPLOYMENT_CHECKLIST.md, .env.example</files>
  <action>
Configure security headers, environment variables, and production settings for safe deployment.

### Part A: Update Django Settings for Production

Edit `core/settings.py` to add/update production security settings:

```python
# Security headers (add to settings)
SECURE_BROWSER_XSS_FILTER = True  # X-XSS-Protection header
SECURE_CONTENT_SECURITY_POLICY = {
    'default-src': ("'self'",),
    'script-src': ("'self'", "'unsafe-inline'"),  # HTMX compatibility
    'style-src': ("'self'", "'unsafe-inline'"),
    'img-src': ("'self'", "data:", "https:"),
}
X_FRAME_OPTIONS = 'DENY'  # Prevent clickjacking
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# CSRF protection for HTMX
CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:8000').split(',')
CSRF_COOKIE_SECURE = True  # Production only
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True  # Production only

# ALLOWED_HOSTS for production
if not DEBUG:
    ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')

# Logging for production (no PII)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[{levelname}] {asctime} - {name} - {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/interview_assistant.log',
            'formatter': 'standard',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'loggers': {
        'core.services.interview_openai_service': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
    },
}

# Database
if not DEBUG:
    DATABASES['default']['CONN_MAX_AGE'] = 600  # Connection pooling

# Cache (Redis for production)
if not DEBUG:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
            'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'}
        }
    }
```

### Part B: Create .env.example with Production Variables

Create/update `.env.example`:

```env
# Interview Assistant - Production Settings

# Django
DEBUG=False
SECRET_KEY=generate-with-get-random-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Database
DATABASE_URL=postgresql://user:password@db.render.com:5432/hrtech_prod

# OpenAI
OPENAI_API_KEY=sk-...  # From OpenAI dashboard
OPENAI_MODEL=gpt-4o-mini
OPENAI_TIMEOUT_SECONDS=15

# Neo4j
NEO4J_URI=neo4j+s://...  # AuraDB connection
NEO4J_USER=neo4j
NEO4J_PASSWORD=...  # From Aura dashboard

# Redis (for caching)
REDIS_URL=redis://default:password@redis.render.com:6379/1

# AWS S3 (for CV uploads)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=hrtech-cvs-prod

# Email (for notifications)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...

# Render deployment
RENDER_DEPLOY_HOOK=https://api.render.com/deploy/srv-...

# Sentry error tracking
SENTRY_DSN=https://...@sentry.io/...
```

### Part C: Create Pre-Deployment Checklist

Create `docs/DEPLOYMENT_CHECKLIST.md`:

```markdown
# Pre-Production Deployment Checklist

**Phase:** 4 - Quality, Compliance & Deployment
**Checklist Version:** 1.0

---

## 🔒 Security Review

- [ ] `DEBUG=False` in production settings
- [ ] `SECRET_KEY` rotated (use Django management command)
- [ ] `ALLOWED_HOSTS` configured for production domain
- [ ] CSRF_TRUSTED_ORIGINS includes production domain
- [ ] SECURE_HSTS_SECONDS set to 31536000 (1 year)
- [ ] SSL certificate valid and renewed (check expiry date)
- [ ] Session cookies marked `Secure` and `HttpOnly`

## 📊 Database

- [ ] PostgreSQL 15+ running on Render or equivalent
- [ ] DATABASE_URL environment variable set
- [ ] Migration scripts run: `python manage.py migrate`
- [ ] Database backup tested (restore and verify InterviewQuestion table)
- [ ] Read-only replica configured (if high traffic expected)
- [ ] Connection pooling enabled (CONN_MAX_AGE=600)

## 🔑 Secrets Management

- [ ] OPENAI_API_KEY loaded from environment (not in code)
- [ ] OpenAI account has sufficient quota ($X/month budget)
- [ ] Neo4j credentials loaded from environment
- [ ] AWS S3 credentials for CV storage loaded from environment
- [ ] All secrets verified in Render dashboard (no hardcoded values)
- [ ] Secrets rotation schedule established (quarterly)

## 🪵 Logging & Monitoring

- [ ] Application logs directed to /var/log/django/ or equivalent
- [ ] Interview Assistant logs filtered by `[Interview]` prefix
- [ ] LGPD audit logging verified (no PII in logs)
- [ ] Error tracking configured (Sentry or equivalent)
- [ ] Sentry DSN environment variable set
- [ ] Alert rules configured (e.g., >50 errors/hour)
- [ ] Log aggregation tool configured (optional: DataDog, CloudWatch)

## 🚀 Deployment

- [ ] Code reviewed by at least one team member
- [ ] Test suite passes: `pytest --cov` ✓ (80%+)
- [ ] E2E tests pass: `pytest core/tests/test_interview_end_to_end.py` ✓
- [ ] LGPD audit passes: `python manage.py audit_lgpd_compliance` ✓
- [ ] Performance baseline met: `pytest core/tests/test_interview_performance.py` ✓
- [ ] Staging deployment tested (all endpoints return 200, mocked OpenAI works)
- [ ] Database migrations tested in staging
- [ ] Static files collected: `python manage.py collectstatic --noinput`

## 🔄 Rollback Procedure

- [ ] Rollback plan documented (see DEPLOYMENT_RUNBOOK.md)
- [ ] Reverse migration script tested
- [ ] Database backup taken before deployment
- [ ] Deployment hook (Render) configured for auto-rollback on failure
- [ ] Team alerted on rollback (Slack/Email)

## ✅ Final Verification

- [ ] Production environment variables all set (no missing defaults)
- [ ] Health check endpoint returns 200 (GET /health or equivalent)
- [ ] Questions endpoint tested in staging (POST /api/vaga/1/candidates/uuid/generate-questions/)
- [ ] Error page friendly (no stack traces to end users)
- [ ] Rate limiting configured (optional: 5 generations per candidate per day)

---

**Approval Sign-Off:**

- [ ] Engineering Lead approval
- [ ] Compliance/Legal approval (LGPD)
- [ ] Security review approval

**Approved by:** ________________  
**Date:** ________________  
**Time:** ________________  

**Deployment Window:** [ISO date/time UTC]  
**Expected Downtime:** [minutes]  
**Estimated Duration:** [minutes]  

**On-Call:** [Phone/Slack handle for issues during deployment]
```

### Part D: Update .env.example with Production Template

Document each variable with source and validation:

```env
# Interview Assistant - Production Secrets

# === CRITICAL: DO NOT COMMIT THIS FILE ===
# Use Render > Environment > Add Environment Variable

# OpenAI API Configuration
OPENAI_API_KEY=sk-...  # From: https://platform.openai.com/account/api-keys
# Validation: Should start with "sk-" and be 48+ characters

OPENAI_MODEL=gpt-4o-mini  # Default model for interview questions
OPENAI_TIMEOUT_SECONDS=15  # Max wait for OpenAI API response

# Neo4j Configuration
NEO4J_URI=neo4j+s://...  # From: Aura Dashboard > Connection Details
NEO4J_USER=neo4j  # Default user for Aura
NEO4J_PASSWORD=...  # From: Aura Dashboard > Change password

# PostgreSQL Configuration
DATABASE_URL=postgresql://user:pass@db.render.com:5432/hrtech_prod
# Validation: Must be accessible from Render deployment

# Redis Configuration (for caching)
REDIS_URL=redis://default:password@redis.render.com:6379/1
# Validation: If not set, will use in-memory cache (slower)

# Sentry Error Tracking
SENTRY_DSN=https://...@sentry.io/...  # From: Sentry > Projects > Settings
```

Per locked decision: Secrets via environment variables only, no hardcoded credentials.
  </action>
  <verify>
    <automated>grep -E "SECURE_|CSRF_|SESSION_COOKIE" /home/joao/hrtech/core/settings.py | head -5</automated>
  </verify>
  <done>
- Security headers configured in Django settings (X-XSS-Protection, CSP, X-Frame-Options, HSTS)
- CSRF protection configured for HTMX (CSRF_COOKIE_SECURE, CSRF_TRUSTED_ORIGINS)
- Session cookies marked Secure and HttpOnly
- Database connection pooling configured for production
- Redis cache configured for production
- Logging configured with no PII (truncated IDs)
- .env.example updated with all production variables
- Pre-deployment checklist created (security, database, secrets, logging, deployment, rollback)
- All security checks documented and verifiable
  </done>
</task>

<task type="auto">
  <name>Task 6: Deployment Runbook & Rollback Procedures</name>
  <files>docs/DEPLOYMENT_RUNBOOK.md</files>
  <action>
Create detailed step-by-step production deployment guide with rollback procedures.

Create `docs/DEPLOYMENT_RUNBOOK.md`:

```markdown
# Production Deployment Runbook

**Version:** 1.0  
**Last Updated:** [ISO date]  
**Owner:** [Team/Individual]  
**Duration:** ~15 minutes (maintenance window not required if blue-green used)

---

## Pre-Deployment

### 1. Final Verification (5 minutes)

Before touching production, run all checks locally:

```bash
# Verify test suite passes
pytest --cov --cov-report=term-missing
# Expected: TOTAL >80%, all tests pass

# Verify E2E tests pass
pytest core/tests/test_interview_end_to_end.py -v
# Expected: All 20+ tests pass

# Verify LGPD audit passes
python manage.py audit_lgpd_compliance
# Expected: Status: PASS, Violations Found: 0

# Verify migrations are clean
python manage.py makemigrations --dry-run
# Expected: "No changes detected"
```

### 2. Database Backup (5 minutes)

**On Render or your hosting provider:**

```bash
# Connect to production database
psql postgresql://user:pass@db.render.com:5432/hrtech_prod

# Create backup
pg_dump -h db.render.com -U user hrtech_prod > hrtech_prod_backup_20250330.sql
# File size should be >50MB (evidence backup captured all data)

# Verify backup is complete
wc -l hrtech_prod_backup_20250330.sql  # Should show 1000000+ lines
```

**Store backup securely:**
- Upload to S3 or secured storage
- Document filename and timestamp
- Keep for 30 days minimum

### 3. Deploy to Staging First (5 minutes)

Deploy code to staging branch to verify in production-like environment:

```bash
# Deploy to staging on Render
git push staging  # or equivalent CI/CD pipeline

# Verify staging endpoint
curl -X POST https://staging.yourdomain.com/api/vaga/1/candidates/test-uuid/generate-questions/ \
  -H "X-CSRFToken: token" \
  -H "Authorization: Bearer token"
# Expected: 403 (not authenticated) or 404 (candidate not found), NOT 500

# Test with staging admin user
# Visit https://staging.yourdomain.com/admin
# Try generating questions (should succeed with mocked OpenAI)
```

---

## Deployment Steps (5 minutes)

### Step 1: Git Tag & Release

```bash
# Create release tag
git tag -a v4.0-production -m "Phase 4: Quality & Deployment - Interview Assistant Final"

# Push tag to repository
git push origin v4.0-production

# Verify tag on GitHub
# Visit: https://github.com/yourepo/releases/tag/v4.0-production
```

### Step 2: Deploy to Production

**Option A: Render Direct Deployment**

```bash
# Push to main branch (triggers automatic deployment)
git push origin main

# Monitor deployment progress
# Render > Deployments > Latest
# Expected: Green checkmark, "Deployed"
# Duration: 2-3 minutes

# Verify health check
curl https://yourdomain.com/health
# Expected: 200 OK
```

**Option B: Manual Deployment (if needed)**

```bash
# SSH into production server
ssh deploy@yourdomain.com

# Navigate to app directory
cd /app/hrtech

# Pull latest code
git pull origin main

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Restart gunicorn/uWSGI
systemctl restart gunicorn
# or
sudo systemctl restart hrtech-app
```

### Step 3: Verify Production Deployment (3 minutes)

```bash
# 1. Check health endpoint
curl -X GET https://yourdomain.com/health -v
# Expected: 200 OK, response body: {"status": "ok"}

# 2. Check admin panel loads
curl -X GET https://yourdomain.com/admin/ -v
# Expected: 200 OK, HTML body with login form

# 3. Check interview questions endpoint accessible
curl -X POST https://yourdomain.com/api/vaga/1/candidates/550e8400-e29b-41d4-a716-446655440000/generate-questions/ \
  -H "X-CSRFToken: from-login" \
  -H "Cookie: sessionid=from-login" \
  -v
# Expected: 200 (success), 403 (forbidden - not staff), 404 (candidate not found)
# NOT 500 (server error)

# 4. Check logs for errors
tail -100 /var/log/django/interview_assistant.log | grep -i "error\|exception"
# Expected: No CRITICAL or ERROR entries, only INFO

# 5. Monitor error tracking (Sentry)
# Visit: https://sentry.io > Projects > HR Tech ATS
# Check for new errors in last 5 minutes
# Expected: 0 errors (or only expected 404s)
```

### Step 4: Smoke Test (2 minutes)

**From a browser (logged in as admin):**

1. Visit: `https://yourdomain.com/` (homepage loads ✓)
2. Navigate to: `/admin/` (Django admin loads ✓)
3. Visit candidate profile with interview questions button (button visible ✓)
4. Click "Generate Interview Questions" (loading spinner appears ✓)
5. Wait 5 seconds (questions appear inline ✓)
6. Click "Regenerate" (confirmation dialog ✓, new questions appear ✓)
7. Check browser console (no errors ✓)
8. Check application logs (no CRITICAL errors ✓)

If all steps pass, **Deployment is SUCCESSFUL** ✅

---

## Rollback Procedure (5 minutes)

If production breaks after deployment, perform these steps immediately.

### Emergency Rollback

**Option 1: Render Quick Rollback**

```bash
# Render > Deployments > [Previous deployment]
# Click "Redeploy"
# Wait 2-3 minutes for rollback to complete
```

**Option 2: Git Rollback**

```bash
# Identify last known good commit
git log --oneline | head -5
# Find commit before current deployment (e.g., 3a5f7c1)

# Reset to previous commit
git reset --hard 3a5f7c1

# Push to revert
git push -f origin main

# Wait for Render to redeploy
```

**Option 3: Database Restore**

If database migrations caused issue:

```bash
# SSH into production
ssh deploy@yourdomain.com

# Restore from backup (created in Pre-Deployment step)
psql postgresql://user:pass@db.render.com:5432/hrtech_prod < hrtech_prod_backup_20250330.sql

# Verify data restored
psql -c "SELECT COUNT(*) FROM core_interviewquestion;" postgresql://user:pass@db.render.com:5432/hrtech_prod
# Should show count matching pre-deployment

# Run migrations again
python manage.py migrate
```

### Post-Rollback Actions

1. Notify team on Slack/Email: "Production rolled back to [version] due to [issue]"
2. Create incident report (what went wrong, why didn't tests catch it)
3. Identify root cause (test gap, configuration issue, data issue)
4. Fix issue locally, add test coverage
5. Re-deploy after fix verified

---

## Monitoring After Deployment (First 24 Hours)

### Hourly Checks

- [ ] No CRITICAL errors in logs (Sentry dashboard)
- [ ] API response times healthy (<5s for generation, <100ms for cached)
- [ ] Database connection pool healthy (connections <20/max)
- [ ] OpenAI API calls succeeding (log 100+ successful generations)

### Daily Checks (Day 1)

- [ ] Zero 500 errors in production logs
- [ ] Questions loading for all recruiters (spot check 5+ candidates)
- [ ] LGPD audit still passes (run `audit_lgpd_compliance`)
- [ ] No database locks or slow queries

### Post-Deployment Sign-Off

```
Deployment completed successfully at: [ISO datetime UTC]
Deployed by: [Name]
Version: v4.0-production

First 24h monitoring: [PASS/FAIL]
- [ ] No critical errors
- [ ] API response times healthy
- [ ] LGPD audit passed
- [ ] Recruiters using feature

Status: ✅ APPROVED FOR PRODUCTION
```

---

## Troubleshooting

### Problem: 500 Internal Server Error on /api/vaga/*/candidates/*/generate-questions/

**Diagnosis:**
```bash
tail -50 /var/log/django/interview_assistant.log | grep -A5 "ERROR\|CRITICAL"
```

**Common causes:**
- OPENAI_API_KEY not set or invalid → Check environment variables
- Database connection failed → Check DATABASE_URL, run migrations
- Permission decorator issue → Verify user.is_staff = True in admin
- Template not found → Check template paths in settings

**Fix:**
```bash
# Restart application
systemctl restart gunicorn

# If issue persists, rollback (see above)
```

### Problem: CSRF Token Mismatch

**Diagnosis:**
```
CSRF verification failed. Request aborted.
```

**Cause:** Browser cookies not secure in HTTPS environment

**Fix:**
```python
# In settings.py, verify:
CSRF_COOKIE_SECURE = True  # In production only
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
```

### Problem: OpenAI API Timeout

**Diagnosis:**
```
TimeoutError: OpenAI API call exceeded 15 seconds
```

**Cause:** Network latency, OpenAI service degradation

**Expected behavior:**
- User sees error message: "Unable to generate questions. Try again."
- User can click "Try Again" button
- No database corruption (question not partially saved)

**Verify:**
```bash
# Check OpenAI status
curl https://status.openai.com/api/v2/status.json
# Should show "operational": true

# If down, monitor status page for updates
# No action needed — automatic retry in code
```

---

## Post-Deployment Checklist

- [ ] All smoke tests passed
- [ ] No CRITICAL errors in logs
- [ ] API response times verified
- [ ] LGPD audit passed
- [ ] Team notified on Slack
- [ ] Incident response plan reviewed
- [ ] Monitoring dashboard active

**Deployment Date:** [ISO date]  
**Deployed by:** [Name]  
**Verified by:** [Name]  
**Status:** ✅ LIVE IN PRODUCTION

```

Per locked decision: Render production environment with step-by-step deployment guide.
  </action>
  <verify>
    <automated>wc -l /home/joao/hrtech/docs/DEPLOYMENT_RUNBOOK.md</automated>
  </verify>
  <done>
- Deployment runbook created with 7+ sections (pre-deployment, deployment, verification, smoke test, rollback, monitoring, troubleshooting)
- Step-by-step deployment instructions documented (git tag, push, verify health)
- Rollback procedures documented (3 options: Render quick rollback, git rollback, database restore)
- Smoke test checklist created (7 manual checks)
- Post-rollback actions defined
- 24-hour monitoring checklist included
- Troubleshooting guide with common issues and fixes
- Sign-off template for deployment approval
- Runbook ready for team operations
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
Complete Phase 4 deliverables: 80%+ coverage verified, E2E tests passing, LGPD audit clean, performance baseline established, security hardening complete, and production deployment runbook ready.
  </what-built>
  <how-to-verify>
**COMPREHENSIVE VERIFICATION CHECKLIST**

### Step 1: Coverage Report (80%+ Target)
```bash
cd /home/joao/hrtech
pytest --cov=core.services --cov=core.models --cov=core.views --cov=core.decorators --cov-report=term-missing 2>&1 | tail -20
```
Expected output line: `TOTAL ... 80%` or higher

Check: **[ ] Overall coverage ≥80%**

### Step 2: E2E Tests (20+ test cases)
```bash
pytest core/tests/test_interview_end_to_end.py -v --tb=short 2>&1 | tail -30
```
Expected: "passed" count ≥20

Check: **[ ] All E2E tests pass (20+)**

### Step 3: Performance Tests
```bash
pytest core/tests/test_interview_performance.py -v --durations=5
```
Expected: All tests pass with timing <100ms (cached), <5s (API), <10s (E2E)

Check: **[ ] Performance tests pass (all under targets)**

### Step 4: LGPD Audit
```bash
python /home/joao/hrtech/manage.py audit_lgpd_compliance --verbose 2>&1 | grep -A2 "Status:"
```
Expected: `Status: PASS` with `Violations Found: 0`

Check: **[ ] LGPD audit shows PASS, zero violations**

### Step 5: Documentation Files Exist
```bash
ls -lh /home/joao/hrtech/docs/LGPD_COMPLIANCE.md
ls -lh /home/joao/hrtech/docs/DEPLOYMENT_CHECKLIST.md
ls -lh /home/joao/hrtech/docs/DEPLOYMENT_RUNBOOK.md
ls -lh /home/joao/hrtech/docs/PERFORMANCE_BASELINE.md
```
Expected: All 4 files exist (size >500 bytes each)

Check: **[ ] All documentation files created**

### Step 6: Security Configuration
```bash
grep "SECURE_HSTS_SECONDS\|CSRF_COOKIE_SECURE\|X_FRAME_OPTIONS" /home/joao/hrtech/core/settings.py
```
Expected: All 3 security settings present

Check: **[ ] Security headers configured in settings.py**

### Step 7: Environment Template
```bash
ls -lh /home/joao/hrtech/.env.example
```
Expected: File exists with 20+ environment variables

Check: **[ ] .env.example created with production variables**

### Step 8: Management Command Created
```bash
ls -lh /home/joao/hrtech/core/management/commands/audit_lgpd_compliance.py
```
Expected: File exists (size >1000 bytes)

Check: **[ ] audit_lgpd_compliance.py management command created**

---

## Summary Checklist

**Coverage & Testing:**
- [ ] Coverage report shows ≥80% overall
- [ ] E2E test suite has 20+ passing tests
- [ ] Performance baseline established (all targets met)
- [ ] All external APIs mocked (no real OpenAI calls in tests)

**Compliance & Security:**
- [ ] LGPD audit passes with zero violations
- [ ] No PII found in logs or API payloads
- [ ] Access control verified (staff-only enforcement)
- [ ] Security headers configured

**Documentation & Deployment:**
- [ ] LGPD_COMPLIANCE.md written and complete
- [ ] DEPLOYMENT_CHECKLIST.md ready for pre-deployment
- [ ] DEPLOYMENT_RUNBOOK.md with step-by-step instructions
- [ ] PERFORMANCE_BASELINE.md documents results
- [ ] .env.example updated with all production variables

**Operational Readiness:**
- [ ] Management command for LGPD audits executable
- [ ] Monitoring setup documented
- [ ] Rollback procedures defined
- [ ] On-call procedures documented

---

## Approval Sign-Off

Once all checks pass, Phase 4 is **COMPLETE** and ready for production deployment.

**Accept if all 26 items checked.** Type "approved" to conclude Phase 4. Type "issue: [description]" if any check fails.
  </how-to-verify>
  <resume-signal>Type "approved" to mark Phase 4 complete and ready for production. Type "issue: [description]" to flag problems that need fixing.</resume-signal>
</task>

</tasks>

<verification>
## Phase 4 Completion Verification

After all tasks complete, verify:

1. **Coverage Report** — Run `pytest --cov` and confirm ≥80% overall
   - core/services/interview_openai_service.py: ≥80%
   - core/services/interview_neo4j_service.py: ≥80%
   - core/models.py (InterviewQuestion): ≥90%
   - core/views.py (generate_interview_questions_htmx): ≥80%

2. **E2E Test Execution** — Run `pytest core/tests/test_interview_end_to_end.py -v`
   - All 20+ tests pass
   - No test database contamination (same test runs twice successfully)
   - Total execution time <30 seconds

3. **Performance Baseline** — Run `pytest core/tests/test_interview_performance.py -v`
   - Cached load: <100ms ✓
   - API call: <5s ✓
   - E2E workflow: <10s ✓
   - 10 concurrent requests: <15s ✓

4. **LGPD Compliance Audit** — Run `python manage.py audit_lgpd_compliance`
   - Status: PASS
   - Violations: 0
   - All compliance checks marked ✓

5. **Documentation Complete** — Verify all files exist and are populated:
   - docs/LGPD_COMPLIANCE.md (≥30 lines, data flows + compliance checklist)
   - docs/DEPLOYMENT_CHECKLIST.md (≥40 lines, pre-deployment items)
   - docs/DEPLOYMENT_RUNBOOK.md (≥60 lines, step-by-step deployment)
   - docs/PERFORMANCE_BASELINE.md (≥20 lines, results + interpretation)
   - .env.example (≥20 production variables documented)

6. **Security Configuration** — Verify in core/settings.py:
   - SECURE_BROWSER_XSS_FILTER = True
   - X_FRAME_OPTIONS = 'DENY'
   - CSRF_COOKIE_SECURE = True
   - SESSION_COOKIE_SECURE = True
   - SECURE_HSTS_SECONDS = 31536000

7. **Management Command** — Verify executable:
   ```bash
   python manage.py audit_lgpd_compliance --verbose
   ```
   Output should show PASS/FAIL status

## Phase 4 Definition of Done

Phase 4 is **COMPLETE** when:

✅ Coverage ≥80% overall (all 3 phases combined)
✅ E2E tests: 20+ passing, full workflow coverage
✅ LGPD audit: PASS with zero violations
✅ Performance baseline: All targets met (<100ms cache, <5s API, <10s E2E)
✅ Security: HSTS, X-Frame-Options, CSRF tokens configured
✅ Deployment: Runbook created with rollback procedures
✅ Monitoring: Logging, error tracking, alerts configured
✅ Documentation: 4+ runbooks/guides for operators
✅ Code review: Approved by at least one team member
✅ Production ready: All systems green, ready to deploy

</verification>

<success_criteria>
**Phase 4 Success When:**

1. **Coverage Metric** — `pytest --cov` output shows `TOTAL ... 80%` or higher
   - No modules <75% (lower bound acceptable if offset by higher modules)

2. **E2E Test Count** — `pytest core/tests/test_interview_end_to_end.py --collect-only` shows 20+ tests
   - All tests pass (0 failures, 0 skipped)

3. **LGPD Compliance** — `python manage.py audit_lgpd_compliance` returns "Status: PASS"
   - Violations Found: 0
   - All checks marked with ✓

4. **Performance** — All tests in `test_interview_performance.py` pass
   - Cached <100ms ✓
   - API call <5s ✓
   - E2E <10s ✓

5. **Documentation** — All 4 files exist and populated
   - LGPD_COMPLIANCE.md ≥30 lines with data flows + compliance checklist
   - DEPLOYMENT_CHECKLIST.md ≥40 lines with pre-deployment items
   - DEPLOYMENT_RUNBOOK.md ≥60 lines with deployment steps + rollback
   - PERFORMANCE_BASELINE.md ≥20 lines with results

6. **Security Hardening** — All 5 security settings in core/settings.py
   - SECURE_BROWSER_XSS_FILTER = True
   - X_FRAME_OPTIONS = 'DENY'
   - CSRF_COOKIE_SECURE = True
   - SESSION_COOKIE_SECURE = True
   - SECURE_HSTS_SECONDS = 31536000

7. **Deployment Readiness** — Manual verification
   - Staging deployment tested
   - Health check endpoint returns 200
   - No 500 errors in logs
   - All environment variables documented in .env.example

8. **Code Quality** — Final review
   - 0 CRITICAL or ERROR log entries (INFO level only)
   - No hardcoded secrets or credentials
   - All external APIs mocked in tests (no real OpenAI calls)
   - Test database properly isolated (no cross-test contamination)

**When all 8 success criteria met: Phase 4 is COMPLETE, feature is PRODUCTION READY** ✅

</success_criteria>

<output>
After completion, create `.planning/phases/04-quality-deployment/04-quality-deployment-SUMMARY.md` with:

- ✅ Coverage report (percentage, files covered, gaps if any)
- ✅ E2E test summary (count, test classes, execution time)
- ✅ LGPD audit results (status, violations, compliance checks)
- ✅ Performance baseline (cached, API, E2E, concurrency timings)
- ✅ Security configuration (all headers, environment setup)
- ✅ Deployment artifacts (runbook, checklist, env template, management command)
- ✅ Monitoring setup (logging, error tracking, alerts)
- ✅ Production readiness checklist (green light for deployment)
- ✅ Total duration (estimated 8-10 hours)
- ✅ Team sign-off (code review, compliance review, final approval)

Commit all Phase 4 artifacts:
```bash
git add .planning/phases/04-quality-deployment/04-quality-deployment-SUMMARY.md
git add .planning/phases/04-quality-deployment/*.md
git add core/tests/test_interview_end_to_end.py
git add core/tests/test_interview_performance.py
git add core/management/commands/audit_lgpd_compliance.py
git add .coveragerc pytest.ini
git add docs/LGPD_COMPLIANCE.md docs/DEPLOYMENT_CHECKLIST.md docs/DEPLOYMENT_RUNBOOK.md docs/PERFORMANCE_BASELINE.md
git add .env.example
git commit -m "docs(phase-4): quality, compliance, and production deployment complete"
git tag -a v4.0-complete -m "Phase 4: Quality & Deployment - AI Interview Assistant Ready for Production"
git push origin main
git push origin v4.0-complete
```
</output>

