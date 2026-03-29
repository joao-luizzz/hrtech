# HRTech Architecture Guide

> Documento essencial para futuros agentes GSD programarem corretamente neste projeto

**Status**: ✅ Production-Ready  
**Última atualização**: Março 2025  
**Versão da arquitetura**: 3.1.0

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Padrões Arquiteturais](#padrões-arquiteturais)
3. [Stack Tecnológico](#stack-tecnológico)
4. [Estrutura de Diretórios](#estrutura-de-diretórios)
5. [Camada de Modelos](#camada-de-modelos)
6. [Service Layer](#service-layer)
7. [Processamento Assíncrono (Celery)](#processamento-assíncrono-celery)
8. [Banco de Grafos (Neo4j)](#banco-de-grafos-neo4j)
9. [Autenticação e Autorização](#autenticação-e-autorização)
10. [LGPD e Segurança](#lgpd-e-segurança)
11. [Checklist para Novos Features](#checklist-para-novos-features)

---

## Visão Geral

O HRTech é uma plataforma de recrutamento inteligente que combina:

- **Persistência Poliglota**: PostgreSQL (transacional) + Neo4j (grafo de skills)
- **IA Generativa**: Extração de CVs com GPT-4o-mini
- **Processamento Assíncrono**: Celery para OCR, parsing de PDFs e matching
- **Frontend Reativo**: Django Templates + Bootstrap 5 + HTMX
- **LGPD Compliant**: Anonymização de dados pessoais antes de IA

### Problema Resolvido

Automatizar o processo de matching entre candidatos e vagas, eliminando análise manual de CVs e aumentando objetividade nas recomendações.

---

## Padrões Arquiteturais

### 1. Service Layer Pattern

**Objetivo**: Centralizar lógica de negócio, isolada das views.

```python
# ✅ CORRETO: Lógica em Service
# core/services/matching_service.py
class MatchingService:
    @staticmethod
    def run_matching(vaga_id: int, limite: int = 50):
        engine = MatchingEngine()
        return engine.executar_matching(vaga_id=vaga_id, salvar_auditoria=True)

# ❌ ERRADO: Lógica na View
# Views NUNCA devem conter lógica complexa
def view_matching(request, vaga_id):
    # 50+ linhas de lógica aqui = ERRADO
    pass
```

**Serviços Existentes**:
- `MatchingService`: Orquestra matching de vagas
- `CVUploadService`: Gerencia upload de CVs
- `PipelineService`: Gerencia etapas do processo seletivo
- `CandidateSearchService`: Busca avançada com Neo4j
- `ExportService`: Exportação de relatórios
- `EngagementService`: Comunicação com candidatos
- `S3Service`: Storage de CVs (singleton)
- `EmailService`: Notificações por email (singleton)

### 2. Persistência Poliglota

**PostgreSQL** armazena dados transacionais:
- Usuários, Candidatos, Vagas
- Auditorias e histórico de ações
- Comentários do RH

**Neo4j** armazena grafo de conhecimento:
- Nó `Candidato`: UUID sincronizado com PostgreSQL
- Nó `Habilidade`: Skills extraídas de CVs
- Relação `TEM_HABILIDADE`: Conecta candidato → skill com nível e experiência

```cypher
MATCH (c:Candidato {uuid: "12345"})-[r:TEM_HABILIDADE]->(h:Habilidade)
WHERE r.nivel >= 3 AND h.nome = "Python"
RETURN c, h, r.nivel
```

### 3. UUID como Chave de Sincronia

O campo `Candidato.id` é um **UUIDField**, não AutoField:

```python
# core/models.py
class Candidato(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="UUID compartilhado com Neo4j"
    )
```

**Regra importante**: Ao criar candidato em PostgreSQL, **sempre crie o nó no Neo4j** com mesmo UUID.

### 4. Singleton Pattern para Conexões Externas

Para evitar overhead de reconexão:

```python
# ✅ CORRETO: Reutiliza singleton
from core.neo4j_connection import get_neo4j_driver

driver = get_neo4j_driver()  # Mesma instância sempre

# ✅ CORRETO: S3Service como singleton
from core.services import get_s3_service

s3 = get_s3_service()  # Mesma instância sempre
```

---

## Stack Tecnológico

| Camada | Tecnologia | Versão | Uso |
|--------|-----------|--------|-----|
| **Backend** | Django | 5.0 | Framework web |
| **DB Transacional** | PostgreSQL | 15+ | Dados estruturados |
| **DB Grafo** | Neo4j AuraDB | 5.x | Matching inteligente |
| **Cache/Queue** | Redis | 7.0+ | Celery broker e cache |
| **Background Jobs** | Celery | 5.3 | Processamento assíncrono |
| **OCR/PDF** | pdfplumber, pytesseract | Latest | Extração de texto |
| **IA** | OpenAI GPT-4o-mini | Latest | Parsing de skills |
| **Frontend** | Bootstrap 5 + HTMX | Latest | UI responsiva |
| **Auth** | django-allauth | 0.60+ | Autenticação social |
| **Storage** | AWS S3 | N/A | CVs e arquivos |
| **Deploy** | Render.com | N/A | Produção |

---

## Estrutura de Diretórios

```
hrtech/
├── core/                          # App principal
│   ├── models.py                  # 🔴 CRÍTICO: Profile, Candidato, Vaga, AuditoriaMatch
│   ├── views.py                   # Views + decorators de autenticação
│   ├── tasks.py                   # 🔴 CRÍTICO: Celery tasks para CV processing
│   ├── neo4j_connection.py        # 🔴 CRÍTICO: Singleton driver Neo4j
│   ├── matching.py                # MatchingEngine (3 camadas)
│   ├── schemas.py                 # Pydantic schemas (CVParseado, etc)
│   ├── decorators.py              # @rh_required, @candidato_required
│   ├── middleware.py              # RequestID tracking
│   ├── services/                  # 🔴 CRÍTICO: Service Layer
│   │   ├── __init__.py            # Exports principais
│   │   ├── matching_service.py    # Orquestra matching
│   │   ├── cv_upload_service.py   # Upload → Celery → Neo4j
│   │   ├── s3_service.py          # Singleton S3 (presigned URLs)
│   │   ├── email_service.py       # Notificações
│   │   └── [7 mais serviços]
│   ├── tests/                     # Testes unitários
│   ├── management/                # Django management commands
│   ├── migrations/                # Schema migrations
│   └── templates/
│       ├── admin/                 # Admin interface
│       ├── [pages]
│
├── hrtech/                        # Settings + URLs
│   ├── settings.py                # 🔴 CRÍTICO: Variáveis de ambiente
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py                  # 🔴 CRÍTICO: Config Celery
│
├── templates/                     # Django templates (HTML)
│   ├── base.html                  # Layout principal
│   └── [pages]
│
├── static/                        # Assets (CSS, JS, imagens)
├── media/                         # User uploads (deprecated - use S3)
├── gsd/                           # 📋 Este arquivo e documentação
├── .env.example                   # Template de variáveis de ambiente
├── requirements.txt               # Dependências Python
├── Procfile                       # 🔴 CRÍTICO: Configuração Render
└── manage.py                      # Django CLI
```

---

## Camada de Modelos

### Profile (Extensão do User)

```python
class Profile(models.Model):
    class Role(models.TextChoices):
        CANDIDATO = 'candidato'    # Pode ver próprio perfil
        RH = 'rh'                  # Acesso total
        ADMIN = 'admin'            # Acesso total + admin
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=Role.choices)
    receber_notificacoes = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

**Decisão**: Role no Profile permite múltiplos níveis de acesso sem superuser.

### Candidato

```python
class Candidato(models.Model):
    # UUID sincronizado com Neo4j
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    
    # Metadados básicos
    nome, email, telefone
    senioridade, anos_experiencia
    
    # Status do CV (pipeline processamento)
    status_cv = models.CharField(
        choices=StatusCV.choices,
        default='pendente'
        # PENDENTE → RECEBIDO → PROCESSANDO → EXTRAINDO → CONCLUIDO/ERRO
    )
    
    # Status no processo seletivo (separate do status_cv)
    etapa_processo = models.CharField(
        choices=EtapaProcesso.choices,
        default='triagem'
        # TRIAGEM → ENTREVISTA_RH → TESTE_TECNICO → ... → CONTRATADO/REJEITADO
    )
    
    # Storage
    cv_s3_key = models.CharField(max_length=500)  # Não armazenar URL completa
    
    # Relacionamentos
    tags = models.ManyToManyField('Tag', through='CandidatoTag')
    user = models.OneToOneField(User, null=True, blank=True)  # Opcional
```

**Regras Críticas**:
- `status_cv`: Rastreia processamento (Celery updates)
- `etapa_processo`: Rastreia progresso no funil do RH
- Ambos devem ser atualizados **separadamente**
- CV é armazenado apenas em S3, nunca como arquivo local

### Vaga

```python
class Vaga(models.Model):
    titulo, descricao
    area = models.CharField()           # Ex: "Backend", "Frontend", "Dados"
    senioridade_desejada = models.CharField()
    
    # Skills como JSONField (não normalizado)
    skills_obrigatorias = models.JSONField(
        help_text='[{"nome": "Python", "nivel_minimo": 3}]'
    )
    skills_desejaveis = models.JSONField(
        help_text='[{"nome": "Docker", "nivel_minimo": 1}]'
    )
    
    status = models.CharField(
        choices=['rascunho', 'aberta', 'pausada', 'fechada']
    )
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
```

**Decisão**: JSONField para skills permite importação de sistemas externos sem normalizar.

### AuditoriaMatch

```python
class AuditoriaMatch(models.Model):
    """Registro IMUTÁVEL de matching - essencial para LGPD"""
    
    # SET_NULL: Preserva histórico mesmo após deleção (LGPD)
    vaga = models.ForeignKey(Vaga, on_delete=models.SET_NULL, null=True)
    candidato = models.ForeignKey(Candidato, on_delete=models.SET_NULL, null=True)
    
    score = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Snapshot imutável (para reprodutibilidade)
    snapshot_skills = models.JSONField()
    versao_algoritmo = models.CharField(default='1.0.0')
    detalhes_calculo = models.JSONField()
    
    created_at = models.DateTimeField(auto_now_add=True)  # Imutável
```

**Decisão**: SET_NULL preserva auditoria quando candidato/vaga são deletados (compliance LGPD).

### HistoricoAcao

```python
class HistoricoAcao(models.Model):
    """Log de todas as ações - LGPD audit trail"""
    
    class TipoAcao(models.TextChoices):
        CANDIDATO_CRIADO = 'candidato_criado'
        CANDIDATO_EDITADO = 'candidato_editado'
        CANDIDATO_DELETADO = 'candidato_deletado'
        CANDIDATO_CV_UPLOAD = 'cv_upload'
        CANDIDATO_CV_VISUALIZADO = 'cv_visualizado'
        CANDIDATO_ETAPA_ALTERADA = 'etapa_alterada'
        VAGA_CRIADA = 'vaga_criada'
        MATCHING_EXECUTADO = 'matching'
        LOGIN = 'login'
        LOGOUT = 'logout'
    
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    tipo_acao = models.CharField(max_length=30, choices=TipoAcao.choices)
    candidato = models.ForeignKey(Candidato, on_delete=models.SET_NULL, null=True, blank=True)
    vaga = models.ForeignKey(Vaga, on_delete=models.SET_NULL, null=True, blank=True)
    detalhes = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

**Helper function** (use sempre para registrar ações):

```python
from core.models import registrar_acao

registrar_acao(
    usuario=request.user,
    tipo_acao=HistoricoAcao.TipoAcao.CANDIDATO_ETAPA_ALTERADA,
    candidato=candidato,
    detalhes={'de': 'triagem', 'para': 'entrevista_rh'},
    ip_address=get_client_ip(request)
)
```

---

## Service Layer

Todos os serviços ficam em `core/services/`. Nunca coloque lógica nas views.

### Padrão de Implementação

```python
# ✅ CORRETO: Service com métodos estáticos
class MeuService:
    @staticmethod
    def fazer_algo(param1, param2):
        # Lógica isolada aqui
        return resultado
    
    @staticmethod
    def fazer_outra_coisa(param):
        # Lógica isolada aqui
        return resultado

# Na view
from core.services import MeuService

resultado = MeuService.fazer_algo(param1, param2)
```

### S3Service (Singleton)

```python
from core.services import get_s3_service

s3 = get_s3_service()

# Download com presigned URL (15 min de validade)
presigned_url = s3.get_presigned_url('cvs/uuid/arquivo.pdf')

# Upload
s3.upload_file(local_path, 's3_key')

# Download para arquivo temp
s3.download_to_temp_file('s3_key', '/tmp/file.pdf')
```

**Decisão**: Armazena apenas chave (key), não URL completa. URLs são geradas via presigned URLs com TTL.

### EmailService (Singleton)

```python
from core.services import get_email_service

email = get_email_service()
email.enviar_notificacao_etapa(candidato, nova_etapa)
```

---

## Processamento Assíncrono (Celery)

### Configuração

```python
# hrtech/celery.py
app = Celery('hrtech')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

```python
# hrtech/settings.py
CELERY_BROKER_URL = config('CELERY_BROKER_URL')  # Redis
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND')  # Redis
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
```

### Pipeline de Processamento de CV

**Fluxo**:
1. **Upload (View)** → Salva em S3, status = `RECEBIDO`
2. **Trigger Task** → `.delay(candidato_id)`
3. **PROCESSANDO** → Extrai texto (pdfplumber ou Tesseract)
4. **EXTRAINDO** → Chama OpenAI para parsear skills
5. **SALVANDO** → Atualiza PostgreSQL + Neo4j
6. **CONCLUIDO** ou **ERRO** → Final

```python
# core/tasks.py

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def processar_cv_task(self, candidato_id: str) -> dict:
    """
    Processa CV: extração → parsing → Neo4j
    
    Retries automáticos se erros transientes (OpenAI rate limit, S3 timeout)
    """
    try:
        candidato = Candidato.objects.get(pk=candidato_id)
        
        # Etapa 1: PROCESSANDO
        candidato.status_cv = 'processando'
        candidato.save(update_fields=['status_cv'])
        
        texto = extrair_texto_cv(...)
        
        # Etapa 2: EXTRAINDO
        candidato.status_cv = 'extraindo'
        candidato.save(update_fields=['status_cv'])
        
        # LGPD: Limpa dados pessoais ANTES de enviar para OpenAI
        texto_limpo = limpar_dados_pessoais(texto)
        cv_parseado = chamar_openai_extracao(texto_limpo)
        
        # Etapa 3: SALVANDO
        candidato.senioridade = cv_parseado.senioridade_inferida
        candidato.anos_experiencia = int(cv_parseado.anos_experiencia)
        candidato.save()
        
        # Salva no Neo4j (mesmo UUID)
        salvar_habilidades_neo4j(
            candidato_uuid=str(candidato.id),
            area=cv_parseado.area_atuacao,
            habilidades=cv_parseado.habilidades,
            senioridade=cv_parseado.senioridade_inferida
        )
        
        candidato.status_cv = 'concluido'
        candidato.save(update_fields=['status_cv'])
        
        return {'status': 'success', 'habilidades_count': len(cv_parseado.habilidades)}
        
    except Candidato.DoesNotExist:
        return {'status': 'error', 'reason': 'candidato_nao_encontrado'}
    
    except (RateLimitError, APIConnectionError) as e:
        # Retry automático para erros transientes
        raise self.retry(exc=e)
    
    except MaxRetriesExceededError:
        candidato.status_cv = 'erro'
        candidato.save(update_fields=['status_cv'])
        return {'status': 'error', 'reason': 'max_retries_exceeded'}
```

### Funções de Suporte

```python
def limpar_dados_pessoais(texto: str) -> str:
    """
    CRÍTICO PARA LGPD: Remove/mascara antes de enviar para OpenAI
    
    Substitui:
    - CPF: 000.000.000-00 → [CPF REMOVIDO]
    - RG: XX.XXX.XXX-X → [RG REMOVIDO]
    - Datas de nascimento → [DATA REMOVIDA]
    - CTPS, PIS → [REMOVIDO]
    
    ⚠️ NUNCA loga o texto original!
    """
    # Implementado em tasks.py - use sempre!
    pass

def extrair_texto_cv(cv_path: str) -> str:
    """
    1. Tenta pdfplumber (PDFs nativos)
    2. Se < 50 caracteres → OCR com Tesseract (PDFs escaneados)
    
    Limita a 15.000 caracteres para não estourar contexto GPT.
    """
    pass

def chamar_openai_extracao(texto_cv: str) -> CVParseado:
    """
    Se OPENAI_MOCK_MODE=True, retorna dados mockados.
    Caso contrário, chama GPT-4o-mini.
    """
    pass
```

### Monitoramento de Tasks

```python
# Frontend usa polling HTMX
# <div hx-get="/api/candidato/{{ id }}/status-cv/" 
#      hx-trigger="every 2s until .concluido" />

# Backend retorna status_cv atual
```

---

## Banco de Grafos (Neo4j)

### Configuração

```python
# core/neo4j_connection.py

def get_neo4j_driver():
    """
    Retorna driver Neo4j como singleton.
    
    Inicializa na primeira chamada, reutiliza nas subsequentes.
    Thread-safe por design do driver.
    """
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
        )
    return _driver

# Context manager (recomendado)
with Neo4jConnection() as conn:
    rows = conn.run_query("MATCH (n) RETURN n LIMIT 10")
```

### Schema (Cypher)

```cypher
# Nós
CREATE CONSTRAINT candidato_uuid IF NOT EXISTS
  FOR (c:Candidato) REQUIRE c.uuid IS UNIQUE

CREATE CONSTRAINT habilidade_nome IF NOT EXISTS
  FOR (h:Habilidade) REQUIRE h.nome IS UNIQUE

CREATE CONSTRAINT area_nome IF NOT EXISTS
  FOR (a:Area) REQUIRE a.nome IS UNIQUE

# Índices para performance
CREATE INDEX idx_candidato_area IF NOT EXISTS
  FOR (c:Candidato) ON (c.area_atuacao)

CREATE INDEX idx_habilidade_nivel IF NOT EXISTS
  FOR (h:Habilidade) ON (h.nivel)
```

### Queries Comuns

```cypher
# Salvar candidato com habilidades
MERGE (c:Candidato {uuid: $uuid})
SET c.nome = $nome, c.senioridade = $senioridade
MERGE (h:Habilidade {nome: $skill_nome})
MERGE (c)-[r:TEM_HABILIDADE {
  nivel: $nivel,
  anos_experiencia: $anos,
  ano_ultima_utilizacao: $ano_uso,
  inferido: $inferido
}]->(h)

# Buscar habilidades por candidato
MATCH (c:Candidato {uuid: $uuid})-[r:TEM_HABILIDADE]->(h:Habilidade)
WHERE r.nivel >= 3
RETURN h.nome, r.nivel, r.anos_experiencia
ORDER BY r.nivel DESC

# Matching: candidatos que têm skill X com nível Y
MATCH (c:Candidato)-[r:TEM_HABILIDADE]->(h:Habilidade {nome: $skill})
WHERE r.nivel >= $nivel_minimo
RETURN c.uuid, c.nome, r.nivel
```

### Algoritmo de Matching (3 Camadas)

Implementado em `core/matching.py`:

**Camada 1: Habilidades Obrigatórias**
- Score: 0-40 pontos
- Requer 100% das skills obrigatórias com nível mínimo

**Camada 2: Habilidades Desejaveis**
- Score: 0-30 pontos
- Calcula overlap percentual

**Camada 3: Senioridade + Experiência**
- Score: 0-30 pontos
- Alinhamento de senioridade e anos de experiência

**Score Final**: Soma das 3 camadas (0-100)

---

## Autenticação e Autorização

### django-allauth

Gerencia sign-up, login, password reset. **Usar** `{% load socialaccount %}` em templates.

### Decorators Personalizados

```python
# core/decorators.py

@rh_required
def view_rh_only(request):
    """Requer role=RH ou role=ADMIN"""
    pass

@candidato_required
def view_candidato_only(request):
    """Requer role=CANDIDATO ou ser o proprietário do perfil"""
    pass

def get_client_ip(request):
    """Extrai IP do cliente (considerando proxies)"""
    return ip

def get_request_id(request):
    """Retorna ID único do request (para logging)"""
    return request_id
```

### Verificação de Acesso

```python
# Dentro de views
def _user_can_access_candidate(user, candidato):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if user.profile.is_rh:  # Profile.Role.RH ou ADMIN
        return True
    return getattr(user, 'candidato', None) == candidato  # Proprietário
```

---

## LGPD e Segurança

### Princípios LGPD Implementados

**1. Minimização de Dados**
- Armazenar apenas dados necessários
- JSONField para dados estruturados (não normalizar excessivamente)

**2. Limpeza de Dados Pessoais (GDPR Right to Be Forgotten)**

```python
def limpar_dados_pessoais(texto: str) -> str:
    # CPF, RG, datas de nascimento → [REMOVIDO]
    # Implementado em tasks.py antes de enviar para OpenAI
    pass

# Fluxo de deleção de candidato:
# 1. Deletar do PostgreSQL
# 2. Deletar nó no Neo4j
# 3. Deletar CV do S3
# 4. Anonimizar AuditoriaMatch (SET_NULL preserva histórico)
```

**3. Auditoria Completa**

```python
# Cada ação registrada em HistoricoAcao
registrar_acao(
    usuario=request.user,
    tipo_acao='candidato_cv_visualizado',
    candidato=candidato,
    ip_address=get_client_ip(request)
)
```

**4. Snapshot Imutável de Matchings**

```python
# AuditoriaMatch.snapshot_skills preserva estado no momento do cálculo
# Permite reproduzir matching mesmo se regras mudem
```

### Segurança

**1. Credenciais via `.env` (python-decouple)**

```python
# ✅ CORRETO
from decouple import config

secret_key = config('SECRET_KEY')  # Sem default em produção!
openai_key = config('OPENAI_API_KEY')

# ❌ ERRADO
secret_key = os.getenv('SECRET_KEY', 'default-key')  # Inseguro!
```

**2. Proteções em Produção (settings.py)**

```python
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    X_FRAME_OPTIONS = 'DENY'
```

**3. CSRF com HTMX**

```html
<!-- Sempre incluir CSRF token em forms e requisições HTMX -->
{% csrf_token %}

<!-- HTMX adiciona header automaticamente se configurado -->
<script>
  document.body.addEventListener('htmx:configRequest', function(detail) {
    detail.headers['X-CSRFToken'] = document.querySelector('[name=csrfmiddlewaretoken]').value;
  });
</script>
```

**4. Validação de Input**

```python
# ✅ CORRETO: Validar sempre
def _parse_skills_payload(raw_payload, label):
    parsed = json.loads(raw_payload or '[]')
    
    if not isinstance(parsed, list):
        return [], [f'{label} inválidas: formato deve ser lista']
    
    if len(parsed) > MAX_SKILLS_PER_VAGA_LIST:
        return [], [f'{label} inválidas: máximo {MAX_SKILLS_PER_VAGA_LIST} itens']
    
    for idx, item in enumerate(parsed):
        nome = str(item.get('nome', '')).strip()
        if not nome or len(nome) > MAX_SKILL_NAME_LENGTH:
            return [], [f'{label} item {idx} inválido']
    
    return parsed, []
```

**5. Arquivo S3 não expõe key**

```python
# ✅ CORRETO: Usar presigned URL com TTL
presigned_url = s3.get_presigned_url('cvs/uuid/arquivo.pdf', ttl=900)  # 15 min

# ❌ ERRADO: Expor URL público ou sem TTL
cv_link = f"https://bucket.s3.amazonaws.com/cvs/uuid/arquivo.pdf"
```

---

## Checklist para Novos Features

Ao implementar novo feature, siga este checklist:

### 1. Definir Modelos

- [ ] Criar model em `core/models.py`
- [ ] Usar `on_delete=models.SET_NULL` para FKs que devem preservar histórico (LGPD)
- [ ] Adicionar `created_at` e `updated_at` timestamps
- [ ] Criar migration: `python manage.py makemigrations && python manage.py migrate`
- [ ] Registrar no `core/admin.py` para Django Admin

### 2. Implementar Service

- [ ] Criar classe em `core/services/`
- [ ] Usar métodos estáticos `@staticmethod`
- [ ] Importar e exportar em `core/services/__init__.py`
- [ ] Testar isoladamente (sem views)

### 3. Criar Views

- [ ] Importar service: `from core.services import MeuService`
- [ ] Views devem **apenas orquestrar**: `resultado = MeuService.fazer_algo(...)`
- [ ] Adicionar decorators de autenticação: `@rh_required`, `@login_required`
- [ ] Registrar ações: `registrar_acao(...)`
- [ ] Usar `get_client_ip(request)` para auditoria

### 4. Processos Assíncrono (se necessário)

- [ ] Implementar task em `core/tasks.py`
- [ ] Usar `@shared_task(bind=True, max_retries=3)`
- [ ] Tratar retries para erros transientes
- [ ] NUNCA tracar view esperando task completar
- [ ] Usar status field para polling frontend

### 5. Neo4j (se necessário)

- [ ] Sincronizar UUID: `Candidato.id` = nó Neo4j `uuid`
- [ ] Usar `Neo4jConnection` context manager
- [ ] Criar índices/constraints no Cypher
- [ ] Testar queries com `$ python manage.py shell`

### 6. Frontend

- [ ] Usar Bootstrap 5 classes
- [ ] Dark mode: usar CSS variables `var(--bg-primary)`, etc
- [ ] HTMX: adicionar `hx-*` attributes para requisições AJAX
- [ ] Sempre incluir `{% csrf_token %}`
- [ ] Validar input no frontend + backend

### 7. Testes

- [ ] Unit tests em `core/tests/`
- [ ] Testar service isoladamente (mock Neo4j, S3, OpenAI)
- [ ] Testar views com client autenticado
- [ ] Testar LGPD: limpar dados pessoais, registrar ações
- [ ] Rodar: `python manage.py test`

### 8. Documentação

- [ ] Comentar código complexo
- [ ] Docstrings em funções públicas
- [ ] Atualizar este arquivo se nova decisão arquitetural

### 9. Deploy (Render.com)

- [ ] Adicionar variáveis de ambiente no Render Dashboard
- [ ] Atualizar `Procfile` se nova task/worker necessário
- [ ] Testar em staging antes de produção
- [ ] Rodar migrations: `python manage.py migrate --no-input`

---

## Troubleshooting

### CV não processa (status fica em PROCESSANDO)

**Causa**: Worker Celery não está rodando ou Redis não conecta.

```bash
# Verificar no Render Logs
# Procure por: "Conexão Redis falhou" ou "Worker não iniciado"

# Localmente
celery -A hrtech worker -l info

# Se Redis não está rodando
redis-cli ping  # Deve retornar PONG
```

### Neo4j não conecta

```python
# Verificar credenciais em settings.py
NEO4J_URI = "neo4j+s://..."  # Deve ser neo4j+s:// para cloud
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "..."  # Do Aura console

# Testar conexão
python manage.py shell
from core.neo4j_connection import get_neo4j_driver
driver = get_neo4j_driver()  # Deve não levantar exceção
```

### S3 presigned URL expira muito rápido

```python
# Aumentar TTL em s3_service.py
presigned_url = s3_client.generate_presigned_url(
    'get_object',
    Params={'Bucket': bucket, 'Key': key},
    ExpiresIn=3600  # 1 hora em vez de 15 min
)
```

### OpenAI rate limit ou timeout

```python
# tasks.py já tem retry automático
# Verificar OPENAI_MOCK_MODE em settings.py para testes

# Se problema persistir
OPENAI_MOCK_MODE = True  # Use dados mockados
```

---

## Referências Rápidas

### URLs da Aplicação

```
/admin/                     # Django Admin
/accounts/login/            # django-allauth login
/accounts/signup/           # django-allauth signup
/perfil/                    # Perfil do usuário
/candidatos/                # Lista de candidatos (RH only)
/vagas/                     # Lista de vagas (RH only)
/upload/                    # Upload de CV (público)
/api/candidato/.../status/  # Polling de status (HTMX)
```

### Variáveis de Ambiente Críticas

```env
# .env.example ou Render Dashboard
SECRET_KEY=                         # Obrigatório em produção
DEBUG=False                         # NUNCA True em produção
ALLOWED_HOSTS=example.com

# Database
DATABASE_URL=postgresql://...

# Neo4j
NEO4J_URI=neo4j+s://...
NEO4J_USER=neo4j
NEO4J_PASSWORD=...

# Redis (Celery)
CELERY_BROKER_URL=redis://...
CELERY_RESULT_BACKEND=redis://...

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MOCK_MODE=False             # True para testes

# AWS S3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=...

# Email
EMAIL_BACKEND=...
EMAIL_HOST=...
EMAIL_PORT=...
```

### Comandos Úteis

```bash
# Setup inicial
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

# Testes
python manage.py test core/tests/

# Worker Celery
celery -A hrtech worker -l info

# Shell Django
python manage.py shell

# Limpeza
python manage.py collectstatic
python manage.py dumpdata > backup.json
```

---

## Conclusão

Este documento é a **verdade única** sobre arquitetura do HRTech. Ao dúvida, **releia-o**.

Futuros agentes GSD devem:
1. ✅ Colocar lógica em Services, não Views
2. ✅ Usar UUIDs para sincronia PostgreSQL ↔ Neo4j
3. ✅ Limpar dados pessoais ANTES de enviar para IA
4. ✅ Registrar ações em HistoricoAcao para auditoria
5. ✅ Usar `@shared_task` para processamento assíncrono
6. ✅ Testar isoladamente: Services → Views → Integração
7. ✅ Honrar LGPD: SET_NULL em FKs, snapshots imutáveis, presigned URLs

**Dúvidas?** Releia a seção relevante deste documento.
