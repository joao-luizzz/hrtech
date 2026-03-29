# Phase 1: Foundation & Permissions - Context

**Gathered:** 2025-03-29  
**Status:** Ready for planning  
**Source:** PROJECT.md + REQUIREMENTS.md + ROADMAP.md

---

## 📌 Phase Boundary

**Goal:** Build the data model, permissions infrastructure, and Neo4j integration for the AI Interview Assistant.

**Deliverables:**
1. **InterviewQuestion Django model** with audit fields (created_by, created_at, is_active)
2. **Database migration** to create the table
3. **Django admin integration** for model visibility
4. **Neo4j queries** for candidate skill gap extraction
5. **Permission decorators/checks** for Recruiter/Admin-only access
6. **Unit tests** for model validation and Neo4j integration

**Success Criteria:**
- ✅ Model created with all required fields and relationships
- ✅ Migrations applied to dev/test databases
- ✅ Permission checks block non-staff users (403 response)
- ✅ Neo4j skill gap queries return accurate data
- ✅ Unit tests cover model methods and permissions
- ✅ Code follows project conventions (CONVENTIONS.md)

**Out of Scope (Phase 2+):**
- OpenAI API integration
- Frontend UI/HTMX views
- Caching logic
- Error handling for API failures
- Testing of OpenAI integration

---

## 🔒 Locked Decisions

### Data Model
- **InterviewQuestion** model with ForeignKey to Candidate
- Fields: `question_text` (TextField), `difficulty_level` (CharField with choices), `created_by` (ForeignKey to User), `created_at` (DateTimeField auto_now_add), `updated_at` (DateTimeField auto_now), `is_active` (BooleanField for soft-delete)
- Meta: ordering by `-created_at`, unique_together on (candidate, is_active) to enforce one active set

### Database
- PostgreSQL (existing, no new databases)
- Single migration file for InterviewQuestion table
- Indexes on `candidate_id`, `created_by_id`, `is_active` for query performance

### Permissions
- Access restricted to `is_staff=True` (Django staff status)
- View decorator: `@staff_required` or permission check `user.is_staff`
- Return **403 Forbidden** for unauthorized access
- Log all permission denials (no PII)

### Neo4j Integration
- Query existing Neo4j instance (already configured in settings)
- Extract skill gaps for candidate + job position
- Return: list of missing skills ([], if 100% match)
- Determine if "Advanced Validation" prompt needed (zero gaps scenario)

### Testing
- Use Django TestCase (existing pattern in project)
- Mock Neo4j queries with unittest.mock.patch
- No real Neo4j calls in tests
- Test both permission pass and fail scenarios
- Minimum 80% coverage for this module

---

## 🎯 The Agent's Discretion

**Technical Choices Not Yet Locked:**
- Exact Neo4j query syntax (agent decides based on existing patterns in codebase)
- Specific permission decorator placement (views vs. URL routing)
- Migration naming convention (follows Django standard)
- Helper methods on InterviewQuestion model (agent optimizes based on usage patterns)
- Test file organization (unit vs. integration tests split)
- logging library and format (use existing project patterns)

**Implementation Details Agent Will Decide:**
- How to serialize skill gaps from Neo4j response
- Whether to cache Neo4j connection (use existing singleton if available)
- Model validation (clean() method vs. save() hooks)
- Relationship on_delete behavior for cascade
- Soft-delete implementation (filter by is_active=True vs. delete flag checks)

---

## 📚 Canonical References

**Downstream agents MUST read these before planning or implementing:**

### Project Vision & Requirements
- `.planning/PROJECT.md` — Vision, problem statement, architecture principles
- `.planning/REQUIREMENTS.md` — All 11 requirements, FR1-FR5, NFR1-NFR6
- `.planning/ROADMAP.md` — 4-phase roadmap, Phase 1 details

### Codebase Architecture & Patterns
- `.planning/codebase/ARCHITECTURE.md` — Design patterns, service layer, Neo4j integration
- `.planning/codebase/STRUCTURE.md` — Django project structure, models location, naming
- `.planning/codebase/CONVENTIONS.md` — Code style, imports, logging, error handling
- `.planning/codebase/TESTING.md` — Test framework, mocking patterns, test locations
- `.planning/codebase/CONCERNS.md` — Known issues to avoid (security, performance, testing)

### Domain Research
- `.planning/research/AI_INTERVIEW_ASSISTANCE_RESEARCH.md` — Best practices for this feature

### Existing Models & ORM
- `core/models.py` — Candidate model, User model relationships (for ForeignKey targets)
- `core/views.py` — Existing view permission patterns
- `core/tests/` — Existing test structure and mocking examples

### Neo4j Integration
- Look for Neo4j singleton/connection pattern in codebase (ARCHITECTURE.md references it)
- Existing Neo4j queries for skill gap calculation (reference for query style)

---

## ⚠️ Risk Mitigation (Phase 1 Specific)

| Risk | Mitigation |
|------|-----------|
| Neo4j query syntax errors | Agent reads existing queries from codebase (ARCHITECTURE.md), tests with mock data |
| Permission checks bypassed | Unit tests verify 403 response, code review before merge |
| Migration conflicts | Use Django's migration system properly, no manual SQL |
| Model relationship issues | Test ForeignKey constraints in unit tests |
| Test coverage gaps | Enforce 80%+ coverage, use coverage.py to measure |

---

## ✅ Phase Completion Criteria

Phase 1 is **complete** when:
1. ✅ InterviewQuestion model exists in `core/models.py`
2. ✅ Migration file created and tested
3. ✅ Model admin registered in `core/admin.py`
4. ✅ Neo4j queries work and tested (no real API calls)
5. ✅ Permission checks implemented and tested
6. ✅ Unit tests cover all model methods + permissions (80%+ coverage)
7. ✅ Code follows CONVENTIONS.md
8. ✅ All tests pass locally
9. ✅ PR submitted with tests

Phase 2 can then begin (Core Service Layer).

---

## 🔄 Dependencies

**Phase 1 has NO blocking dependencies:**
- Uses existing Candidate model (stable)
- Uses existing User model (stable)
- Uses existing Neo4j connection (stable)
- Parallel work possible on Phase 2 (OpenAI service) after Phase 1 model is finalized

---

**Ready for detailed planning. Agent should now create PLAN.md with specific tasks, owners, and timeline.**
