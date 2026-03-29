# Codebase Structure

**Analysis Date:** 2025-01-10

## Directory Layout

```
/home/joao/hrtech/
├── hrtech/                 # Django project configuration
│   ├── __init__.py
│   ├── settings.py         # Main Django settings (331 lines)
│   ├── settings_test.py    # Test-specific settings (68 lines)
│   ├── urls.py             # Root URL dispatcher (26 lines)
│   ├── wsgi.py             # WSGI application entry
│   ├── asgi.py             # ASGI application entry
│   └── celery.py           # Celery configuration (104 lines)
│
├── core/                   # Main application directory
│   ├── models.py           # ORM models (747 lines, 10 model classes)
│   ├── views.py            # View functions (1285 lines, 50+ routes)
│   ├── urls.py             # App URL patterns (150 lines)
│   ├── admin.py            # Django admin customization (115 lines)
│   ├── apps.py             # App configuration
│   ├── decorators.py       # Auth decorators (108 lines)
│   ├── middleware.py       # Custom middleware (24 lines)
│   ├── schemas.py          # Pydantic validation schemas (95 lines)
│   ├── matching.py         # Matching algorithm (899 lines)
│   ├── neo4j_connection.py # Neo4j driver singleton (170 lines)
│   ├── tasks.py            # Celery async tasks (599 lines)
│   │
│   ├── services/           # Service layer (1468 lines total)
│   │   ├── __init__.py
│   │   ├── s3_service.py
│   │   ├── email_service.py
│   │   ├── cv_upload_service.py
│   │   ├── matching_service.py
│   │   ├── pipeline_service.py
│   │   ├── candidate_search_service.py
│   │   ├── export_service.py
│   │   ├── engagement_service.py
│   │   ├── candidate_portal_service.py
│   │   └── saved_filter_service.py
│   │
│   ├── management/
│   │   ├── commands/
│   │   │   ├── setup_rh.py         # Initialize demo data
│   │   │   └── testar_matching.py  # Test matching algorithm
│   │   └── __init__.py
│   │
│   ├── migrations/         # Django schema migrations (auto-generated)
│   ├── templates/          # App-specific HTML templates
│   ├── tests/              # Unit and integration tests
│   │   ├── test_matching_engine.py
│   │   ├── test_cv_upload_service.py
│   │   ├── test_pipeline_mock.py
│   │   ├── test_backend_validations.py
│   │   ├── test_dashboard_observability.py
│   │   ├── test_smoke_flows.py
│   │   └── __init__.py
│   └── __init__.py
│
├── templates/              # Project-wide HTML templates
│   ├── account/            # Django-allauth templates
│   ├── admin/              # Admin customizations
│   └── emails/             # Email templates
│
├── static/                 # Static assets (CSS, JS, images)
│   ├── css/
│   └── js/
│
├── staticfiles/            # Collected static files (production)
│   ├── admin/
│   ├── js/
│   ├── css/
│   └── ... (third-party)
│
├── media/                  # User-uploaded files
│   ├── cvs/                # CV files uploaded via S3 (local dev)
│   └── templates/
│
├── scripts/                # Custom management scripts
├── docs/                   # Documentation
│   ├── planning/
│   └── reports/
│
├── gsd/                    # GSD task management (agents)
├── .planning/              # Planning documents (auto-generated)
│   └── codebase/
│
├── manage.py               # Django CLI entry point
├── requirements.txt        # Python dependencies
├── runtime.txt             # Python version (3.10)
├── Procfile                # Procfile entry (gunicorn)
├── build.sh                # Build script
├── render.yaml             # Render deployment config
├── .env.example            # Environment template (never commit secrets)
├── README.md               # Project documentation
└── .gitignore              # Git ignore patterns
```

## Directory Purposes

**hrtech/ (Project Config):**
- Purpose: Django project-level configuration and entry points
- Contains: Settings, URL routing, WSGI/ASGI apps, Celery config
- Key files: `settings.py` (postgres, Neo4j, Redis, AWS S3, OpenAI config)

**core/ (Application Logic):**
- Purpose: Main business logic and domain models
- Contains: Models (10 classes), views (50+ functions), services (11 modules)
- Key files:
  - `models.py`: Profile, Candidato, Vaga, AuditoriaMatch, HistoricoAcao, etc.
  - `views.py`: All HTTP handlers (upload, matching, dashboard, pipeline)
  - `matching.py`: Three-layer scoring algorithm
  - `neo4j_connection.py`: Graph database connectivity

**core/services/ (Business Logic):**
- Purpose: Encapsulate business logic, external integrations
- Contains: 11 service modules totaling 1468 lines
- Modules:
  - `s3_service.py`: AWS S3 file operations
  - `email_service.py`: Email rendering and sending (SendGrid)
  - `cv_upload_service.py`: Upload validation and rate limiting
  - `matching_service.py`: Orchestrates matching algorithm execution
  - `pipeline_service.py`: Kanban pipeline state management
  - `candidate_search_service.py`: Dynamic search filter composition
  - `export_service.py`: Excel/CSV export generation
  - `engagement_service.py`: Comments, favorites, engagement tracking
  - `candidate_portal_service.py`: Candidate-facing dashboard context
  - `saved_filter_service.py`: Search filter CRUD

**core/management/ (Admin Commands):**
- Purpose: Django management commands for operations
- Commands:
  - `setup_rh.py`: Initialize demo RH user, 5 sample vagas, 100 test candidatos
  - `testar_matching.py`: Run matching algorithm with fixtures, output rankings

**core/tests/ (Test Suite):**
- Purpose: Unit, integration, and smoke tests
- Coverage: Matching algorithm, CV upload, validations, observability, smoke flows
- Framework: pytest-django or unittest (depends on test file)

**templates/ (HTML Templates):**
- Purpose: Server-rendered HTML (Django template language)
- Subdirectories:
  - `account/`: Login, signup, password reset (from allauth)
  - `admin/`: Admin interface customizations
  - `emails/`: Email templates (CV processed, error, etapa changed)
- Engine: Django Jinja2 with custom filters

**static/ (Frontend Assets):**
- Purpose: CSS, JavaScript, images served in development
- Subdirectories:
  - `css/`: Custom stylesheets
  - `js/`: HTMX integration, dynamic UI interactions
- Collection: `collectstatic` copies to `staticfiles/` for production

## Key File Locations

**Entry Points:**
- `manage.py`: Django CLI (migrations, runserver, management commands)
- `hrtech/wsgi.py`: Production entry point (gunicorn)
- `hrtech/asgi.py`: ASGI entry point (for async support)
- `core/urls.py`: App URL dispatcher (50+ routes)

**Configuration:**
- `hrtech/settings.py`: Main configuration (database, caches, auth, integrations)
- `hrtech/settings_test.py`: Test-specific overrides (in-memory DB, mock services)
- `hrtech/celery.py`: Async task configuration (broker, queues, scheduling)
- `requirements.txt`: Python dependencies (Django, Neo4j, Celery, OpenAI, etc.)

**Core Logic:**
- `core/matching.py`: Intelligent candidate-to-job matching (899 lines)
- `core/neo4j_connection.py`: Graph database driver and connection pooling
- `core/tasks.py`: Celery tasks for async CV processing (pdfplumber → GPT-4o-mini)
- `core/views.py`: HTTP request handlers (1285 lines, split logically by domain)
- `core/models.py`: Domain models (Candidato, Vaga, AuditoriaMatch, etc.)

**Business Logic:**
- `core/services/matching_service.py`: Orchestrates matching algorithm
- `core/services/cv_upload_service.py`: Upload validation, rate limiting, security
- `core/services/pipeline_service.py`: Kanban board state management
- `core/services/candidate_search_service.py`: Filter composition, Queryset building
- `core/services/s3_service.py`: AWS S3 integration (upload, download, delete)
- `core/services/email_service.py`: Email template rendering and sending

**Testing:**
- `core/tests/test_matching_engine.py`: Algorithm correctness tests
- `core/tests/test_backend_validations.py`: Input validation tests
- `core/tests/test_smoke_flows.py`: End-to-end happy path tests

**Security & Middleware:**
- `core/decorators.py`: Auth decorators (@rh_required, @candidato_required)
- `core/middleware.py`: Request ID injection for traceability

## Naming Conventions

**Files:**
- Views: snake_case, descriptive name (e.g., `upload_cv.html`, `dashboard_rh.html`)
- Models: PascalCase, singular (e.g., `Candidato`, `Vaga`, `AuditoriaMatch`)
- Services: PascalCase, ends with `Service` (e.g., `CVUploadService`)
- Tests: `test_*.py` prefix, mirror module name (e.g., `test_matching_engine.py`)
- Migrations: Auto-generated by Django (e.g., `0001_initial.py`)
- Celery tasks: snake_case, ends with `_task` (e.g., `processar_cv_task`)

**Directories:**
- App directory: lowercase (e.g., `core`)
- Package directories: lowercase (e.g., `services`, `management`)
- Template directories: plural or descriptive (e.g., `templates/emails`, `templates/account`)

**Functions/Methods:**
- Views: snake_case, verb-first for actions (e.g., `rodar_matching()`, `upload_cv()`)
- Views: adjective-first for reads (e.g., `buscar_candidatos()`, `listar_comentarios()`)
- Model methods: snake_case (e.g., `__str__()`, property methods use @property)
- Service methods: snake_case, static or classmethod (e.g., `CVUploadService.validate_upload_payload()`)
- Tasks: snake_case, ends with `_task` (e.g., `processar_cv_task()`)

**Variables/Constants:**
- URLs: snake_case with hyphens in paths (e.g., `/rh/candidatos/`, `/minha-area/`)
- Model field names: snake_case (e.g., `status_cv`, `etapa_processo`)
- Choices: UPPER_CASE (e.g., `StatusCV.CONCLUIDO`, `Senioridade.SENIOR`)
- Django settings: UPPER_CASE (e.g., `NEO4J_URI`, `OPENAI_API_KEY`)

## Where to Add New Code

**New Feature (e.g., "Email Candidates"):**
- Primary code: `core/services/email_service.py` (or new `bulk_email_service.py`)
- Views: Add route to `core/urls.py`, implement in `core/views.py`
- Models: Extend existing or create `EmailCampaign` model in `core/models.py`
- Tests: Create `core/tests/test_bulk_email.py`
- Migrations: Auto-generated via `makemigrations`
- Templates: Add to `templates/emails/campaign.html`

**New Component/Module (e.g., "Interview Scheduling"):**
- Implementation: Create `core/services/interview_service.py`
- Register in: `core/services/__init__.py` (add to `__all__`)
- Models: Add `Interview`, `InterviewSlot` to `core/models.py`
- URLs: Add routes to `core/urls.py` with prefix `/rh/interviews/`
- Views: Implement in `core/views.py` or split into separate file
- Async tasks (if needed): Add to `core/tasks.py`
- Tests: Create `core/tests/test_interview_service.py`

**New Async Task (e.g., "Send reminder emails"):**
- Implementation: Add to `core/tasks.py` as `@shared_task` decorated function
- Scheduling: Configure in `hrtech/celery.py` (CELERY_BEAT_SCHEDULE)
- Error handling: Use Celery retry mechanism with exponential backoff
- Logging: Use standard logger with request_id context

**Utilities/Helpers:**
- Shared functions: `core/services/` (prefer service classes over loose functions)
- Model helpers: Add as model methods or static methods
- View utilities: Create `core/utils.py` if needed (currently inline)
- Decorators: Add to `core/decorators.py`

**External Integration:**
- New API client: Create `core/services/new_service.py`
- Environment variables: Add to `.env.example` with documentation
- Configuration: Add to `hrtech/settings.py` with decouple config()
- Testing: Mock in `settings_test.py`, use fixtures or mocks in tests

## Special Directories

**migrations/:**
- Purpose: Django schema version control
- Generated: Yes (by `makemigrations` command)
- Committed: Yes (must be in git for reproducibility)
- Never edit manually (Django manages these)

**staticfiles/:**
- Purpose: Collected static files for production serving
- Generated: Yes (by `collectstatic` command)
- Committed: No (generated from `static/`)
- Contains: Minified CSS/JS, vendor files, manifests

**media/:**
- Purpose: User-uploaded files (CVs, documents)
- Generated: Yes (by upload handlers)
- Committed: No (user data, excluded in .gitignore)
- Production: Stored on AWS S3 (media/ is local dev fallback)

**.planning/codebase/:**
- Purpose: Auto-generated architecture and coding documentation
- Generated: Yes (by GSD tools)
- Committed: Yes (reference documents for development)
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, etc.

**venv/:**
- Purpose: Python virtual environment (dev only)
- Generated: Yes (by `python -m venv venv`)
- Committed: No (excluded in .gitignore)
- Production: Not used (dependencies installed in Docker/Render)

## Request Lifecycle

**HTTP Request → Response:**

1. **WSGI Entry** (`hrtech/wsgi.py`):
   - Django application receives request
   - Middleware stack processes request

2. **Middleware Chain** (in order):
   - `SecurityMiddleware`: HTTPS enforcement, security headers
   - `RequestIDMiddleware`: Generate/inject X-Request-ID
   - `WhiteNoiseMiddleware`: Serve static files
   - `SessionMiddleware`: Load session data
   - `AuthenticationMiddleware`: Load user from session
   - `AllAuthMiddleware`: Social auth state management
   - Others: CSRF, XFrame, etc.

3. **URL Routing** (`hrtech/urls.py` → `core/urls.py`):
   - URL pattern matched (regex or path converter)
   - View function/method retrieved
   - kwargs extracted from URL

4. **View Execution** (`core/views.py`):
   - Authentication check (if decorated with @login_required)
   - Authorization check (if decorated with @rh_required)
   - Request parsing (GET params, POST data, JSON body)
   - Business logic delegation to service layer
   - Context building for template or JSON response

5. **Service Layer** (`core/services/`):
   - Query composition (filter, order, paginate)
   - Data transformation
   - External API calls (Neo4j, S3, OpenAI)
   - Error handling and logging

6. **Data Access** (`core/models.py`):
   - Django ORM translates to SQL
   - PostgreSQL returns results
   - Objects instantiated from rows

7. **Response Building**:
   - Template rendered (if HTML)
   - JSON serialized (if API endpoint)
   - Status code set
   - Headers added (X-Request-ID, etc.)

8. **Response Return**:
   - Middleware post-processing
   - WSGI response object returned
   - HTTP response sent to client

**Async Task Flow:**

1. View calls `processar_cv_task.delay(candidato_id, ...)`
2. Task queued in Redis
3. Celery worker picks up task
4. Task executes: `processar_cv_task(candidato_id, ...)`
5. Updates Candidato status (RECEBIDO → PROCESSANDO → EXTRAINDO → CONCLUIDO)
6. On completion: Email notification sent, Neo4j updated
7. On failure (max retries exceeded): Status set to ERRO, email notification

---

*Structure analysis: 2025-01-10*
