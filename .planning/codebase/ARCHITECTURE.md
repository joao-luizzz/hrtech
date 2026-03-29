# Architecture

**Analysis Date:** 2025-01-10

## Pattern Overview

**Overall:** Polyglot persistence Django application with a three-tier architecture combining relational database (PostgreSQL), graph database (Neo4j), and asynchronous processing (Celery).

**Key Characteristics:**
- Dual-database synchronization pattern: PostgreSQL for transactional data, Neo4j for intelligent skill matching
- Service layer abstraction for business logic separation
- HTMX-driven interactive UI with AJAX endpoints
- Asynchronous CV processing pipeline with task queue
- Role-based access control (candidato, rh, admin)
- LGPD-compliant audit trail for all operations

## Layers

**Presentation Layer:**
- Purpose: User interface and HTTP request handling
- Location: `core/views.py` (1285 lines), templates in `templates/`
- Contains: Django CBV/FBV views, HTMX response handlers, form validation
- Depends on: Service layer, models, Django auth (allauth)
- Used by: HTTP clients, browsers, AJAX requests

**Application/Service Layer:**
- Purpose: Business logic orchestration and external integrations
- Location: `core/services/` (1468 lines total)
- Contains:
  - `matching_service.py`: Orchestrates matching engine execution
  - `cv_upload_service.py`: CV upload validation and rate limiting
  - `pipeline_service.py`: Kanban pipeline management
  - `candidate_search_service.py`: Filters and search composition
  - `engagement_service.py`: Comments and favorites management
  - `export_service.py`: Excel/CSV export generation
  - `s3_service.py`: AWS S3 operations
  - `email_service.py`: Email template rendering and sending
  - `candidate_portal_service.py`: Candidate dashboard context building
  - `saved_filter_service.py`: Search filter persistence
- Depends on: Data access layer (models), external services (S3, email)
- Used by: View layer, task handlers

**Data Access Layer:**
- Purpose: ORM abstraction and query building
- Location: `core/models.py` (747 lines)
- Contains:
  - `Profile`: User role management (candidato, rh, admin)
  - `Candidato`: Candidate records with CV status and pipeline state
  - `Vaga`: Job posting with skill requirements (JSONField)
  - `AuditoriaMatch`: Immutable matching audit trail (LGPD compliance)
  - `HistoricoAcao`: Action history for workflow tracking
  - `Comentario`: RH team notes and comments
  - `Favorito`: Candidate bookmarks
  - `Tag`: Skill categorization
  - `CandidatoTag`: Candidate-skill associations
  - `FiltroSalvo`: User-saved search filters
- Depends on: Django ORM, PostgreSQL
- Used by: Service layer, views

**Matching Engine Layer:**
- Purpose: Intelligent skill matching using graph algorithms
- Location: `core/matching.py` (899 lines)
- Contains: Three-layer scoring algorithm (skills + similarity + profile compatibility)
- Depends on: Neo4j driver, models
- Used by: MatchingService, views

**External Integration Layer:**
- Purpose: Integration with third-party services
- Location: Various files
- Contains:
  - Neo4j AuraDB: Graph database for skill relationships (`core/neo4j_connection.py` - 170 lines)
  - AWS S3: Document storage (`core/services/s3_service.py`)
  - OpenAI: CV text extraction and skill parsing (`core/tasks.py` - 599 lines)
  - Redis: Celery message broker and caching
  - Django-Allauth: Social authentication
  - SendGrid/Email: Notifications

**Async Processing Layer:**
- Purpose: Background task execution without blocking requests
- Location: `core/tasks.py`, `hrtech/celery.py` (104 lines)
- Contains:
  - `processar_cv_task`: CV text extraction pipeline (pdfplumber → OCR → GPT-4o-mini)
  - `varrer_jobs_fantasmas`: Periodic job monitoring
  - Two task queues: default and openai (rate-limited)
- Depends on: Celery, Redis, OpenAI API, Neo4j
- Used by: View layer (async task submission)

## Data Flow

**CV Upload & Processing Pipeline:**

1. User uploads CV file (`upload_cv` view)
2. Validation: file type, size, rate limiting
3. Save to S3, create Candidato record with status=PENDENTE
4. Return status token for polling
5. Trigger `processar_cv_task` (async)
6. Task updates status: RECEBIDO → PROCESSANDO → EXTRAINDO → CONCLUIDO/ERRO
7. Extract text: pdfplumber (PDF) or Tesseract OCR (images)
8. Parse skills: GPT-4o-mini with masking for LGPD
9. Save to Neo4j: Create skill nodes and relationships
10. Update Candidato with parsed skills
11. HTMX polling refreshes UI with status

**Matching Execution Flow:**

1. RH user clicks "Rodar Matching" on job posting
2. `rodar_matching` view (protected by @rh_required)
3. Delegate to `MatchingService.run_matching(vaga_id)`
4. MatchingEngine executes three-layer algorithm:
   - Layer 1 (60%): Required skills match with temporal decay
   - Layer 2 (25%): Related skills via Neo4j SIMILAR_A relationships
   - Layer 3 (15%): Profile compatibility (seniority, area)
5. Filter candidates with score ≥ 40
6. Sort by: availability > seniority gap > creation date
7. Save to `AuditoriaMatch` (immutable audit trail)
8. Return ranked results to template

**Candidate Search & Filter Flow:**

1. User accesses `/rh/candidatos/` with query parameters
2. `buscar_candidatos` view passes params to `CandidateSearchService`
3. Service composes Queryset with filters:
   - Senioridade, anos_experiência, disponibilidade
   - Skills (intersection or union of tags)
   - Etapa pipeline, favorito status
4. Pagination applied (default 20 per page)
5. Return context with candidates + filter summary

**Action History Recording:**

1. Every significant user action triggers `registrar_acao()`
2. Recorded in `HistoricoAcao` table with:
   - User, timestamp, action type (create, update, delete)
   - IP address, request_id for traceability
   - Object references (Candidato, Vaga, etc.)
3. Audit trail preserved even if primary records deleted

**State Management:**

- **Candidate Status**: Pipeline stage in `Candidato.etapa_processo` (TRIAGEM → PROPOSTA → CONTRATADO)
- **CV Processing**: Status tracked in `Candidato.status_cv` for UI polling
- **Session State**: Django sessions for authenticated users (allauth managed)
- **Neo4j Graph State**: Skill nodes, skill relationships (REQUER, SIMILAR_A), candidate nodes
- **Redis Cache**: CV processing job IDs, rate limiting counters

## Key Abstractions

**Service Singleton Pattern:**

Services accessed via factory functions to enable testing:
- `get_s3_service()`: Returns configured S3Service instance
- `get_email_service()`: Returns configured EmailService instance
- `get_neo4j_driver()`: Returns singleton Neo4j driver (thread-safe)

**Neo4j Singleton Connection:**

Located in `core/neo4j_connection.py`:
- `get_neo4j_driver()` initializes on first call
- Reuses connection in subsequent calls
- Pool size: 50 connections, lifetime 3600s
- Automatic retry on transient failures
- Context manager support for session management

**Role-Based Access Control:**

- `@rh_required`: Protects RH-only views (returns 403 if not RH)
- `@candidato_required`: Candidato-exclusive views
- `@ajax_login_required`: AJAX endpoints return 401 (not redirect)
- Profile.is_rh property: `role in [RH, ADMIN]`
- Profile.is_candidato property: `role == CANDIDATO`

**Dual-Write Synchronization:**

UUID used as shared primary key between PostgreSQL and Neo4j:
1. Create record in PostgreSQL with generated UUID
2. Write corresponding Neo4j nodes with same UUID
3. On update: synchronize both databases
4. On delete: cascade delete from both (LGPD compliance)

## Entry Points

**Web Application:**
- Location: `hrtech/wsgi.py`
- Triggers: HTTP requests via gunicorn
- Responsibilities: WSGI application entry, static file serving (whitenoise)

**URL Router:**
- Location: `hrtech/urls.py` (26 lines)
- Triggers: All HTTP requests
- Routes to: Django admin, allauth, core.urls

**Core URLs:**
- Location: `core/urls.py` (150 lines)
- Triggers: All paths under `/`
- Routes to: 50+ view functions across:
  - Public: home, upload_cv, status_cv_htmx
  - Protected (RH): dashboard_rh, rodar_matching, pipeline_kanban, CRUD vagas
  - Protected (Candidato): minha_area, minhas_aplicacoes, dashboard_candidato
  - Admin: Django admin interface

**Asynchronous Entry Points:**
- `processar_cv_task.delay()`: Triggered from view after upload
- `varrer_jobs_fantasmas.apply_async()`: Scheduled via Celery Beat (hourly)

**Management Commands:**
- `python manage.py setup_rh`: Initialize demo RH user and vagas
- `python manage.py testar_matching`: Test matching algorithm with fixtures

## Error Handling

**Strategy:** Exception propagation with user-friendly error messages

**Patterns:**

1. **Validation Errors**:
   - `CVUploadService.validate_upload_payload()` returns list of error strings
   - Views check errors, add to Django messages, re-render with context

2. **Service-Layer Exceptions**:
   - Services raise specific exceptions (not caught, let propagate)
   - Callers responsible for exception handling
   - Example: `neo4j.exceptions.ServiceUnavailable` from Neo4j driver

3. **Task Failures (Celery)**:
   - Max retries configured (default 3)
   - On `MaxRetriesExceededError`: log and update Candidato.status_cv = ERRO
   - Email notification sent via `notify_cv_error()`

4. **View Error Handling**:
   - Try/except around service calls
   - Add error messages to Django messages framework
   - Return error context or redirect to referring page
   - Log detailed errors with request_id for debugging

5. **Database Consistency**:
   - `@transaction.atomic` on critical operations (matching, deletion)
   - Rollback if any step fails
   - Signal handlers for cascading updates

## Cross-Cutting Concerns

**Logging:**
- Framework: Python standard logging
- Configuration: LOGGING dict in `hrtech/settings.py`
- Levels: DEBUG (dev), INFO (prod)
- Formatters: Include timestamp, level, logger name, message
- Usage: `logger = logging.getLogger(__name__)` in each module
- Sensitive data masked: Never log CV content, PII masked in logs

**Validation:**
- Backend validation: Django form validators + custom validators
- Frontend validation: HTML5 required, type attributes
- Service layer validation: Pydantic models in `core/schemas.py`
- Example: `CVParseado` schema validates extracted CV data

**Authentication:**
- Framework: Django-allauth (django.contrib.auth + custom)
- Backends: ModelBackend (username/password) + AllAuth socialaccount
- Session: Django sessions middleware (cookie-based)
- CSRF: Django CSRF protection (enabled even for AJAX/HTMX)

**Authorization:**
- Decorator-based: `@login_required`, `@rh_required`
- Model-level: Profile.role field with choices
- View-level: `_user_can_access_candidate()` utility
- Audit logging: All actions recorded in HistoricoAcao

**Request Tracing:**
- Middleware: `RequestIDMiddleware` generates UUID per request
- Header: X-Request-ID propagated through responses
- Logging context: `request_id` included in log records
- Task context: Request ID passed to Celery tasks for correlation

**Rate Limiting:**
- CV upload: 5 uploads per IP per hour, 10 per email per day
- Implementation: Cache-based counters in CVUploadService
- Matching: No limit (RH can run multiple times)

**Auditing:**
- All writes recorded: Create, update, move (pipeline), delete
- Immutable trail: AuditoriaMatch and HistoricoAcao
- Data preserved: SET_NULL on FK for deleted objects
- LGPD compliance: Full traceability of decisions and actions

---

*Architecture analysis: 2025-01-10*
