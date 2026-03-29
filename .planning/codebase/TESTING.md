# Testing Patterns

**Analysis Date:** 2024-12-19

## Test Framework

### Runner

**Django TestCase (built-in):**
- Framework: Django test framework (included with Django 5.0)
- Config: Settings via `hrtech/settings.py` (Django TEST configuration)
- Run command: `python manage.py test core` or `python manage.py test core.tests.test_matching_engine`

**Test discovery:**
- Automatic discovery of `test_*.py` files in `core/tests/` directory
- TestCase classes extend `django.test.TestCase` or `django.test.TransactionTestCase`

### Assertion Library

**Django assertions:**
- Built-in `TestCase.assertEqual()`, `assertContains()`, `assertIn()`, `assertNotIn()`
- HTTP-specific: `assertEqual(response.status_code, 200)`, `assertContains(response, 'text')`
- No external assertion library used (using Python/Django native assertions)

### Run Commands

```bash
# Run all core tests
python manage.py test core

# Run specific test file
python manage.py test core.tests.test_matching_engine

# Run specific test class
python manage.py test core.tests.test_matching_engine.MatchingEngineTests

# Run specific test method
python manage.py test core.tests.test_matching_engine.MatchingEngineTests.test_camada_1_match_perfeito

# Watch/continuous mode - Not configured (Django doesn't have built-in watch mode)
# Would require pytest-watch or similar if needed

# Coverage - Not configured (no coverage tool detected in requirements)
# Can be added with: coverage run --source='.' manage.py test core
```

## Test File Organization

### Location

**Test directory structure:**
- All tests in: `core/tests/`
- Subdirectory of main app module
- Separate from source code but in same package

### File Listing

```
core/tests/
├── __init__.py (empty)
├── test_backend_validations.py    (365 lines)
├── test_dashboard_observability.py (64 lines)
├── test_matching_engine.py        (657 lines)
├── test_pipeline_mock.py          (867 lines)
└── test_smoke_flows.py            (306 lines)
```

**Total test code: 2,259 lines**

### Naming

**File pattern:** `test_*.py` prefix (Django convention)
- Corresponds to feature/module being tested
- Examples:
  - `test_matching_engine.py`: Tests for matching algorithm in `core/matching.py`
  - `test_backend_validations.py`: Tests for input validation in `core/views.py`
  - `test_pipeline_mock.py`: Tests for CV processing pipeline with mocks
  - `test_smoke_flows.py`: Integration smoke tests
  - `test_dashboard_observability.py`: Dashboard metrics tests

**Test class naming:** `[Feature]Tests` pattern (PascalCase with Tests suffix)
- Examples:
  - `MatchingEngineTests` (in `test_matching_engine.py`)
  - `UploadBackendValidationTests` (in `test_backend_validations.py`)
  - `PipelineMockTests` (in `test_pipeline_mock.py`)
  - `QueueConfigSmokeTests` (in `test_smoke_flows.py`)

**Test method naming:** `test_[scenario]` pattern
- Descriptive names explaining what's being tested
- Examples:
  - `test_camada_1_match_perfeito`: Layer 1 perfect match scenario
  - `test_upload_rejeita_email_invalido`: Upload rejects invalid email
  - `test_camada_1_decaimento_temporal`: Layer 1 temporal decay
  - `test_score_final_candidato_perfeito`: Final score for perfect candidate

### Structure

```
core/tests/
└── Test files for:
    - Matching algorithm (layers, scoring, ordering)
    - Input validation (email, PDF, name length, rate limits)
    - Pipeline processing (OpenAI mocking, status transitions)
    - Dashboard observability (ghost jobs, error counts)
    - Integration flows (upload → polling → completion)
```

## Test Structure

### Suite Organization

**Test class structure with setUp:**
```python
class MatchingEngineTests(TestCase):
    """
    Testes unitários do MatchingEngine.

    Organização:
    - test_camada_1_*: Testes do match direto de skills
    - test_camada_2_*: Testes do match por similaridade
    - test_camada_3_*: Testes de compatibilidade de perfil
    - test_score_final_*: Testes do cálculo integrado
    - test_gap_*: Testes da análise de gaps
    - test_ordenacao_*: Testes de ordenação e desempate
    """

    def setUp(self):
        """Fixtures comuns para os testes."""
        self.engine = MatchingEngine(score_minimo=40.0)
        
        # Mock objects with inline fixtures
        self.vaga_mock = MagicMock()
        self.vaga_mock.id = 1
        self.vaga_mock.titulo = "Analista de Dados Pleno"
        # ... more setup
```

**Patterns:**
- Each TestCase class groups related tests for a feature
- `setUp()` method (lowercase, not `setUpClass()`) called before each test
- Fixtures created inline in setUp or as class constants
- Tests are isolated (no shared state between tests)

### Setup and Teardown

**Method-level setUp (most common):**
```python
def setUp(self):
    """Fixtures comuns para os testes."""
    self.engine = MatchingEngine(score_minimo=40.0)
    cache.clear()  # Clear cache before each test
```

**Class-level setUpClass (for expensive operations):**
```python
@classmethod
def setUpClass(cls):
    super().setUpClass()
    cls.temp_media = tempfile.mkdtemp(prefix='hrtech-test-media-')

@classmethod
def tearDownClass(cls):
    shutil.rmtree(cls.temp_media, ignore_errors=True)
    super().tearDownClass()
```

**Used for:**
- `setUp()`: Create test data, initialize mocks, clear caches
- `tearDownClass()`: Clean up temporary files, directories (see `test_smoke_flows.py`)

### Assertion Patterns

**HTTP assertions:**
```python
self.assertEqual(response.status_code, 200)
self.assertEqual(response.status_code, 400)
self.assertEqual(response.status_code, 429)
self.assertContains(response, 'Expected text', status_code=400)
self.assertNotIn('token=', html)
```

**Model/data assertions:**
```python
candidato = Candidato.objects.get(email='smoke-upload@example.com')
self.assertEqual(candidato.status_cv, Candidato.StatusCV.RECEBIDO)
self.assertEqual(response.context['stats']['jobs_fantasmas'], 1)
self.assertIn('Saude Operacional do Pipeline', response.content.decode())
```

**Mock call assertions:**
```python
mock_delay.assert_called_once_with(str(candidato.id))
mock_candidato.objects.get.return_value = MagicMock(disponivel=True)
```

## Mocking

### Framework

**unittest.mock module:**
- `patch()` decorator for patching dependencies
- `MagicMock()` for creating mock objects
- `PropertyMock()` for mocking properties

**Import pattern:**
```python
from unittest.mock import patch, MagicMock, PropertyMock
```

### Patterns

**Example 1: Mock external service (Neo4j in matching tests)**
```python
class MatchingEngineTests(TestCase):
    def setUp(self):
        self.engine = MatchingEngine(score_minimo=40.0)
        
        # Create mock vaga
        self.vaga_mock = MagicMock()
        self.vaga_mock.id = 1
        self.vaga_mock.titulo = "Analista de Dados Pleno"
        self.vaga_mock.skills_obrigatorias = [
            {'nome': 'SQL', 'nivel_minimo': 3},
        ]
        
        # Create mock candidato with complete fixture
        self.candidato_perfeito = {
            'candidato_id': 'uuid-123',
            'candidato_nome': 'João Silva',
            'skills': [
                {'nome': 'SQL', 'nivel': 4, 'anos_experiencia': 5, ...}
            ],
            'similaridades': []
        }
```

**Example 2: Mock function with @patch decorator**
```python
@patch('core.views.processar_cv_task.delay')
def test_upload_e_polling_ate_status_final(self, mock_delay):
    response = self.client.post(
        reverse('core:processar_upload'),
        data={...}
    )
    mock_delay.assert_called_once_with(str(candidato.id))
```

**Example 3: Mock OpenAI task with side effects**
```python
@patch('core.tasks.OpenAI')
def test_openai_mock_retorna_json_valido(self, mock_openai_class):
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    # Mock response
    mock_client.beta.messages.create.return_value = MagicMock(
        content=[MagicMock(text=json.dumps(MOCK_CV_JSON_VALIDO))]
    )
```

**Example 4: Override Django settings for specific test**
```python
@override_settings(UPLOAD_RATE_LIMIT_MAX_BY_IP=1, UPLOAD_RATE_LIMIT_MAX_BY_EMAIL=1)
@patch('core.views.processar_cv_task.delay')
def test_upload_rejeita_quando_rate_limit_excedido(self, mock_delay):
    # Test rate limiting with custom settings
```

### What to Mock

**Mock these dependencies:**
- External APIs: OpenAI, Neo4j queries
- Celery tasks: Use `.delay()` in views, mock in tests
- File I/O: Temporary directories with context managers
- Time-dependent logic: Mock `timezone.now()`
- Expensive operations: Database queries on external systems

**Examples from code:**
- `@patch('core.views.processar_cv_task.delay')` - Don't actually queue tasks
- `@patch('core.tasks.OpenAI')` - Don't call real OpenAI API
- `@patch('core.neo4j_connection.run_query')` - Don't query real Neo4j
- `MagicMock(available=True)` - Mock candidato object with specific attributes

### What NOT to Mock

**Don't mock these:**
- Django models and ORM (use TestCase which provides test database)
- Request/response cycle (use `self.client.post()` for full integration)
- Pydantic validation (test actual validation, not mocked)
- Cache operations (clear with `cache.clear()`)
- View logic (test actual execution path)

**Why:**
- We want to test real database interactions
- Full HTTP cycle testing catches integration issues
- Validation logic must be tested as-is
- Mocking too much defeats the purpose of testing

## Fixtures and Factories

### Test Data

**Inline fixture pattern:**
```python
def setUp(self):
    """Fixtures comuns para os testes."""
    self.user = User.objects.create_user(
        username='rh_user',
        email='rh@example.com',
        password='pass1234'
    )
    self.user.profile.role = self.user.profile.Role.RH
    self.user.profile.save()
```

**Inline dictionary fixtures (for mock responses):**
```python
MOCK_CV_JSON_VALIDO = {
    "area_atuacao": "Backend",
    "senioridade_inferida": "pleno",
    "habilidades": [
        {
            "nome": "Python",
            "nivel": 4,
            "anos_experiencia": 5.0,
            "ano_ultima_utilizacao": 2024,
            "inferido": False
        },
    ]
}
```

**Helper methods for file fixtures:**
```python
def _valid_pdf_file(self, name='cv.pdf'):
    return SimpleUploadedFile(
        name,
        b'%PDF-1.4\n1 0 obj\n<<>>\nendobj\n',
        content_type='application/pdf'
    )

# Usage
pdf = self._valid_pdf_file()
fake_pdf = SimpleUploadedFile('cv.pdf', b'not-a-real-pdf', content_type='application/pdf')
```

### Location

**Fixtures are defined:**
- **Inline in each test class:** setUp() method
- **Class-level constants:** Shared mock data
- **Module-level constants:** Shared test data (e.g., `MOCK_CV_JSON_VALIDO` at top of `test_pipeline_mock.py`)
- **No separate factory/fixture files:** Not using factory_boy or pytest fixtures

**Rationale:**
- Small project, fixtures are simple dictionaries and model instances
- Fixtures live close to where they're used (in test class)
- Clarity over abstraction (can see exactly what data is used)

## Coverage

### Requirements

**No coverage requirements enforced** - no `.coveragerc` or coverage configuration found

**Estimated coverage by feature:**
- Matching engine: ~85% (comprehensive tests for all 3 layers)
- Upload/validation: ~80% (happy path + error cases tested)
- Pipeline: ~70% (mocked OpenAI, status transitions tested)
- Dashboard: ~40% (limited observability tests)
- Services: ~30% (minimal integration tests)
- Overall estimate: **50-60%**

### View Coverage

```bash
# To add coverage testing:
pip install coverage
coverage run --source='.' manage.py test core
coverage report
coverage html  # Generates htmlcov/index.html
```

## Test Types

### Unit Tests

**Scope:** Individual functions/methods in isolation

**Examples:**
- `test_camada_1_match_perfeito()` - Tests MatchingEngine._calcular_scores() for one skill matching scenario
- `test_parse_skills_payload()` - Tests `_parse_skills_payload()` function with various inputs
- `test_upload_rejeita_email_invalido()` - Tests CVUploadService.validate_email()

**Approach:**
- Use mocks for external dependencies (Neo4j, OpenAI, S3)
- Create minimal fixtures (just data needed for test)
- Test one behavior per test method

**Location:**
- `test_matching_engine.py` - ~100 unit tests for matching algorithm
- `test_backend_validations.py` - ~50 unit tests for input validation
- `test_pipeline_mock.py` - ~40 unit tests with mocked pipeline

### Integration Tests

**Scope:** Multiple components working together

**Examples:**
- `test_upload_e_polling_ate_status_final()` - Upload → Celery queue → polling for completion
- `test_openai_mock_retorna_json_valido()` - Full pipeline with mocked OpenAI
- `test_dashboard_rh_exibe_metricas()` - Dashboard view with real database data

**Approach:**
- Use `TransactionTestCase` when full transactions needed
- Test database state changes
- Test HTTP request/response cycles
- Mock only external APIs (OpenAI, S3)

**Location:**
- `test_smoke_flows.py` - Smoke tests for queue + upload + polling
- `test_pipeline_mock.py` - Pipeline integration with mocked OpenAI
- `test_dashboard_observability.py` - Dashboard metrics calculation

### E2E Tests

**Status:** NOT implemented

**Why:**
- No Selenium or browser automation tests
- No staging environment tests
- Would need: real OpenAI API calls (expensive), real Neo4j (complex setup)

**Could be added with:**
- Django LiveServerTestCase for browser tests
- Selenium/Playwright for automated UI tests
- Separate test environment with real services

## Common Patterns

### Async Testing

**Not applicable** - No async views (Django 5.0 async not used)

**Celery task testing:**
- Mock Celery task `.delay()` in views to avoid queue
- Test task logic separately with mocked dependencies
- Example:
```python
@patch('core.views.processar_cv_task.delay')
def test_upload_queues_task(self, mock_delay):
    response = self.client.post(reverse('core:processar_upload'), data={...})
    mock_delay.assert_called_once_with(str(candidato.id))
```

### Error Testing

**Test error paths explicitly:**
```python
def test_upload_rejeita_pdf_falso(self):
    fake_pdf = SimpleUploadedFile('cv.pdf', b'not-a-real-pdf', ...)
    response = self.client.post(
        reverse('core:processar_upload'),
        data={'nome': 'Fulano', 'email': 'fulano@example.com', 'cv': fake_pdf}
    )
    self.assertEqual(response.status_code, 400)
    self.assertContains(response, 'Arquivo inválido', status_code=400)
```

**Test exception handling:**
```python
def test_openai_mock_retorna_json_invalido_senioridade(self):
    # Test that ValidationError is caught and job marked as FAILED
    with patch(...) as mock_openai:
        mock_openai.return_value = json.dumps(MOCK_CV_JSON_INVALIDO_SENIORIDADE)
        # Verify job status is ERROR
        self.assertEqual(candidato.status_cv, Candidato.StatusCV.ERRO)
```

**Test retries:**
```python
def test_openai_transient_error_retry(self):
    # Test that transient errors trigger retry
    with patch('core.tasks.OpenAI') as mock_openai:
        mock_openai.side_effect = RateLimitError("rate limited")
        # Task should be retried (checked via mock call count or state)
```

### Cache Testing

**Clear cache between tests:**
```python
def setUp(self):
    cache.clear()
```

**Test cache behavior:**
- Not explicitly tested in code
- Cache used for rate limiting (implicitly tested in `test_upload_rejeita_quando_rate_limit_excedido`)

### Database State Testing

**Use TestCase (with rollback after each test):**
```python
class UploadBackendValidationTests(TestCase):
    def test_upload_rejeita_nome_muito_curto(self):
        response = self.client.post(...)
        # Database automatically rolled back after test
```

**Use TransactionTestCase (when transactions matter):**
```python
class PipelineMockTests(TransactionTestCase):
    # Tests database state with actual transaction behavior
    # Slower (no rollback optimization)
```

## Test Coverage Summary

| Feature | Coverage | Tests | Location |
|---------|----------|-------|----------|
| Matching Algorithm (3 layers) | 85% | ~100+ | `test_matching_engine.py` |
| Input Validation | 80% | ~50+ | `test_backend_validations.py` |
| Pipeline/OpenAI | 70% | ~40+ | `test_pipeline_mock.py` |
| Dashboard/Observability | 40% | ~10 | `test_dashboard_observability.py` |
| Integration Flows | 60% | ~20 | `test_smoke_flows.py` |
| **Overall Estimate** | **~50-60%** | **~220+** | `core/tests/` |

## Best Practices Followed

✅ **Tests are isolated** - No shared state, each test clears cache/DB
✅ **Descriptive test names** - Clear what's being tested
✅ **Setup/teardown** - Proper fixture creation and cleanup
✅ **Mock external dependencies** - Don't call real OpenAI/Neo4j
✅ **Test both happy path and errors** - Validation tests, pipeline failures
✅ **Use Django TestCase** - Proper transaction handling
✅ **Comments explain intent** - Docstrings describe test strategy

## Gaps Identified

⚠️ **No coverage tool configured** - Should add pytest-cov or coverage.py
⚠️ **Limited E2E tests** - No browser automation or end-to-end flows
⚠️ **Limited dashboard tests** - Only 64 lines of observability tests
⚠️ **No API integration tests** - Neo4j integration only via mocks
⚠️ **No performance tests** - No benchmarks for matching algorithm
⚠️ **No load/stress tests** - No tests for concurrent uploads or matching
⚠️ **Limited service layer tests** - Most services untested in isolation
⚠️ **No test documentation** - No test plan or test case documentation (README)

---

*Testing analysis: 2024-12-19*
