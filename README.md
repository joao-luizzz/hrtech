# HRTech - Sistema de Recomendação de Candidatos

Sistema SaaS de recrutamento que usa grafos para fazer matching inteligente entre candidatos e vagas.

## 🔒 Segurança

**IMPORTANTE:** Este projeto usa variáveis de ambiente para todas as credenciais.

### Configuração Inicial

1. **Copie o arquivo de exemplo:**
   ```bash
   cp .env.example .env
   ```

2. **Gere uma SECRET_KEY segura:**
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

3. **Preencha TODAS as variáveis obrigatórias no `.env`**

4. **NUNCA commite o arquivo `.env`** - ele já está no `.gitignore`

### Variáveis Obrigatórias

| Variável | Descrição |
|----------|-----------|
| `SECRET_KEY` | Chave secreta do Django (50+ caracteres) |
| `DB_NAME` | Nome do banco PostgreSQL |
| `DB_USER` | Usuário do PostgreSQL |
| `DB_PASSWORD` | Senha do PostgreSQL |
| `NEO4J_URI` | URI de conexão do Neo4j |
| `NEO4J_USER` | Usuário do Neo4j |
| `NEO4J_PASSWORD` | Senha do Neo4j |

## 🚀 Stack

- **Backend:** Django 5 + PostgreSQL + Neo4j AuraDB
- **Processamento Assíncrono:** Celery + Redis
- **NLP/IA:** pdfplumber → Tesseract OCR → GPT-4o-mini
- **Storage:** AWS S3 (presigned URLs)
- **Frontend:** Bootstrap 5 + HTMX + Chart.js

## 📦 Instalação

```bash
# Clone o repositório
git clone <seu-repo>
cd hrtech

# Crie o ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Instale as dependências
pip install -r requirements.txt

# Configure o .env (veja seção Segurança)
cp .env.example .env
# Edite o .env com suas credenciais

# Execute as migrations
python manage.py migrate

# (Opcional) Popule com dados de teste
python popular_banco.py

# Inicie o servidor
python manage.py runserver
```

## 🏗️ Arquitetura

### Persistência Poliglota

- **PostgreSQL:** Dados transacionais (Candidato, Vaga, AuditoriaMatch)
- **Neo4j:** Grafo de habilidades e conexões para matching
- **Redis:** Broker do Celery + cache
- **S3:** Storage de CVs (acesso via presigned URLs)

### Sincronização

O UUID do candidato é compartilhado entre PostgreSQL e Neo4j, servindo como chave de sincronia.

## 📋 LGPD

- PDFs acessados apenas via presigned URL (TTL 15 min)
- Dados pessoais removidos antes de chamadas à OpenAI
- AuditoriaMatch usa `SET_NULL` para preservar histórico
- Logs nunca registram conteúdo de CVs

## 🧪 Desenvolvimento

```bash
# Rodar testes
python manage.py test

# Verificar configuração
python manage.py check

# Criar superusuário
python manage.py createsuperuser
```

## 📄 Licença

[Sua licença aqui]
