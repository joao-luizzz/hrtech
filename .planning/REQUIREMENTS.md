# REQUIREMENTS: AI Interview Assistant (Phase 7)

**Module:** Interview Question Generation Service  
**Version:** 1.0  
**Status:** Approved for Planning

---

## 📋 Functional Requirements

### FR1: Interview Question Generation

**User Story:** As a recruiter, I want to generate AI-powered technical interview questions for a candidate based on their skill gaps so I can effectively assess candidates without preparation time.

**Requirements:**
- Generate exactly **3 interview questions** per candidate
- Questions must be personalized based on **Neo4j skill gap data**
- Questions must match the skill gap scenario (gaps vs. full match)
- OpenAI API call with **15-second timeout**
- Response must include question text + difficulty level
- Response must be valid JSON (forced output format)

**Acceptance Criteria:**
- ✅ Questions are generated from OpenAI API with correct Neo4j context
- ✅ API timeout enforced (no hanging requests)
- ✅ Error messages are user-friendly and actionable

---

### FR2: Question Caching & Persistence

**User Story:** As the system, I want to cache generated questions in the database so recruiters see fast results and we minimize OpenAI API costs.

**Requirements:**
- Create **InterviewQuestion** Django model with:
  - `candidate` (ForeignKey to Candidate)
  - `question_text` (TextField)
  - `difficulty_level` (CharField: easy/medium/hard)
  - `created_by` (ForeignKey to User/Recruiter)
  - `created_at` (DateTimeField auto_now_add)
  - `updated_at` (DateTimeField auto_now)

- Check database before API call (if questions exist, skip OpenAI)
- Load existing questions instantly without API latency
- Save new questions atomically (all-or-nothing)

**Acceptance Criteria:**
- ✅ InterviewQuestion model created with audit fields
- ✅ Existing questions returned in <100ms
- ✅ New questions only generated if not in database
- ✅ Atomic saves prevent partial data corruption

---

### FR3: Question Regeneration

**User Story:** As a recruiter, I want to regenerate questions if they're not helpful so I can get fresh, more relevant questions.

**Requirements:**
- Provide **"Regenerate" button** on candidate profile
- Overwrite old questions with new ones (keep latest only)
- Do not clutter UI with historical questions
- Maintain audit trail (old questions in DB marked as inactive or soft-deleted)

**Acceptance Criteria:**
- ✅ Recruiter can regenerate on-demand
- ✅ Only 3 latest questions displayed
- ✅ Old questions soft-deleted or marked inactive
- ✅ Audit trail preserved

---

### FR4: Permission & Access Control

**User Story:** As the system, I want to restrict question generation to recruiters only so we control API costs and maintain security.

**Requirements:**
- Feature accessible only to **Recruiter + Admin roles** (Django staff status)
- Non-recruiters see no button, no questions
- View must check `is_staff` or custom role permission
- Raise **403 Forbidden** if unauthorized

**Acceptance Criteria:**
- ✅ Non-staff users cannot access feature
- ✅ Permission check enforced at view level
- ✅ Proper 403 response for unauthorized access

---

### FR5: Edge Case - No Skill Gaps (100% Match)

**User Story:** As the system, I want to intelligently handle candidates with no skill gaps so we generate appropriate "Advanced Validation" questions.

**Requirements:**
- Detect when Neo4j query returns **zero skill gaps**
- Adjust OpenAI prompt to generate **"Advanced Validation Questions"**
- Questions must probe **deep knowledge**, not gaps
- Instruct AI: "Verify candidate actually possesses claimed skills at senior level"

**Acceptance Criteria:**
- ✅ No skill gap detected (100% match scenario)
- ✅ Prompt dynamically switches to advanced questions
- ✅ Generated questions appropriate for validation, not gaps

---

## 🛡️ Non-Functional Requirements

### NFR1: Error Handling & Resilience

**Requirement:**
- OpenAI API failures must not crash the application
- Timeout (15 sec) + RateLimitError + API exceptions all caught
- Return user-friendly HTML error fragment (red alert box)
- Restore "Generate" button so recruiter can retry
- Log errors securely (no PII, no candidate data logged)

**Acceptance Criteria:**
- ✅ API failure returns graceful error message
- ✅ Application remains stable
- ✅ Recruiter can retry without page reload
- ✅ Errors logged securely

---

### NFR2: Database Integrity

**Requirement:**
- Questions saved to DB **only after successful API response parsing**
- Failed API calls leave database clean (no orphaned records)
- No partial data (all 3 questions or nothing)

**Acceptance Criteria:**
- ✅ No InterviewQuestion records on API failure
- ✅ Recruiter can retry immediately
- ✅ Database remains consistent

---

### NFR3: Performance

**Requirement:**
- Cached question load: **< 100 ms**
- API call latency: **3-5 seconds** (expected, acceptable)
- HTMX inline update: no full page reload
- Loading spinner shown during generation

**Acceptance Criteria:**
- ✅ Cached questions load instantly
- ✅ Loading UX feedback provided
- ✅ HTMX partial response swap works

---

### NFR4: Cost Optimization

**Requirement:**
- Minimize OpenAI API calls via caching
- Estimated cost: **$0.04 per question set** (3 questions)
- Monitor token usage in logs
- Alert on unexpected cost spikes

**Acceptance Criteria:**
- ✅ Questions cached effectively
- ✅ API called only once per candidate
- ✅ Token usage logged

---

### NFR5: Security & Compliance (LGPD)

**Requirement:**
- **No PII sent to OpenAI** — only skill gap data
- **Audit trail** on InterviewQuestion model (created_by, created_at)
- **LGPD compliance:** No sensitive candidate data exposed
- All API calls logged (without response content, just timestamps)
- Access restricted to staff/recruiters

**Acceptance Criteria:**
- ✅ Skill gap data only sent to OpenAI (no names, emails, etc.)
- ✅ Audit fields track who generated what when
- ✅ No LGPD violations in question generation flow

---

### NFR6: Code Quality & Testing

**Requirement:**
- **80% test coverage** for interview module
- Unit tests for interview_service (OpenAI mocking)
- Integration tests for Django view
- Mock all external API calls (unittest.mock)
- No real OpenAI API calls in tests

**Acceptance Criteria:**
- ✅ Unit tests for service logic
- ✅ Integration tests for view/auth
- ✅ OpenAI mocked in all tests
- ✅ 80% coverage achieved

---

## 📊 Data Requirements

### Interview Questions Model

```python
class InterviewQuestion(models.Model):
    candidate = ForeignKey(Candidate, on_delete=CASCADE, related_name='interview_questions')
    question_text = TextField()
    difficulty_level = CharField(max_length=10, choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')])
    created_by = ForeignKey(User, on_delete=SET_NULL, null=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    is_active = BooleanField(default=True)  # For soft-delete on regeneration
    
    class Meta:
        ordering = ['-created_at']
```

---

## 🎨 UI/UX Requirements

### Candidate Profile View

1. **Display Existing Questions** (if exist)
   - Show all 3 questions with difficulty badges
   - Display "Generated by [Recruiter Name] on [Date]"
   - Provide "Regenerate" button

2. **Generate Flow**
   - "Generate Technical Questions" button (initially)
   - Click triggers HTMX POST request
   - Show loading spinner while fetching
   - Inline HTML swap (no page reload)

3. **Error State**
   - Red alert box with error message
   - "Try Again" button to retry
   - Restore "Generate" button state

4. **Success State**
   - Show 3 questions with difficulty levels
   - Display timestamp and recruiter name
   - Show "Regenerate" option

---

## 🔗 Integration Points

### Neo4j Integration
- Query candidate skill gaps from graph database
- Return gap data (list of missing skills for role)
- Handle "no gaps" scenario

### OpenAI Integration
- Call GPT-4o-mini for question generation
- Construct prompt from skill gaps + role context
- Parse JSON response (3 questions)
- Handle timeouts + rate limits

### Django ORM
- Save InterviewQuestion to PostgreSQL
- Query for existing questions
- Update/soft-delete on regeneration

### HTMX Frontend
- Inline HTML partial swap (no page reload)
- Loading spinner feedback
- Error fragment rendering

---

## ✅ Table Stakes (Minimum Viable)

- [x] InterviewQuestion model with audit fields
- [x] Generate view with permission checks
- [x] Neo4j skill gap query
- [x] OpenAI API integration with timeout
- [x] Question caching in database
- [x] Error handling & user feedback
- [x] HTMX inline update
- [x] Unit + integration tests (80% coverage)
- [x] LGPD compliance (no PII to OpenAI)
- [x] Regeneration support

---

## 🚫 Out of Scope (Phase 7)

- Candidate-facing question views (recruiters only)
- Complex audit log table (use model fields)
- Advanced caching strategies (simple DB caching)
- Multi-language support
- Heavy UI customization
- Selenium/E2E tests (integration tests sufficient)

---

## 📚 Success Metrics

| Metric | Target |
|--------|--------|
| Time to generate (API) | 3-5 seconds |
| Time to load (cached) | < 100 ms |
| Test coverage | ≥ 80% |
| API cost per question | ≤ $0.04 |
| Error recovery time | < 1 minute |
| Recruiter adoption | 100% of interviewers |

---

## 🔄 Approval & Sign-Off

- **Product Owner:** Phase 7 Immediate Goal (from questioning)
- **Tech Lead:** Architecture approved (service layer + Neo4j)
- **Security/Compliance:** LGPD requirements met
- **QA:** Testing strategy defined (80% coverage)

**Status:** ✅ Ready for phase planning and execution
