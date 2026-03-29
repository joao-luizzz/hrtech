# Technology Stack

**Analysis Date:** 2024-12-19

## Languages

**Primary:**
- **Python** 3.10.12 - Backend server, Celery workers, scripting
  - Defined in: `runtime.txt`
  - Used across: `hrtech/`, `core/`, `scripts/`

**Secondary:**
- **HTML/CSS/JavaScript** - Frontend, templates, interactive UI
  - Bootstrap 5.3.2 for CSS framework
  - HTMX 1.9 for interactive components without heavy JS
  - Vanilla JavaScript for dark mode, CSRF handling
  - Chart.js for data visualization

## Runtime & Package Manager

**Environment:**
- **Python 3.10.12** (specified in `runtime.txt`)
- **pip** for package management

**Lockfile:**
- `requirements.txt` present with pinned versions
- All dependencies frozen to specific versions (e.g., Django>=5.0,<6.0)

## Frameworks

**Core:**
- **Django** 5.0 - Full-stack web framework
  - Defined in: `requirements.txt` line 2
  - Used in: `hrtech/settings.py`, `hrtech/urls.py`, `hrtech/wsgi.py`
  - Admin customization: `templates/admin/`, `core/admin.py`
  - Template engine: Django templates (server-side rendering)

**Authentication & Authorization:**
- **django-allauth** 65.0.0 - Complete authentication system
  - Defined in: `requirements.txt` line 32
  - Used in: `hrtech/settings.py` lines 68-70, 94-96
  - Provides: signup, login, password reset, email verification
  - Templates: `templates/account/`

**Admin Interface:**
- **django-admin-interface** 0.32.0 - Styled admin panel
  - Defined in: `requirements.txt` line 36
  - Configuration: `hrtech/settings.py` line 57
  - Templates: `templates/admin/base_site.html`

**Testing:**
- Django built-in TestCase framework
  - Test files: `core/tests/test_*.py`
  - Run with: `python manage.py test`

**Build/Dev:**
- **Gunicorn** 21.x - WSGI application server
  - Defined in: `requirements.txt` line 3
  - Used in production via `Procfile`, `render.yaml`

- **WhiteNoise** 6.6.0 - Static files serving in production
  - Defined in: `requirements.txt` line 4
  - Configured in: `hrtech/settings.py` line 81

## Key Dependencies

### Critical Infrastructure

- **psycopg2-binary** 2.9.9 - PostgreSQL adapter
  - `requirements.txt` line 8
  - Used in: `hrtech/settings.py` line 150 (Django database engine)

- **neo4j** 5.14.0 - Neo4j graph database driver
  - `requirements.txt` line 11
  - Used in: `core/neo4j_connection.py` (lines 22, 85)
  - Import: `from neo4j import GraphDatabase`

- **celery** 5.3.4 - Task queue for async processing
  - `requirements.txt` line 14
  - Configured in: `hrtech/celery.py`
  - Used in: `core/tasks.py` (async CV processing)
  - Decorators: `@shared_task`, `@celery_app.task`

- **redis** 5.0.1 - In-memory data store
  - `requirements.txt` line 15
  - Used for: Celery broker, cache backend
  - Configuration: `hrtech/settings.py` lines 192-216

### External APIs & Services

- **openai** 1.3.0 - OpenAI API client
  - `requirements.txt` line 21
  - Used in: `core/tasks.py` (lines 34, 56-61)
  - Purpose: Extract skills from CVs using GPT-4o-mini
  - Configuration: `hrtech/settings.py` lines 240-245

- **boto3** 1.33.0 - AWS SDK
  - `requirements.txt` line 18
  - Used in: `core/services/s3_service.py` (lines 34-35)
  - Purpose: Upload/download CVs to S3
  - Import: `from botocore.exceptions import ClientError`

### Data Processing

- **pdfplumber** 0.10.3 - PDF text extraction
  - `requirements.txt` line 24
  - Used in: `core/tasks.py` (line 37)
  - Purpose: Extract text from PDF CVs before OpenAI processing

- **pytesseract** 0.3.10 - OCR for scanned documents
  - `requirements.txt` line 25
  - Purpose: Extract text from image-based CVs

- **openpyxl** 3.1.2 - Excel file handling
  - `requirements.txt` line 35
  - Used in: `core/services/export_service.py`
  - Purpose: Export candidate/matching data to Excel

### Validation & Security

- **pydantic** 2.5.0 - Data validation with Python type hints
  - `requirements.txt` line 28
  - Used in: `core/schemas.py` (CV parsing contracts)
  - Classes: `CVParseado`, `SCHEMA_INSTRUCOES`

- **cryptography** 46.0.6 - Cryptographic recipes
  - `requirements.txt` line 29
  - Used for: Secure credential handling

- **python-decouple** 3.8 - Environment variable management
  - `requirements.txt` line 5
  - Used in: `hrtech/settings.py` (config function)
  - Purpose: Load `.env` variables securely

## Configuration Files

**Environment:**
- `.env` - Runtime configuration (contains secrets, not committed)
  - Template: `.env.example` (guide for setup)
  - Used with: `python-decouple.config()`
  - Variables: `SECRET_KEY`, `DB_*`, `NEO4J_*`, `OPENAI_API_KEY`, `AWS_*`, `CELERY_*`

**Django:**
- `hrtech/settings.py` - Main configuration (lines 1-330+)
  - Installed apps: line 55-73
  - Middleware: line 78-89
  - Database config: line 148-162
  - Cache config: line 200-216
  - Celery config: line 192-235
  - Security settings: line 30-50

**Celery:**
- `hrtech/celery.py` - Celery app configuration
  - Task queues: line 54-61
  - Beat scheduler: line 84-90
  - Task routing: line 64-66

**Build:**
- `Procfile` - Heroku/Render process types
  - `web`, `worker`, `beat` services
- `render.yaml` - Render deployment blueprint
  - 3 services: web, worker, beat
- `runtime.txt` - Python version specification

## Platform Requirements

**Development:**
- Python 3.10+
- PostgreSQL 15+ (local dev)
- Redis 7+ (local dev)
- Neo4j AuraDB account (free tier available)
- OpenAI API key (optional, mock mode available)

**Production:**
- **Render.com** - PaaS hosting
  - Web Service for Django app
  - PostgreSQL add-on
- **Upstash** - Serverless Redis
  - For Celery broker in production
- **Neo4j AuraDB** - Managed graph database
  - Cloud Neo4j instance
- **AWS S3** (optional) - For CV storage
  - Private bucket with presigned URLs

## Version Constraints

From `requirements.txt`:

```
Django>=5.0,<6.0              # Major version 5 only
celery>=5.3.4                  # At least 5.3.4
redis>=5.0.1                   # Major version 5+
neo4j>=5.14.0                  # At least 5.14.0
openai>=1.3.0                  # At least 1.3.0
boto3>=1.33.0                  # At least 1.33.0
pydantic>=2.5.0                # Major version 2
cryptography>=46.0.6           # At least 46.0.6
django-allauth>=65.0.0         # At least 65.0.0
openpyxl>=3.1.2                # At least 3.1.2
```

## Key Technology Decisions

1. **Polyglot Persistence**: PostgreSQL (ACID) + Neo4j (graphs) + Redis (cache/broker)
   - Rationale: Different data types require different storage optimizations
   - PostgreSQL for relational data: Candidato, Vaga, AuditoriaMatch
   - Neo4j for skill graphs: Matching algorithms via graph traversal
   - Redis for async queue broker: Celery task queue

2. **Django as Full Stack**: Server-side rendering with templates + HTMX
   - Rationale: Simpler deployment, no separate frontend build
   - Uses `WhiteNoise` to serve statics without CDN
   - HTMX for interactivity without heavy JavaScript bundles

3. **Celery for Async Processing**: CV processing in background workers
   - Rationale: PDF parsing and OpenAI calls are slow (>3s)
   - Task routing: Separate queue for OpenAI with rate limiting (20 req/min)
   - Configuration: `hrtech/celery.py` lines 64-66, `hrtech/settings.py` lines 228-232

4. **OpenAI for Skill Extraction**: GPT-4o-mini for parsing CVs
   - Rationale: LLMs understand context better than keyword matching
   - Mock mode available: `OPENAI_MOCK_MODE=True` for free development
   - Configuration: `hrtech/settings.py` lines 240-245

5. **AWS S3 with Presigned URLs**: Secure CV storage
   - Rationale: LGPD compliance - CVs contain sensitive personal data
   - Never public: Bucket is private, access only via presigned URLs (15min TTL)
   - Configuration: `hrtech/settings.py` lines 179-183
   - Implementation: `core/services/s3_service.py`

6. **UUID as Cross-Database Key**: Sync between PostgreSQL and Neo4j
   - Rationale: Unique identifier maintained across multiple databases
   - Used in: `core/models.py` line 91 (Candidato), `core/neo4j_connection.py`

---

*Stack analysis: 2024-12-19*
