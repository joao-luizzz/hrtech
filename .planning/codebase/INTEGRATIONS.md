# External Integrations

**Analysis Date:** 2024-12-19

## APIs & External Services

### OpenAI - Skill Extraction from CVs

- **Service:** OpenAI GPT-4o-mini
- **What it's used for:** Extract technical and soft skills from CV text
  - Parses unstructured CV text into structured skill objects
  - Assigns proficiency levels (1-5 scale)
  - Infers years of experience per skill
  - Categorizes skills by area (backend, frontend, data, devops)

**Implementation Details:**
- **Client Package:** `openai` 1.3.0 (`requirements.txt` line 21)
- **Client Setup:** `core/tasks.py` lines 50-61
  ```python
  def get_openai_client() -> OpenAI:
      """Retorna cliente OpenAI como singleton."""
      global _openai_client
      if _openai_client is None:
          _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
      return _openai_client
  ```

**Auth & Configuration:**
- Environment variable: `OPENAI_API_KEY` (set in `.env`)
- Configuration location: `hrtech/settings.py` lines 240-245
- Mock mode available: `OPENAI_MOCK_MODE=True` for development (no API calls)

**Task Integration:**
- Celery task: `core.tasks.chamar_openai_task`
- Queue routing: `core.tasks.chamar_openai_task` → `openai` queue
- Rate limiting: 20 requests per minute (configured in `hrtech/settings.py` line 230)
- Retry on error: Up to 5 retries with exponential backoff (`core/tasks.py`)

**Schema & Contract:**
- Pydantic schema: `core/schemas.py` (CVParseado model)
- Mock data fallback: `core/tasks.py` lines 68-97 (MOCK_HABILIDADES_POR_AREA)

---

## Data Storage

### PostgreSQL - Relational Database

- **Type:** PostgreSQL 15+
- **Purpose:** Transactional data (ACID guarantees)
- **What's stored:**
  - Candidatos (candidates)
  - Vagas (job openings)
  - AuditoriaMatch (matching audit logs)
  - Comentarios (comments on candidates)
  - Favoritos (favorites/bookmarks)
  - Profile (user roles and settings)
  - HistoricoAcao (action history for LGPD compliance)

**Connection Configuration:**
- Environment variables (required in `.env`):
  ```
  DB_NAME=hrtech
  DB_USER=postgres
  DB_PASSWORD=<secret>
  DB_HOST=localhost
  DB_PORT=5432
  ```
- Django ORM engine: `django.db.backends.postgresql` (`hrtech/settings.py` line 150)
- Connection pooling: `CONN_MAX_AGE=60` seconds (`hrtech/settings.py` line 157)
- Adapter: `psycopg2-binary` 2.9.9 (`requirements.txt` line 8)

**Models Location:** `core/models.py` (lines 1-650+)
- `Profile` - User roles and preferences
- `Candidato` - Candidate with UUID as PK
- `Vaga` - Job opening with required skills
- `AuditoriaMatch` - Matching audit trail
- `Comentario` - Notes on candidates
- `Favorito` - Bookmarked candidates
- `HistoricoAcao` - Action log for compliance

**Migrations:** `core/migrations/` directory

---

### Neo4j AuraDB - Graph Database

- **Type:** Neo4j graph database (managed cloud)
- **Purpose:** Skill graph and intelligent matching
- **What's stored:**
  - `:Candidato` nodes with UUID matching PostgreSQL
  - `:Skill` nodes (technical and soft skills)
  - `:Vaga` nodes with skill requirements
  - Relationships: `[:TEM_SKILL]`, `[:REQUER_SKILL]`

**Connection Configuration:**
- Environment variables (required in `.env`):
  ```
  NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
  NEO4J_USER=neo4j
  NEO4J_PASSWORD=<secret>
  ```
- Django config: `hrtech/settings.py` lines 168-170
- Driver package: `neo4j` 5.14.0 (`requirements.txt` line 11)

**Connection Management:** `core/neo4j_connection.py`
- Singleton pattern: `get_neo4j_driver()` (line 74)
- Context manager: `Neo4jConnection` class (line 31-71)
- Query wrappers:
  - `run_query()` - Read queries (line 114)
  - `run_write_query()` - Write queries (line 144)
- Connection pooling: max_connection_pool_size=50 (line 46)

**Usage Examples:**
- Matching query: `core/matching.py` - Finds similar candidates via skill graph
- Data sync: `core/tasks.py` - Saves skills to Neo4j after OpenAI processing
- Search: `core/services/candidate_search_service.py`

**Cypher Query Pattern:**
```cypher
MATCH (c:Candidato)-[:TEM_SKILL]->(s:Skill)<-[:REQUER_SKILL]-(v:Vaga)
WHERE v.uuid = $vaga_uuid
RETURN c, COUNT(s) as skills_match, SUM(s.peso) as score
ORDER BY score DESC
```

---

### Redis - Cache & Message Broker

- **Type:** Redis 7.0+ (key-value store)
- **Purpose:** 
  1. Celery broker - task queue
  2. Cache backend - session/rate limit cache

**Connection Configuration:**
- Environment variables (required in `.env` for production):
  ```
  CELERY_BROKER_URL=redis://localhost:6379/0
  CELERY_RESULT_BACKEND=redis://localhost:6379/0
  CACHE_URL=redis://localhost:6379/1
  ```
- Django cache backend: `django.core.cache.backends.redis.RedisCache` (line 203)
- Fallback: LocMemCache for development if Redis unavailable (line 210)
- Default timeout: 300 seconds (5 minutes) (line 206)

**Production Deployment:**
- **Upstash** Redis serverless (free tier available)
- Connection string uses `redis://` or `rediss://` (SSL)

**Celery Broker Configuration:**
- `hrtech/settings.py` lines 192-193
- Task serialization: JSON only (line 219)
- Task timeout: 300 seconds (5 min max), 240 sec soft limit (lines 224-225)

---

## Authentication & Identity

### django-allauth - Authentication System

- **Service:** Local authentication (self-hosted)
- **What it's used for:**
  - User registration with email
  - Email-based login
  - Password reset and recovery
  - Email verification (optional in dev, mandatory in prod)
  - Session management

**Configuration:**
- Package: `django-allauth` 65.0.0 (`requirements.txt` line 32)
- Django settings: `hrtech/settings.py` lines 104-123
  ```python
  ACCOUNT_LOGIN_METHODS = {'email'}
  ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
  ACCOUNT_EMAIL_VERIFICATION = 'optional'  # Dev, 'mandatory' in prod
  ACCOUNT_UNIQUE_EMAIL = True
  ```

**Backends:**
- Django default: `django.contrib.auth.backends.ModelBackend`
- Allauth: `allauth.account.auth_backends.AuthenticationBackend`
- Configured in: `hrtech/settings.py` lines 94-96

**Email Backend:**
- Development: Console output (no SMTP needed)
- Production: SMTP (Gmail or custom)
  - Variables: `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
  - Configured in: `hrtech/settings.py` lines 114-123

**User Roles:** Via `Profile` model
- CANDIDATO - Regular candidate
- RH - Recruiter with admin permissions
- ADMIN - Full system access
- `Profile.is_rh` property for permission checks (line 70)

**Templates:** `templates/account/` directory
- Login, signup, password reset forms
- Email verification templates

**Decorators for Authorization:** `core/decorators.py`
- `@rh_required` - Restrict to RH/admin users
- Used in: `core/views.py` for admin-only endpoints

---

## Webhooks & Callbacks

### Incoming Webhooks

**None detected** - System receives no external webhooks

### Outgoing Event Handlers

**Email Notifications:**
- **Service:** SMTP (Gmail or custom)
- **Templates:** `templates/emails/` directory
  - `cv_processado.html` - CV processed successfully
  - `cv_erro.html` - CV processing error
  - `etapa_alterada.html` - Candidate status changed

**Celery Email Tasks:**
- `core/services/email_service.py`
- Async email sending via Celery (no blocking)
- Used in: CV processing completion, status changes

**Dashboard Notifications:**
- In-app messages via Django messages framework
- No external webhooks

---

## File Storage

### AWS S3 - CV Document Storage

- **Service:** Amazon Web Services S3
- **What it's used for:** Secure storage of candidate CVs (PDFs)
  - Uploads via presigned URLs (temporary access)
  - Downloads via presigned URLs (15-minute TTL)
  - Private bucket - never publicly accessible

**Configuration:**
- Environment variables (required for S3 usage):
  ```
  AWS_ACCESS_KEY_ID=<secret>
  AWS_SECRET_ACCESS_KEY=<secret>
  AWS_STORAGE_BUCKET_NAME=hrtech-cvs
  AWS_S3_REGION_NAME=us-east-1
  AWS_PRESIGNED_URL_TTL=900  # 15 minutes
  ```
- Django settings: `hrtech/settings.py` lines 179-183
- SDK package: `boto3` 1.33.0 (`requirements.txt` line 18)

**Service Implementation:** `core/services/s3_service.py`
- Class: `S3Service` (line 41)
- Methods:
  - `upload_cv(file, candidato_id)` - Upload CV to S3
  - `get_presigned_url(s3_key)` - Generate temporary download URL
  - `delete_cv(s3_key)` - Delete CV (LGPD compliance)

**Security:**
- Bucket is ALWAYS private (line 8 comment)
- Access only via presigned URLs with short TTL (15 min)
- No public URLs ever generated
- LGPD compliant: CVs deleted when candidate is deleted

**Fallback Storage:**
- If S3 not configured: local filesystem
- Detection: `S3Service.enabled` property (line 54)
- Fallback logging: `logger.warning("S3 não configurado - usando storage local")`

**File Organization in S3:**
- Path pattern: `{candidato_uuid}/{filename}`
- Keeps files organized by candidate
- UUID ensures uniqueness across systems

---

## PDF Processing & OCR

### pdfplumber - PDF Text Extraction

- **Package:** `pdfplumber` 0.10.3 (`requirements.txt` line 24)
- **Purpose:** Extract text from PDF files
- **Used in:** `core/tasks.py` (line 37)
- **Task:** `processar_cv_task` extracts text before OpenAI processing

**Implementation:**
```python
import pdfplumber
# Used in CV processing pipeline to extract raw text from PDF
```

**Limitations:**
- Works best with text-based PDFs
- For scanned/image-based CVs, falls back to OCR

### pytesseract - OCR for Scanned Documents

- **Package:** `pytesseract` 0.3.10 (`requirements.txt` line 25)
- **Purpose:** Extract text from image-based/scanned CVs
- **Used in:** CV processing pipeline (fallback)
- **External dependency:** Tesseract binary (must be installed separately)

**Requirements:**
- Linux: `apt-get install tesseract-ocr`
- Mac: `brew install tesseract`
- Windows: Download installer from GitHub

---

## Monitoring & Observability

### Application Logging

- **Framework:** Python `logging` module
- **Configuration:** `hrtech/settings.py` lines 323-330
- **Log levels:**
  - DEBUG - Development tracing
  - INFO - Application events
  - WARNING - Potentially problematic
  - ERROR - Error conditions
  - CRITICAL - Critical errors

**LGPD Compliance:**
- PII (Personal Identifiable Information) NEVER logged
- Comment in `core/tasks.py` lines 13-15:
  ```
  REGRAS DE SEGURANÇA (LGPD):
  - NUNCA logar conteúdo de CVs (texto ou bytes)
  - Mascarar CPF, RG, datas ANTES de enviar para OpenAI
  ```

**Loggers:**
- Used across: `core/neo4j_connection.py`, `core/tasks.py`, `core/services/s3_service.py`
- Request tracking: `core/decorators.py` provides request ID middleware

### Error Handling in Celery Tasks

- **Retry mechanism:** `core/tasks.py`
- **Exception types handled:**
  - `RateLimitError` (OpenAI) - Retry with backoff
  - `APIConnectionError` (OpenAI) - Network retry
  - `APITimeoutError` (OpenAI) - Timeout retry
  - `MaxRetriesExceededError` (Celery) - Mark as failed
  - General exceptions - Log and mark as error

---

## CI/CD & Deployment

### Hosting Platform

**Render.com** - PaaS (Platform as a Service)
- Web Service - Django/Gunicorn application
- PostgreSQL add-on - Managed relational database
- Background workers - Celery workers (2 types)
- Scheduler - Celery Beat for periodic tasks

**Configuration Files:**
- `render.yaml` - Deployment blueprint (3 services)
- `Procfile` - Process types for Render/Heroku compatibility

**Build Command:**
```bash
pip install -r requirements.txt && \
  python manage.py collectstatic --noinput && \
  python manage.py migrate
```

**Start Commands:**
- Web: `gunicorn hrtech.wsgi --bind 0.0.0.0:$PORT --workers 2`
- Worker: `celery -A hrtech worker -l INFO -Q default,openai`
- Beat: `celery -A hrtech beat -l INFO`

### Environment Configuration on Render

**Required Environment Variables:**
- Django: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `X_FRAME_OPTIONS`
- Database: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- Neo4j: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- Redis/Celery: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- OpenAI: `OPENAI_API_KEY`
- AWS (optional): `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- Email (optional): `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`

**Related Services Used:**
1. **Upstash** - Serverless Redis (for Celery broker)
2. **Neo4j AuraDB** - Managed graph database
3. **AWS S3** - File storage (optional)
4. **Gmail/SMTP** - Email delivery (optional)

---

## Secrets Management

**Approach:**
- `python-decouple` 3.8 loads from `.env` file
- Never hardcoded in source code
- `.env` file NOT committed to git (in `.gitignore`)
- `.env.example` provides template for setup

**Configuration Loading:**
```python
from decouple import config, Csv
SECRET_KEY = config('SECRET_KEY')  # Raises error if not in .env
DEBUG = config('DEBUG', default=False, cast=bool)
```

**Location:** `hrtech/settings.py` (lines 18-34)

**Critical Secrets Required:**
- Django: `SECRET_KEY`
- Database: `DB_PASSWORD`
- Neo4j: `NEO4J_PASSWORD`
- OpenAI: `OPENAI_API_KEY`
- AWS: `AWS_SECRET_ACCESS_KEY`
- Email: `EMAIL_HOST_PASSWORD`

---

## Integration Data Flow Examples

### CV Upload & Processing Pipeline

```
1. User uploads PDF (view: core/views.py upload_candidato)
   ↓
2. File stored in S3 (S3Service.upload_cv)
   ↓
3. Celery task queued: processar_cv_task
   ↓
4. pdfplumber extracts text from PDF
   ↓
5. OpenAI (GPT-4o-mini) parses skills from text
   ↓
6. Skills saved to:
   - PostgreSQL (core/models.py - Candidato.skills_json)
   - Neo4j (Neo4j nodes and relationships)
   ↓
7. Email notification sent (async via Celery)
```

### Matching Algorithm

```
1. User selects a Vaga (job opening)
   ↓
2. MatchingService queries Neo4j graph:
   - Find all Candidatos with matching skills
   - Calculate compatibility score via graph traversal
   - Order by score (relevance)
   ↓
3. Results cached in Redis (15 min TTL)
   ↓
4. AuditoriaMatch logged to PostgreSQL
```

### Dashboard Analytics

```
1. User loads dashboard (core/views.py dashboard_rh)
   ↓
2. Query metrics from PostgreSQL:
   - Total candidates, vagas
   - Matching statistics
   ↓
3. Render charts via Chart.js (frontend)
   ↓
4. Data cached in Redis for performance
```

---

*Integration audit: 2024-12-19*
