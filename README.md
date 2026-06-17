# HRTech — Motor de Recrutamento Inteligente com Grafos e IA

<p align="center">
  <strong>Matching de candidatos e vagas em 3 camadas usando Neo4j, Django e GPT-4</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Django-5.x-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django">
  <img src="https://img.shields.io/badge/Neo4j-AuraDB-008CC1?style=for-the-badge&logo=neo4j&logoColor=white" alt="Neo4j">
  <img src="https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=for-the-badge&logo=openai&logoColor=white" alt="OpenAI">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Celery-5.x-37814A?style=flat-square&logo=celery&logoColor=white" alt="Celery">
  <img src="https://img.shields.io/badge/Redis-7+-DC382D?style=flat-square&logo=redis&logoColor=white" alt="Redis">
  <img src="https://img.shields.io/badge/HTMX-1.9-3366CC?style=flat-square&logo=htmx&logoColor=white" alt="HTMX">
  <img src="https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=flat-square&logo=bootstrap&logoColor=white" alt="Bootstrap">
  <img src="https://img.shields.io/badge/Deploy-Render-46E3B7?style=flat-square&logo=render&logoColor=white" alt="Render">
  <img src="https://img.shields.io/badge/Dark_Mode-Suportado-1a1d23?style=flat-square&logo=dark-reader&logoColor=white" alt="Dark Mode">
  <img src="https://img.shields.io/badge/LGPD-Compliant-00875A?style=flat-square&logo=shield&logoColor=white" alt="LGPD">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" alt="License">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Neo4j_Certified_Professional-✓-008CC1?style=flat-square&logo=neo4j&logoColor=white" alt="Neo4j Certified Professional">
  <img src="https://img.shields.io/badge/Graph_Data_Analyst-✓-008CC1?style=flat-square&logo=neo4j&logoColor=white" alt="Graph Data Analyst">
</p>

---

## 📌 Sobre o Projeto

O **HRTech** é uma plataforma ATS (Applicant Tracking System) multi-tenant que combina **persistência poliglota** (PostgreSQL + Neo4j) e **IA generativa** (GPT-4) para automatizar e otimizar o recrutamento técnico.

O diferencial está no **motor de matching de 3 camadas** que calcula a compatibilidade entre candidatos e vagas usando **traversal de grafos** no Neo4j, ao invés de simples busca por keywords. Habilidades extraídas dos currículos por IA são persistidas como nós em um grafo de conhecimento, onde relações de **similaridade** entre skills (ex: `React ←SIMILAR_A→ Vue.js`) enriquecem a recomendação para muito além do match direto.

### O Problema que Resolve

| Antes (manual) | Depois (HRTech) |
|:---|:---|
| Recruiter lê 100+ CVs por vaga | Upload de CV → extração automática de skills via GPT-4 |
| Matching subjetivo baseado em keywords | Score 0-100 calculado via traversal de grafo em 3 camadas |
| Sem rastreabilidade de decisões | Auditoria completa: snapshot de skills, scores e gaps por match |
| Planilhas para tracking de pipeline | Dashboard Kanban interativo com drag-and-drop |
| Perguntas de entrevista genéricas | IA gera 3 perguntas personalizadas com base nos gaps de skills |

---

## 🧠 Como o Matching Funciona

O coração do HRTech é um algoritmo de **3 camadas** que roda sobre o grafo de skills no Neo4j:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SCORE FINAL (0-100)                             │
│                                                                     │
│  ┌──────────────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│  │   CAMADA 1 (60%)     │  │  CAMADA 2 (25%) │  │ CAMADA 3 (15%)│  │
│  │   Skills Diretas     │  │  Similaridade   │  │ Perfil        │  │
│  │                      │  │                 │  │               │  │
│  │  "Candidato tem      │  │ "Candidato tem  │  │ "Candidato é  │  │
│  │   Python nível 4,    │  │  Tableau, que   │  │  Pleno, vaga  │  │
│  │   vaga pede nível 3" │  │  é similar a    │  │  pede Sênior" │  │
│  │                      │  │  Power BI (0.8)"│  │               │  │
│  │  ✓ Match direto      │  │  ✓ Match parcial│  │  ✓ Penalidade │  │
│  │  ✓ Decaimento de     │  │  ✓ Peso da      │  │    proporcional│  │
│  │    15%/ano por        │  │    similaridade │  │  ✓ Área de    │  │
│  │    skill defasada     │  │    do grafo     │  │    atuação    │  │
│  └──────────────────────┘  └─────────────────┘  └───────────────┘  │
│                                                                     │
│  Desempate: Disponibilidade → Menor gap senioridade → Data cadastro │
│  Threshold: Score < 40 = filtrado automaticamente                   │
└─────────────────────────────────────────────────────────────────────┘
```

### O Grafo de Skills (Neo4j)

```
                    ┌─────────┐
          ┌────────→│  React  │←───────┐
          │  nivel:4│         │        │ SIMILAR_A
          │         └─────────┘        │ peso: 0.85
          │                            ▼
    ┌───────────┐              ┌─────────────┐
    │ Candidato │              │   Vue.js     │
    │  "Maria"  │              └─────────────┘
    │  uuid:... │                      ▲
    └───────────┘                      │ SIMILAR_A
          │                            │ peso: 0.70
          │  nivel:3           ┌─────────────┐
          └───────────────────→│  Angular    │
                               └─────────────┘
                                       ▲
                                       │ REQUER (nivel_min:3)
                               ┌─────────────┐
                               │  Vaga "Dev  │
                               │  Frontend"  │
                               └─────────────┘
```

**Camada 1** encontra o match direto `Maria → React → Vaga`. **Camada 2** descobre que `Maria tem Angular, que é SIMILAR_A Vue.js`, enriquecendo o score mesmo sem match direto. **Camada 3** ajusta pela senioridade e área de atuação.

### Query Cypher Principal

```cypher
MATCH (c:Candidato {uuid: $uuid})-[r:TEM_HABILIDADE]->(h:Habilidade)
OPTIONAL MATCH (h)-[sim:SIMILAR_A]-(h2:Habilidade)
RETURN h.nome AS skill, r.nivel AS nivel,
       r.anos_experiencia AS anos, r.ano_ultima_utilizacao AS ano_uso,
       COLLECT({similar: h2.nome, peso: sim.peso}) AS similares
```

> **Decisão arquitetural:** Uma query Cypher única com `OPTIONAL MATCH` ao invés de múltiplas round-trips. O Neo4j otimiza o traversal do grafo; a agregação final (scores, penalizações, desempate) é feita em Python para flexibilidade.

---

## 🏗️ Arquitetura

```
┌───────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                    │
│                Django Templates + Bootstrap 5 + HTMX                  │
│              Dashboard Kanban │ Chart.js │ Dark Mode                  │
└──────────────────────────┬────────────────────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────────────────┐
│                       DJANGO 5 BACKEND                                │
│                                                                       │
│  ┌──────────────┐   ┌───────────────┐   ┌──────────────────────────┐ │
│  │  Views/URLs  │   │ Service Layer │   │    Celery Workers        │ │
│  │  (HTMX)     │   │               │   │  ┌────────────────────┐  │ │
│  └──────────────┘   │ MatchingEngine│   │  │ processar_cv_task  │  │ │
│                     │ InterviewSvc  │   │  │ extração GPT-4     │  │ │
│                     │ CandidateSvc  │   │  │ sync Neo4j         │  │ │
│                     └───────────────┘   │  └────────────────────┘  │ │
└─────┬──────────────────────┬────────────┴──────────┬─────────────────┘
      │                      │                       │
      ▼                      ▼                       ▼
┌───────────┐       ┌──────────────┐       ┌─────────────────────┐
│ PostgreSQL│       │  Neo4j       │       │       Redis         │
│           │       │  AuraDB      │       │                     │
│ Candidatos│       │              │       │  Celery Broker      │
│ Vagas     │       │ :Candidato   │       │  Cache de sessões   │
│ Auditoria │       │ :Habilidade  │       │  Rate limiting      │
│ Orgs      │       │ :SIMILAR_A   │       │                     │
└───────────┘       └──────────────┘       └─────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌─────────┐ ┌─────────┐ ┌──────────┐
         │ OpenAI  │ │  AWS S3 │ │pdfplumber│
         │ GPT-4o  │ │ Storage │ │ + OCR    │
         │ mini    │ │ de CVs  │ │          │
         └─────────┘ └─────────┘ └──────────┘
```

### Decisões Arquiteturais

| Decisão | Alternativa Rejeitada | Justificativa |
|:--------|:----------------------|:--------------|
| **Persistência Poliglota** (Postgres + Neo4j) | Tudo em Postgres com JSON | Grafos nativos permitem traversal O(relações) vs O(n²) para similaridade |
| **UUID como chave de sincronia** entre bancos | Auto-increment | Identificação única cross-database sem acoplamento |
| **Celery + Redis** para processamento de CVs | Processamento síncrono | Upload de CV leva 5-15s (GPT + parsing) — bloquearia o request HTTP |
| **Cálculos no Neo4j, agregação em Python** | Tudo no Cypher | Neo4j é ótimo em traversal, Python dá flexibilidade para regras de negócio |
| **Snapshot de skills na auditoria** | Referência ao estado atual | LGPD exige reprodutibilidade — o cálculo deve ser explicável meses depois |
| **Presigned URLs (S3)** para CVs | Bucket público | CVs nunca ficam expostos; URLs expiram em 15 minutos |

---

## 📋 Funcionalidades

### Upload & Processamento de CVs
| Feature | Descrição |
|:--------|:----------|
| Upload de PDF | Validação de magic bytes, tamanho (10MB) e content-type |
| Extração de texto | `pdfplumber` + Tesseract OCR para PDFs escaneados |
| Extração de skills via IA | GPT-4o-mini identifica habilidades técnicas, soft skills e níveis |
| Persistência no grafo | Skills são criadas como nós `:Habilidade` com relação `TEM_HABILIDADE` no Neo4j |
| Processamento assíncrono | Celery task com retry e timeout — não bloqueia o HTTP |

### Motor de Matching
| Feature | Descrição |
|:--------|:----------|
| Matching de 3 camadas | Skills diretas (60%) + Similaridade (25%) + Perfil (15%) |
| Decaimento temporal | Skills defasadas perdem 15%/ano (ex: jQuery com 3 anos → -45%) |
| Match por similaridade | Grafo `SIMILAR_A` descobre skills equivalentes (Tableau ↔ Power BI) |
| Gap analysis | Identifica skills ausentes e abaixo do nível mínimo da vaga |
| Auditoria completa | Snapshot do cálculo salvo em `AuditoriaMatch` (LGPD) |
| Threshold configurável | Score mínimo padrão: 40 (filtra ruído) |

### Entrevistas com IA
| Feature | Descrição |
|:--------|:----------|
| Geração de perguntas | 3 perguntas técnicas personalizadas baseadas nos **gaps de skills** do candidato |
| Smart prompting | Se não há gaps, gera perguntas avançadas de validação |
| Cache inteligente | Segunda geração para o mesmo candidato retorna em <100ms (leitura do banco) |
| LGPD-safe | Nenhum dado pessoal (nome, email) é enviado à OpenAI — apenas skill gaps |

### Gestão de Recrutamento
| Feature | Descrição |
|:--------|:----------|
| Dashboard Kanban | Pipeline visual com drag-and-drop (Triagem → Entrevista → Aprovado) |
| Cadastro de vagas | Skills obrigatórias/desejáveis com nível mínimo (1-5) |
| Busca avançada | Filtros por skills (AND/OR), senioridade, disponibilidade, nível mínimo |
| Candidatos similares | Encontra perfis parecidos via traversal do grafo |
| Comentários e favoritos | Sistema colaborativo de notas por candidato |
| Exportação Excel | Rankings e candidatos exportáveis com filtros aplicados |

### Dashboard & Analytics
| Feature | Descrição |
|:--------|:----------|
| Métricas e KPIs | Candidatos por etapa, distribuição por senioridade, tendências |
| Gráficos interativos | Chart.js para visualizações do funil de recrutamento |
| Relatórios imprimíveis | Perfil do candidato formatado para impressão/PDF |

### Multi-Tenancy & Segurança
| Feature | Descrição |
|:--------|:----------|
| Isolamento por organização | Todas as views e queries filtram por `organization` do usuário |
| Proteção contra IDOR | 16+ views com `get_object_or_404(..., organization=user_org)` |
| Neo4j escopo de tenant | Queries Cypher filtram por `{organization_id: $org_id}` |
| Rate limiting | Proteção contra abuse em upload e endpoints caros |
| CSRF em todos os forms | Django CSRF + `@csrf_protect` em views POST |
| LGPD compliant | Exclusão de dados, exportação, auditoria de acesso, PII masking |
| Headers de segurança | HSTS, X-Frame-Options DENY, XSS Filter, SSL redirect |
| Credenciais seguras | 100% via `python-decouple`, zero hardcoded |

### UX & Interface
| Feature | Descrição |
|:--------|:----------|
| Dark Mode | Tema escuro com CSS variables, sincronizado em todo o sistema |
| HTMX | Interatividade sem recarregar a página (polling, swaps inline) |
| Responsivo | Mobile-first com Bootstrap 5 |
| Admin customizado | `django-admin-interface` com tema coerente |

---

## 🔧 Tech Stack

### Backend
| Tecnologia | Versão | Uso |
|:-----------|:-------|:----|
| Python | 3.10+ | Linguagem principal |
| Django | 5.x | Framework full-stack |
| Celery | 5.x | Task queue assíncrona (processamento de CVs, extração de skills) |
| Pydantic | 2.x | Validação e contrato de dados para respostas da OpenAI |
| Gunicorn | 21.x | WSGI server de produção |

### Bancos de Dados
| Tecnologia | Tipo | Uso |
|:-----------|:-----|:----|
| PostgreSQL 15+ | Relacional (ACID) | Candidatos, Vagas, Auditoria, Organizations |
| Neo4j AuraDB | Grafo | Skills, relações `TEM_HABILIDADE` e `SIMILAR_A` |
| Redis 7+ | Key-Value | Celery broker, cache de sessões, rate limiting |

### Integrações Externas
| Serviço | Uso |
|:--------|:----|
| OpenAI GPT-4o-mini | Extração de skills de CVs + geração de perguntas de entrevista |
| AWS S3 | Storage seguro de currículos (presigned URLs, 15min TTL) |
| pdfplumber + Tesseract | Parsing de PDFs e OCR para documentos escaneados |

### Frontend
| Tecnologia | Uso |
|:-----------|:----|
| Bootstrap 5.3 | Framework CSS responsivo |
| HTMX 1.9 | Interatividade sem JavaScript pesado |
| Chart.js | Gráficos do dashboard de analytics |
| Bootstrap Icons | Iconografia consistente |
| D3.js | Animações na landing page |

### DevOps & Deploy
| Ferramenta | Uso |
|:-----------|:----|
| Render | PaaS (Web Service + PostgreSQL) |
| Upstash | Redis serverless (Celery broker) |
| Docker | Container para testes (`Dockerfile.test` com Python 3.11) |
| WhiteNoise | Serving de estáticos em produção |

---

## 🚀 Instalação Local

### Pré-requisitos

- Python 3.10+ (ou Docker)
- PostgreSQL 15+
- Redis 7+ (ou Docker)
- Conta Neo4j AuraDB ([free tier](https://neo4j.com/cloud/platform/aura-graph-database/))
- Chave API OpenAI (opcional — use `OPENAI_MOCK_MODE=True` para dev)

### Setup

```bash
# 1. Clone o repositório
git clone https://github.com/joao-luizzz/hrtech.git
cd hrtech

# 2. Crie o ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais (SECRET_KEY, DB_*, NEO4J_*, etc.)

# 5. Execute as migrations
python manage.py migrate

# 6. Colete arquivos estáticos
python manage.py collectstatic --noinput

# 7. (Opcional) Popule o banco com dados de teste (PostgreSQL e Neo4j)
python scripts/popular_banco.py

# 8. (Opcional) Semeie as relações de similaridade de habilidades no Neo4j
python manage.py seed_skill_similarities --force

# 9. (Opcional) Reprocesse todos os currículos cadastrados para atualizar o grafo Neo4j
python manage.py reprocess_cvs --all --sync

# 10. Inicie o servidor
python manage.py runserver
```

```bash
# Em terminais separados:
celery -A hrtech worker -l info -Q default,openai    # Worker
celery -A hrtech beat -l info                         # Beat scheduler
```

Acesse: **http://localhost:8000**

### Rodando Testes (via Docker)

O projeto inclui um `Dockerfile.test` que isola o ambiente de testes com Python 3.11:

```bash
# Build da imagem
docker build -t hrtech-test -f Dockerfile.test .

# Roda os testes
docker run --rm \
  -e SECRET_KEY=test-key \
  -e DB_NAME=t -e DB_USER=t -e DB_PASSWORD=t -e DB_HOST=localhost \
  -e NEO4J_URI=bolt://localhost:7687 -e NEO4J_USER=t -e NEO4J_PASSWORD=t \
  -e REDIS_URL=redis://localhost:6379 -e DEBUG=True \
  -e OPENAI_API_KEY=sk-dummy \
  hrtech-test
```

> Os testes usam SQLite em memória e mocks para Neo4j/OpenAI — não precisam de serviços externos.

---

## ☁️ Deploy no Render

O projeto inclui `render.yaml` com 3 serviços:

| Serviço | Tipo | Tier |
|:--------|:-----|:-----|
| `hrtech-web` | Gunicorn | Free/Starter |
| `hrtech-worker` | Celery Worker | Free/Starter |
| `hrtech-beat` | Celery Beat | Free/Starter |

```bash
# No Render: New + → Blueprint → Apontar para este repositório
# Configurar variáveis de ambiente obrigatórias antes do deploy
```

---

## 📁 Estrutura do Projeto

```
hrtech/
├── core/                          # App principal
│   ├── matching.py                # Motor de matching de 3 camadas (919 linhas)
│   ├── neo4j_connection.py        # Singleton de conexão Neo4j com pool
│   ├── schemas.py                 # Contrato Pydantic para respostas OpenAI
│   ├── views.py                   # Views Django (1600+ linhas)
│   ├── models.py                  # Candidato, Vaga, Organization, AuditoriaMatch
│   ├── tasks.py                   # Celery tasks (processar_cv, sync Neo4j)
│   ├── services/                  # Service layer
│   │   ├── matching_service.py    # Orquestração do matching
│   │   ├── interview_openai_service.py  # Geração de perguntas via GPT-4
│   │   ├── interview_neo4j_service.py   # Skill gaps via grafo
│   │   ├── candidate_search_service.py  # Busca avançada com filtros
│   │   ├── cv_upload_service.py   # Upload + validação de PDFs
│   │   └── candidate_portal_service.py  # Portal do candidato
│   ├── tests/                     # 14 arquivos de teste
│   │   ├── test_matching_engine.py      # Testes do motor de matching
│   │   ├── test_tenant_isolation.py     # Testes de isolamento multi-tenant
│   │   ├── test_interview_*.py          # Testes de geração de perguntas
│   │   └── test_security_pentest.py     # Testes de penetração
│   └── templates/core/            # Templates Django + HTMX partials
│
├── hrtech/                        # Configurações do projeto
│   ├── settings.py                # Settings com python-decouple
│   ├── settings_test.py           # Settings para testes (SQLite + mocks)
│   └── celery.py                  # Configuração do Celery
│
├── scripts/                       # Utilitários
│   ├── popular_banco.py           # Seed de dados (PostgreSQL + Neo4j)
│   └── tenant_isolation_checker.py # Auditor de isolamento de tenant
│
├── Dockerfile.test                # Container Python 3.11 para testes
├── Procfile                       # Processos para Render/Heroku
├── render.yaml                    # Blueprint de deploy (3 serviços)
├── requirements.txt               # Dependências Python
└── .env.example                   # Template de variáveis de ambiente
```

---

## 🗺️ Roadmap

- [x] Upload e extração automática de skills (GPT-4)
- [x] Grafo de conhecimento no Neo4j (skills + similaridade)
- [x] Motor de matching de 3 camadas com auditoria
- [x] Dashboard Kanban com drag-and-drop
- [x] Dashboard de analytics com Chart.js
- [x] Área do candidato (portal, aplicações, vinculação)
- [x] Sistema de comentários e favoritos
- [x] Exportação para Excel (candidatos + rankings)
- [x] Busca avançada com filtros por skills (Neo4j)
- [x] Geração de perguntas de entrevista com IA (GPT-4o-mini)
- [x] Multi-tenant isolation (16+ views protegidas)
- [x] LGPD compliance (exclusão, exportação, auditoria)
- [x] Dark Mode em todo o sistema
- [x] Landing page com D3.js
- [ ] Autenticação com Google/LinkedIn OAuth
- [ ] API REST pública para integrações
- [ ] Notificações por email (Celery Beat)
- [ ] Integração com LinkedIn para importar perfis
- [ ] CI/CD com GitHub Actions

---

## 📜 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## 👤 Autor

**João Luiz** — [GitHub](https://github.com/joao-luizzz)

Neo4j Certified Professional · Graph Data Analyst

---

<p align="center">
  <sub>Construído com Django, Neo4j e OpenAI</sub>
  <br>
  <sub>🧠 Matching por Grafos · 🤖 IA Generativa · 🔒 Multi-Tenant · 🌙 Dark Mode</sub>
</p>
