# Phase 1: Foundation & Permissions - PLAN

**Created:** 2025-03-29  
**Status:** Ready for execution  
**Target Duration:** 1-2 weeks (1-2 person-days effort)

---

## 📋 Plan Overview

### Goal
Build the data model, permissions infrastructure, and Neo4j integration for the AI Interview Assistant feature. This phase establishes the foundation that all subsequent phases (Core Service, OpenAI Integration, Frontend) depend on.

### Success Criteria
- ✅ InterviewQuestion model created with all required fields and relationships
- ✅ Database migration created, tested, and applied locally
- ✅ Model admin registered for Django admin interface
- ✅ Neo4j skill gap queries implemented and tested (mocked)
- ✅ Permission checks verified (403 response for unauthorized users)
- ✅ Unit tests written with **80%+ coverage** for interview module
- ✅ Code follows project conventions (CONVENTIONS.md)
- ✅ All tests pass locally
- ✅ Git commit with summary prepared for PR

### Estimated Duration
- **Model + Migration:** 1-2 hours
- **Neo4j Integration:** 2-3 hours (query development + testing)
- **Permissions + Admin:** 1 hour
- **Unit Tests:** 3-4 hours (to reach 80% coverage)
- **Buffer & Review:** 1 hour
- **Total:** ~8-11 hours (1-1.5 person-days)

---

## 🏗️ Work Breakdown

### Task Group 1: Data Model & Migration (Prerequisite)

#### Task 1.1: Create InterviewQuestion Django Model
**Owner:** Agent  
**Effort:** 1-2 hours  
**Blocks:** All other tasks

**Description:**
Create the InterviewQuestion model in `core/models.py` with:
- ForeignKey to Candidate (on_delete=CASCADE, related_name='interview_questions')
- ForeignKey to User for created_by (on_delete=SET_NULL, null=True)
- TextField for question_text
- CharField for difficulty_level with choices (easy, medium, hard)
- DateTimeField for created_at (auto_now_add=True)
- DateTimeField for updated_at (auto_now=True)
- BooleanField for is_active (default=True, for soft-delete on regeneration)
- Meta: ordering=['-created_at'], unique_together on (candidate, is_active) to enforce one active set

**Key Details:**
- Follow existing model patterns from Candidato, Vaga, etc.
- Use UUID primary key if consistent with codebase patterns (check existing models)
- Add helpful docstring explaining the model's role in the interview workflow
- Add __str__() method returning readable representation (e.g., "Q: {question_text[:50]}... (Difficulty: {difficulty})")

**Acceptance Criteria:**
- Model defined in core/models.py
- All 8 fields present with correct types and constraints
- Model has verbose_name and verbose_name_plural in Meta
- Model includes docstring with usage notes
- No syntax errors when imported

---

#### Task 1.2: Create & Apply Database Migration
**Owner:** Agent  
**Effort:** 30-45 minutes  
**Depends On:** Task 1.1

**Description:**
Create Django migration for the InterviewQuestion table:

1. Run: `python manage.py makemigrations core`
   - Should generate `core/migrations/000X_auto_YYYYMMDD_HHMM.py`
   
2. Review migration file:
   - Verify all fields are present
   - Verify ForeignKey constraints reference correct models
   - Verify indexes are created for:
     - candidate_id (for "get questions for candidate" queries)
     - created_by_id (for "get questions created by recruiter" queries)
     - is_active (for filtering active vs. inactive questions)
   - Verify unique_together constraint on (candidate, is_active)

3. Test migration:
   - Run: `python manage.py migrate core --plan` (dry run, shows SQL)
   - Run: `python manage.py migrate core` (apply to test DB)

4. Document migration in git commit message

**Key Details:**
- Use Django's migration system, no manual SQL
- Ensure migration is reversible (for rollback capability)
- Test both forward and reverse migrations locally

**Acceptance Criteria:**
- Migration file exists in core/migrations/
- `python manage.py migrate core` completes without errors
- Database schema includes InterviewQuestion table with all columns
- Indexes created for candidate_id, created_by_id, is_active
- Migration is reversible: `python manage.py migrate core 000X --zero` works

---

### Task Group 2: Admin Interface (Fast Win)

#### Task 2.1: Register Model in Django Admin
**Owner:** Agent  
**Effort:** 30 minutes  
**Depends On:** Task 1.1

**Description:**
Register InterviewQuestion in `core/admin.py`:

1. Create ModelAdmin class: `InterviewQuestionAdmin`
   - list_display: (question_text, difficulty_level, created_by, created_at, is_active)
   - list_filter: (difficulty_level, is_active, created_at)
   - search_fields: (question_text, candidate__name)
   - readonly_fields: (created_at, updated_at)
   - fieldsets: Group fields logically (Content, Metadata, Status)
   - ordering: ('-created_at',)

2. Register model: `admin.site.register(InterviewQuestion, InterviewQuestionAdmin)`

3. Verify in Django admin:
   - Navigate to http://localhost:8000/admin/
   - Confirm InterviewQuestion appears in app list
   - Confirm list view displays columns correctly
   - Confirm filters and search work

**Key Details:**
- Follow existing admin patterns from Candidato, Vaga admin classes
- Make question_text and difficulty_level read-only (no manual editing via admin)
- Add helpful help_text to fields in fieldsets

**Acceptance Criteria:**
- ModelAdmin class created and registered
- Django admin loads without errors
- Admin list view displays all key fields
- Filters and search functionality work
- Read-only fields cannot be edited

---

### Task Group 3: Neo4j Integration (Critical)

#### Task 3.1: Design & Document Neo4j Skill Gap Query
**Owner:** Agent  
**Effort:** 1 hour  
**Depends On:** None (parallel with 1.1-1.2)

**Description:**
Design and document the Neo4j Cypher query for extracting candidate skill gaps:

1. **Query Purpose:**
   Extract skills required for a job position that a candidate does NOT possess.
   
   Input: candidate_id (UUID), job_position_id (UUID)  
   Output: List of {skill_name, required_level, candidate_current_level}

2. **Query Design:**
   - Find Vaga (job) node with job_position_id
   - Get list of required skills from Vaga.skills_obrigatorias JSONField (or Neo4j relationships)
   - Find Candidato node with candidate_id
   - Check which required skills candidate possesses (via POSSUE relationship?)
   - Return skills present in Vaga but absent in Candidato (gap analysis)
   - Also return similarity-based matches (SIMILAR_A relationships)

3. **Edge Cases:**
   - Candidate has zero skills → all job skills are gaps
   - Candidate has all skills → empty gap list (triggers "Advanced Validation" prompt in Phase 2)
   - Job has no skills defined → empty gap list

4. **Documentation:**
   Create docstring explaining:
   - Cypher query structure
   - Parameter names and types
   - Expected return format (JSON structure)
   - Examples of return values for different scenarios
   - Link to Neo4j ARCHITECTURE.md patterns

**Key Details:**
- Review existing Neo4j queries in `core/matching.py` (ARCHITECTURE.md references them)
- Look for patterns in how skills are stored (JSONField vs. graph relationships)
- Determine if query runs against existing Neo4j schema or if new relationships needed
- Consider performance (query should run in < 100ms for typical data)

**Acceptance Criteria:**
- Query documented with clear parameter/return format
- Query handles all edge cases (zero skills, full match, missing data)
- Query aligns with existing Neo4j patterns in codebase
- Query performance considerations documented

---

#### Task 3.2: Implement Neo4j Skill Gap Service
**Owner:** Agent  
**Effort:** 1.5-2 hours  
**Depends On:** Task 3.1, Task 1.1

**Description:**
Create a service module `core/services/interview_service.py` (or add method to existing service) that wraps Neo4j skill gap queries:

1. **Module Location:** `core/services/interview_neo4j_service.py` (following naming patterns)

2. **Class: `InterviewNeo4jService`**
   ```python
   class InterviewNeo4jService:
       """Service for Neo4j queries related to interview generation."""
       
       def get_candidate_skill_gaps(self, candidate_id: str, vaga_id: str) -> dict:
           """
           Get skill gaps for a candidate relative to a job position.
           
           Args:
               candidate_id (str): UUID of candidate
               vaga_id (str): UUID of job position
           
           Returns:
               dict with structure:
               {
                   'gaps': [
                       {'nome': 'Python', 'nivel_minimo': 3, 'nivel_candidato': 1},
                       ...
                   ],
                   'has_gaps': bool (True if gaps exist, False if 100% match),
                   'total_required': int (total skills for job),
                   'total_matched': int (skills candidate has),
               }
           """
   ```

3. **Implementation Details:**
   - Use get_neo4j_driver() from core/neo4j_connection.py (existing singleton)
   - Run Cypher query from Task 3.1
   - Serialize Neo4j response to Python dict
   - Handle Neo4j connection errors gracefully (log, raise with context)
   - Add logging for debugging (log query params, not results, for LGPD)

4. **Error Handling:**
   - Catch Neo4jConnectionError → log with context, re-raise
   - Catch ServiceUnavailable → log with context, raise custom InterviewNeo4jError
   - Return empty gaps list on timeout (fail-safe for Phase 2 service layer)

5. **Code Style:**
   - Follow CONVENTIONS.md import organization
   - Use type hints (from typing import List, Dict, Optional)
   - Add module docstring explaining Neo4j integration pattern

**Acceptance Criteria:**
- Service class exists in core/services/interview_neo4j_service.py
- Method get_candidate_skill_gaps() returns correct data structure
- Connection errors logged and re-raised with context
- Type hints present for all parameters and returns
- Module follows import organization (stdlib → django → local)

---

### Task Group 4: Permissions (Security)

#### Task 4.1: Create Permission Decorators & Checks
**Owner:** Agent  
**Effort:** 45 minutes  
**Depends On:** Task 1.1

**Description:**
Create or extend permission checks in `core/decorators.py` for interview question access:

1. **Decorator: `@staff_required`** (if not exists, create)
   ```python
   def staff_required(view_func):
       """
       Decorator that requires user to be staff (is_staff=True).
       
       Returns 403 Forbidden for non-staff users.
       Must be used AFTER @login_required:
           @login_required
           @staff_required
           def interview_generate_view(request):
               ...
       """
       @wraps(view_func)
       def wrapper(request, *args, **kwargs):
           if not request.user.is_staff:
               logger.warning(f"Unauthorized interview access from {get_client_ip(request)}")
               return HttpResponseForbidden("You do not have permission to access this feature.")
           return view_func(request, *args, **kwargs)
       return wrapper
   ```

2. **Helper Function: `can_access_interview_questions(user)`**
   ```python
   def can_access_interview_questions(user) -> bool:
       """
       Check if user can access interview question generation.
       
       Args:
           user (User): Django user object
       
       Returns:
           bool: True if user.is_staff, False otherwise
       """
       return user.is_staff
   ```

3. **Logging:**
   - Log all permission denials: IP, timestamp, attempted action
   - Never log user credentials or sensitive data
   - Include request_id for tracing (use existing get_request_id() pattern)

**Key Details:**
- Review existing decorators in core/decorators.py (rh_required, etc.)
- Use same pattern and style as existing decorators
- Add type hints where applicable
- Ensure decorator is importable from core.decorators module

**Acceptance Criteria:**
- Decorator @staff_required exists and is importable
- Helper function can_access_interview_questions() exists
- Both are documented with docstrings
- Logging is present (no PII)
- Code follows existing decorator patterns in project

---

### Task Group 5: Unit Tests (80% Coverage Goal)

#### Task 5.1: Create Test File for Interview Module
**Owner:** Agent  
**Effort:** 3-4 hours  
**Depends On:** Task 1.1, 3.2, 4.1

**Description:**
Create comprehensive unit tests in `core/tests/test_interview_questions.py`:

**Test Suite Organization:**

```
class InterviewQuestionModelTests(TestCase):
    """Unit tests for InterviewQuestion model."""
    
    def setUp(self):
        # Create test data
    
    def test_model_creation_with_all_fields(self):
        # Test valid model instantiation
    
    def test_question_text_required(self):
        # Test model validation
    
    def test_difficulty_level_choices(self):
        # Test enum choices
    
    def test_is_active_default_true(self):
        # Test default value
    
    def test_unique_together_constraint(self):
        # Test (candidate, is_active) uniqueness
    
    def test_string_representation(self):
        # Test __str__() method


class InterviewNeo4jServiceTests(TestCase):
    """Unit tests for Neo4j skill gap service."""
    
    @patch('core.services.interview_neo4j_service.get_neo4j_driver')
    def test_get_candidate_skill_gaps_with_gaps(self, mock_driver):
        # Test Neo4j query with mocked driver
    
    @patch('core.services.interview_neo4j_service.get_neo4j_driver')
    def test_get_candidate_skill_gaps_no_gaps_100_match(self, mock_driver):
        # Test advanced validation scenario
    
    @patch('core.services.interview_neo4j_service.get_neo4j_driver')
    def test_get_candidate_skill_gaps_connection_error(self, mock_driver):
        # Test error handling
    
    def test_service_returns_correct_data_structure(self):
        # Test response format


class InterviewPermissionTests(TestCase):
    """Unit tests for interview permission checks."""
    
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@example.com',
            password='pass1234',
            is_staff=True
        )
        self.non_staff_user = User.objects.create_user(
            username='regular_user',
            email='user@example.com',
            password='pass1234',
            is_staff=False
        )
    
    def test_can_access_interview_questions_staff_user(self):
        # Test staff user can access
    
    def test_can_access_interview_questions_non_staff_user(self):
        # Test non-staff user cannot access
    
    def test_staff_required_decorator_allows_staff(self):
        # Test @staff_required allows staff user
    
    def test_staff_required_decorator_forbids_non_staff(self):
        # Test @staff_required returns 403 for non-staff
```

**Coverage Targets (80%+):**
- `core/models.py` InterviewQuestion: **100%** (model validation, choices, defaults)
- `core/services/interview_neo4j_service.py`: **85%+** (queries, error handling, edge cases)
- `core/decorators.py` (staff_required, can_access): **100%** (both branches tested)
- Overall module coverage: **80%+**

**Mocking Strategy:**
- Mock `get_neo4j_driver()` to avoid real Neo4j connections
- Mock Neo4j response with realistic data structures
- Use Django TestCase for database transactions (auto-rollback)
- Use @patch decorator for service-level mocking

**Key Details:**
- Follow existing test patterns from test_matching_engine.py, test_backend_validations.py
- Use setUp() for fixture creation
- Use inline fixtures (dictionaries) for mock Neo4j responses
- Test both happy path and error scenarios
- Test edge cases (empty gaps, 100% match, null values)

**Acceptance Criteria:**
- Test file exists: core/tests/test_interview_questions.py
- All tests pass: `python manage.py test core.tests.test_interview_questions`
- Coverage ≥ 80%: `coverage run --source='core' manage.py test core.tests.test_interview_questions && coverage report`
- Tests cover model validation, Neo4j integration, permissions
- Mocked dependencies (no real Neo4j calls)

---

#### Task 5.2: Measure & Report Coverage
**Owner:** Agent  
**Effort:** 30 minutes  
**Depends On:** Task 5.1

**Description:**
Measure test coverage and generate report:

1. **Install coverage tool:**
   ```bash
   pip install coverage
   ```

2. **Run tests with coverage:**
   ```bash
   coverage run --source='core.models,core.services,core.decorators' manage.py test core.tests.test_interview_questions
   ```

3. **Generate report:**
   ```bash
   coverage report
   coverage html  # Generates htmlcov/index.html
   ```

4. **Verify coverage ≥ 80%:**
   - Interview module target: 80%+
   - If below 80%, add more tests for missing branches

5. **Document results:**
   - Include coverage report in git commit message or PR description
   - Note: "Core interview module coverage: 82% (42/51 lines)"

**Key Details:**
- Coverage ≥ 80% is acceptance criteria
- Report should show line-by-line coverage in HTML report
- Identify any untested branches and plan follow-up tests if needed
- Store report output for PR documentation

**Acceptance Criteria:**
- coverage ≥ 80% for interview module
- coverage report generated (text and HTML)
- Coverage results documented for PR

---

## 📊 Dependency Graph

```
Task 1.1 (Model) ─┬─→ Task 1.2 (Migration)
                  ├─→ Task 2.1 (Admin)
                  ├─→ Task 3.2 (Neo4j Service)
                  └─→ Task 4.1 (Permissions)
                  
Task 3.1 (Neo4j Design) ─→ Task 3.2 (Neo4j Service)

Task 3.2 (Neo4j Service) ┐
Task 4.1 (Permissions) ──┼─→ Task 5.1 (Tests) ─→ Task 5.2 (Coverage)
Task 1.2 (Migration) ────┘

Task 2.1 (Admin) ─→ (optional test, can skip if admin works)
```

**Wave 1 (Parallel):**
- Task 1.1 (Model)
- Task 3.1 (Neo4j Design)

**Wave 2 (Parallel):**
- Task 1.2 (Migration) — depends on 1.1
- Task 2.1 (Admin) — depends on 1.1
- Task 3.2 (Neo4j Service) — depends on 3.1, 1.1
- Task 4.1 (Permissions) — depends on 1.1

**Wave 3 (Sequential):**
- Task 5.1 (Tests) — depends on 1.2, 3.2, 4.1
- Task 5.2 (Coverage Report) — depends on 5.1

---

## ✅ Verification Steps

### Build Verification
Run after each major task:
```bash
# Check syntax
python -m py_compile core/models.py core/services/interview_neo4j_service.py

# Run migrations
python manage.py migrate core

# Run tests
python manage.py test core.tests.test_interview_questions -v 2
```

### Model Verification (Task 1.1)
- [ ] Model imports without errors: `python manage.py shell -c "from core.models import InterviewQuestion; print(InterviewQuestion._meta.fields)"`
- [ ] All 8 fields present
- [ ] ForeignKey relationships set correctly
- [ ] Meta options (ordering, unique_together) applied

### Migration Verification (Task 1.2)
- [ ] Migration file created and reviewed
- [ ] Migration applies cleanly: `python manage.py migrate core --plan` shows SQL
- [ ] `python manage.py migrate core` completes
- [ ] Table exists in database: `python manage.py dbshell` → `\dt core_interviewquestion` (PostgreSQL) or `SELECT * FROM core_interviewquestion LIMIT 0;`
- [ ] Indexes created for performance
- [ ] Migration is reversible

### Admin Verification (Task 2.1)
- [ ] ModelAdmin class registered
- [ ] Django admin loads: `python manage.py runserver` → http://localhost:8000/admin/
- [ ] InterviewQuestion appears in core app list
- [ ] Admin list_display shows all columns
- [ ] Filters (difficulty, is_active, created_at) work
- [ ] Search (question_text, candidate name) works

### Neo4j Service Verification (Task 3.2)
- [ ] Service imports without errors
- [ ] get_candidate_skill_gaps() method exists
- [ ] Returns correct data structure (dict with 'gaps', 'has_gaps', 'total_required', 'total_matched')
- [ ] Handles mocked Neo4j responses correctly
- [ ] Error handling works (catches and re-raises with context)
- [ ] Logging present (no PII)

### Permission Verification (Task 4.1)
- [ ] @staff_required decorator exists and is importable
- [ ] can_access_interview_questions() function exists
- [ ] Staff user passes permission check: `can_access_interview_questions(staff_user) == True`
- [ ] Non-staff user fails: `can_access_interview_questions(non_staff_user) == False`
- [ ] Logging occurs on permission denial

### Test Verification (Task 5.1)
- [ ] Test file exists: `ls core/tests/test_interview_questions.py`
- [ ] All tests pass: `python manage.py test core.tests.test_interview_questions -v 2`
- [ ] Tests are isolated (setUp clears state, tearDown cleanup if needed)
- [ ] Neo4j mocked (no real connections): `grep -n "patch.*neo4j" core/tests/test_interview_questions.py` shows @patch decorators
- [ ] Models tested (create, validate, choices)
- [ ] Service tested (gaps, no-gaps, errors)
- [ ] Permissions tested (allow, deny, logging)

### Coverage Verification (Task 5.2)
- [ ] coverage ≥ 80%: `coverage report | grep "TOTAL"`
- [ ] Coverage breakdown documented
- [ ] Untested lines identified and justified
- [ ] Coverage report stored for PR

---

## 🚨 Risk Mitigation

| Risk | Probability | Impact | Mitigation | Contingency |
|------|-------------|--------|-----------|-------------|
| Neo4j query syntax errors | Medium | High | Review ARCHITECTURE.md, test with mocked data first | Use simpler query, add debug logging |
| Permission checks bypassed | Low | Critical | Unit tests verify 403 response, code review before merge | Add view-level integration test |
| Migration conflicts with existing tables | Low | Medium | Use Django migration system, no manual SQL, test in isolation | Rename table, adjust migration order |
| Model ForeignKey relationship issues | Low | Medium | Test in unit tests (create with valid FK), review model constraints | Adjust on_delete behavior, test cascade |
| Test coverage < 80% | Medium | Medium | Write comprehensive tests, measure coverage early | Prioritize critical paths first, add tests iteratively |
| Neo4j connection unavailable during dev | Low | Low | Mock Neo4j in tests, connection not required for Phase 1 | Skip Neo4j testing, focus on model/permissions |
| Database migration fails in production | Low | Critical | Test migration locally first, reversible migrations only | Rollback migration, adjust schema |

**Mitigation Actions:**
1. **Neo4j Query Development:**
   - Start with existing query patterns from core/matching.py
   - Test queries against mocked Neo4j responses
   - Use ARCHITECTURE.md as reference

2. **Test Coverage:**
   - Measure coverage after each test task (Task 5.1)
   - If < 80%, identify untested branches and add tests immediately
   - Prioritize critical code paths (permissions, model constraints)

3. **Migration Safety:**
   - Test migrations on local development database first
   - Run `python manage.py migrate core --plan` to review SQL before applying
   - Keep migrations reversible (never use data deletion in migration)

4. **Permission Testing:**
   - Test both allowed and denied scenarios
   - Verify 403 response (not 500 or redirect)
   - Log all denials for security audit

---

## 📅 Timeline & Sequencing

### Critical Path Analysis

**Parallel Opportunities:**
- Task 1.1 (Model) and Task 3.1 (Neo4j Design) can run in parallel
- Task 1.2 (Migration), 2.1 (Admin), 3.2 (Service), 4.1 (Permissions) can run in parallel after Task 1.1
- Task 5.1 (Tests) requires all above to complete

**Recommended Sequence:**
1. **Hour 0-1:** Task 1.1 (Model) + Task 3.1 (Neo4j Design) — parallel
2. **Hour 1-3:** Task 1.2 (Migration) + Task 2.1 (Admin) + Task 3.2 (Service) + Task 4.1 (Permissions) — parallel
3. **Hour 3-7:** Task 5.1 (Tests) — sequential (requires all above)
4. **Hour 7-8:** Task 5.2 (Coverage) — sequential (requires tests)

**Daily Breakdown (for 1-2 person-days):**

**Day 1 (4-5 hours):**
- 09:00-10:00: Task 1.1 (Model) — Create InterviewQuestion model
- 10:00-10:30: Task 1.2 (Migration) — Create & test migration
- 10:30-11:00: Task 2.1 (Admin) — Register in admin
- 11:00-12:00: Task 3.1 (Neo4j Design) — Design skill gap query
- 13:00-14:30: Task 3.2 (Service) — Implement Neo4j service
- 14:30-15:30: Task 4.1 (Permissions) — Create decorators

**Day 2 (3-5 hours):**
- 09:00-12:30: Task 5.1 (Tests) — Write comprehensive tests
- 12:30-13:00: Task 5.2 (Coverage) — Measure & report
- 13:00+: Buffer & cleanup, prepare for commit

**Milestones & Gates:**
- ✅ **Milestone 1 (Hour 1):** Model created, no syntax errors
- ✅ **Milestone 2 (Hour 3):** Migration applied, admin works
- ✅ **Milestone 3 (Hour 5):** Neo4j & Permissions working
- ✅ **Milestone 4 (Hour 8):** All tests pass, coverage ≥ 80%
- ✅ **Go/No-Go Gate (Hour 8):** Coverage check — if < 80%, add tests before next phase

---

## 📝 Code Review Checklist

Before committing Phase 1, verify:

### Model & Database
- [ ] InterviewQuestion model follows existing model patterns (Candidato, Vaga)
- [ ] All 8 fields present with correct types
- [ ] ForeignKey relationships use correct models (Candidate, User)
- [ ] Meta options (ordering, unique_together) applied
- [ ] Migration is reversible and applies without errors
- [ ] Database schema matches model definition
- [ ] Indexes created for performance (candidate_id, created_by_id, is_active)

### Admin Interface
- [ ] ModelAdmin registered with admin.site.register()
- [ ] list_display shows key fields
- [ ] list_filter works for difficulty, is_active, created_at
- [ ] search_fields allow searching by question text and candidate name
- [ ] Read-only fields prevent manual editing (created_at, updated_at)
- [ ] Admin looks consistent with existing admin classes

### Neo4j Integration
- [ ] Service file follows naming convention (interview_neo4j_service.py)
- [ ] Neo4j query documented with parameter/return format
- [ ] Uses get_neo4j_driver() singleton (existing pattern)
- [ ] Error handling with logging (no PII)
- [ ] Service tested with mocks (no real Neo4j calls)
- [ ] Query performance documented (target: < 100ms)

### Permissions
- [ ] @staff_required decorator exists and is importable
- [ ] can_access_interview_questions() function exists
- [ ] Both documented with docstrings
- [ ] Logging on permission denial (IP, timestamp, no credentials)
- [ ] Follows existing decorator patterns (rh_required, etc.)

### Tests & Coverage
- [ ] Test file: core/tests/test_interview_questions.py
- [ ] Tests cover model validation, Neo4j service, permissions
- [ ] All tests pass locally: `python manage.py test core.tests.test_interview_questions`
- [ ] Coverage ≥ 80% for interview module
- [ ] Neo4j mocked (@patch decorators present)
- [ ] No real external API calls in tests
- [ ] Edge cases tested (empty gaps, 100% match, errors)

### Code Quality
- [ ] Code follows CONVENTIONS.md (naming, imports, logging, error handling)
- [ ] No syntax errors: `python -m py_compile core/models.py core/services/interview_neo4j_service.py core/decorators.py`
- [ ] Type hints present where applicable
- [ ] Docstrings present (module, class, method level)
- [ ] Comments for non-obvious logic
- [ ] No hardcoded values (use settings if needed)
- [ ] LGPD compliance: no PII logging, audit trail fields present

### Git & Documentation
- [ ] Commit message clear and descriptive
- [ ] PR description includes test results and coverage report
- [ ] Links to CONTEXT.md and REQUIREMENTS.md
- [ ] No unrelated changes in commit

---

## 🎯 Success Criteria (Go/No-Go for Phase 2)

Phase 1 is **COMPLETE** when ALL of the following are true:

1. ✅ **Model Exists**
   - InterviewQuestion model in core/models.py
   - All 8 fields with correct types and constraints
   - Relationships defined (FK to Candidate, FK to User)

2. ✅ **Migration Applied**
   - Migration file created and applied
   - Database schema matches model
   - Indexes created for performance
   - Migration reversible

3. ✅ **Admin Interface Working**
   - Model registered in Django admin
   - List view displays key fields
   - Filters and search functional

4. ✅ **Neo4j Integration Implemented**
   - Service module created with skill gap queries
   - Service tested with mocked Neo4j
   - Returns correct data structure
   - Handles errors gracefully

5. ✅ **Permissions Enforced**
   - @staff_required decorator implemented
   - can_access_interview_questions() function works
   - Permission checks return 403 for unauthorized users
   - Logging on denial (audit trail)

6. ✅ **Tests Written & Passing**
   - Test file exists: core/tests/test_interview_questions.py
   - All tests pass: `python manage.py test core.tests.test_interview_questions`
   - Coverage ≥ 80% for interview module
   - Tests cover model, Neo4j service, permissions
   - Neo4j mocked (no real API calls)

7. ✅ **Code Quality**
   - Follows CONVENTIONS.md
   - No syntax errors
   - Type hints present
   - Docstrings present
   - LGPD compliant (no PII logging)

8. ✅ **Git & Documentation**
   - Committed with clear message
   - PR ready with test results and coverage report
   - No merge conflicts

**Phase 1 Go Criteria:**
- All 8 items above are ✅ complete
- Coverage report shows ≥ 80% for interview module
- Code review checklist all checked
- Ready to merge and move to Phase 2

**Phase 1 No-Go Criteria:**
- Any of the 8 items above is incomplete
- Coverage < 80% (failing acceptance criteria)
- Code review issues not resolved
- Failing tests or merge conflicts

---

## 📚 References & Resources

### Phase 1 Context
- `.planning/phases/01-foundation-permissions/CONTEXT.md` — User decisions, locked constraints, phase boundary

### Codebase Documentation
- `.planning/codebase/ARCHITECTURE.md` — Service layer, Neo4j patterns, matching engine example
- `.planning/codebase/CONVENTIONS.md` — Code style, naming, imports, logging, comments
- `.planning/codebase/TESTING.md` — Test framework, mocking patterns, test organization

### Project Documentation
- `.planning/REQUIREMENTS.md` — Full requirements (FR1-FR5, NFR1-NFR6)
- `.planning/ROADMAP.md` — 4-phase roadmap

### Code References
- `core/models.py` — Existing model patterns (Candidato, Vaga, User)
- `core/decorators.py` — Existing decorator patterns (@rh_required, @ajax_login_required)
- `core/tests/test_matching_engine.py` — Test patterns, mocking examples
- `core/neo4j_connection.py` — Neo4j singleton pattern, session management
- `core/matching.py` — Neo4j query examples, skill matching logic

---

## 🔄 Phase 1 Handoff to Phase 2

**What Phase 2 (Core Service Layer) will consume from Phase 1:**
1. **InterviewQuestion model** — persist generated questions
2. **Neo4j skill gap queries** — input to OpenAI prompt construction
3. **Permission checks** — ensure only recruiters can generate
4. **Test patterns** — extend with OpenAI mocking, integration tests

**What Phase 2 will NOT depend on:**
- Frontend/HTMX views (Phase 3)
- OpenAI API integration (Phase 2 will build this)
- Caching logic (Phase 2 will add this)

**Parallel Work Opportunity:**
- Phase 2 (Core Service) and Phase 3 (Frontend) can start in parallel after Phase 1 model + migrations are committed
- Phase 2 depends on model schema (✓ available from Phase 1)
- Phase 3 depends on service interface (will be available mid-Phase 2)

---

**Plan Created:** 2025-03-29  
**Status:** Ready for execution  
**Target Duration:** 1-2 weeks (1-2 person-days)  
**Next Step:** Begin execution with Task 1.1 (Model Creation)
