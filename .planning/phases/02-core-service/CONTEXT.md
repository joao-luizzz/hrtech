# Phase 2: Core Service Layer - Context

**Gathered:** 2025-03-29  
**Status:** Ready for planning  
**Source:** REQUIREMENTS.md + ROADMAP.md + Phase 1 Completion

---

## 📌 Phase Boundary

**Goal:** Build the OpenAI integration service, implement question caching, timeout logic, and robust error handling.

**Deliverables:**
1. **InterviewOpenAIService** — Call OpenAI GPT-4o-mini for question generation
2. **Question Caching Logic** — Check DB before API call, save atomically
3. **Timeout & Retry** — 15-second timeout, exponential backoff
4. **Error Handling** — Graceful degradation, user-friendly messages
5. **Cost Monitoring** — Token tracking and budget alerts
6. **Edge Case Handling** — "No skill gaps" → Advanced Validation questions
7. **Service Integration Tests** — 80% coverage with mocked OpenAI

**Success Criteria:**
- ✅ OpenAI service generates 3 questions per candidate
- ✅ Caching prevents duplicate API calls
- ✅ 15-second timeout enforced (no hanging requests)
- ✅ All API failures handled gracefully
- ✅ Error messages user-friendly (no stack traces)
- ✅ "No skill gaps" scenario detected and handled
- ✅ Question regeneration overwrites old questions
- ✅ Token usage logged for cost monitoring
- ✅ All tests mocked (no real OpenAI calls)
- ✅ 80%+ coverage

**Out of Scope (Phase 3+):**
- Frontend UI/HTMX views
- Async Celery task queue integration
- Advanced caching strategies (Redis, TTL policies)
- Cost alerting system (monitoring, notifications)

---

## 🔒 Locked Decisions

### OpenAI Integration
- **Model:** GPT-4o-mini (cost-optimized)
- **Timeout:** 15 seconds (strict, fail-fast)
- **Questions Generated:** Exactly 3 per candidate
- **Output Format:** JSON with question + difficulty_level fields
- **Prompt Style:** Few-shot examples for deterministic output
- **API Key:** Via `OPENAI_API_KEY` environment variable (python-decouple)

### Caching Strategy
- **Storage:** PostgreSQL (existing InterviewQuestion table)
- **Check:** Look for `is_active=True` questions before API call
- **Save:** All-or-nothing (all 3 questions or none)
- **Regeneration:** Mark old questions `is_active=False`, create new ones

### Error Handling
- **Timeout:** 15-second limit on OpenAI API call
- **RateLimitError:** Exponential backoff (3 retries, increasing wait)
- **Generic APIException:** Log and return user-friendly error
- **Database Error:** Rollback transaction, no orphaned records
- **User Feedback:** Red alert box HTML fragment, "Retry" button

### Edge Cases
- **No Skill Gaps (100% Match):** Detect zero-gap scenario, switch prompt to "Advanced Validation Questions"
- **Invalid Neo4j Response:** Gracefully use empty gap list, adjust prompt

### Testing
- **Mocking:** `unittest.mock.patch` for OpenAI client
- **No Real API Calls:** All tests use mock responses
- **Test Scenarios:** Success, timeout, rate limit, parse error, no gaps, 100% match

---

## 🎯 The Agent's Discretion

**Technical Choices Not Yet Locked:**
- Exact OpenAI prompt engineering (agent optimizes for question quality)
- Retry strategy implementation (exponential backoff parameters)
- Token counting approach (exact method for cost tracking)
- Response parsing (JSON parsing strategy, error recovery)
- Service class structure (methods, helper functions, state management)
- Test file organization (single file vs. split by concern)
- Logging format and levels (structured logging vs. simple)
- Async vs. synchronous implementation (Phase 2 = sync, Phase 3+ = async)

---

## 📚 Canonical References

**Downstream agents MUST read these before planning or implementing:**

### Requirements & Research
- `.planning/REQUIREMENTS.md` — FR1-FR5, NFR1-NFR6 (focus on FR1, FR2, NFR1, NFR4)
- `.planning/research/AI_INTERVIEW_ASSISTANCE_RESEARCH.md` — Best practices, cost optimization, error patterns

### Phase 1 Completion
- `.planning/phases/01-foundation-permissions/01-foundation-permissions-SUMMARY.md` — Model design, Neo4j patterns, test structure

### Codebase Patterns
- `.planning/codebase/ARCHITECTURE.md` — Service layer patterns, exception handling
- `.planning/codebase/CONVENTIONS.md` — Error logging (LGPD-safe), code style
- `.planning/codebase/TESTING.md` — Mocking patterns for external APIs

### Existing Code
- `core/models.py` — InterviewQuestion model (from Phase 1)
- `core/services/interview_neo4j_service.py` — Neo4j service pattern (from Phase 1)
- `core/tests/test_interview_questions.py` — Test structure and mocking (from Phase 1)
- `requirements.txt` — Current dependencies (check for openai package)

---

## ⚠️ Risk Mitigation (Phase 2 Specific)

| Risk | Mitigation |
|------|-----------|
| OpenAI API costs spiral | Token counting + daily budget alerts, cache aggressively |
| Prompt produces low-quality questions | Few-shot examples in prompt, human review before launch |
| Timeout too aggressive (15s) | Start with 15s, adjust to 20s if 20%+ timeouts observed |
| Race condition on question creation | Database constraint (unique_active), atomic transaction |
| JSON parsing fails | Try/except with graceful error message, retry with simpler prompt |
| "No gaps" edge case missed | Unit test scenario coverage, log all gap queries |
| Token counting inaccurate | Use OpenAI's official token counter library (tiktoken) |

---

## ✅ Phase Completion Criteria

Phase 2 is **complete** when:
1. ✅ InterviewOpenAIService created in `core/services/`
2. ✅ OpenAI integration with 15s timeout implemented
3. ✅ Caching logic (check → generate → save) working
4. ✅ All error scenarios handled with user-friendly messages
5. ✅ Edge case ("no gaps") detected and handled
6. ✅ Token counting + cost logging implemented
7. ✅ Regeneration overwrites old questions (soft-delete)
8. ✅ Integration tests cover all service methods (80%+ coverage)
9. ✅ All OpenAI calls mocked in tests (no real API usage)
10. ✅ All tests pass locally
11. ✅ PR submitted with service and tests

Phase 3 can then begin (Frontend & User Workflows).

---

## 🔄 Dependencies

**Phase 2 requires:**
- ✅ InterviewQuestion model (from Phase 1)
- ✅ Neo4j service (from Phase 1)
- ✅ Permission decorators (from Phase 1)
- ✅ OpenAI API key (environment variable, must be available)

**Phase 2 provides for Phase 3:**
- ✅ InterviewOpenAIService (callable service)
- ✅ Error handling patterns
- ✅ Caching logic (ready for frontend view integration)
- ✅ Test patterns (reusable in Phase 3)

---

**Ready for detailed planning. Agent should now create PLAN.md with specific tasks, owners, and timeline.**
