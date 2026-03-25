# HRTech - Sistema Inteligente de Recrutamento

<p align="center">
  <strong>Matching inteligente entre candidatos e vagas usando grafos e IA generativa</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Django-5.0-092E20?logo=django&logoColor=white" alt="Django">
  <img src="https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Neo4j-AuraDB-008CC1?logo=neo4j&logoColor=white" alt="Neo4j">
  <img src="https://img.shields.io/badge/Redis-7.0-DC382D?logo=redis&logoColor=white" alt="Redis">
  <img src="https://img.shields.io/badge/OpenAI-GPT--4-412991?logo=openai&logoColor=white" alt="OpenAI">
  <img src="https://img.shields.io/badge/Bootstrap-5.3-7952B3?logo=bootstrap&logoColor=white" alt="Bootstrap">
  <img src="https://img.shields.io/badge/HTMX-1.9-3366CC?logo=htmx&logoColor=white" alt="HTMX">
  <img src="https://img.shields.io/badge/Deploy-Render-46E3B7?logo=render&logoColor=white" alt="Render">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Dark_Mode-Suportado-1a1d23?logo=dark-reader&logoColor=white" alt="Dark Mode">
  <img src="https://img.shields.io/badge/LGPD-Compliant-00875A?logo=shield&logoColor=white" alt="LGPD">
  <img src="https://img.shields.io/badge/License-MIT-yellow?logo=opensourceinitiative&logoColor=white" alt="License">
</p>

---

## Sobre o Projeto

O **HRTech** é uma plataforma de recrutamento que utiliza **persistência poliglota** e **IA generativa** para automatizar o processo de matching entre candidatos e vagas.

O sistema extrai habilidades de currículos usando GPT-4 e calcula compatibilidade através de um grafo de conhecimento no Neo4j, eliminando horas de análise manual de CVs.

### Problema Resolvido

| Antes | Depois |
|-------|--------|
| Recrutadores analisam CVs manualmente | Upload do CV com extração automática de skills |
| Planilhas para tracking de candidatos | Dashboard Kanban visual |
| Matching subjetivo baseado em keywords | Score de compatibilidade calculado via grafo |
| Processo lento e sujeito a viés | Recomendações objetivas e auditáveis |

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                │
│              Django Templates + Bootstrap 5 + HTMX              │
│                    Dashboard Kanban + Chart.js                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DJANGO 5 BACKEND                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Views     │  │   Models    │  │   Celery Tasks          │  │
│  │   URLs      │  │   Forms     │  │   (Processamento CV)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                  │                      │
         ▼                  ▼                      ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐
│  PostgreSQL │    │   Neo4j     │    │         Redis           │
│  ─────────  │    │  AuraDB     │    │       ─────────         │
│  Candidatos │    │  ─────────  │    │  Celery Broker + Cache  │
│  Vagas      │    │  Grafo de   │    │                         │
│  Auditoria  │    │  Skills     │    │                         │
└─────────────┘    └─────────────┘    └─────────────────────────┘
                          │
                          ▼
┌───────────────────────────────────────────────────────────────┐
│                      INTEGRAÇÕES                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ OpenAI GPT-4│  │   AWS S3    │  │   pdfplumber + OCR      │ │
│  │ Extração de │  │  Storage    │  │   Leitura de PDFs       │ │
│  │   Skills    │  │  de CVs     │  │                         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

### Decisões Arquiteturais

| Decisão | Justificativa |
|---------|---------------|
| **Persistência Poliglota** | PostgreSQL para ACID, Neo4j para traversal de grafos |
| **UUID como Chave de Sincronia** | Identificação única entre bancos diferentes |
| **Neo4j AuraDB** | Grafo gerenciado na nuvem, zero ops overhead |
| **Celery + Redis** | Processamento de CVs sem bloquear requests HTTP |
| **WhiteNoise** | Serve estáticos em produção sem CDN adicional |
| **Presigned URLs (S3)** | CVs nunca ficam públicos, LGPD compliant |

---

## Tech Stack

### Backend
| Tecnologia | Versão | Uso |
|------------|--------|-----|
| Python | 3.10 | Linguagem principal |
| Django | 5.0 | Framework web full-stack |
| Celery | 5.x | Task queue para processamento assíncrono |
| Gunicorn | 21.x | WSGI server de produção |

### Bancos de Dados
| Tecnologia | Tipo | Uso |
|------------|------|-----|
| PostgreSQL | Relacional | Candidatos, Vagas, Auditoria (ACID) |
| Neo4j AuraDB | Grafo | Skills e relacionamentos para matching |
| Redis | Key-Value | Broker Celery + cache de sessões |

### Integrações Externas
| Serviço | Uso |
|---------|-----|
| OpenAI GPT-4 | Extração inteligente de habilidades do CV |
| AWS S3 | Storage seguro de currículos |
| pdfplumber | Parsing de PDFs |
| Tesseract OCR | Leitura de CVs escaneados |

### Frontend
| Tecnologia | Uso |
|------------|-----|
| Bootstrap 5 | Framework CSS responsivo |
| HTMX | Interatividade sem JavaScript pesado |
| Chart.js | Gráficos do dashboard de analytics |
| Bootstrap Icons | Iconografia consistente |
| Dark Mode | Tema escuro com CSS variables |

### DevOps & Deploy
| Ferramenta | Uso |
|------------|-----|
| Render | PaaS para deploy (Web + PostgreSQL) |
| Upstash | Redis serverless (Celery broker) |
| WhiteNoise | Serving de arquivos estáticos |
| GitHub | Versionamento e CI/CD |

---

## Funcionalidades

### Core
- **Upload de Currículos** - Suporte a PDF com extração automática de texto
- **Extração de Skills com IA** - GPT-4 identifica habilidades técnicas e soft skills
- **Grafo de Conhecimento** - Neo4j armazena e relaciona skills entre si
- **Matching Inteligente** - Algoritmo de compatibilidade candidato ↔ vaga
- **Busca de Candidatos Similares** - Encontra perfis semelhantes baseado em skills

### Gestão de Recrutamento
- **Dashboard Kanban** - Pipeline visual de recrutamento com drag-and-drop
- **Cadastro de Vagas** - Skills requeridas e peso de cada uma
- **Sistema de Tags** - Categorize candidatos com etiquetas coloridas
- **Comentários e Notas** - Adicione observações em cada candidato
- **Auditoria de Matches** - Histórico completo das recomendações

### Dashboard & Analytics
- **Dashboard RH** - Métricas e KPIs do processo de recrutamento
- **Gráficos Interativos** - Chart.js para visualização de dados
- **Distribuição por Senioridade** - Análise do pool de candidatos
- **Tendências Temporais** - Acompanhe a evolução ao longo do tempo
- **Funil de Etapas** - Visualize a conversão entre etapas

### Área do Candidato
- **Portal do Candidato** - Área dedicada para acompanhar candidaturas
- **Minhas Aplicações** - Visualize status de cada vaga aplicada
- **Perfil Editável** - Atualize informações e habilidades

### UX & Interface
- **Dark Mode** - Tema escuro sincronizado em todo o sistema
- **Design Responsivo** - Funciona em desktop, tablet e mobile
- **Admin Customizado** - Painel administrativo estilizado
- **HTMX** - Interatividade sem recarregar a página

### Segurança & Compliance
- **Autenticação Completa** - Login, cadastro, recuperação de senha (django-allauth)
- **LGPD Compliant** - CVs em bucket privado, acesso via presigned URL
- **Logs sem PII** - Dados pessoais nunca são logados
- **Credenciais Seguras** - Todas via variáveis de ambiente

---

## Modelo de Dados

### PostgreSQL (Relacional)

```sql
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Candidato     │     │      Vaga       │     │ AuditoriaMatch  │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (UUID)    PK │     │ id (UUID)    PK │     │ id           PK │
│ nome            │     │ titulo          │     │ candidato_id FK │
│ email           │     │ descricao       │     │ vaga_id      FK │
│ telefone        │     │ skills_req JSON │     │ score           │
│ cv_url          │     │ status          │     │ created_at      │
│ skills_json     │     │ created_at      │     │ observacoes     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Neo4j (Grafo)

```cypher
(:Candidato {uuid, nome})
        │
        │ [:TEM_SKILL {nivel}]
        ▼
    (:Skill {nome, categoria})
        ▲
        │ [:REQUER_SKILL {peso}]
        │
(:Vaga {uuid, titulo})
```

O matching é calculado por traversal no grafo:
```cypher
MATCH (c:Candidato)-[:TEM_SKILL]->(s:Skill)<-[:REQUER_SKILL]-(v:Vaga)
WHERE v.uuid = $vaga_uuid
RETURN c, COUNT(s) as skills_match, SUM(s.peso) as score
ORDER BY score DESC
```

---

## Instalação Local

### Pré-requisitos

- Python 3.10+
- PostgreSQL 15+
- Redis 7+ (ou Docker)
- Conta Neo4j AuraDB (free tier disponível)
- Chave API OpenAI (opcional para dev)

### Setup

```bash
# 1. Clone o repositório
git clone https://github.com/joao-luizzz/hrtech.git
cd hrtech

# 2. Crie o ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais
```

### Variáveis de Ambiente

```env
# Django
SECRET_KEY=sua-chave-secreta-50-caracteres-minimo
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL
DB_NAME=hrtech
DB_USER=postgres
DB_PASSWORD=sua-senha
DB_HOST=localhost
DB_PORT=5432

# Neo4j AuraDB
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=sua-senha-neo4j

# Redis (Celery)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# OpenAI (opcional - use mock mode para dev)
OPENAI_API_KEY=sk-xxxxx
OPENAI_MOCK_MODE=True  # Gera skills mockadas sem gastar créditos

# AWS S3 (opcional)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=hrtech-cvs
```

### Executando

```bash
# Execute as migrations
python manage.py migrate

# Colete arquivos estáticos
python manage.py collectstatic --noinput

# (Opcional) Popule com dados de teste
python popular_banco.py

# Inicie o servidor Django
python manage.py runserver

# Em outro terminal, inicie o Celery
celery -A hrtech worker -l info
```

Acesse: **http://localhost:8000**

---

## Deploy no Render

### Serviços Utilizados

| Serviço | Tier | Uso |
|---------|------|-----|
| Render Web Service | Free/Starter | Aplicação Django |
| Render PostgreSQL | Free | Banco relacional |
| Upstash Redis | Free | Celery broker |
| Neo4j AuraDB | Free | Grafo de skills |

### Variáveis no Render Dashboard

```
SECRET_KEY         → Gerar com: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DEBUG              → False
ALLOWED_HOSTS      → seu-app.onrender.com
DB_NAME            → (do Render PostgreSQL)
DB_USER            → (do Render PostgreSQL)
DB_PASSWORD        → (do Render PostgreSQL)
DB_HOST            → (do Render PostgreSQL)
NEO4J_URI          → (do Neo4j AuraDB)
NEO4J_USER         → neo4j
NEO4J_PASSWORD     → (sua senha)
CELERY_BROKER_URL  → (do Upstash Redis)
OPENAI_API_KEY     → (sua chave)
```

### Build & Start Commands

**Build Command:**
```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
```

**Start Command:** *(já no Procfile)*
```bash
gunicorn hrtech.wsgi --bind 0.0.0.0:$PORT --workers 2
```

---

## Estrutura do Projeto

```
hrtech/
├── core/                      # App principal
│   ├── migrations/            # Migrations do banco
│   ├── templates/core/        # Templates do app
│   │   ├── candidatos/        # Busca e similares
│   │   ├── candidato/         # Área do candidato
│   │   ├── vagas/             # CRUD de vagas
│   │   └── partials/          # Componentes HTMX
│   ├── models.py              # Candidato, Vaga, Tag, Comentario
│   ├── views.py               # Views e lógica de negócio
│   ├── tasks.py               # Tasks Celery (processar_cv)
│   ├── neo4j_connection.py    # Singleton de conexão Neo4j
│   └── openai_service.py      # Extração de skills via GPT-4
│
├── hrtech/                    # Configurações do projeto
│   ├── settings.py            # Settings com python-decouple
│   ├── urls.py                # Rotas principais
│   ├── celery.py              # Configuração Celery
│   └── wsgi.py                # Entry point produção
│
├── templates/                 # Templates globais
│   ├── base.html              # Layout base com dark mode
│   ├── admin/                 # Admin customizado
│   └── account/               # Templates de autenticação
│
├── static/                    # Arquivos estáticos
│   ├── css/                   # CSS customizado (admin)
│   └── js/                    # JavaScript (dark mode)
│
├── staticfiles/               # Coletados pelo collectstatic
│
├── Procfile                   # Start command (Render/Heroku)
├── runtime.txt                # Versão Python (3.10.12)
├── requirements.txt           # Dependências Python
├── .env.example               # Template de variáveis
└── manage.py                  # CLI Django
```

---

## Segurança

| Medida | Implementação |
|--------|---------------|
| Credenciais | Todas via `python-decouple`, zero hardcoded |
| HTTPS | `SECURE_SSL_REDIRECT = True` em produção |
| Cookies | `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` |
| Headers | HSTS, X-Frame-Options DENY, XSS Filter |
| Storage | S3 bucket privado, acesso via presigned URL (15min TTL) |
| Logs | LGPD compliant - nunca logam conteúdo de CVs |

---

## Desenvolvimento

```bash
# Rodar testes
python manage.py test

# Verificar configuração
python manage.py check --deploy

# Criar superusuário
python manage.py createsuperuser

# Shell interativo
python manage.py shell
```

---

## Roadmap

- [x] ~~Autenticação com email~~ (django-allauth)
- [x] ~~Dashboard de Analytics com gráficos~~
- [x] ~~Sistema de Tags para candidatos~~
- [x] ~~Área do Candidato~~
- [x] ~~Dark Mode em todo o sistema~~
- [x] ~~Admin customizado~~
- [ ] Autenticação com Google/LinkedIn OAuth
- [ ] API REST para integrações
- [ ] Notificações por email (Celery Beat)
- [ ] Relatórios exportáveis (PDF/Excel)
- [ ] Multi-tenancy para empresas
- [ ] Integração com LinkedIn para importar perfis

---

## Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## Autor

**João Luiz** - [GitHub](https://github.com/joao-luizzz)

---

<p align="center">
  <sub>Desenvolvido com Django, Neo4j e OpenAI</sub>
  <br>
  <sub>🌙 Dark Mode | 📊 Analytics | 🤖 IA | 🔒 LGPD Compliant</sub>
</p>
