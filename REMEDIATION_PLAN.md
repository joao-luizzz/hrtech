# 🔧 PLANO DE REMEDIAÇÃO DE SEGURANÇA - HRTECH
## Guia Detalhado de Correções

**Objetivo:** Corrigir todas as vulnerabilidades críticas e de alta severidade em 30 dias.
**Responsável:** Equipe de desenvolvimento
**Prazo Final:** 2026-05-02

---

## 📅 CRONOGRAMA DE EXECUÇÃO

### SEMANA 1: VULNERABILIDADES CRÍTICAS (Bloqueante para Produção)
**Deadline:** 2026-04-09
**Status:** 🔴 NÃO INICIADO

#### 1.1. Implementar Tenant Isolation (8 horas)
**Prioridade:** 🔴 CRÍTICA
**Responsável:** Backend Lead

**Tarefas:**
- [ ] Criar middleware `TenantMiddleware` para injetar `tenant_id` automaticamente
- [ ] Criar manager customizado `TenantManager` para filtrar por organization
- [ ] Aplicar `TenantManager` em todos os modelos (Candidato, Vaga, AuditoriaMatch, etc.)
- [ ] Adicionar decorator `@tenant_required` para views
- [ ] Atualizar TODAS as queries para incluir filtro de organization

**Arquivos a modificar:**
```
core/middleware.py
core/managers.py (novo arquivo)
core/models.py (Candidato, Vaga, AuditoriaMatch)
core/decorators.py (@tenant_required)
core/views.py (TODAS as views)
```

**Código de exemplo:**

```python
# core/middleware.py
class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            request.tenant = request.user.profile.organization
        else:
            request.tenant = None
        return self.get_response(request)

# core/managers.py
from django.db import models

class TenantManager(models.Manager):
    def get_queryset(self):
        from threading import local
        thread_local = getattr(self, '_thread_local', None)
        if thread_local and hasattr(thread_local, 'tenant_id'):
            return super().get_queryset().filter(organization_id=thread_local.tenant_id)
        return super().get_queryset()

    def set_tenant(self, tenant_id):
        if not hasattr(self, '_thread_local'):
            from threading import local
            self._thread_local = local()
        self._thread_local.tenant_id = tenant_id

# core/decorators.py
def tenant_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'tenant') or request.tenant is None:
            return HttpResponseForbidden('Tenant não identificado')
        # Configurar tenant no manager
        from core.models import Candidato, Vaga, AuditoriaMatch
        Candidato.objects.set_tenant(request.tenant.id)
        Vaga.objects.set_tenant(request.tenant.id)
        AuditoriaMatch.objects.set_tenant(request.tenant.id)
        return view_func(request, *args, **kwargs)
    return wrapper
```

**Testes obrigatórios:**
```python
# core/tests/test_tenant_isolation.py
def test_candidato_isolation():
    """Usuário da Org A não deve ver candidatos da Org B"""
    org_a = Organization.objects.create(nome="Empresa A")
    org_b = Organization.objects.create(nome="Empresa B")

    candidato_a = Candidato.objects.create(nome="João", organization=org_a)
    candidato_b = Candidato.objects.create(nome="Maria", organization=org_b)

    user_a = User.objects.create(username="user_a")
    user_a.profile.organization = org_a
    user_a.profile.save()

    # Login como user_a
    client = Client()
    client.force_login(user_a)

    # Tentar acessar candidato da Org B
    response = client.get(f'/candidato/{candidato_b.id}/')
    assert response.status_code == 404  # Não deve encontrar

    # Acessar candidato da própria Org
    response = client.get(f'/candidato/{candidato_a.id}/')
    assert response.status_code == 200  # Deve funcionar
```

---

#### 1.2. Parametrizar Queries Cypher (4 horas)
**Prioridade:** 🔴 CRÍTICA
**Responsável:** Backend Developer

**Tarefas:**
- [ ] Auditar TODAS as chamadas para `run_query()` e `run_write_query()`
- [ ] Garantir que NENHUMA query concatena strings
- [ ] Adicionar validação de input em nomes de habilidades
- [ ] Implementar whitelist de caracteres permitidos

**Arquivos a modificar:**
```
core/neo4j_connection.py
core/matching.py
core/services/*.py (todos que usam Neo4j)
```

**Validação obrigatória:**
```python
# core/validators.py
import re

ALLOWED_SKILL_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\s\.\-\+#]{1,100}$')

def validate_skill_name(name: str) -> str:
    """
    Valida e sanitiza nome de habilidade.
    Apenas alfanuméricos, espaços e alguns caracteres especiais.
    """
    if not name or not isinstance(name, str):
        raise ValueError("Nome de habilidade inválido")

    name = name.strip()

    if not ALLOWED_SKILL_NAME_PATTERN.match(name):
        raise ValueError(
            f"Nome de habilidade contém caracteres inválidos: {name}"
        )

    return name

# Aplicar em views.py:_parse_skills_payload()
nome = validate_skill_name(item.get('nome', ''))
```

**Teste de segurança:**
```python
def test_cypher_injection_prevention():
    """Tentativa de injection deve falhar"""
    malicious_skill = "Python'; DETACH DELETE (n); //"

    with pytest.raises(ValueError):
        validate_skill_name(malicious_skill)
```

---

#### 1.3. Implementar Rate Limiting Global (6 horas)
**Prioridade:** 🔴 CRÍTICA
**Responsável:** DevOps + Backend

**Tarefas:**
- [ ] Instalar `django-ratelimit`
- [ ] Configurar Redis para cache de rate limits
- [ ] Aplicar rate limiting em TODOS os endpoints protegidos
- [ ] Configurar limites específicos para endpoints caros

**Instalação:**
```bash
pip install django-ratelimit==4.0.0
```

**Configuração:**
```python
# settings.py
INSTALLED_APPS += ['django_ratelimit']

RATELIMIT_ENABLE = not DEBUG
RATELIMIT_USE_CACHE = 'default'

# Configuração do Redis para rate limiting
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': CACHE_URL,
        'KEY_PREFIX': 'hrtech',
        'TIMEOUT': 300,
    }
}
```

**Aplicar em views:**
```python
# core/views.py
from django_ratelimit.decorators import ratelimit

# Endpoints de leitura: 100 req/min
@ratelimit(key='user', rate='100/m', method='GET')
@ratelimit(key='ip', rate='200/m', method='GET')
@login_required
def dashboard_rh(request):
    ...

# Endpoints de escrita: 30 req/min
@ratelimit(key='user', rate='30/m', method='POST')
@ratelimit(key='ip', rate='50/m', method='POST')
@login_required
@rh_required
def criar_vaga(request):
    ...

# Endpoints CAROS (matching): 10 req/min
@ratelimit(key='user', rate='10/m', method='POST')
@ratelimit(key='ip', rate='20/m', method='POST')
@login_required
@rh_required
def rodar_matching(request, vaga_id):
    ...

# Endpoints MUITO CAROS (OpenAI): 5 req/min
@ratelimit(key='user', rate='5/m', method='POST')
@ratelimit(key='ip', rate='10/m', method='POST')
@login_required
@staff_required
def generate_interview_questions_htmx(request, vaga_id, candidate_id):
    ...
```

**Tratamento de erro:**
```python
# core/views.py
from django_ratelimit.exceptions import Ratelimited

def handler429(request, exception=None):
    return JsonResponse({
        'error': 'Muitas requisições. Aguarde alguns minutos e tente novamente.',
        'retry_after': 60
    }, status=429)

# urls.py
handler429 = 'core.views.handler429'
```

---

#### 1.4. Adicionar Verificação de Ownership em TODAS as Views (8 horas)
**Prioridade:** 🔴 CRÍTICA
**Responsável:** Backend Team

**Tarefas:**
- [ ] Auditar TODAS as views que acessam Candidato/Vaga
- [ ] Adicionar filtro de `organization` em TODOS os `get_object_or_404()`
- [ ] Criar helper function para verificação de ownership
- [ ] Adicionar testes para cada endpoint

**Helper function:**
```python
# core/decorators.py
def get_object_or_404_with_tenant(model, request, **kwargs):
    """
    Similar ao get_object_or_404, mas filtra por organization automaticamente.
    """
    if not hasattr(request, 'tenant') or request.tenant is None:
        raise Http404("Tenant não identificado")

    kwargs['organization'] = request.tenant
    return get_object_or_404(model, **kwargs)
```

**Aplicar em views:**
```python
# ❌ ANTES (VULNERÁVEL)
def detalhe_candidato_match(request, vaga_id, candidato_id):
    vaga = get_object_or_404(Vaga, pk=vaga_id)
    candidato = get_object_or_404(Candidato, pk=candidato_id)

# ✅ DEPOIS (SEGURO)
def detalhe_candidato_match(request, vaga_id, candidato_id):
    vaga = get_object_or_404_with_tenant(Vaga, request, pk=vaga_id)
    candidato = get_object_or_404_with_tenant(Candidato, request, pk=candidato_id)
```

**Lista de views a corrigir:**
```
✅ dashboard_candidato (views.py:936)
✅ ranking_candidatos (views.py:549)
✅ detalhe_candidato_match (views.py:563)
✅ buscar_candidatos (views.py:780)
✅ editar_vaga (views.py:425)
✅ excluir_vaga (views.py:484)
✅ listar_comentarios (views.py:1177)
✅ adicionar_comentario (views.py:1144)
✅ toggle_favorito (views.py:1210)
✅ meus_favoritos (views.py:1228)
```

---

### SEMANA 2: VULNERABILIDADES DE ALTA SEVERIDADE
**Deadline:** 2026-04-16
**Status:** 🟠 AGUARDANDO SEMANA 1

#### 2.1. Corrigir Migrações de Criação de Usuário (2 horas)

**Tarefas:**
- [ ] Remover defaults de email/username nas migrações
- [ ] Adicionar validação de senha forte
- [ ] Criar comando `manage.py create_admin` separado
- [ ] Deprecar migrações automáticas de usuário

**Código:**
```python
# core/management/commands/create_admin.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from core.models import Profile
import getpass

class Command(BaseCommand):
    help = 'Cria usuário admin RH com validação de senha forte'

    def handle(self, *args, **options):
        email = input('Email do admin: ')
        username = input('Username (Enter para usar email): ') or email

        while True:
            password = getpass.getpass('Senha: ')
            password2 = getpass.getpass('Confirme a senha: ')

            if password != password2:
                self.stdout.write(self.style.ERROR('Senhas não coincidem'))
                continue

            try:
                validate_password(password)
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(str(e)))

        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )

        Profile.objects.create(user=user, role='rh')

        self.stdout.write(self.style.SUCCESS(f'Admin criado: {email}'))
```

---

#### 2.2. Sanitização de Input em JSON Fields (4 horas)

**Tarefas:**
- [ ] Criar função de sanitização de HTML
- [ ] Aplicar em _parse_skills_payload()
- [ ] Adicionar validação de charset
- [ ] Implementar CSP headers

**Código:**
```python
# core/validators.py
import bleach
import re

ALLOWED_SKILL_CHARS = re.compile(r'^[a-zA-Z0-9\s\.\-\+#\(\)\/]{1,100}$')

def sanitize_skill_name(name: str) -> str:
    """
    Remove HTML/JS malicioso e valida charset.
    """
    # Remove HTML tags
    name = bleach.clean(name, tags=[], strip=True)

    # Remove caracteres de controle
    name = ''.join(char for char in name if char.isprintable())

    # Valida charset
    if not ALLOWED_SKILL_CHARS.match(name):
        raise ValueError(f"Caracteres inválidos em: {name}")

    return name.strip()
```

**CSP Headers:**
```python
# settings.py
MIDDLEWARE += [
    'csp.middleware.CSPMiddleware',
]

CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")  # Remover unsafe-inline em produção
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "fonts.googleapis.com")
CSP_FONT_SRC = ("'self'", "fonts.gstatic.com")
CSP_IMG_SRC = ("'self'", "data:", "*.amazonaws.com")  # S3
```

---

#### 2.3. Filtro de Log para Dados Sensíveis (3 horas)

**Código:**
```python
# core/logging_filters.py
import logging
import re

class SensitiveDataFilter(logging.Filter):
    """Remove dados sensíveis dos logs."""

    SENSITIVE_PATTERNS = [
        (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL]'),
        (re.compile(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b'), '[CPF]'),
        (re.compile(r'\b\d{11}\b'), '[CPF]'),
        (re.compile(r'password["\s:=]+([^"\s,}]+)', re.IGNORECASE), 'password=[REDACTED]'),
        (re.compile(r'token["\s:=]+([^"\s,}]+)', re.IGNORECASE), 'token=[REDACTED]'),
    ]

    def filter(self, record):
        if isinstance(record.msg, str):
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        return True

# settings.py
LOGGING = {
    'filters': {
        'sensitive': {
            '()': 'core.logging_filters.SensitiveDataFilter',
        },
    },
    'handlers': {
        'console': {
            'filters': ['sensitive'],
        },
    },
}
```

---

#### 2.4. Headers de Segurança Adicionais (1 hora)

```python
# settings.py
if not DEBUG:
    # Já existentes (✅)
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000

    # ADICIONAR:
    SECURE_REFERRER_POLICY = 'same-origin'
    CSRF_COOKIE_SAMESITE = 'Strict'
    SESSION_COOKIE_SAMESITE = 'Strict'
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

    # Permissions Policy
    SECURE_PERMISSIONS_POLICY = {
        "geolocation": [],
        "microphone": [],
        "camera": [],
        "payment": [],
    }
```

---

### SEMANA 3: VULNERABILIDADES MÉDIAS + MELHORIAS
**Deadline:** 2026-04-23

#### 3.1. Melhorar Validação de Upload de Arquivos (4 horas)

**Tarefas:**
- [ ] Integrar com ClamAV para scan de vírus
- [ ] Validar estrutura do PDF
- [ ] Limitar número de páginas
- [ ] Remover metadata e JavaScript de PDFs

**Código:**
```python
# core/validators.py
import PyPDF2
import subprocess

def validate_pdf_file(file):
    """Validação completa de PDF."""
    errors = []

    # 1. Magic bytes (já existe)
    file_header = file.read(5)
    file.seek(0)
    if file_header != b'%PDF-':
        errors.append('Arquivo não é um PDF válido')
        return errors

    # 2. Validar estrutura com PyPDF2
    try:
        pdf = PyPDF2.PdfReader(file)
        file.seek(0)

        # Limitar número de páginas
        if len(pdf.pages) > 20:
            errors.append('PDF não pode ter mais de 20 páginas')

        # Verificar se tem JavaScript embarcado
        for page in pdf.pages:
            if '/JS' in page or '/JavaScript' in page:
                errors.append('PDF contém JavaScript (não permitido)')
                break

    except Exception as e:
        errors.append(f'PDF corrompido: {str(e)}')

    # 3. Scan de vírus com ClamAV
    try:
        result = subprocess.run(
            ['clamdscan', '--no-summary', '-'],
            stdin=file,
            capture_output=True,
            timeout=30
        )
        file.seek(0)

        if result.returncode != 0:
            errors.append('Arquivo contém malware (bloqueado)')
    except FileNotFoundError:
        # ClamAV não instalado (dev environment)
        pass
    except subprocess.TimeoutExpired:
        errors.append('Timeout no scan de vírus')

    return errors
```

---

#### 3.2. Implementar Auditoria Completa (6 horas)

**Código:**
```python
# core/middleware.py
class DataAccessAuditMiddleware:
    """Registra TODO acesso a dados pessoais."""

    PROTECTED_MODELS = ['Candidato', 'AuditoriaMatch', 'InterviewQuestion']

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Logar após resposta (se foi bem-sucedida)
        if response.status_code == 200 and request.user.is_authenticated:
            self._log_access(request, response)

        return response

    def _log_access(self, request, response):
        # Detectar acesso a dados de candidatos
        if 'candidato' in request.path or 'cv' in request.path:
            HistoricoAcao.objects.create(
                usuario=request.user,
                tipo_acao=HistoricoAcao.TipoAcao.CANDIDATO_CV_VISUALIZADO,
                detalhes={
                    'path': request.path,
                    'method': request.method,
                },
                ip_address=get_client_ip(request)
            )
```

---

#### 3.3. Circuit Breaker para Neo4j (3 horas)

```python
# core/circuit_breaker.py
import time
from functools import wraps

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half_open

    def call(self, func, *args, **kwargs):
        if self.state == 'open':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'half_open'
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e

    def on_success(self):
        self.failures = 0
        self.state = 'closed'

    def on_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = 'open'

# Aplicar
neo4j_circuit_breaker = CircuitBreaker()

def run_query(query, parameters=None):
    return neo4j_circuit_breaker.call(_run_query_impl, query, parameters)
```

---

#### 3.4. Atualizar Dependências (2 horas)

```bash
# Atualizar requirements.txt
openai>=1.12.0  # Versão atual (antes: 1.3.0)
django-ratelimit==4.0.0  # Nova dependência
django-csp==3.8  # Content Security Policy
bleach==6.0.0  # Sanitização de HTML
PyPDF2==3.0.0  # Validação de PDF
python-magic==0.4.27  # Detecção de tipo de arquivo

# Executar
pip install -r requirements.txt
pip-audit  # Verificar vulnerabilidades
safety check  # Verificar CVEs
```

---

### SEMANA 4: COMPLIANCE LGPD + TESTES
**Deadline:** 2026-04-30

#### 4.1. Implementar Endpoints de LGPD (8 horas)

**Tarefas:**
- [ ] Endpoint de deleção de dados (direito ao esquecimento)
- [ ] Endpoint de export de dados (portabilidade)
- [ ] Endpoint de revogação de consentimento
- [ ] Página de política de privacidade

**Código:**
```python
# core/views.py
@login_required
@require_POST
def solicitar_exclusao_dados(request):
    """
    Art. 18, VI da LGPD - Direito ao esquecimento.
    """
    candidato = getattr(request.user, 'candidato', None)

    if not candidato:
        return JsonResponse({'error': 'Candidato não encontrado'}, status=404)

    # Criar solicitação de exclusão (não deletar imediatamente)
    from core.models import SolicitacaoExclusao
    solicitacao = SolicitacaoExclusao.objects.create(
        candidato=candidato,
        solicitado_por=request.user,
        tipo='exclusao_total'
    )

    # Enviar email para DPO
    EmailService.send_dpo_notification(
        subject='Solicitação de Exclusão de Dados - LGPD',
        candidato=candidato,
        solicitacao=solicitacao
    )

    return JsonResponse({
        'success': True,
        'mensagem': 'Solicitação registrada. Será processada em até 15 dias.',
        'protocolo': str(solicitacao.id)
    })

@login_required
@require_GET
def exportar_meus_dados(request):
    """
    Art. 18, II da LGPD - Portabilidade de dados.
    """
    candidato = getattr(request.user, 'candidato', None)

    if not candidato:
        return JsonResponse({'error': 'Candidato não encontrado'}, status=404)

    # Gerar JSON com todos os dados
    dados = {
        'candidato': {
            'nome': candidato.nome,
            'email': candidato.email,
            'telefone': candidato.telefone,
            'senioridade': candidato.senioridade,
            'anos_experiencia': candidato.anos_experiencia,
            'criado_em': candidato.created_at.isoformat(),
        },
        'habilidades': list(candidato.habilidades.values()),
        'historico': list(candidato.historico.values()),
        'comentarios': list(candidato.comentarios.values()),
    }

    response = JsonResponse(dados, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = 'attachment; filename="meus_dados.json"'

    # Registrar acesso
    HistoricoAcao.objects.create(
        usuario=request.user,
        tipo_acao='export_dados_lgpd',
        candidato=candidato,
    )

    return response
```

**Model:**
```python
# core/models.py
class SolicitacaoExclusao(models.Model):
    candidato = models.ForeignKey(Candidato, on_delete=models.CASCADE)
    solicitado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    tipo = models.CharField(max_length=20, choices=[
        ('exclusao_total', 'Exclusão Total'),
        ('exclusao_cv', 'Exclusão apenas de CV'),
    ])
    status = models.CharField(max_length=20, choices=[
        ('pendente', 'Pendente'),
        ('aprovada', 'Aprovada'),
        ('processada', 'Processada'),
    ], default='pendente')
    created_at = models.DateTimeField(auto_now_add=True)
```

---

#### 4.2. Publicar Política de Privacidade (4 horas)

**Criar:**
```
templates/legal/politica_privacidade.html
templates/legal/termos_uso.html
templates/legal/consentimento.html
```

**Conteúdo mínimo:**
- Quais dados são coletados
- Finalidade do tratamento
- Base legal (Art. 7 LGPD)
- Compartilhamento com terceiros (OpenAI, AWS)
- Direitos do titular
- Contato do DPO
- Prazo de retenção

---

#### 4.3. Executar Pentest Automatizado (4 horas)

**Ferramentas:**
```bash
# 1. OWASP ZAP
docker run -t owasp/zap2docker-stable zap-baseline.py \
    -t http://localhost:8000 \
    -r zap-report.html

# 2. Nikto
nikto -h http://localhost:8000 -output nikto-report.txt

# 3. SQLMap (testar endpoints)
sqlmap -u "http://localhost:8000/rh/candidatos/?q=test" \
    --cookie="sessionid=xxx" \
    --level=5 \
    --risk=3

# 4. Nmap
nmap -sV -sC localhost -p 8000

# 5. Safety (Python dependencies)
safety check

# 6. Bandit (Python security linter)
bandit -r /home/runner/work/hrtech/hrtech/core/
```

---

#### 4.4. Testes de Autorização (8 horas)

**Criar suite completa:**
```python
# core/tests/test_authorization.py
import pytest
from django.test import Client
from core.models import Organization, Candidato, User, Profile

@pytest.mark.django_db
class TestTenantIsolation:
    def test_candidato_isolation(self):
        """Usuário da Org A não deve ver candidatos da Org B"""
        # Setup
        org_a = Organization.objects.create(nome="Empresa A")
        org_b = Organization.objects.create(nome="Empresa B")

        candidato_a = Candidato.objects.create(
            nome="João",
            email="joao@test.com",
            organization=org_a
        )
        candidato_b = Candidato.objects.create(
            nome="Maria",
            email="maria@test.com",
            organization=org_b
        )

        user_a = User.objects.create_user('user_a', 'a@test.com', 'pass')
        user_a.profile.organization = org_a
        user_a.profile.role = 'rh'
        user_a.profile.save()

        # Test
        client = Client()
        client.force_login(user_a)

        # Deve falhar ao acessar candidato da Org B
        response = client.get(f'/candidato/{candidato_b.id}/')
        assert response.status_code == 404

        # Deve funcionar ao acessar candidato da Org A
        response = client.get(f'/candidato/{candidato_a.id}/')
        assert response.status_code == 200

    def test_vaga_isolation(self):
        # Similar para vagas
        pass

    def test_matching_isolation(self):
        # Similar para matching
        pass
```

---

## 📊 MÉTRICAS DE SUCESSO

Após implementar todas as correções, validar:

### Testes Automatizados:
- [ ] **100% dos testes** de tenant isolation passando
- [ ] **0 vulnerabilidades** detectadas pelo safety
- [ ] **0 vulnerabilidades** detectadas pelo bandit
- [ ] **Cobertura de testes ≥ 80%** em código de segurança

### Pentest:
- [ ] **ZAP Baseline:** 0 alertas críticos ou altos
- [ ] **Nikto:** 0 vulnerabilidades críticas
- [ ] **SQLMap:** Nenhuma injeção detectada

### Compliance:
- [ ] **Política de privacidade** publicada
- [ ] **Endpoints LGPD** funcionando
- [ ] **Auditoria completa** de acessos implementada

---

## 🚀 DEPLOY CHECKLIST

Antes de fazer deploy em produção:

- [ ] ✅ Todas as correções da Semana 1 implementadas e testadas
- [ ] ✅ Todas as correções da Semana 2 implementadas e testadas
- [ ] ✅ Pentest automatizado executado sem alertas críticos
- [ ] ✅ Testes de autorização 100% passando
- [ ] ✅ Política de privacidade publicada
- [ ] ✅ DPO designado e contato publicado
- [ ] ✅ Backup automatizado configurado
- [ ] ✅ Monitoramento (Sentry/CloudWatch) configurado
- [ ] ✅ WAF (Cloudflare/AWS WAF) configurado
- [ ] ✅ SSL/TLS configurado
- [ ] ✅ DEBUG=False verificado
- [ ] ✅ SECRET_KEY única e forte
- [ ] ✅ ALLOWED_HOSTS configurado corretamente

---

**FIM DO PLANO DE REMEDIAÇÃO**

**Próximos passos:**
1. Criar branch `security-fixes`
2. Implementar correções semana a semana
3. Abrir PR com cada grupo de correções
4. Code review por security champion
5. Testes em staging
6. Deploy em produção

**Contato:**
- Security Champion: [Nome]
- DPO: [Nome]
- DevOps Lead: [Nome]
