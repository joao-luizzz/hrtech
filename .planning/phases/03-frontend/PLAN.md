---
phase: "03-frontend"
plan: 01
type: execute
wave: 1
depends_on: ["02-core-service"]
files_modified:
  - core/views.py
  - core/urls.py
  - core/templates/core/detalhe_candidato_match.html
  - core/templates/core/partials/interview_questions_display.html
  - core/templates/core/partials/interview_questions_error.html
autonomous: true
requirements: ["FR3", "FR4", "FR6", "NFR1", "NFR5", "NFR6"]
user_setup: []

must_haves:
  truths:
    - "Recruiter can click 'Generate Questions' button on candidate profile"
    - "HTMX POST request triggers question generation without page reload"
    - "Generated questions appear inline below button with difficulty badges"
    - "Regenerate button soft-deletes old questions and generates new ones"
    - "Error messages display with red alert box and 'Try Again' button"
    - "Non-staff users see no button (403 response on direct API access)"
    - "Loading spinner shows while generation is in progress"
    - "Questions persist after page refresh (read from database)"
  
  artifacts:
    - path: "core/views.py"
      provides: "Django view function generate_interview_questions_htmx()"
      min_lines: 80
      exports: ["generate_interview_questions_htmx"]
    
    - path: "core/urls.py"
      provides: "URL pattern mapping /api/candidates/<id>/generate-questions/"
      contains: "path('api/candidates/<candidate_id>/generate-questions/', ...)"
    
    - path: "core/templates/core/partials/interview_questions_display.html"
      provides: "HTML partial showing 3 interview questions with difficulty badges"
      min_lines: 30
    
    - path: "core/templates/core/partials/interview_questions_error.html"
      provides: "HTML partial with red alert box and 'Try Again' button"
      min_lines: 15
    
    - path: "core/templates/core/detalhe_candidato_match.html"
      provides: "Integration: button and container for HTMX swap"
      contains: "id='interview-questions-container'"
  
  key_links:
    - from: "core/templates/core/detalhe_candidato_match.html (button)"
      to: "core/views.py generate_interview_questions_htmx()"
      via: "hx-post to /api/candidates/<id>/generate-questions/"
      pattern: "hx-post=.*/api/candidates/.*/generate-questions/"
    
    - from: "core/views.py generate_interview_questions_htmx()"
      to: "core/services/interview_openai_service.py InterviewOpenAIService.get_candidate_questions()"
      via: "Service method call"
      pattern: "service\\.get_candidate_questions|InterviewOpenAIService"
    
    - from: "core/views.py generate_interview_questions_htmx()"
      to: "core/templates/core/partials/interview_questions_display.html OR interview_questions_error.html"
      via: "render() returns HTML fragment"
      pattern: "render.*interview_questions"
    
    - from: "core/templates/core/partials/interview_questions_display.html (Regenerate btn)"
      to: "core/views.py generate_interview_questions_htmx()"
      via: "HTMX POST with force_regenerate=true"
      pattern: "hx-post.*force_regenerate"

---

<objective>
**Phase 3: Frontend & User Workflows for AI Interview Assistant**

Build the HTTP endpoints, HTMX integration, and user-facing workflows that allow recruiters to generate and regenerate AI interview questions for candidates without page reload. Integrate with the InterviewOpenAIService from Phase 2 and add permission checks, error handling, and loading states.

**Purpose:**
- Enable recruiters to generate personalized interview questions with one click
- Provide seamless HTMX experience (no page refresh, inline updates)
- Handle errors gracefully with retry capability
- Restrict feature to staff-only users
- Support question regeneration (soft-delete old, create new)

**Output:**
- HTTP endpoint at `/api/candidates/{candidate_id}/generate-questions/` (POST + DELETE)
- HTML fragments for success (questions) and error (alert box)
- Integrated button on candidate profile view
- Full HTMX wiring with loading states
- Integration tests covering all workflows

**Success Criteria:**
- Recruiter clicks button → HTMX POST → questions appear inline in <5 seconds
- Regenerate button works (overwrites old, maintains audit trail)
- Error states show user-friendly message with retry option
- Non-staff users get 403 response (no button visible)
- All tests pass with mocked service layer
- Browser testing confirms UI/UX works (manual verification)

**Estimated Duration:** 8-10 hours
- Task 1 (View + URL): 2-3 hours
- Task 2 (Templates + HTMX): 2-3 hours  
- Task 3 (Integration Testing): 2-3 hours
- Task 4 (Manual Verification): 1-2 hours (checkpoint)
</objective>

<execution_context>
@.github/get-shit-done/workflows/execute-plan.md
@.planning/PROJECT.md
@.planning/STATE.md
</execution_context>

<context>
@.planning/REQUIREMENTS.md
@.planning/codebase/STRUCTURE.md
@.planning/codebase/CONVENTIONS.md
@.planning/phases/02-core-service/02-core-service-SUMMARY.md

## Key Dependencies & Context

**Phase 2 Service Layer (Ready):**
- `core/services/interview_openai_service.py::InterviewOpenAIService.get_candidate_questions(candidate, force_regenerate=False)`
  - Returns: `(questions: List[InterviewQuestion], error: Optional[str])`
  - Raises: `TimeoutError`, `APIException`, `ValidationException`
  - Handles caching, regeneration, soft-delete automatically

**Phase 1 Models & Permissions (Ready):**
- `core.models::InterviewQuestion` — Model with candidato FK, question_text, difficulty_level, created_by, created_at, is_active
- `core.decorators::@staff_required` — Permission decorator (returns 403 if not staff)

**Existing HTMX Patterns (in codebase):**
- Located in `core/templates/core/partials/`
- Pattern: `<button hx-post="..." hx-target="#id" hx-swap="outerHTML" hx-confirm="...">`
- Swap strategies: `outerHTML` (replace element), `innerHTML` (replace content)
- Example files: `comentario_item.html`, `status_polling.html`, `matching_error.html`

**Existing Django Views (Reference):**
- `core/views.py::detalhe_candidato_match()` — Candidate detail view (where button will appear)
- `core/views.py::status_cv_htmx()` — Example HTMX endpoint using `render(request, partial_path, context)`

**URL Patterns (Existing):**
- `core/urls.py` — All endpoints registered here
- Pattern: `path('api/.../', view_func, name='...')`
- Django template tag: `{% url 'core:endpoint_name' candidate_id %}`

## Interfaces & Types to Implement Against

From Phase 2 service (already implemented):
```python
class InterviewOpenAIService:
    def get_candidate_questions(
        self, 
        candidate: 'Candidato',
        force_regenerate: bool = False
    ) -> List['InterviewQuestion']:
        """
        Returns list of InterviewQuestion objects (active questions for candidate).
        If force_regenerate=True, soft-deletes old questions first.
        Raises TimeoutError, APIException on failure.
        """
        pass

# Model fields (from Phase 1)
class InterviewQuestion(models.Model):
    id: UUID
    candidate: ForeignKey(Candidato)
    question_text: str  # TextField
    difficulty_level: str  # 'easy', 'medium', 'hard'
    created_by: ForeignKey(User)
    created_at: datetime
    updated_at: datetime
    is_active: bool  # For soft-delete on regenerate
```

## View Response Formats

**Success Response (HTTP 200):**
```html
<!-- HTML fragment with 3 questions -->
<div id="interview-questions-container">
  <div class="alert alert-success">Generated 3 interview questions</div>
  <div class="card">
    <div class="card-body">
      <h6>Question 1</h6>
      <p>What is your experience with...</p>
      <span class="badge bg-warning">Medium</span>
    </div>
  </div>
  ...
  <button hx-post="..." hx-confirm="...">Regenerate Questions</button>
</div>
```

**Error Response (HTTP 400/500):**
```html
<!-- HTML fragment with error alert -->
<div id="interview-questions-container">
  <div class="alert alert-danger">
    Unable to generate questions. OpenAI service temporarily unavailable.
    <button hx-post="..." class="btn btn-sm btn-link">Try Again</button>
  </div>
</div>
```

**Initial State (before generation):**
```html
<div id="interview-questions-container">
  <button hx-post="/api/candidates/{id}/generate-questions/"
          hx-target="#interview-questions-container"
          hx-swap="innerHTML"
          hx-indicator="#loading-spinner">
    Generate Interview Questions
  </button>
  <div id="loading-spinner" class="htmx-request">Loading...</div>
</div>
```
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create Django View Endpoint with Permission Check & Error Handling</name>
  
  <files>core/views.py</files>
  
  <action>
Add a new view function `generate_interview_questions_htmx()` to `core/views.py` following Django + HTMX conventions from the codebase.

**Implementation Details:**

1. **Function Signature & Decorators:**
   ```python
   @login_required
   @staff_required  # Enforces is_staff=True, returns 403 if not authorized
   @require_http_methods(["POST"])
   def generate_interview_questions_htmx(request, candidate_id: str):
   ```

2. **Authorization & Validation:**
   - Verify `request.user.is_staff` (second check, defensive)
   - Get Candidato object: `candidato = get_object_or_404(Candidato, pk=candidate_id)`
   - If not found: return 404 (Django auto)
   - Verify user can access this candidate (re-use `_user_can_access_candidate()` helper from line 60)

3. **Extract Request Parameters:**
   - `force_regenerate = request.POST.get('force_regenerate', 'false').lower() == 'true'`
   - Defaults to False (normal generate, no regenerate unless explicit)

4. **Call Service Layer:**
   ```python
   from core.services import InterviewOpenAIService
   
   service = InterviewOpenAIService()
   try:
       questions = service.get_candidate_questions(
           candidate=candidato,
           force_regenerate=force_regenerate
       )
       # Success case: questions is a list of InterviewQuestion objects
       context = {'candidato': candidato, 'questions': questions}
       return render(request, 'core/partials/interview_questions_display.html', context)
   
   except TimeoutError as e:
       logger.warning(f"[Interview] Timeout generating questions for {candidato_id[:8]}...")
       context = {'error_message': 'Generation took too long. Please try again.'}
       return render(request, 'core/partials/interview_questions_error.html', context)
   
   except APIException as e:
       logger.error(f"[Interview] API error generating questions for {candidato_id[:8]}: {e}")
       context = {'error_message': 'OpenAI service unavailable. Please try again.'}
       return render(request, 'core/partials/interview_questions_error.html', context)
   
   except Exception as e:
       logger.exception(f"[Interview] Unexpected error generating questions for {candidato_id[:8]}")
       context = {'error_message': 'An unexpected error occurred. Please try again.'}
       return render(request, 'core/partials/interview_questions_error.html', context)
   ```

5. **Response Headers for HTMX:**
   - No special headers needed; return plain HTML
   - Status code: 200 on success, 400/500 on error (but still return HTML fragment for display)

6. **Logging (LGPD-Compliant):**
   - Log truncated candidate ID only: `candidato_id[:8]`
   - No PII logged (no names, emails, question content)
   - Format: `[Interview] {event} for {candidate_id[:8]}: {status}`

7. **Import Statements Needed:**
   - `from core.services import InterviewOpenAIService`
   - `APIException` from service (may need to check what exception names are in Phase 2)
   - `logger` (already imported in views.py)

**Code Style:**
- Follow existing views.py patterns (snake_case, docstrings, 4-space indent)
- Add a module-level docstring: `# ================================================================ # INTERVIEW QUESTIONS (HTMX) # ================================================================`
- Place after existing matching/pipeline views

**Place in File:**
- Add after the pipeline views (around line 660, before `buscar_candidatos`)
  </action>
  
  <verify>
    <automated>
      python manage.py shell -c "
        from core.views import generate_interview_questions_htmx
        import inspect
        source = inspect.getsource(generate_interview_questions_htmx)
        assert '@staff_required' in source, 'Missing @staff_required decorator'
        assert 'InterviewOpenAIService' in source, 'Missing service import'
        assert 'interview_questions_display.html' in source, 'Missing success template'
        assert 'interview_questions_error.html' in source, 'Missing error template'
        assert 'force_regenerate' in source, 'Missing force_regenerate parameter'
        print('View function structure verified.')
      "
    </automated>
  </verify>
  
  <done>
    - View function exists in core/views.py
    - Decorated with @login_required, @staff_required, @require_http_methods("POST")
    - Accepts candidate_id and force_regenerate parameters
    - Calls InterviewOpenAIService.get_candidate_questions()
    - Returns HTML fragments (success or error)
    - Handles TimeoutError, APIException, generic exceptions
    - Logs with truncated candidate ID (LGPD compliant)
    - Includes docstring and type hints
  </done>
</task>

<task type="auto">
  <name>Task 2: Add URL Pattern & Integrate Button into Candidate Profile Template</name>
  
  <files>
    core/urls.py
    core/templates/core/detalhe_candidato_match.html
  </files>
  
  <action>
**Part A: Add URL Pattern (core/urls.py)**

1. Open `core/urls.py` and locate the urlpatterns list.
2. Add new path for interview questions endpoint:
   ```python
   path(
       'api/candidates/<candidate_id>/generate-questions/',
       views.generate_interview_questions_htmx,
       name='generate_interview_questions_htmx'
   ),
   ```
3. Place this with other API endpoints (likely near the top of urlpatterns)

**Part B: Add Button & Container to Candidate Profile (core/templates/core/detalhe_candidato_match.html)**

1. Open `core/templates/core/detalhe_candidato_match.html`
2. Find a suitable location on the candidate detail view (likely in the sidebar or details section)
   - Look for existing sections like "Comentarios", "Favorito", etc.
   - Add near the top of candidate info for visibility

3. Add this HTML snippet (if questions don't exist yet):
   ```html
   <!-- Interview Questions Section -->
   <div class="card mb-3" id="interview-questions-card">
       <div class="card-header bg-light">
           <h6 class="mb-0"><i class="bi bi-chat-dots"></i> Interview Questions</h6>
       </div>
       <div class="card-body" id="interview-questions-container">
           {% if questions %}
               <!-- Show questions (will be filled by partial) -->
               {% include 'core/partials/interview_questions_display.html' %}
           {% else %}
               <!-- Show button to generate -->
               <button type="button"
                       class="btn btn-primary"
                       hx-post="{% url 'core:generate_interview_questions_htmx' candidato.id %}"
                       hx-target="#interview-questions-container"
                       hx-swap="innerHTML"
                       hx-indicator="#interview-questions-spinner">
                   <i class="bi bi-wand2"></i> Generate Interview Questions
               </button>
               <div id="interview-questions-spinner" class="htmx-request spinner-border spinner-border-sm ms-2" style="display:none;">
                   <span class="visually-hidden">Loading...</span>
               </div>
           {% endif %}
       </div>
   </div>
   ```

4. **Notes on Integration:**
   - Use `hx-target="#interview-questions-container"` to swap the container content
   - Use `hx-swap="innerHTML"` to replace just the inner HTML (keeps the card wrapper)
   - Use `hx-indicator="#interview-questions-spinner"` to show/hide spinner during request
   - `candidato.id` is the variable name in the template context (verify in existing detalhe_candidato_match.html)
   - `questions` variable should be passed from view (add to context in the existing view)

5. **Alternative if candidato context variable has different name:**
   - Check existing detalhe_candidato_match view to see the context variable name
   - Adjust `candidato` → actual variable name (e.g., `candidate`, `c`, etc.)

**Part C: Modify Existing View to Pass Questions Context**

1. In `core/views.py`, find `detalhe_candidato_match()` function (around line 561)
2. Add to the context dict passed to render():
   ```python
   # Fetch active interview questions for this candidate
   questions = InterviewQuestion.objects.filter(
       candidate_id=candidato_id,
       is_active=True
   ).order_by('-created_at')
   
   context = {
       # ... existing context ...
       'questions': questions,
   }
   ```
3. Add import at top: `from core.models import InterviewQuestion` (if not already present)

**Code Style:**
- Use existing Bootstrap classes in templates (btn, btn-primary, card, etc.)
- Use existing Bootstrap Icons (bi-wand2, bi-chat-dots)
- Follow template formatting conventions (indentation, variable naming)
  </action>
  
  <verify>
    <automated>
      # Verify URL pattern exists
      python manage.py shell -c "
        from django.urls import reverse
        try:
            url = reverse('core:generate_interview_questions_htmx', kwargs={'candidate_id': 'test123'})
            assert '/api/candidates/test123/generate-questions/' in url
            print('URL pattern verified:', url)
        except Exception as e:
            print('FAILED:', e)
      "
      
      # Verify template file exists and has key elements
      grep -q "interview-questions-container" /home/joao/hrtech/core/templates/core/detalhe_candidato_match.html && \
      grep -q "hx-post.*generate_interview_questions_htmx" /home/joao/hrtech/core/templates/core/detalhe_candidato_match.html && \
      echo "Template integration verified."
    </automated>
  </verify>
  
  <done>
    - URL pattern added to core/urls.py
    - Candidate profile template modified with button and container
    - Button triggers HTMX POST to correct endpoint
    - HTMX attributes configured (hx-post, hx-target, hx-swap, hx-indicator)
    - Loading spinner added for visual feedback
    - Template passes questions context from modified view
    - Detalhe_candidato_match view updated to fetch and pass questions
  </done>
</task>

<task type="auto">
  <name>Task 3: Create HTML Partials for Success & Error States</name>
  
  <files>
    core/templates/core/partials/interview_questions_display.html
    core/templates/core/partials/interview_questions_error.html
  </files>
  
  <action>
**File 1: Success Template (interview_questions_display.html)**

Create file `core/templates/core/partials/interview_questions_display.html` with:

```html
<!-- Partial: Interview Questions Display -->
<!-- Shows 3 generated interview questions with difficulty badges and regenerate button -->

<div id="interview-questions-display">
    <!-- Success message -->
    <div class="alert alert-success alert-dismissible fade show" role="alert">
        <i class="bi bi-check-circle me-2"></i>
        <strong>Success!</strong> Generated {{ questions|length }} interview questions for {{ candidato.nome|default:"candidate" }}.
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>

    <!-- Questions list -->
    <div class="questions-list">
        {% for question in questions %}
        <div class="card mb-3 border-left-warning" id="question-{{ question.id }}">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h6 class="card-title mb-0">Question {{ forloop.counter }}</h6>
                    <span class="badge bg-{% if question.difficulty_level == 'easy' %}success{% elif question.difficulty_level == 'medium' %}warning{% else %}danger{% endif %}">
                        {{ question.get_difficulty_level_display|default:question.difficulty_level|title }}
                    </span>
                </div>
                <p class="card-text">{{ question.question_text }}</p>
                <small class="text-muted">
                    <i class="bi bi-person me-1"></i>Generated by {{ question.created_by.first_name|default:question.created_by.email }}
                    <span class="mx-2">|</span>
                    <i class="bi bi-clock me-1"></i>{{ question.created_at|date:"d/m/Y H:i" }}
                </small>
            </div>
        </div>
        {% endfor %}
    </div>

    <!-- Regenerate button -->
    <div class="d-flex gap-2">
        <button type="button"
                class="btn btn-outline-primary"
                hx-post="{% url 'core:generate_interview_questions_htmx' candidato.id %}"
                hx-target="#interview-questions-container"
                hx-swap="innerHTML"
                hx-indicator="#interview-questions-spinner"
                hx-vals='{"force_regenerate": "true"}'
                hx-confirm="Replace current questions with new ones?">
            <i class="bi bi-arrow-repeat me-1"></i> Regenerate Questions
        </button>
    </div>
</div>
```

**File 2: Error Template (interview_questions_error.html)**

Create file `core/templates/core/partials/interview_questions_error.html` with:

```html
<!-- Partial: Interview Questions Error -->
<!-- Shows error message with retry button -->

<div id="interview-questions-error">
    <div class="alert alert-danger alert-dismissible fade show" role="alert">
        <i class="bi bi-exclamation-circle me-2"></i>
        <strong>Unable to Generate Questions</strong>
        <p class="mb-3">{{ error_message|default:"An error occurred while generating interview questions. Please try again." }}</p>
        
        <button type="button"
                class="btn btn-sm btn-outline-danger"
                hx-post="{% url 'core:generate_interview_questions_htmx' candidato.id %}"
                hx-target="#interview-questions-container"
                hx-swap="innerHTML"
                hx-indicator="#interview-questions-spinner">
            <i class="bi bi-arrow-repeat me-1"></i> Try Again
        </button>
        
        <button type="button" 
                class="btn btn-sm btn-link text-danger" 
                data-bs-dismiss="alert">
            Dismiss
        </button>
    </div>
</div>
```

**Implementation Notes:**

1. **Naming Convention:**
   - Both files use `interview_questions_` prefix (consistent with codebase)
   - Placed in `core/templates/core/partials/` directory (alongside other HTMX fragments)

2. **Success Template Details:**
   - Loops over `questions` context variable (list of InterviewQuestion objects)
   - Displays each question with:
     - Question number (from forloop.counter)
     - Question text (question.question_text)
     - Difficulty badge with color coding:
       - easy → green (bg-success)
       - medium → yellow (bg-warning)
       - hard → red (bg-danger)
     - Audit info: who generated it and when
   - "Regenerate Questions" button:
     - Uses `hx-vals='{"force_regenerate": "true"}'` to pass parameter
     - Uses `hx-confirm` for user confirmation
     - Targets same container for swap

3. **Error Template Details:**
   - Displays error_message from context
   - Provides "Try Again" button (retries same endpoint)
   - Provides "Dismiss" button (closes alert)
   - Uses Bootstrap alert danger styling (red)

4. **HTMX Details:**
   - Both use `hx-target="#interview-questions-container"` (from parent card)
   - Both use `hx-swap="innerHTML"` (replace inner content)
   - Both use `hx-indicator="#interview-questions-spinner"` (show spinner during request)
   - Regenerate button uses `hx-confirm` for safety (built-in HTMX feature)

5. **Context Variables Expected:**
   - Success template: `questions` (queryset/list), `candidato` (Candidato object)
   - Error template: `error_message` (string), `candidato` (Candidato object)

6. **Bootstrap & Icons:**
   - Uses existing Bootstrap classes (alert, badge, card, btn, etc.)
   - Uses Bootstrap Icons (bi-check-circle, bi-exclamation-circle, bi-arrow-repeat, etc.)
   - Colors: success (green), warning (yellow), danger (red)
   - All consistent with existing project templates

7. **Responsive Design:**
   - Uses Bootstrap grid (d-flex, gap-2, align-items-start)
   - Badges and buttons stack responsively
   - Text wraps naturally
  </action>
  
  <verify>
    <automated>
      # Verify both template files exist
      test -f /home/joao/hrtech/core/templates/core/partials/interview_questions_display.html && \
      test -f /home/joao/hrtech/core/templates/core/partials/interview_questions_error.html && \
      echo "Template files created."
      
      # Verify key elements in success template
      grep -q "interview-questions-display" /home/joao/hrtech/core/templates/core/partials/interview_questions_display.html && \
      grep -q "for question in questions" /home/joao/hrtech/core/templates/core/partials/interview_questions_display.html && \
      grep -q "Regenerate Questions" /home/joao/hrtech/core/templates/core/partials/interview_questions_display.html && \
      grep -q "force_regenerate" /home/joao/hrtech/core/templates/core/partials/interview_questions_display.html && \
      echo "Success template structure verified."
      
      # Verify key elements in error template
      grep -q "interview-questions-error" /home/joao/hrtech/core/templates/core/partials/interview_questions_error.html && \
      grep -q "alert-danger" /home/joao/hrtech/core/templates/core/partials/interview_questions_error.html && \
      grep -q "Try Again" /home/joao/hrtech/core/templates/core/partials/interview_questions_error.html && \
      echo "Error template structure verified."
    </automated>
  </verify>
  
  <done>
    - Success template created with:
      - Alert showing generation confirmation
      - Question cards with text, difficulty badge, and audit info
      - Regenerate button with confirmation dialog
      - HTMX attributes for inline swap
    - Error template created with:
      - Red alert box with error message
      - "Try Again" button (retries generation)
      - "Dismiss" button (closes alert)
      - HTMX attributes for inline swap
    - Both templates use consistent Bootstrap styling
    - Both accept correct context variables
    - Both integrated with HTMX for seamless swapping
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 4: Create Integration Tests for HTMX Workflows & Permission Checks</name>
  
  <files>
    core/tests/test_interview_questions_view.py
  </files>
  
  <behavior>
    - **Test 1: Permission Check** — Non-staff user POST to endpoint receives 403 response
    - **Test 2: Staff User Generate** — Staff user POSTs, receives 200 with HTML fragment (questions displayed)
    - **Test 3: Generate with Mock Service** — Mock InterviewOpenAIService, verify service called with correct candidate
    - **Test 4: Error Handling** — Service raises APIException, view returns 200 with error template
    - **Test 5: Regenerate Flag** — POST with force_regenerate=true passes flag to service
    - **Test 6: Spinner Indicator** — Template includes htmx-request spinner div
    - **Test 7: Questions Display** — Returned HTML contains all 3 questions with difficulty badges
    - **Test 8: Regenerate Button** — Success template includes "Regenerate Questions" button with hx-confirm
    - **Test 9: Candidate Not Found** — Invalid candidate_id returns 404
    - **Test 10: Initial State** — GET detalhe_candidato_match without questions shows "Generate" button
  </behavior>
  
  <action>
Create integration test file `core/tests/test_interview_questions_view.py` (450+ lines):

```python
"""
Tests for Interview Questions HTMX View Endpoint
=====================================================

Integration tests for:
- Permission checks (staff_required decorator)
- HTMX POST request handling
- Service layer mocking
- Error handling and user feedback
- Template rendering with correct context
- Regenerate workflow
"""

import logging
from unittest.mock import patch, MagicMock
from datetime import datetime

from django.test import TestCase, Client, TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from core.models import Candidato, InterviewQuestion, Profile


logger = logging.getLogger(__name__)


class InterviewQuestionsViewPermissionTests(TestCase):
    """Test permission checks on interview questions endpoint."""
    
    def setUp(self):
        """Create test users and candidate."""
        self.client = Client()
        
        # Non-staff user
        self.normal_user = User.objects.create_user(
            username='normal_user',
            email='normal@example.com',
            password='testpass123',
            is_staff=False
        )
        
        # Staff user (recruiter)
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='recruiter@example.com',
            password='testpass123',
            is_staff=True
        )
        
        # Create test candidate
        self.candidate = Candidato.objects.create(
            nome='Test Candidate',
            email='candidate@example.com',
            arquivo_cv='test.pdf',
            status_cv=Candidato.StatusCV.CONCLUIDO,
            anos_experiencia=3
        )
    
    def test_non_staff_user_gets_403(self):
        """Non-staff user receives 403 Forbidden."""
        self.client.login(username='normal_user', password='testpass123')
        
        url = reverse('core:generate_interview_questions_htmx', 
                      kwargs={'candidate_id': str(self.candidate.id)})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 403)
    
    def test_unauthenticated_user_redirected(self):
        """Unauthenticated user redirected to login."""
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'candidate_id': str(self.candidate.id)})
        response = self.client.post(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_staff_user_allowed(self):
        """Staff user is allowed access (returns 200 or error response)."""
        self.client.login(username='staff_user', password='testpass123')
        
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'candidate_id': str(self.candidate.id)})
        
        with patch('core.services.interview_openai_service.InterviewOpenAIService') as mock_service:
            # Mock service returns empty list
            mock_instance = MagicMock()
            mock_instance.get_candidate_questions.return_value = []
            mock_service.return_value = mock_instance
            
            response = self.client.post(url)
        
        # Should succeed (not 403)
        self.assertNotEqual(response.status_code, 403)


class InterviewQuestionsViewFunctionalTests(TestCase):
    """Test HTMX workflow and template rendering."""
    
    def setUp(self):
        """Create test data."""
        self.client = Client()
        
        self.staff_user = User.objects.create_user(
            username='recruiter',
            email='recruiter@example.com',
            password='testpass123',
            is_staff=True
        )
        
        self.candidate = Candidato.objects.create(
            nome='John Doe',
            email='john@example.com',
            arquivo_cv='john.pdf',
            status_cv=Candidato.StatusCV.CONCLUIDO,
            anos_experiencia=5
        )
        
        self.client.login(username='recruiter', password='testpass123')
    
    def test_generate_questions_returns_html_fragment(self):
        """Successful generation returns HTML fragment with questions."""
        # Create mock questions
        q1 = InterviewQuestion(
            candidate=self.candidate,
            question_text='What is your experience with Python?',
            difficulty_level='medium',
            created_by=self.staff_user
        )
        q2 = InterviewQuestion(
            candidate=self.candidate,
            question_text='Design a scalable API',
            difficulty_level='hard',
            created_by=self.staff_user
        )
        q3 = InterviewQuestion(
            candidate=self.candidate,
            question_text='Explain REST principles',
            difficulty_level='easy',
            created_by=self.staff_user
        )
        
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'candidate_id': str(self.candidate.id)})
        
        with patch('core.services.interview_openai_service.InterviewOpenAIService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_candidate_questions.return_value = [q1, q2, q3]
            mock_service.return_value = mock_instance
            
            response = self.client.post(url)
        
        # Should return 200 with HTML
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'interview-questions-display', response.content)
        self.assertIn(b'Python', response.content)
        self.assertIn(b'medium', response.content.lower())
    
    def test_error_returns_error_template(self):
        """Service error returns error template with retry button."""
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'candidate_id': str(self.candidate.id)})
        
        from core.services.interview_openai_service import APIException
        
        with patch('core.services.interview_openai_service.InterviewOpenAIService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_candidate_questions.side_effect = APIException("API is down")
            mock_service.return_value = mock_instance
            
            response = self.client.post(url)
        
        # Should return 200 with error template
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'interview-questions-error', response.content)
        self.assertIn(b'Unable to Generate', response.content)
        self.assertIn(b'Try Again', response.content)
    
    def test_timeout_error_handling(self):
        """Timeout error returns user-friendly error message."""
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'candidate_id': str(self.candidate.id)})
        
        with patch('core.services.interview_openai_service.InterviewOpenAIService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_candidate_questions.side_effect = TimeoutError("Request timeout")
            mock_service.return_value = mock_instance
            
            response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'took too long', response.content)
    
    def test_force_regenerate_parameter(self):
        """force_regenerate=true parameter is passed to service."""
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'candidate_id': str(self.candidate.id)})
        
        with patch('core.services.interview_openai_service.InterviewOpenAIService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_candidate_questions.return_value = []
            mock_service.return_value = mock_instance
            
            response = self.client.post(url, {'force_regenerate': 'true'})
            
            # Verify service was called with force_regenerate=True
            mock_instance.get_candidate_questions.assert_called_once()
            call_kwargs = mock_instance.get_candidate_questions.call_args[1]
            self.assertTrue(call_kwargs.get('force_regenerate', False))
    
    def test_candidate_not_found_returns_404(self):
        """Invalid candidate_id returns 404."""
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'candidate_id': 'invalid-id-12345'})
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 404)
    
    def test_template_includes_regenerate_button(self):
        """Success template includes Regenerate button with hx-confirm."""
        q1 = InterviewQuestion(
            candidate=self.candidate,
            question_text='Test question',
            difficulty_level='medium',
            created_by=self.staff_user
        )
        
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'candidate_id': str(self.candidate.id)})
        
        with patch('core.services.interview_openai_service.InterviewOpenAIService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_candidate_questions.return_value = [q1]
            mock_service.return_value = mock_instance
            
            response = self.client.post(url)
        
        self.assertIn(b'Regenerate Questions', response.content)
        self.assertIn(b'hx-confirm', response.content)
        self.assertIn(b'force_regenerate', response.content)


class InterviewQuestionsHTMXIntegrationTests(TransactionTestCase):
    """Test HTMX behavior and attributes in response."""
    
    def setUp(self):
        self.client = Client()
        
        self.staff_user = User.objects.create_user(
            username='recruiter',
            email='recruiter@example.com',
            password='testpass123',
            is_staff=True
        )
        
        self.candidate = Candidato.objects.create(
            nome='Jane Smith',
            email='jane@example.com',
            arquivo_cv='jane.pdf',
            status_cv=Candidato.StatusCV.CONCLUIDO,
            anos_experiencia=4
        )
        
        self.client.login(username='recruiter', password='testpass123')
    
    def test_response_contains_correct_htmx_targets(self):
        """Response HTML includes HTMX-compatible structure."""
        # Create questions
        for i in range(3):
            InterviewQuestion.objects.create(
                candidate=self.candidate,
                question_text=f'Question {i+1}',
                difficulty_level=['easy', 'medium', 'hard'][i],
                created_by=self.staff_user,
                is_active=True
            )
        
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'candidate_id': str(self.candidate.id)})
        
        with patch('core.services.interview_openai_service.InterviewOpenAIService') as mock_service:
            mock_instance = MagicMock()
            questions = InterviewQuestion.objects.filter(
                candidate=self.candidate,
                is_active=True
            )
            mock_instance.get_candidate_questions.return_value = list(questions)
            mock_service.return_value = mock_instance
            
            response = self.client.post(url)
        
        # Check for HTMX-compatible structure
        self.assertIn(b'interview-questions-display', response.content)
        self.assertIn(b'hx-post', response.content)  # Regenerate button
        self.assertIn(b'generate_interview_questions_htmx', response.content)


class CandidateProfileIntegrationTests(TestCase):
    """Test that candidate profile shows/hides button appropriately."""
    
    def setUp(self):
        self.client = Client()
        
        self.staff_user = User.objects.create_user(
            username='recruiter',
            email='recruiter@example.com',
            password='testpass123',
            is_staff=True
        )
        
        self.candidate = Candidato.objects.create(
            nome='Test Candidate',
            email='test@example.com',
            arquivo_cv='test.pdf',
            status_cv=Candidato.StatusCV.CONCLUIDO,
            anos_experiencia=3
        )
        
        self.vaga = self._create_vaga()
        
        self.client.login(username='recruiter', password='testpass123')
    
    def _create_vaga(self):
        """Helper to create a test job position."""
        from core.models import Vaga
        return Vaga.objects.create(
            titulo='Test Position',
            descricao='Test',
            user=self.staff_user
        )
    
    def test_profile_shows_button_when_no_questions(self):
        """Candidate profile shows 'Generate' button when no questions exist."""
        url = reverse('core:detalhe_candidato_match',
                      kwargs={'vaga_id': str(self.vaga.id),
                              'candidato_id': str(self.candidate.id)})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Generate Interview Questions', response.content)
        self.assertIn(b'interview-questions-container', response.content)
    
    def test_profile_shows_questions_when_exist(self):
        """Candidate profile shows questions when they exist."""
        # Create questions
        InterviewQuestion.objects.create(
            candidate=self.candidate,
            question_text='Test question',
            difficulty_level='medium',
            created_by=self.staff_user,
            is_active=True
        )
        
        url = reverse('core:detalhe_candidato_match',
                      kwargs={'vaga_id': str(self.vaga.id),
                              'candidato_id': str(self.candidate.id)})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Should show the question in the profile
        # (exact assertion depends on template rendering)
```

**Instructions for Test File:**

1. **Location:** Save as `core/tests/test_interview_questions_view.py`

2. **Test Classes:**
   - `InterviewQuestionsViewPermissionTests` — Permission checks (403, redirects)
   - `InterviewQuestionsViewFunctionalTests` — Main workflow (generate, errors, regenerate)
   - `InterviewQuestionsHTMXIntegrationTests` — HTMX response structure
   - `CandidateProfileIntegrationTests` — Integration with candidate profile view

3. **Mocking Strategy:**
   - Use `@patch('core.services.interview_openai_service.InterviewOpenAIService')`
   - Mock the service instance to control return values and side effects
   - No real API calls or database state from Phase 2

4. **Test Setup:**
   - Create test users (staff and non-staff)
   - Create test candidate
   - Create test questions
   - Use Client() to make HTTP requests

5. **Run Tests:**
   ```bash
   python manage.py test core.tests.test_interview_questions_view -v 2
   python manage.py test core.tests.test_interview_questions_view --cov=core.views
   ```

6. **Coverage Target:**
   - Aim for 80%+ coverage of `generate_interview_questions_htmx()` function
   - Cover all branches: success, timeout, API error, generic error
   - Cover permission checks and template rendering
  </action>
  
  <verify>
    <automated>
      # Run the test suite
      cd /home/joao/hrtech && python manage.py test core.tests.test_interview_questions_view -v 2 2>&1 | tee /tmp/test_output.txt
      
      # Check if tests passed
      if grep -q "FAILED\|ERROR" /tmp/test_output.txt; then
        echo "TESTS FAILED - See output above"
        exit 1
      else
        echo "All tests passed!"
        grep "OK\|Ran" /tmp/test_output.txt
      fi
    </automated>
  </verify>
  
  <done>
    - Integration test file created (test_interview_questions_view.py)
    - Permission tests verify @staff_required decorator works
    - Functional tests verify service integration and error handling
    - HTMX integration tests verify response structure
    - Candidate profile tests verify button/questions display logic
    - All tests use mocked service (no real API calls)
    - Tests cover happy path, errors, timeouts, regenerate
    - 10+ test cases with clear naming and docstrings
    - Tests follow project conventions (TransactionTestCase, setUp, assertions)
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
  - HTTP endpoint for generating interview questions (Django view + URL routing)
  - HTMX-integrated candidate profile with button
  - Success template showing 3 questions with difficulty badges
  - Error template with red alert and retry button
  - Regenerate button with confirmation dialog
  - Full integration test suite with 10+ test cases
  - Service layer integration with error handling
  </what-built>
  
  <how-to-verify>
  **Step 1: Start Development Server**
  ```bash
  cd /home/joao/hrtech
  python manage.py runserver
  ```
  
  **Step 2: Access Candidate Profile**
  - Go to http://localhost:8000/core/dashboard_rh/ (RH dashboard)
  - Click on a candidate to view their profile
  - Look for "Interview Questions" section with "Generate Interview Questions" button
  
  **Step 3: Generate Questions (Happy Path)**
  - Click "Generate Interview Questions" button
  - Observe:
    - Loading spinner appears (3 sec)
    - Page does NOT reload (HTMX swap)
    - 3 questions appear with difficulty badges (easy/medium/hard)
    - Success alert shows "Generated 3 interview questions"
    - Timestamp shows when generated
  
  **Step 4: Regenerate Questions**
  - Click "Regenerate Questions" button
  - Confirm dialog appears
  - After confirmation:
    - Old questions replaced with new ones
    - Page still does NOT reload
    - Success alert shows update
  
  **Step 5: Test Error Handling (if service is down)**
  - Temporarily disable OpenAI API or stop service
  - Click "Generate" button
  - Observe:
    - Error alert appears (red box)
    - Error message is user-friendly
    - "Try Again" button appears
    - No console errors visible
  
  **Step 6: Test Permission (Non-Staff User)**
  - Logout, login as non-staff user
  - Navigate to same candidate profile
  - Verify:
    - "Generate Interview Questions" button NOT visible
    - Direct API call to /api/candidates/{id}/generate-questions/ returns 403
  
  **Step 7: Run Integration Tests**
  ```bash
  python manage.py test core.tests.test_interview_questions_view -v 2
  ```
  - All tests should pass (10+ test cases)
  - Check output for "OK" status
  
  **Expected Outcomes:**
  ✓ Generate button appears only for staff users
  ✓ Clicking generates questions inline (no page reload)
  ✓ Questions display with correct formatting
  ✓ Regenerate button works with confirmation
  ✓ Error messages are user-friendly
  ✓ All integration tests pass
  ✓ No console JavaScript errors
  ✓ HTMX requests complete in <5 seconds
  </how-to-verify>
  
  <resume-signal>
  Type one of:
  - "approved" — All verification steps passed, feature works as expected
  - "issues: {description}" — Describe any issues found (e.g., "button not showing", "error message unclear", etc.)
  - "needs-fix: {component}" — Specific component needs rework (e.g., "template styling", "error handling", etc.)
  </resume-signal>
</task>

</tasks>

<verification>
## Phase 3 Completion Verification

### Automated Checks
- ✅ View function exists with @staff_required decorator
- ✅ URL pattern registered in core/urls.py
- ✅ HTML partials created for success and error states
- ✅ Integration tests pass (10+ test cases)
- ✅ Candidate profile template modified with button and container
- ✅ HTMX attributes properly configured (hx-post, hx-target, hx-swap, hx-indicator)
- ✅ Error handling covers TimeoutError, APIException, generic exceptions
- ✅ Logging is LGPD-compliant (truncated candidate IDs)

### Manual Verification (Checkpoint)
- [ ] Recruiter can generate questions with one click
- [ ] Loading spinner shows while generating
- [ ] Questions appear inline without page reload
- [ ] Regenerate button works with confirmation
- [ ] Error messages are user-friendly with retry button
- [ ] Non-staff users cannot access feature (403 response)
- [ ] All integration tests pass

### Success Criteria Coverage
| Criterion | Status | Evidence |
|-----------|--------|----------|
| HTTP endpoint created | ✅ | generate_interview_questions_htmx() in views.py |
| Permission check in place | ✅ | @staff_required decorator |
| HTMX inline swap working | ✅ | hx-post, hx-target, hx-swap attributes |
| Error handling displays messages | ✅ | interview_questions_error.html template |
| Regenerate button works | ✅ | force_regenerate parameter, hx-confirm |
| URL routing configured | ✅ | path() in core/urls.py |
| Template integration complete | ✅ | detalhe_candidato_match.html modified |
| Integration tests created | ✅ | test_interview_questions_view.py (10+ tests) |
| All workflows tested | ✅ | Permission, generate, error, regenerate tests |
| UI verified in browser | [ ] | See checkpoint verification |

</verification>

<success_criteria>
**Phase 3 is complete when:**

1. ✅ **View Endpoint Created** — `generate_interview_questions_htmx()` function in core/views.py
   - Decorated with @login_required, @staff_required, @require_http_methods("POST")
   - Accepts candidate_id and force_regenerate parameters
   - Calls InterviewOpenAIService.get_candidate_questions()
   - Returns HTML fragments (success or error)
   - Handles exceptions (TimeoutError, APIException, generic)
   - Logs with truncated candidate ID (LGPD compliant)

2. ✅ **URL Routing** — Path registered in core/urls.py
   - Pattern: `/api/candidates/<candidate_id>/generate-questions/`
   - Named: `generate_interview_questions_htmx`
   - Method: POST only
   - Accessible from Django templates via `{% url 'core:...' candidato.id %}`

3. ✅ **Candidate Profile Integration** — Modified detalhe_candidato_match.html
   - Shows "Generate Interview Questions" button (if no questions exist)
   - Shows generated questions + "Regenerate" button (if questions exist)
   - Button container with id="interview-questions-container"
   - Loading spinner with id="interview-questions-spinner"

4. ✅ **HTML Templates Created** — Two HTMX-compatible partials
   - `interview_questions_display.html` — Shows 3 questions with difficulty badges
   - `interview_questions_error.html` — Shows error alert with "Try Again" button
   - Both use correct HTMX attributes (hx-post, hx-target, hx-swap)
   - Both pass/use correct context variables

5. ✅ **Error Handling** — User-friendly error messages
   - TimeoutError → "Generation took too long"
   - APIException → "OpenAI service unavailable"
   - Generic Exception → "An unexpected error occurred"
   - All display with red alert box and retry button

6. ✅ **Regenerate Workflow** — force_regenerate parameter
   - Button passes force_regenerate=true via hx-vals
   - View passes to service: force_regenerate=True
   - Service soft-deletes old, creates new (handles internally)
   - User confirms with hx-confirm dialog

7. ✅ **Permission Checks** — @staff_required enforced
   - Non-staff users receive 403 response
   - Button hidden from non-staff (checked in template)
   - No questions visible to non-staff users

8. ✅ **Integration Tests** — test_interview_questions_view.py
   - 10+ test cases covering:
     - Permission checks (403, redirects)
     - Happy path (generate, error, timeout)
     - Regenerate workflow
     - Template rendering
     - HTMX structure
   - All use mocked service (no real API calls)
   - All tests pass

9. ✅ **HTMX Integration** — Seamless user experience
   - POST request triggers without page reload
   - Loading spinner shown during request
   - Questions appear inline in container
   - Regenerate button works without refresh
   - Error messages displayed inline

10. ✅ **Browser Verification** — Manual testing (checkpoint)
    - Feature works end-to-end in browser
    - Generate button visible to staff users
    - Loading spinner shows during request
    - Questions appear with correct formatting
    - Regenerate button works with confirmation
    - Error handling works as expected
    - No console errors visible

**Phase 3 deliverables ready for Phase 4 (Quality & Deployment).**
</success_criteria>

<output>
After completion, create `.planning/phases/03-frontend/03-frontend-SUMMARY.md` with:

## Execution Summary

```markdown
---
phase: 03-frontend
plan: 01
subsystem: "HTMX Frontend Integration"
tags: ["htmx", "django-views", "error-handling", "permissions", "integration-tests"]
status: "complete"
completion_date: "{date}"
duration_hours: {actual hours}
---

# Phase 3 Summary: Frontend & User Workflows

**Build status:** ✅ Complete
**Test coverage:** {coverage}%
**Integration tests:** {count} tests passed

## Deliverables

### View Layer
- HTTP endpoint: `/api/candidates/{id}/generate-questions/` (POST)
- Permission: @staff_required decorator enforced
- Error handling: TimeoutError, APIException, generic exceptions
- Logging: LGPD-compliant (truncated candidate IDs)

### Frontend
- Candidate profile integration
- "Generate Interview Questions" button (HTMX)
- Questions display with difficulty badges
- Regenerate button with confirmation
- Loading spinner during request
- Error alert with retry button

### Templates
- `interview_questions_display.html` — Success state (3 questions)
- `interview_questions_error.html` — Error state (alert + retry)

### Tests
- {count} integration tests
- Permission checks, happy path, error cases
- All mocked (no real API calls)
- {coverage}% coverage of view layer

## Architecture

Service → View → Template → HTMX → Browser
```

Plus include the same structure as Phase 2 SUMMARY with:
- Deliverables table
- Test coverage details
- Performance characteristics
- Known stubs/limitations
- Success criteria checklist
- Next steps (Phase 4)
```
</output>

