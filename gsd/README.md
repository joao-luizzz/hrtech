# HRTech - GSD Documentation Index

Documentação técnica centralizada para agentes GSD trabalharem no HRTech.

---

## 📚 Documentos Principais

### 1. **ARCHITECTURE.md** ⭐ LEIA PRIMEIRO

Explicação profunda da arquitetura do projeto:

- **Padrões Arquiteturais**: Service Layer, Persistência Poliglota, UUID Sync, Singletons
- **Stack Tecnológico**: Django, PostgreSQL, Neo4j, Redis, Celery, OpenAI
- **Estrutura de Diretórios**: Onde cada coisa fica
- **Camada de Modelos**: Profile, Candidato, Vaga, AuditoriaMatch, HistoricoAcao
- **Service Layer**: 9 serviços existentes (MatchingService, CVUploadService, etc)
- **Celery + Tasks**: Pipeline de processamento de CV (upload → OCR → GPT-4 → Neo4j)
- **Neo4j**: Grafo de habilidades, queries cypher, matching 3-camadas
- **Autenticação**: django-allauth + decorators personalizados
- **LGPD**: Anonymização de dados, direito ao esquecimento, audit trail completo
- **Checklist**: Como implementar novos features corretamente
- **Troubleshooting**: Problemas comuns e soluções

→ **Link**: `gsd/ARCHITECTURE.md`

---

### 2. **PATTERNS.md** 🔧 COPIAR/COLAR

Exemplos prontos para usar ao implementar:

1. ✅ Criar um novo Service
2. ✅ Implementar View com Service
3. ✅ Celery Task com Retry
4. ✅ Neo4j Query com Context Manager
5. ✅ Formulário com CSRF + Validação
6. ✅ Registrar Ação (LGPD Audit)
7. ✅ S3 Presigned URL (Seguro)
8. ✅ Limpar Dados Pessoais (LGPD)
9. ✅ Deletar Candidato (Direito ao Esquecimento)
10. ✅ Polling HTMX para Status
11. ✅ Dark Mode CSS
12. ✅ Teste Unitário com Mock

→ **Link**: `gsd/PATTERNS.md`

---

## 🎯 Como Usar Esta Documentação

### Cenário 1: Novo no projeto?

1. Ler `ARCHITECTURE.md` completamente
2. Entender o fluxo: Upload → Celery → Neo4j → Matching
3. Visualizar structure: `core/models.py`, `core/services/`, `core/tasks.py`
4. Rodar o projeto localmente

### Cenário 2: Implementar nova feature?

1. Consultar "Checklist para Novos Features" em `ARCHITECTURE.md`
2. Copiar exemplo relevante de `PATTERNS.md`
3. Adaptar para seu caso
4. Testar com `python manage.py test`

### Cenário 3: Bug ou integração?

1. Procurar na seção "Troubleshooting" de `ARCHITECTURE.md`
2. Se Neo4j: ver "Banco de Grafos (Neo4j)"
3. Se Celery: ver "Processamento Assíncrono (Celery)"
4. Se segurança: ver "LGPD e Segurança"

---

## 📋 Referência Rápida

### Estrutura de Diretórios

```
core/
├── models.py              ← Profile, Candidato, Vaga, AuditoriaMatch
├── views.py               ← Views + decorators
├── tasks.py               ← Celery tasks para CV processing
├── neo4j_connection.py    ← Singleton driver Neo4j
├── matching.py            ← MatchingEngine (3 camadas)
├── schemas.py             ← Pydantic schemas
├── decorators.py          ← @rh_required, @candidato_required
├── middleware.py          ← RequestID tracking
└── services/              ← 9 serviços isolados
    ├── matching_service.py
    ├── cv_upload_service.py
    ├── s3_service.py
    ├── email_service.py
    └── [mais 5]
```

### Padrões Principais

| Padrão | Onde | Exemplo |
|--------|------|---------|
| **Service Layer** | `core/services/*.py` | `MeuService.fazer_algo(param)` |
| **Celery Task** | `core/tasks.py` | `@shared_task def processar_cv_task(...)` |
| **Neo4j Query** | Service com `Neo4jConnection()` | `conn.run_query("MATCH ...")` |
| **S3 Upload** | Service com `get_s3_service()` | `s3.upload_file(local_path, s3_key)` |
| **Registro Audit** | Toda view importante | `registrar_acao(usuario, tipo, ...)` |
| **Autenticação** | Decorators | `@rh_required`, `@login_required` |

### Comandos Frequentes

```bash
# Desenvolvimento
python manage.py runserver
python manage.py shell
python manage.py test
python manage.py makemigrations
python manage.py migrate

# Celery (background)
celery -A hrtech worker -l info

# Admin Django
python manage.py createsuperuser
# Acesso: /admin/

# Limpeza
python manage.py collectstatic
python manage.py dumpdata > backup.json
```

---

## 🔑 Conceitos-Chave

### 1. Service Layer

**Nunca** coloque lógica complexa em views. Sempre use Services:

```python
# ❌ ERRADO
def view_fazer_algo(request):
    # 50+ linhas de lógica aqui
    pass

# ✅ CORRETO
def view_fazer_algo(request):
    resultado = MeuService.fazer_algo(param)
    return render(...)
```

### 2. UUID Sync: PostgreSQL ↔ Neo4j

`Candidato.id` é UUID compartilhado com Neo4j:

```python
candidato = Candidato.objects.create(id=uuid4(), nome="João")
# Criou em PostgreSQL com UUID

# Depois, no Neo4j:
MERGE (c:Candidato {uuid: "mesma-uuid"})
```

### 3. Persistência Poliglota

| DB | Armazena |
|----|----------|
| **PostgreSQL** | Candidato, Vaga, AuditoriaMatch, HistoricoAcao |
| **Neo4j** | Nó Candidato + Habilidades + Relações |
| **Redis** | Cache + Celery Queue |
| **S3** | Arquivos PDF de CVs |

### 4. Pipeline de Processamento de CV

```
Upload → RECEBIDO → [Celery Task] → PROCESSANDO 
  → EXTRAINDO → [OpenAI] → Neo4j + PostgreSQL 
  → CONCLUIDO/ERRO
```

Status atualizado em `Candidato.status_cv`, frontend faz polling.

### 5. LGPD Compliance

**Regras invioláveis**:

- ✅ Limpar CPF, RG, datas antes de enviar para IA
- ✅ Registrar TODAS as ações em `HistoricoAcao`
- ✅ Usar `SET_NULL` em FKs para preservar histórico
- ✅ Presigned URLs com TTL para S3
- ✅ Deletar em cascata: PostgreSQL → Neo4j → S3

### 6. Autenticação com Roles

```python
class Profile.Role:
    CANDIDATO = 'candidato'  # Acesso limitado ao próprio perfil
    RH = 'rh'                # Acesso total (vagas, matching, candidatos)
    ADMIN = 'admin'          # Acesso total + Django Admin
```

---

## ⚠️ Armadilhas Comuns

### 1. Tracar View Esperando Task Completar

❌ **ERRADO**:
```python
def view_processar(request):
    resultado = processar_cv_task(candidato_id)  # Bloqueia!
    return JsonResponse(resultado)
```

✅ **CORRETO**:
```python
def view_processar(request):
    processar_cv_task.delay(candidato_id)  # Assíncrono
    return JsonResponse({'status': 'enfileirado'})
```

### 2. Hardcode de Credenciais

❌ **ERRADO**:
```python
SECRET_KEY = 'abc123xyz789'
OPENAI_KEY = 'sk-...'
```

✅ **CORRETO**:
```python
from decouple import config

SECRET_KEY = config('SECRET_KEY')  # Do .env
OPENAI_KEY = config('OPENAI_API_KEY')
```

### 3. Esquecer de Limpar Dados Pessoais

❌ **ERRADO**:
```python
texto = extrair_texto_cv(...)
cv_parseado = chamar_openai(texto)  # CPF exposto!
```

✅ **CORRETO**:
```python
texto = extrair_texto_cv(...)
texto_limpo = limpar_dados_pessoais(texto)
cv_parseado = chamar_openai(texto_limpo)
```

### 4. Cascade Delete

❌ **ERRADO**:
```python
candidato = ForeignKey(Candidato, on_delete=models.CASCADE)
# Se deletar candidato, auditoria desaparece (LGPD problem!)
```

✅ **CORRETO**:
```python
candidato = ForeignKey(Candidato, on_delete=models.SET_NULL, null=True)
# Se deletar candidato, auditoria permanece (anonimizada)
```

### 5. Guardar URL S3 em Campo

❌ **ERRADO**:
```python
class Candidato(models.Model):
    cv_url = models.URLField()  # Expõe a URL pública!
```

✅ **CORRETO**:
```python
class Candidato(models.Model):
    cv_s3_key = models.CharField()  # Apenas a chave
    # URL é gerada via presigned_url com TTL
```

---

## 🚀 Workflow Típico para Novo Feature

### 1. Design (Arquitetura)

- Quais models precisam?
- Quais validações?
- Precisa Neo4j?
- Precisa Celery?
- Qual role de usuário tem acesso?

### 2. Implementação (Backend)

1. Criar model em `core/models.py`
2. Criar migration: `makemigrations && migrate`
3. Criar service em `core/services/nuevo_service.py`
4. Criar view em `core/views.py`
5. Registrar em `core/urls.py`
6. Registrar action em `HistoricoAcao`

### 3. Testes

- Unit test do service (mock Neo4j, S3)
- Test da view (autenticação, validação)
- Test LGPD (dados não são logados, audit trail existe)
- `python manage.py test`

### 4. Frontend

- Template HTML com Bootstrap 5
- Dark mode: usar CSS variables
- HTMX: se requisição AJAX sem reload de página
- Sempre: `{% csrf_token %}`

### 5. Deploy

- Variáveis de ambiente no Render Dashboard
- Migration automática: `python manage.py migrate --no-input`
- Logs: `celery worker -l info`

---

## 📞 Suporte Rápido

**Pergunta**: Como implementar um novo campo no Candidato?

1. Ler `ARCHITECTURE.md` → "Camada de Modelos"
2. Ver exemplo de Candidato.modelo
3. Adicionar field em `core/models.py`
4. Rodar `makemigrations && migrate`
5. Atualizar `core/admin.py` se precisa editar no admin

---

**Pergunta**: Como disparar uma task Celery?

1. Ler `ARCHITECTURE.md` → "Processamento Assíncrono (Celery)"
2. Ver exemplo de `processar_cv_task`
3. Copiar padrão: `@shared_task(bind=True, max_retries=3)`
4. Usar: `minha_task.delay(param)`
5. Frontend faz polling do status

---

**Pergunta**: Como fazer busca avançada com Neo4j?

1. Ler `ARCHITECTURE.md` → "Banco de Grafos (Neo4j)"
2. Ler exemplo de Cypher queries
3. Implementar em Service com `Neo4jConnection()`
4. Testar no Django shell: `python manage.py shell`

---

## 📦 Versões Principais

- **Django**: 5.0
- **Python**: 3.10+
- **PostgreSQL**: 15+
- **Neo4j AuraDB**: 5.x
- **Redis**: 7.0+
- **Celery**: 5.3+
- **OpenAI**: Latest (GPT-4o-mini)

---

## 🔗 Links Rápidos

- **README.md**: Visão geral do projeto
- **ARCHITECTURE.md**: Detalhes técnicos (este é o principal!)
- **PATTERNS.md**: Exemplos prontos para copiar/colar
- **Django Docs**: https://docs.djangoproject.com
- **Celery Docs**: https://docs.celeryproject.io
- **Neo4j Docs**: https://neo4j.com/docs/

---

**Última atualização**: Março 2025  
**Status**: ✅ Production-Ready  
**Manutenedor**: GSD Agents
