# Phase 3: Frontend & User Workflows - Context

**Gathered:** 2025-03-30  
**Status:** Ready for planning  
**Source:** REQUIREMENTS.md + ROADMAP.md + Phase 1&2 Completion

---

## 📌 Phase Boundary

**Goal:** Build the HTTP endpoints, HTMX integration, and user workflows for the AI Interview Assistant feature.

**Deliverables:**
1. **Django View** — HTTP endpoint for question generation (`/api/candidates/{id}/generate-questions/`)
2. **HTMX Integration** — Inline HTML fragment swap (no page reload)
3. **Question Regeneration** — Delete old, generate new (soft-delete)
4. **Error Handling** — User-friendly error messages, retry button
5. **URL Routing** — Wire up views to candidate profile
6. **Frontend Tests** — Integration tests (Django TestCase)

**Success Criteria:**
- ✅ Recruiter can click "Generate Questions" button
- ✅ Loading spinner shown while generating
- ✅ Questions appear inline without page reload (HTMX)
- ✅ Regenerate button overwrites old questions
- ✅ Errors shown with retry option
- ✅ Non-recruiters see no button (403 response)
- ✅ No page reload, all async via HTMX
- ✅ UI/Integration tests cover all workflows

**Out of Scope (Phase 4+):**
- End-to-end tests (Selenium)
- Performance optimization
- Advanced caching (Redis, TTL)
- Async Celery integration

---

## 🔒 Locked Decisions

### URLs
- **Generate Questions POST:** `/api/candidates/{candidate_id}/generate-questions/`
- **Delete & Regenerate DELETE:** Same endpoint (idempotent)
- **Permission Check:** `@staff_required` decorator

### Frontend
- **Technology:** Django templates + HTMX
- **Button Location:** On candidate profile (existing template)
- **Interaction:** Click → POST via HTMX → inline swap
- **Loading:** Show spinner while request pending
- **Error Display:** Red alert box with error message + "Try Again" button

### Response Formats
- **Success:** HTML fragment with 3 questions + "Regenerate" button
- **Error:** HTML fragment with red alert + "Try Again" button
- **Status:** HTTP 200 (success) or 400/403/500 (error)

### Workflow
1. Recruiter loads candidate profile
2. Backend checks: questions exist + is_active=True?
3. If yes: render questions + "Regenerate" button
4. If no: render "Generate Questions" button
5. Click "Generate" → HTMX POST → Service call → DB save → HTML swap
6. Click "Regenerate" → Same flow but delete old first

---

## 🎯 The Agent's Discretion

**Technical Choices Not Yet Locked:**
- Exact HTMX event handlers (`hx-post`, `hx-confirm`, etc.)
- HTML template structure (fieldsets, cards, divs)
- CSS classes and styling (use project's existing theme)
- JavaScript for loading spinner (pure JS vs. library)
- Toast notifications vs. alert box for errors
- Confirm dialog for regenerate (hx-confirm vs. custom modal)
- API response format (JSON vs. HTML fragments)

---

## 📚 Canonical References

**Downstream agents MUST read these before planning or implementing:**

### Requirements & Architecture
- `.planning/REQUIREMENTS.md` — FR1-FR5, NFR1-NFR6 (focus on UI/UX, error handling)
- `.planning/codebase/STRUCTURE.md` — Django project structure, URL routing patterns
- `.planning/codebase/CONVENTIONS.md` — Code style, imports, templates

### Phase 2 Code
- `.planning/phases/02-core-service/02-core-service-SUMMARY.md` — Service API reference
- `core/services/interview_openai_service.py` — Service methods and error patterns

### Existing Frontend Patterns
- Look for candidate profile view in codebase
- HTMX usage examples (existing templates with hx-* attributes)
- Django form handling patterns (CSRF, POST)
- Error message display patterns (alerts, modals)

---

## ⚠️ Risk Mitigation (Phase 3 Specific)

| Risk | Mitigation |
|------|-----------|
| HTMX event handling complex | Reference existing HTMX in codebase, keep it simple |
| Race condition on questions | Use database unique constraint (already in Phase 1) |
| User confusion on error | Clear error message + "Try Again" button |
| CSRF token missing | Django `{% csrf_token %}` in all forms |
| Slow response time | Cache existing questions, show loading state |

---

## ✅ Phase Completion Criteria

Phase 3 is **complete** when:
1. ✅ Django view created for generate endpoint
2. ✅ Permission checks in place (403 for non-staff)
3. ✅ HTMX integration working (inline swap, no reload)
4. ✅ Error handling displays user-friendly messages
5. ✅ Regenerate button deletes old and creates new
6. ✅ URL routing wired to candidate profile
7. ✅ Template integration on candidate profile view
8. ✅ Integration tests cover all workflows (happy path + errors)
9. ✅ HTMX requests tested (mocked service calls)
10. ✅ UI works in browser (manual verification)

Phase 4 can then begin (Quality & Deployment).

---

## 🔄 Dependencies

**Phase 3 requires:**
- ✅ InterviewOpenAIService (from Phase 2)
- ✅ InterviewQuestion model (from Phase 1)
- ✅ Permission decorators (from Phase 1)
- ✅ Candidate profile view (existing, needs modification)

**Phase 3 provides for Phase 4:**
- ✅ Complete HTTP endpoints
- ✅ HTMX integration patterns
- ✅ Error handling UI
- ✅ Integration test patterns

---

**Ready for detailed planning. Agent should now create PLAN.md with specific tasks and timeline.**
