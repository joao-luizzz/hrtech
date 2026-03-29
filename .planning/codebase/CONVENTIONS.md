# Coding Conventions

**Analysis Date:** 2024-12-19

## Naming Patterns

### Files

**Python module files:**
- `snake_case` for all Python files
- Examples: `models.py`, `views.py`, `tasks.py`, `candidate_search_service.py`, `test_matching_engine.py`

**Service classes:**
- `snake_case` filenames containing service class (e.g., `candidate_search_service.py` contains `CandidateSearchService`)

**Test files:**
- `test_*.py` prefix pattern (Django TestCase standard)
- Organized in `core/tests/` directory
- Examples: `test_matching_engine.py`, `test_backend_validations.py`, `test_pipeline_mock.py`

### Classes

**PascalCase naming:**
- Model classes: `Profile`, `Candidato`, `Vaga`, `AuditoriaMatch`, `HistoricoAcao`
- Service classes: `CandidateSearchService`, `CVUploadService`, `MatchingService`, `PipelineService`
- Exception/Error classes: Standard Django patterns
- TestCase classes: `UploadBackendValidationTests`, `MatchingEngineTests`, `PipelineMockTests`

**Inner/Enum classes:**
- Use PascalCase with explicit purpose
- Examples from models (`core/models.py`):
  - `Profile.Role` - enum with choices CANDIDATO, RH, ADMIN
  - `Candidato.Senioridade` - enum with JUNIOR, PLENO, SENIOR
  - `Candidato.StatusCV` - enum with PENDENTE, RECEBIDO, PROCESSANDO, EXTRAINDO, CONCLUIDO, ERRO
  - `Candidato.EtapaProcesso` - enum with process stages

### Functions and Methods

**snake_case naming:**
- All function and method names use snake_case
- Examples: `executar_matching()`, `_buscar_candidatos_neo4j()`, `_calcular_scores()`, `apply_filters()`

**Private methods/functions:**
- Prefix with single underscore: `_user_can_access_candidate()`, `_parse_skills_payload()`
- Used internally within module but may be imported elsewhere

**Constants:**
- UPPER_SNAKE_CASE for module-level constants
- Examples: `MAX_SKILLS_PER_VAGA_LIST = 50`, `MAX_SKILL_NAME_LENGTH = 100`, `SCORE_MINIMO = 40.0`
- Algorithm constants: `PESO_CAMADA_1`, `PESO_CAMADA_2`, `PESO_CAMADA_3`, `FATOR_DECAIMENTO`

### Variables

**snake_case for all variables:**
- Local variables: `candidato_id`, `vaga_id`, `status_cv`, `anos_experiencia`
- Parameter names: `candidato`, `vaga`, `request`, `user`
- In Portuguese: project uses Portuguese naming extensively (domain language)
  - Examples: `disponivel`, `senioridade`, `habilidades`, `skills_obrigatorias`

**Abbreviations:**
- Avoid single-letter variables except in loops (`for i in range()`)
- Use meaningful prefixes for related variables:
  - Mock objects: `mock_candidato`, `vaga_mock`, `candidato_perfeito`
  - Dictionary keys: `candidato_id`, `candidato_nome`, `candidato_senioridade`

### Types and Models

**Django Model field naming:**
- Use snake_case: `status_cv`, `etapa_processo`, `anos_experiencia`, `senioridade_desejada`
- Use underscores for compound concepts: `cv_s3_key`, `ano_ultima_utilizacao`
- Related fields: `user`, `candidato` (related_name also snake_case)

**Dataclass and Pydantic fields:**
- snake_case field names aligned with model conventions
- Examples from `core/schemas.py` (implied from code): `area_atuacao`, `senioridade_inferida`, `anos_experiencia`

## Code Style

### Formatting

**Line length:**
- No explicit linter found, but code suggests flexible approach
- Functions in `core/views.py` are 1285 lines; large files use logical sections
- Docstrings and complex logic broken into readable chunks

**Indentation:**
- 4 spaces (Python standard)

**Blank lines:**
- Double blank lines between top-level classes and functions
- Single blank lines between methods
- Sections within files separated by comments with equals signs

**Comments and section markers:**
- Module header comments with title, purpose, and architecture notes
- Section markers: `# =============================================================================`
- Inline comments for non-obvious logic

### Linting

**No explicit linting configuration found** (no `.pylintrc`, `.flake8`, or similar in root)

**Code follows implicit style:**
- Clean imports organization
- Consistent naming patterns across modules
- Descriptive variable names

## Import Organization

### Order in imports

1. Standard library imports (`import os`, `import json`, `import logging`, `from datetime import ...`)
2. Third-party imports (`from django...`, `from celery...`, `from pydantic...`)
3. Local imports (`from core.models import ...`, `from core.services import ...`)

**Example from `core/views.py`:**
```python
# Standard library
import json
import logging
from decimal import Decimal

# Django
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse, HttpResponseForbidden, StreamingHttpResponse
from django.db.models import Count, Avg, Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.urls import reverse

# Local
from core.models import (
    Candidato, Vaga, AuditoriaMatch, HistoricoAcao, registrar_acao,
    Comentario, Favorito, Profile
)
from core.tasks import processar_cv_task
from core.neo4j_connection import run_query
from core.decorators import rh_required, get_client_ip, get_request_id
from core.services import (
    CVUploadService,
    get_s3_service,
    MatchingService,
    PipelineService,
    CandidateSearchService,
    ExportService,
    EngagementService,
    SavedFilterService,
    CandidatePortalService,
)
```

### Path aliases

**No alias imports detected** - all imports use full relative paths from `core/` or absolute imports from `django`, `celery`, etc.

### Local imports organization

- Group related imports together: all `core.models` imports, all `core.services` imports
- Multi-line imports use parentheses for readability
- Import specific items rather than modules when possible

## Error Handling

### Exception handling patterns

**Try-except with logging:**
- Always log exceptions using `logger.exception()` or `logger.error()`
- Example from `core/views.py`:
```python
try:
    # operation
except Exception as e:
    logger.exception("Falha no upload do CV para storage remoto")
    # Return error response or re-raise
```

**Specific exception types:**
- Catch specific exceptions when possible: `except json.JSONDecodeError:`, `except ValueError as exc:`
- Generic `except Exception` used for broad error handling with logging

**HTTP error responses:**
- Return `HttpResponseForbidden`, `JsonResponse` with status codes
- Status codes used: 200 (success), 400 (validation), 401 (auth), 429 (rate limit), 500 (server error)
- Example: `return JsonResponse({'error': 'message'}, status=401)`

**Celery task error handling:**
- Use `MaxRetriesExceededError` from celery.exceptions
- Transient vs permanent errors: retry with backoff for transient, log and move on for permanent
- Example from `core/tasks.py`: catch `RateLimitError`, `APIConnectionError`, `APITimeoutError` separately from `APIError`

### Validation patterns

**Pydantic validation:**
- Use `pydantic.ValidationError` for structured data validation
- Example: `CVParseado` schema validates JSON from OpenAI
- Catch `ValidationError` and report field-level errors to user

**Custom validators:**
- Django model validators: `MinValueValidator`, `MaxValueValidator` on integer fields
- Helper functions for complex validation: `_parse_skills_payload()` returns `(parsed, errors)`
- Return tuples of `(valid_data, error_list)` for multi-field validation

## Logging

### Framework

**Standard Python logging module:**
- Logger creation: `logger = logging.getLogger(__name__)` in each module
- Configured via `LOGGING` dict in `hrtech/settings.py`

### Patterns

**When to log:**
- Entry/exit of long-running tasks: `logger.info(f"Iniciando extração de texto do CV")`
- Important state transitions: `logger.info(f"CV recebido para candidato {candidato.id}")`
- Warnings for recoverable issues: `logger.warning("PDF protegido por senha detectado")`
- Errors for failures: `logger.error(f"Candidato {candidato_id} não encontrado")`
- Full exception details: `logger.exception("...")` for caught exceptions

**Log levels used:**
- `DEBUG`: Detailed information for debugging (when `DEBUG=True` in settings)
- `INFO`: Confirmation that things are working as expected
- `WARNING`: Something unexpected happened or will happen (fallback OCR, retry)
- `ERROR`: Serious problem, feature not working (max retries, file not found)

**LGPD compliance:**
- **NEVER log CV text content or personal data**
- Mask sensitive information before logging: CPF, RG, dates
- Log only: candidate ID (first 8 chars), status, error types
- Example from `core/tasks.py`: `logger.info(f"[Task {self.request.id}] Processando CV candidato={candidato_id[:8]}...")`

**Example from code:**
```python
logger.info(f"[MOCK MODE] Gerando CV parseado: area={area}, senioridade={senioridade}")
logger.warning("PDF protegido por senha detectado")
logger.error(f"Erro na extração: {e}")
logger.warning("Falha ao reagendar retry de processamento")
```

## Comments

### When to comment

**Module docstrings (required):**
- Every `.py` file starts with triple-quoted docstring
- Include: title, purpose, architecture decisions, usage examples
- Example from `core/models.py`:
```python
"""
HRTech - Models
===============

Arquitetura de Persistência Poliglota:
- Este arquivo define os models PostgreSQL (dados transacionais)
- Neo4j armazena o grafo de habilidades (ver core/neo4j_connection.py)
- UUID é a chave de sincronia entre os dois bancos

Decisões Arquiteturais Importantes:
1. UUID como PK em Candidato - mesmo valor usado no Neo4j
2. SET_NULL em AuditoriaMatch - preserva histórico mesmo após deleção (LGPD)
3. JSONField para skills - flexibilidade sem normalização excessiva
...
"""
```

**Class docstrings:**
- Use triple-quoted docstrings for classes
- Include: purpose, roles/behaviors, usage notes
- Example from `core/models.py`:
```python
class Profile(models.Model):
    """
    Perfil estendido do usuário com role e configurações.

    Roles:
    - candidato: Pode ver próprio perfil e matches
    - rh: Pode gerenciar vagas, ver todos candidatos, rodar matching
    - admin: Acesso total (superuser)
    """
```

**Method/Function docstrings:**
- Use triple-quoted docstrings for important methods
- Include: what it does, parameters, return value
- Example from `core/decorators.py`:
```python
def rh_required(view_func):
    """
    Decorator que exige que o usuário seja RH ou Admin.

    Deve ser usado APÓS @login_required:
        @login_required
        @rh_required
        def view(request):
            ...
    """
```

**Inline comments:**
- For non-obvious algorithmic decisions
- For important business rules
- Example: `# Superuser tem acesso total`, `# Verifica se tem profile e se é RH`

**Avoid comments for:**
- Obvious code: don't comment `x = x + 1`
- Outdated decisions: update code instead

### JSDoc/Docstring style

**No JSDoc used** (Python project, not JavaScript)

**Python docstrings:**
- Triple-quoted strings (""" or ''')
- First line is summary
- Blank line, then detailed description
- Lists of items use markdown-style bullets
- Code examples in triple backticks

**Architecture decision comments:**
- Comments within docstrings explain WHY
- Example from `core/matching.py`:
```python
# Decisões Arquiteturais:
# 1. Query Cypher única vs múltiplas queries
#    DECISÃO: Query única com OPTIONAL MATCH
#    RAZÃO: Reduz roundtrips ao Neo4j, melhor performance
```

## Function Design

### Size and scope

**No strict limit** but functions are kept focused:
- Views in `core/views.py`: range from ~20 lines (e.g., `home()`) to ~150 lines (e.g., `detalhe_candidato_match()`)
- Service methods: 20-80 lines
- Helper functions: < 30 lines

**Multi-step operations:**
- Broken into multiple functions with clear names
- Example: `processar_cv_task()` calls `_extrair_texto()`, `limpar_dados_pessoais()`, `chamar_openai_extracao()`, `salvar_habilidades_neo4j()`

### Parameters

**Positional parameters:**
- Limited to essential data (request, object IDs, required data)
- Example: `def rodar_matching(request, vaga_id):`

**Keyword parameters:**
- Used for optional filters and configuration
- Example: `CandidateSearchService.apply_filters(query_params: dict, request_id: str = 'n/a')`

**Default values:**
- Used for optional parameters with sensible defaults
- Example from matching: `MatchingEngine(score_minimo: float = SCORE_MINIMO)`

**Type hints:**
- Used selectively in function signatures
- Example from `core/decorators.py`: `def get_client_ip(request) -> str:`
- Example from `core/models.py`: fields have type hints in dataclasses

### Return values

**Single return values:**
- Functions return single objects or primitives
- Example: `get_client_ip()` returns string IP address

**Tuple returns for multiple values:**
- Used when function can fail or return alternative types
- Example: `_parse_skills_payload()` returns `(parsed: list, errors: list)`
- Error handling pattern: `(data, error_message)` tuples

**Dictionary returns:**
- Used for complex structured responses
- Example: `PipelineService.build_pipeline_data()` returns dict with keys: `vaga`, `pipeline`, `total`, `etapas`

**Query results:**
- Return Django QuerySets for model queries (allows chaining)
- Example: `Candidato.objects.filter(...).order_by(...)`

## Module Design

### Exports

**Explicit exports in `__init__.py`:**
- Example from `core/services/__init__.py`:
```python
from .s3_service import S3Service, get_s3_service
from .email_service import EmailService, get_email_service
from .cv_upload_service import CVUploadService
# ... more imports ...

__all__ = [
    'S3Service',
    'get_s3_service',
    'EmailService',
    'get_email_service',
    'CVUploadService',
    # ...
]
```

**Pattern:**
- Import from submodules, re-export in `__all__`
- Allows `from core.services import CVUploadService` instead of `from core.services.cv_upload_service import CVUploadService`

### Barrel files

**Used for service layer:**
- `core/services/__init__.py` is a barrel file
- Collects all service classes and factory functions
- Enables cleaner imports throughout the application

**Not used for:**
- Models (import directly: `from core.models import Candidato`)
- Views (import directly: `from core.views import ...`)
- Tests (import directly: `from core.tests.test_* import TestCase`)

### Module organization patterns

**Coherence by feature/responsibility:**
- `core/services/`: All business logic layer (one service per file)
- `core/tests/`: All tests grouped together
- `core/management/commands/`: Django management commands
- Top-level files in `core/`: Core abstractions (models, views, tasks, matching engine)

**Dependency direction:**
- Views → Services → Models
- Services → External APIs (S3, OpenAI, Neo4j)
- Tests → Everything (with mocks)

---

*Convention analysis: 2024-12-19*
