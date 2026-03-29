# Phase 2: Core Service Layer - Execution Plan

**OpenAI Integration, Question Caching, Error Handling, Edge Cases & Testing**

---

## 📋 Plan Overview

### Goal

Build the **InterviewOpenAIService** with robust question generation, intelligent caching, comprehensive error handling, and cost monitoring. Phase 2 establishes the core business logic layer that will be consumed by Phase 3 (Frontend Views) and beyond.

### Why This Matters

- **Cost Control:** Caching prevents duplicate API calls, reducing OpenAI spend
- **User Experience:** Cached questions load instantly; API timeouts fail gracefully
- **Quality Assurance:** Mocked tests ensure reliability without real API usage
- **Compliance:** Token counting and audit trails meet LGPD requirements
- **Maintainability:** Service layer abstraction separates business logic from views

### Success Criteria

✅ **Service Implementation:**
- InterviewOpenAIService class with 6 core methods
- GPT-4o-mini model integration with 15-second timeout
- Generate exactly 3 questions per candidate
- Atomic save (all-or-nothing)

✅ **Caching & Persistence:**
- Check DB before API call (avoid duplicate generation)
- Regeneration soft-deletes old questions, creates new ones
- No orphaned records on failure (transaction rollback)

✅ **Error Handling:**
- Timeout errors (15s limit)
- RateLimitError with exponential backoff
- Generic APIException with user-friendly messaging
- Database errors with atomic rollback

✅ **Edge Cases:**
- "No skill gaps" (100% match) → Switch to "Advanced Validation Questions"
- Invalid Neo4j response → Graceful fallback
- Malformed JSON from OpenAI → Retry with simpler prompt

✅ **Testing & Coverage:**
- 80%+ test coverage on interview module
- All 10 service methods tested
- Zero real OpenAI API calls in tests
- Mocked Neo4j service, mocked OpenAI client

✅ **Cost Monitoring:**
- Token counting via tiktoken library
- Cost logging (3 questions ≈ $0.04)
- Per-request cost tracking

### Estimated Duration & Effort

| Metric | Value |
|--------|-------|
| **Total Duration** | 15-20 hours |
| **Implementation Tasks** | 3 tasks × 2-3 hours |
| **Testing Tasks** | 2 tasks × 3-4 hours |
| **Code Review & Fixes** | 2-3 hours |
| **Parallel Waves** | 2 waves |
| **Critical Path** | Wave 1 (Service) → Wave 2 (Tests) |

---

## 🎯 Work Breakdown

### Phase 2 Deliverables

| Component | Task | Effort | Depends On |
|-----------|------|--------|-----------|
| **Service Layer** | Task 1: InterviewOpenAIService | 4-5h | Phase 1 complete |
| **Caching Logic** | Task 1 (embedded) | 1-2h | InterviewQuestion model |
| **Error Handling** | Task 1 (embedded) + Task 2 | 2-3h | Phase 1 patterns |
| **Edge Cases** | Task 2: Edge Case Handler | 2h | Task 1 service |
| **Testing** | Task 3: Unit Tests | 3-4h | Task 1 + 2 |
| **Integration Tests** | Task 4: Integration Tests | 2-3h | Task 3 complete |
| **Code Review** | Task 5: Review & Fixes | 1-2h | Task 3 + 4 |

---

## 🏗️ Detailed Task Breakdown

### Task 1: Build InterviewOpenAIService (4-5 hours)

**Purpose:** Core service class implementing OpenAI integration, caching, and error handling

**Files to Create/Modify:**
- `core/services/interview_openai_service.py` (NEW - ~300-400 lines)
- `core/services/__init__.py` (MODIFY - add export)

**Implementation Scope:**

This task creates the main service class with the following methods:

#### Method 1: `get_candidate_questions(candidate_id, vaga_id, force_regenerate=False)`
- **Purpose:** Main entry point, implements caching logic
- **Logic:**
  1. If `force_regenerate=False`, query DB for active questions
  2. If found, return cached questions immediately
  3. If not found or `force_regenerate=True`:
     - Call Neo4j service to fetch skill gaps
     - Call OpenAI API with gap-based prompt
     - Save all 3 questions atomically
     - Return questions
- **Returns:** `List[Dict]` with fields: `[{question_text, difficulty_level}, ...]`
- **Errors Handled:**
  - `TimeoutError` → Log, return user-friendly error message
  - `RateLimitError` → Log, retry logic delegated to caller
  - Database errors → Rollback transaction

#### Method 2: `_get_cached_questions(candidate_id)`
- **Purpose:** Query DB for active questions
- **Logic:**
  - `InterviewQuestion.objects.filter(candidato_id=candidate_id, is_active=True)`
  - If found, return as list of dicts
  - If not found, return `None`
- **Performance:** < 100ms (indexed query)

#### Method 3: `_generate_questions_openai(candidate_id, skill_gaps, vaga_context)`
- **Purpose:** Call OpenAI API with smart prompt
- **Logic:**
  1. Detect if `skill_gaps` is empty (100% match scenario)
  2. If no gaps: Use "Advanced Validation Questions" prompt
  3. If gaps exist: Use "Skill Gap Focused Questions" prompt
  4. Construct JSON-forced prompt with few-shot examples
  5. Call OpenAI GPT-4o-mini with `timeout=15s`
  6. Parse JSON response
  7. Count tokens for cost tracking
  8. Validate response (3 questions, valid difficulty levels)
- **Returns:** `List[Dict]` with fields: `[{question_text, difficulty_level}, ...]`
- **Errors Handled:**
  - `openai.error.Timeout` → Re-raise as `TimeoutError`
  - `openai.error.RateLimitError` → Re-raise for caller's retry logic
  - `json.JSONDecodeError` → Log, retry with simpler prompt
  - `openai.error.APIError` → Log, raise custom exception

#### Method 4: `_save_questions_atomic(candidate_id, created_by_user, questions, vaga_id)`
- **Purpose:** Save questions to DB atomically
- **Logic:**
  1. Start transaction
  2. Soft-delete old active questions: `InterviewQuestion.objects.filter(...).update(is_active=False)`
  3. Create new questions: `InterviewQuestion.objects.bulk_create([...])`
  4. Commit transaction
  5. On error: Rollback (no orphaned records)
- **Returns:** `List[InterviewQuestion]` (created objects)
- **Constraint:** All 3 questions saved or none

#### Method 5: `_construct_openai_prompt(skill_gaps, vaga_context, has_gaps)`
- **Purpose:** Build the LLM prompt
- **Logic:**
  1. If `has_gaps=True`:
     - Prompt: "Generate 3 technical interview questions for skill gaps:"
     - Include gap names, levels, criticality
  2. If `has_gaps=False`:
     - Prompt: "Generate 3 advanced validation questions to probe depth:"
     - Focus on deep knowledge, not gaps
  3. Add few-shot examples (2-3 good questions)
  4. Force JSON output format with schema
  5. Specify exactly 3 questions
- **Returns:** `str` (prompt text)

#### Method 6: `_validate_openai_response(response_text)`
- **Purpose:** Parse and validate JSON response
- **Logic:**
  1. Parse JSON from response
  2. Validate structure: `{"questions": [{question_text, difficulty_level}, ...]}`
  3. Validate: exactly 3 questions
  4. Validate: difficulty_level in ['easy', 'medium', 'hard']
  5. Validate: question_text not empty, reasonable length (20-500 chars)
  6. Return parsed questions or raise `ValueError`
- **Returns:** `List[Dict]` (validated questions)

#### Helper: `_count_tokens(text)`
- **Purpose:** Track token usage for cost monitoring
- **Logic:**
  - Use `tiktoken` library to count tokens
  - Estimate cost: `tokens * $0.15 / 1M`
  - Log: `f"[Cost Tracking] tokens={N}, estimated_cost=${X}"`
- **Returns:** `int` (token count)

**Error Handling Strategy:**

| Error Type | Handling |
|-----------|----------|
| `openai.error.Timeout` | Catch, log with request_id, raise `TimeoutError` |
| `openai.error.RateLimitError` | Catch, log, raise for caller's retry logic |
| `openai.error.APIError` | Catch, log without PII, raise `APIException` |
| `json.JSONDecodeError` | Catch, retry prompt once with simpler format |
| Database errors (Integrity, Operational) | Catch, rollback transaction, log with request_id |

**Logging Pattern:**

```python
logger.info(f"[{candidate_id[:8]}] Fetching cached questions")
logger.info(f"[{candidate_id[:8]}] Cache miss, calling OpenAI")
logger.info(f"[Cost] tokens={N}, cost_estimate=${X}")
logger.warning(f"[{candidate_id[:8]}] OpenAI timeout, retrying")
logger.error(f"[{candidate_id[:8]}] Database error on save: {error_type}")
```

**Testing Hooks:**

- Service accepts optional `openai_client` and `neo4j_service` in `__init__` for injection
- Mock both in tests
- All real OpenAI calls must be mocked

---

### Task 2: Edge Case Handler & Prompt Engineering (2-3 hours)

**Purpose:** Implement smart prompt switching for "no skill gaps" scenario

**Files to Modify:**
- `core/services/interview_openai_service.py` (METHOD: `_construct_openai_prompt`)

**Implementation Scope:**

#### Scenario 1: Skill Gaps Exist (Normal Case)

**Prompt Structure:**
```
You are an expert technical interviewer.

CONTEXT:
- Position: {job_title}
- Candidate Level: {seniority}
- Required Skills: {required_skills}
- Candidate Skills: {candidate_skills}

SKILL GAPS TO EXPLORE (what candidate lacks):
{gap_list}

TASK: Generate exactly 3 technical interview questions that explore these gaps.

CONSTRAINTS:
- Questions must be answerable in 5-10 minutes
- Assess both theoretical knowledge AND practical ability
- Follow-up probes acceptable within question
- Avoid yes/no questions

EXAMPLES OF GOOD QUESTIONS:
1. "How would you optimize a slow database query? Walk me through your debugging process."
2. "What's the difference between a HashMap and a TreeMap? When would you use each?"
3. "Design a rate limiter for an API. Explain trade-offs."

OUTPUT FORMAT (JSON):
{
  "questions": [
    {"question_text": "...", "difficulty_level": "easy|medium|hard"},
    {"question_text": "...", "difficulty_level": "easy|medium|hard"},
    {"question_text": "...", "difficulty_level": "easy|medium|hard"}
  ]
}
```

#### Scenario 2: No Skill Gaps (100% Match)

**Detection Logic:**
```python
if not skill_gaps or len(skill_gaps) == 0:
    has_gaps = False
else:
    has_gaps = True
```

**Prompt Structure:**
```
You are an expert technical interviewer conducting ADVANCED VALIDATION questions.

CONTEXT:
- Position: {job_title}
- Candidate Level: {seniority}
- All Required Skills: {all_skills}
- Candidate Has All Skills At Required Level

TASK: Generate 3 ADVANCED VALIDATION questions to probe depth of knowledge.
These questions verify the candidate actually possesses claimed expertise at senior level.

CONSTRAINTS:
- Questions should be challenging (not trivial)
- Focus on real-world architectural decisions, not syntax
- Probe for nuanced understanding and trade-offs
- Avoid simple recall questions

EXAMPLES OF GOOD ADVANCED VALIDATION QUESTIONS:
1. "Design a microservices architecture for a 1M user SaaS platform. Explain scaling, monitoring, failure modes."
2. "You're deciding between PostgreSQL and MongoDB for a financial system. What criteria guide your decision?"
3. "Walk me through optimizing a 30-second batch job to 5 seconds. What strategies would you try?"

OUTPUT FORMAT (JSON):
{
  "questions": [
    {"question_text": "...", "difficulty_level": "hard"},
    {"question_text": "...", "difficulty_level": "hard"},
    {"question_text": "...", "difficulty_level": "hard"}
  ]
}
```

**Quality Assurance for Prompt:**

Test scenarios to validate prompt effectiveness:
1. **Skill Gap Case (Python 2 → 3 migration):** Questions focus on asyncio, type hints
2. **No Gap Case (Senior Python dev):** Questions probe async patterns, memory management, concurrency
3. **Empty Gaps Edge Case:** Gracefully use generic advanced questions

---

### Task 3: Comprehensive Unit Tests (3-4 hours)

**Purpose:** Test all service methods with 80%+ coverage, mocked OpenAI & Neo4j

**Files to Create:**
- `core/tests/test_interview_openai_service.py` (NEW - ~400-500 lines)

**Test Coverage:**

#### Test Class 1: `InterviewOpenAIServiceTests` (Main Service)

| Test Case | Scenario | Mocks | Assertions |
|-----------|----------|-------|-----------|
| `test_get_cached_questions_returns_existing` | Questions exist in DB | Neo4j, OpenAI | Returns cached questions, no API call |
| `test_get_cached_questions_generates_on_miss` | No questions in DB | Neo4j (gaps), OpenAI (API) | API called, questions saved, returned |
| `test_force_regenerate_overwrites_old` | Questions exist, force=True | Neo4j, OpenAI | Old marked inactive, new created |
| `test_timeout_raises_error` | OpenAI timeout (15s) | Neo4j, OpenAI (timeout) | TimeoutError raised, logged |
| `test_rate_limit_raises_error` | OpenAI rate limit | Neo4j, OpenAI (rate limit) | RateLimitError raised, logged |
| `test_api_error_raises_exception` | OpenAI API error (500) | Neo4j, OpenAI (error) | APIException raised, logged |
| `test_json_parse_error_retries` | Invalid JSON response | Neo4j, OpenAI (invalid JSON) | Retry once, handle gracefully |
| `test_database_error_rolls_back` | DB integrity error | Neo4j, OpenAI, DB (error) | Transaction rolled back, no orphaned records |
| `test_three_questions_exact` | Success case | Neo4j, OpenAI (3 questions) | Exactly 3 questions saved |

#### Test Class 2: `EdgeCaseHandlingTests`

| Test Case | Scenario | Mocks | Assertions |
|-----------|----------|-------|-----------|
| `test_no_skill_gaps_switches_prompt` | 0 gaps (100% match) | Neo4j (no gaps), OpenAI | Prompt contains "Advanced Validation", questions are hard |
| `test_empty_gaps_list_handled` | gaps=[] | Neo4j, OpenAI | Fallback to advanced prompt, no crash |
| `test_invalid_neo4j_response_uses_fallback` | Neo4j returns None | Neo4j (None), OpenAI | Uses empty gaps, advanced prompt, succeeds |

#### Test Class 3: `PromptEngineeringTests`

| Test Case | Scenario | Assertions |
|-----------|----------|-----------|
| `test_prompt_contains_skill_gaps` | Normal gaps case | Prompt includes gap names, levels |
| `test_prompt_contains_few_shot_examples` | Any case | Prompt includes 2+ example questions |
| `test_prompt_forces_json_output` | Any case | Prompt specifies JSON format, 3 questions |
| `test_advanced_validation_prompt_wording` | No gaps case | Prompt says "Advanced", "depth", "senior level" |

#### Test Class 4: `TokenCountingAndCostTests`

| Test Case | Scenario | Mocks | Assertions |
|-----------|----------|-------|-----------|
| `test_token_counting_executed` | Success case | Neo4j, OpenAI | Token count logged, cost calculated |
| `test_cost_estimate_logged` | Success case | Neo4j, OpenAI | Log contains "Cost Tracking", "$X" |
| `test_token_count_reasonable` | Success case | Neo4j, OpenAI | Tokens between 100-500 (rough estimate) |

#### Test Class 5: `AtomicSaveTests`

| Test Case | Scenario | Mocks | Assertions |
|-----------|----------|-------|-----------|
| `test_save_creates_three_questions` | Success case | Neo4j, OpenAI | 3 InterviewQuestion records in DB |
| `test_save_marks_old_inactive` | Regeneration | Neo4j, OpenAI | Old questions have is_active=False |
| `test_save_rollback_on_error` | DB error | Neo4j, OpenAI, DB error | 0 questions saved, no orphaned records |
| `test_save_uses_provided_user` | Success case | Neo4j, OpenAI | created_by = provided user |
| `test_save_sets_correct_candidate` | Success case | Neo4j, OpenAI | candidato_id matches input |

#### Test Class 6: `ValidationTests`

| Test Case | Scenario | Assertions |
|-----------|----------|-----------|
| `test_validate_correct_response` | Valid JSON | Parsed questions returned |
| `test_validate_rejects_wrong_count` | 2 questions instead of 3 | ValueError raised |
| `test_validate_rejects_invalid_difficulty` | difficulty="unknown" | ValueError raised |
| `test_validate_rejects_empty_question` | question_text="" | ValueError raised |

**Mock Setup Pattern:**

```python
@patch('core.services.interview_openai_service.get_neo4j_driver')
@patch('core.services.interview_openai_service.openai.ChatCompletion.create')
def test_example(self, mock_openai, mock_neo4j):
    # Setup mocks
    mock_neo4j_service = MagicMock()
    mock_neo4j_service.get_candidate_skill_gaps.return_value = {
        'gaps': [{'nome': 'Python', 'gap': 2}],
        'has_gaps': True,
        'total_required': 5,
        'total_matched': 3
    }
    
    mock_openai.return_value = {
        'choices': [{
            'message': {
                'content': '{"questions": [...]}'
            }
        }]
    }
    
    service = InterviewOpenAIService(
        openai_client=mock_openai,
        neo4j_service=mock_neo4j_service
    )
    
    # Test
    result = service.get_candidate_questions(candidate_id, vaga_id)
    
    # Assertions
    self.assertEqual(len(result), 3)
    mock_openai.assert_called_once()
```

**Coverage Target:**
- Line coverage: ≥ 80%
- Method coverage: 100% (all 6 service methods)
- Error path coverage: ≥ 80%

---

### Task 4: Integration Tests with Database (2-3 hours)

**Purpose:** Test service with real Django models, in-memory DB

**Files to Create:**
- `core/tests/test_interview_openai_integration.py` (NEW - ~250-350 lines)

**Test Scenarios:**

#### Test Class: `InterviewOpenAIIntegrationTests`

| Test Case | Scenario | Setup | Assertions |
|-----------|----------|-------|-----------|
| `test_full_workflow_generate_and_cache` | Generate → Save → Retrieve | Candidato, Vaga, User fixtures | Questions saved to DB, cache hit on second call |
| `test_generate_with_real_model_relationships` | Django ORM interactions | Candidato, Vaga, InterviewQuestion | Proper FK relationships, soft-delete behavior |
| `test_permission_check_integration` | Via decorator (Phase 3) | Staff user, non-staff user | (Placeholder for Phase 3 integration) |
| `test_concurrent_generation_safety` | Two simultaneous requests | Race condition test | First wins, second gets existing questions |
| `test_database_state_after_timeout` | API times out | Mock timeout | DB unchanged, no partial data |
| `test_audit_trail_created_by` | created_by field tracking | Recruiter user | created_by_id set correctly |

**Database Fixtures:**

```python
class InterviewOpenAIIntegrationTests(TransactionTestCase):
    """Integration tests with real Django ORM."""
    
    def setUp(self):
        # Create test user (recruiter)
        self.recruiter = User.objects.create_user(
            username='recruiter@test.com',
            email='recruiter@test.com',
            password='test123'
        )
        self.recruiter.is_staff = True
        self.recruiter.save()
        
        # Create test candidate
        self.candidato = Candidato.objects.create(
            id='550e8400-e29b-41d4-a716-446655440001',
            nome='João Silva',
            email='joao@test.com',
            # ... other fields
        )
        
        # Create test vaga (job posting)
        self.vaga = Vaga.objects.create(
            id='550e8400-e29b-41d4-a716-446655440002',
            titulo='Python Developer',
            # ... other fields
        )
```

---

### Task 5: Code Review & Iteration (1-2 hours)

**Purpose:** Review code, fix issues, verify coverage

**Checklist:**

- [ ] All 6 service methods implemented and tested
- [ ] Error handling covers all scenarios (timeout, rate limit, API error, DB error)
- [ ] Caching logic works (check → generate → save → return)
- [ ] Atomic save prevents orphaned records
- [ ] Edge case (no gaps) detected and handled
- [ ] Token counting implemented and logged
- [ ] All tests pass locally
- [ ] Test coverage ≥ 80%
- [ ] Logging is LGPD-safe (no PII, no CV content)
- [ ] Docstrings complete and clear
- [ ] Type hints on all methods
- [ ] Service is injectable (constructor params for mocks)

---

## 📊 Wave Structure & Parallelization

```
Wave 1 (Parallel - ~4-5 hours total)
├── Task 1: InterviewOpenAIService
│   ├── Method implementation (all 6 methods)
│   ├── Error handling
│   ├── Caching logic
│   └── Token counting
└── (Task 2 overlaps: Prompt engineering within Task 1)

Wave 2 (Sequential after Wave 1 - ~5-7 hours total)
├── Task 3: Unit Tests
│   ├── Service method tests
│   ├── Edge case tests
│   ├── Validation tests
│   └── Error path tests
├── Task 4: Integration Tests
│   ├── ORM integration
│   ├── Database state verification
│   └── Concurrent safety
└── Task 5: Code Review & Fixes
    ├── Coverage verification
    ├── Issue resolution
    └── Final validation
```

**Dependency Chain:**
- Task 1 → Task 3 & 4 (both test Task 1)
- Task 2 (prompt engineering) → embedded in Task 1
- Task 3 & 4 can run parallel
- Task 5 runs after Task 3 & 4 complete

---

## ✅ Verification Strategy

### Phase Completion Checklist

- [ ] **Service Implementation:**
  - [ ] `core/services/interview_openai_service.py` exists with 6 methods
  - [ ] Service imported in `core/services/__init__.py`
  - [ ] All methods have type hints and docstrings
  - [ ] Error handling for all 5 error types implemented

- [ ] **Caching Verified:**
  - [ ] `test_get_cached_questions_returns_existing` passes
  - [ ] `test_get_cached_questions_generates_on_miss` passes
  - [ ] `test_force_regenerate_overwrites_old` passes

- [ ] **Error Handling Verified:**
  - [ ] `test_timeout_raises_error` passes
  - [ ] `test_rate_limit_raises_error` passes
  - [ ] `test_api_error_raises_exception` passes
  - [ ] `test_database_error_rolls_back` passes

- [ ] **Edge Cases Verified:**
  - [ ] `test_no_skill_gaps_switches_prompt` passes
  - [ ] `test_invalid_neo4j_response_uses_fallback` passes

- [ ] **Testing Coverage:**
  - [ ] `pytest core/tests/test_interview_openai_service.py` → 100% pass
  - [ ] `pytest core/tests/test_interview_openai_integration.py` → 100% pass
  - [ ] Coverage report shows ≥ 80% overall
  - [ ] All openai API calls mocked (no real calls)

- [ ] **Code Quality:**
  - [ ] No PII in logs (candidate IDs truncated)
  - [ ] Transaction handling prevents orphaned records
  - [ ] Service is testable (injectable dependencies)

### Test Execution Commands

```bash
# Run all interview tests
python manage.py test core.tests.test_interview_openai_service
python manage.py test core.tests.test_interview_openai_integration

# Run with verbose output
python manage.py test core.tests.test_interview_openai_service -v 2

# Check coverage (requires coverage.py)
coverage run --source='core' manage.py test core.tests.test_interview_openai_service
coverage report --include=core/services/interview_openai_service.py
```

### Code Review Checklist

#### Architecture & Design
- [ ] Service uses dependency injection for OpenAI & Neo4j
- [ ] Methods are single-responsibility (one task per method)
- [ ] Error handling is specific (catch particular exceptions)
- [ ] Logging is contextual (includes request_id, truncated IDs)

#### Security & Compliance
- [ ] No PII logged (CV content, full IDs, email addresses)
- [ ] Transaction atomic (all-or-nothing saves)
- [ ] Rate limit respects OpenAI's limits
- [ ] LGPD audit trail (created_by, created_at tracked)

#### Code Quality
- [ ] Type hints on all parameters and returns
- [ ] Docstrings on all public methods
- [ ] No magic numbers (constants defined at module top)
- [ ] Error messages user-friendly (no stack traces to end users)

#### Testing
- [ ] All service methods covered by tests
- [ ] All error paths tested
- [ ] Edge cases covered (no gaps, empty response, timeout)
- [ ] Mocks prevent real API calls
- [ ] Integration tests use real Django ORM

---

## ⚠️ Risk Mitigation

### Phase 2 Specific Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| **OpenAI API costs spike** | Budget blow-up | Medium | Caching first, token counting, daily alert threshold |
| **Timeout too aggressive** | High failure rate | Low | Start 15s, increase to 20s if needed, monitor latency |
| **Prompt quality issues** | Poor questions | Medium | Few-shot examples, human review before launch, test cases |
| **Race condition on save** | Duplicate/orphaned records | Low | Atomic transaction, unique constraint on (candidato, is_active) |
| **Neo4j service unavailable** | No gap data | Low | Fallback to empty gaps, use advanced prompt, log and alert |
| **JSON parsing fails** | API response unusable | Low | Retry with simpler prompt, graceful error message |
| **Token counter inaccurate** | Cost estimates wrong | Low | Use tiktoken library (official), compare to OpenAI's logs |

### Contingency Plans

**If Timeout Too Aggressive:**
- Increase timeout to 20s (config constant at module top)
- Monitor percentage of timeouts in logs
- If >5% timeouts, extend further

**If Prompt Quality Poor:**
- Add human review step (Phase 3 feature: "Regenerate" button)
- Iterate few-shot examples based on real results
- Consider sampling approach: generate 5 questions, pick 3 best

**If OpenAI Costs Exceed Budget:**
- Enable caching (already designed in)
- Use GPT-3.5-turbo instead of GPT-4o-mini for 80% of cases
- Batch generation (generate for multiple candidates at once)

**If Neo4j Service Fails:**
- Catch exception in `get_candidate_questions()`
- Log error with context
- Return empty gaps `[]`
- Use "Advanced Validation Questions" prompt
- Alert operator

---

## 📚 Reference Documents

### Must-Read Before Starting

1. **`.planning/REQUIREMENTS.md`** — FR1-FR5, NFR1-NFR6
   - Focus on: FR1 (generation), FR2 (caching), NFR1 (error handling), NFR4 (cost)

2. **`.planning/codebase/ARCHITECTURE.md`** — Service layer patterns
   - Read: Service layer abstraction, exception handling patterns, Neo4j singleton pattern

3. **`.planning/codebase/CONVENTIONS.md`** — Code style
   - Read: Logging patterns (LGPD-safe), error handling, imports, docstrings

4. **`.planning/codebase/TESTING.md`** — Test patterns
   - Read: Mock patterns, test file organization, `unittest.mock` usage

5. **`.planning/research/AI_INTERVIEW_ASSISTANCE_RESEARCH.md`** — Best practices
   - Read: Prompt engineering patterns, error handling best practices, token counting

6. **`.planning/phases/01-foundation-permissions/01-foundation-permissions-SUMMARY.md`** — Phase 1 patterns
   - Read: Test structure, Neo4j service pattern, soft-delete approach

### Key Code Files to Understand

| File | Purpose | Read Sections |
|------|---------|--------------|
| `core/models.py` | InterviewQuestion model | InterviewQuestion class definition |
| `core/services/interview_neo4j_service.py` | Neo4j pattern | `get_candidate_skill_gaps()` method |
| `core/tests/test_interview_questions.py` | Test pattern from Phase 1 | Mock setup, test structure |
| `core/decorators.py` | Auth decorators | `staff_required`, `can_access_interview_questions` |
| `requirements.txt` | Dependencies | Check for openai, tiktoken |

---

## 📋 Task Checklist (Implementation Order)

### Before Starting
- [ ] Read all reference documents (REQUIREMENTS, ARCHITECTURE, CONVENTIONS)
- [ ] Review Phase 1 summary (test patterns, Neo4j service pattern)
- [ ] Ensure openai and tiktoken packages in requirements.txt
- [ ] Ensure OpenAI API key available as environment variable

### Task 1: InterviewOpenAIService
- [ ] Create `core/services/interview_openai_service.py`
- [ ] Implement `__init__` with dependency injection
- [ ] Implement `get_candidate_questions()` (main entry point)
- [ ] Implement `_get_cached_questions()`
- [ ] Implement `_generate_questions_openai()`
- [ ] Implement `_save_questions_atomic()`
- [ ] Implement `_construct_openai_prompt()`
- [ ] Implement `_validate_openai_response()`
- [ ] Implement `_count_tokens()`
- [ ] Add error handling for all 5 error types
- [ ] Add comprehensive docstrings
- [ ] Add type hints to all methods
- [ ] Update `core/services/__init__.py` to export service
- [ ] Verify no syntax errors: `python manage.py check`

### Task 2: Edge Case Handler (embedded in Task 1)
- [ ] Implement gap detection logic in `_generate_questions_openai()`
- [ ] Implement prompt switching in `_construct_openai_prompt()`
- [ ] Test: no gaps scenario uses "Advanced Validation" wording

### Task 3: Unit Tests
- [ ] Create `core/tests/test_interview_openai_service.py`
- [ ] Implement mock setup for OpenAI and Neo4j
- [ ] Write tests for main service method (6 test cases)
- [ ] Write tests for caching (3 test cases)
- [ ] Write tests for error handling (4 test cases)
- [ ] Write tests for edge cases (3 test cases)
- [ ] Write tests for prompt engineering (4 test cases)
- [ ] Write tests for token counting (3 test cases)
- [ ] Write tests for validation (4 test cases)
- [ ] Run tests: `python manage.py test core.tests.test_interview_openai_service -v 2`
- [ ] Verify all mocks prevent real API calls

### Task 4: Integration Tests
- [ ] Create `core/tests/test_interview_openai_integration.py`
- [ ] Implement database fixtures (Candidato, Vaga, User)
- [ ] Write integration tests for full workflow (6 test cases)
- [ ] Test real Django ORM interactions
- [ ] Test atomic transaction behavior
- [ ] Run tests: `python manage.py test core.tests.test_interview_openai_integration -v 2`

### Task 5: Code Review & Fixes
- [ ] Run all tests: both unit and integration
- [ ] Verify test coverage ≥ 80%
- [ ] Check code against checklist (architecture, security, quality, testing)
- [ ] Fix any issues found
- [ ] Final verification: all tests pass
- [ ] Commit with message: `feat(phase-2): implement InterviewOpenAIService with caching, error handling, and 80% test coverage`

---

## 🎯 Success Criteria (Phase 2 Complete)

Phase 2 is **COMPLETE** when:

1. ✅ **Service exists and is functional:**
   - File: `core/services/interview_openai_service.py`
   - All 6 methods implemented
   - Callable from views (ready for Phase 3)

2. ✅ **Caching works:**
   - Database queries return cached questions in < 100ms
   - API called only once per candidate (unless regenerated)

3. ✅ **Error handling robust:**
   - Timeout (15s) caught and handled
   - Rate limit errors caught
   - API errors caught and logged
   - Database errors rolled back
   - All errors logged without PII

4. ✅ **Edge cases handled:**
   - "No skill gaps" detected and switches to advanced prompt
   - Invalid Neo4j response uses fallback
   - Malformed JSON retried gracefully

5. ✅ **Testing comprehensive:**
   - 30+ test cases written and passing
   - 80%+ code coverage achieved
   - All OpenAI API calls mocked (zero real calls)
   - Integration tests use real Django ORM

6. ✅ **Cost tracking implemented:**
   - Token counting via tiktoken
   - Cost estimates logged per request
   - Monthly budget tracking capability

7. ✅ **Code quality high:**
   - Type hints on all methods
   - Docstrings on all public methods
   - Logging is LGPD-safe
   - Service is testable (injectable)

8. ✅ **Documentation complete:**
   - README updated with service usage
   - Docstrings explain all methods
   - Error codes documented

---

## 📞 Ownership & Handoff

### This Phase Builds:
- **InterviewOpenAIService** → Available for Phase 3 (Frontend Views)
- **Error handling patterns** → Reusable in future services
- **Test mocking patterns** → Reference for testing external APIs

### Phase 3 Consumes:
- `InterviewOpenAIService.get_candidate_questions()` method
- Error handling (catches TimeoutError, APIException)
- Caching behavior (forces regeneration when needed)

### Future Dependencies:
- Phase 4+ can extend with async task queue (Celery)
- Phase 4+ can add cost alerting system
- Phase 4+ can add Redis caching layer (on top of DB)

---

## 📝 Appendix: Code Snippets

### Service Constructor

```python
from core.neo4j_connection import get_neo4j_driver
from openai import OpenAI, APIError, APITimeoutError
import logging

logger = logging.getLogger(__name__)

class InterviewOpenAIService:
    def __init__(self, openai_client=None, neo4j_service=None):
        """
        Initialize service with optional dependency injection.
        
        Args:
            openai_client: OpenAI client instance (default: new client from env)
            neo4j_service: Neo4j service instance (default: InterviewNeo4jService)
        """
        self.openai_client = openai_client or OpenAI()
        self.neo4j_service = neo4j_service or InterviewNeo4jService()
        self.driver = get_neo4j_driver()
```

### Error Handling Pattern

```python
import openai

try:
    response = self.openai_client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[...],
        temperature=0.7,
        timeout=15,
        response_format={'type': 'json_object'}
    )
except openai.APITimeoutError as e:
    logger.warning(f"[{candidate_id[:8]}] OpenAI timeout: {e}")
    raise TimeoutError("OpenAI API timed out. Please try again.")
except openai.RateLimitError as e:
    logger.warning(f"[{candidate_id[:8]}] Rate limit: {e}")
    raise  # Let caller handle retry logic
except openai.APIError as e:
    logger.error(f"[{candidate_id[:8]}] API error: {type(e).__name__}")
    raise APIException(f"Failed to generate questions. Please try again.")
```

### Atomic Save Pattern

```python
from django.db import transaction

@transaction.atomic
def _save_questions_atomic(self, candidate_id, created_by_user, questions, vaga_id):
    """Save all 3 questions atomically, soft-delete old ones."""
    # Soft-delete old questions
    InterviewQuestion.objects.filter(
        candidato_id=candidate_id,
        is_active=True
    ).update(is_active=False)
    
    # Create new questions
    new_questions = InterviewQuestion.objects.bulk_create([
        InterviewQuestion(
            candidato_id=candidate_id,
            question_text=q['question_text'],
            difficulty_level=q['difficulty_level'],
            created_by=created_by_user
        )
        for q in questions
    ])
    
    return new_questions
```

### Mock Setup in Tests

```python
from unittest.mock import patch, MagicMock
from django.test import TestCase

class InterviewOpenAIServiceTests(TestCase):
    @patch('core.services.interview_openai_service.InterviewNeo4jService')
    def test_get_cached_questions_returns_existing(self, mock_neo4j_class):
        # Create test data
        candidato = Candidato.objects.create(...)
        InterviewQuestion.objects.create(
            candidato=candidato,
            question_text="What is OOP?",
            difficulty_level='easy'
        )
        
        # Setup mock
        mock_neo4j = MagicMock()
        
        # Call service
        service = InterviewOpenAIService(neo4j_service=mock_neo4j)
        result = service.get_candidate_questions(str(candidato.id), 'vaga-id')
        
        # Assert
        self.assertEqual(len(result), 1)
        mock_neo4j.get_candidate_skill_gaps.assert_not_called()
```

---

**Status:** Ready for execution | **Approval:** Phase 2 planning complete

**Next Steps:**
1. Agent begins Task 1: InterviewOpenAIService implementation
2. Run Task 3 & 4: Testing in parallel after Task 1
3. Task 5: Final review and verification
4. Merge to main and prepare Phase 3 (Frontend Views)
