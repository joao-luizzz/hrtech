# 🧹 Scripts de Gerenciamento de Cache

Guia completo para usar os scripts de cache durante desenvolvimento e antes de deploy.

---

## 📋 Índice

1. [Problema: Por que o cache?](#-problema-por-que-o-cache)
2. [Solução rápida](#-solução-rápida)
3. [Scripts disponíveis](#-scripts-disponíveis)
4. [Quando usar cada um](#-quando-usar-cada-um)
5. [Troubleshooting](#-troubleshooting)

---

## 🔴 Problema: Por que o cache?

### Cenário típico:
1. Você muda um arquivo de template (`.html`)
2. Salva o arquivo no VS Code
3. Recarrega a página no navegador
4. **Ahhh, a mudança não aparece!** 😫

### Culpados comuns:

1. **Cache do Navegador** (temporário)
   - Cluick Ctrl+Shift+R resolve

2. **Cache Django em memória** (LocMemCache)
   - Existe enquanto o servidor Django está rodando
   - Perdido ao reiniciar o servidor

3. **Cache Redis** (persistente) ⚠️ **ESTE É O VILÃO**
   - Survive restarts Django
   - Precisa limpar manualmente com `redis-cli FLUSHALL`
   - É o cache mais problemático em desenvolvimento

---

## ⚡  Solução Rápida

### Option 1: Script Shell (Mais Rápido)
```bash
bash scripts/quick_cache_clean.sh
```

Depois: Hardrefresh no navegador com `Ctrl + Shift + R`

### Option 2: Script Python (Mais Controle)
```bash
python scripts/clean_cache.py
```

Depois: Hardrefresh no navegador com `Ctrl + Shift + R`

### Option 3: Redis CLI Direto (Terminal)
```bash
redis-cli FLUSHALL
```

Depois: Hardrefresh no navegador com `Ctrl + Shift + R`

---

## 🛠️ Scripts Disponíveis

### 1. `scripts/quick_cache_clean.sh`

**Propósito:** Limpeza rápida sem python

**Uso:**
```bash
bash scripts/quick_cache_clean.sh              # Limpa cache
bash scripts/quick_cache_clean.sh --verify     # Apenas status
```

**Saída:**
```
✅ Redis CONECTADO (chaves: 42)
🧹 Limpando cache do Redis...
✅ Cache limpo!

PRÓXIMOS PASSOS:
1. Abra o navegador
2. Hardrefresh: Ctrl+Shift+R (Windows/Linux) ou Cmd+Shift+R (Mac)
3. Recarregue com F5
```

**Vantagens:**
- Não precisa de Python
- Rápido e simples
- Mostra status do Redis

**Limitações:**
- Só limpa se Redis está rodando
- Limpa TUDO (cache + Celery tasks)

---

### 2. `scripts/clean_cache.py`

**Propósito:** Limpeza Python com mais controle

**Uso:**
```bash
# Limpa apenas cache da aplicação
python scripts/clean_cache.py

# Limpa TUDO do Redis (cache + Celery)
python scripts/clean_cache.py --all

# Apenas mostra status
python scripts/clean_cache.py --verify
```

**Saída:**
```
======================================================================
GERENCIADOR DE CACHE
======================================================================
Ambiente: DEVELOPMENT
Debug: True
Backend de Cache: LocMemCache

🟡 Redis NÃO configurado (usando LocMemCache em memória)

======================================================================
✨ Pronto! Recarregue a página no navegador (Ctrl+Shift+R)
======================================================================
```

**Vantagens:**
- Mais seguro (pede confirmação antes de limpar)
- Mostra detalhes do cache
- Integrado com Django

**Como usar:**
1. Abra terminal na pasta do projeto
2. Ativa venv: `source venv/bin/activate`
3. Roda: `python scripts/clean_cache.py`

---

### 3. `scripts/verify_settings.py`

**Propósito:** Verificação de configurações ANTES de deploy

**Uso:**
```bash
# Verificação completa
python scripts/verify_settings.py

# Modo estrito (mais rigoroso)
python scripts/verify_settings.py --strict

# Apenas para contexto de produção
python scripts/verify_settings.py --production
```

**Checa:**
- ✅ DEBUG está False em produção
- ✅ SECRET_KEY é forte
- ✅ ALLOWED_HOSTS configurado
- ✅ SSL settings em produção
- ✅ Redis configurado corretamente
- ✅ Database pronto
- ✅ Sem secrets hardcoded
- ✅ .env.example atualizado
- ✅ Static files prontos

**Saída tipo:**
```
======================================================================
✅ VERIFICAÇÃO PRÉ-DEPLOY
======================================================================
Ambiente: PRODUCTION
Debug: False

🔍 MODO DEBUG
✅ DEBUG=False (seguro para produção)

🔍 SECRET KEY
✅ SECRET_KEY forte (56 caracteres)

🔍 ALLOWED HOSTS
✅ ALLOWED_HOSTS configurado: yourdomain.com, www.yourdomain.com

📊 RESUMO
======================================================================
✅ Debug Mode
✅ Secret Key
✅ Allowed Hosts
✅ SSL Settings
✅ Redis/Cache
✅ Database
✅ Secrets no Code
✅ Arquivo .env
✅ Static Files

Resultado: 9/9 verificações ok

✨ TUDO OK - pronto para deploy!
```

---

## 🎯 Quando Usar Cada Um

### Cenário 1: "Mudei um template e não vê na tela"
**Use:** `bash scripts/quick_cache_clean.sh` (mais rápido)

### Cenário 2: "Quero limpar cache COM segurança"
**Use:** `python scripts/clean_cache.py` (pede confirmação)

### Cenário 3: "Vou fazer deploy, preciso checar tudo"
**Use:** `python scripts/verify_settings.py` (checklist completo)

### Cenário 4: "Só quero saber o status do cache"
**Use:** `python scripts/clean_cache.py --verify` (não faz nada)

### Cenário 5: "Preciso limpar Celery tasks também"
**Use:** `python scripts/clean_cache.py --all` (confirmação antes)

---

## 📝 Workflow Recomendado Dia-a-Dia

### 1. **Começar o Dia**
```bash
# Ativa ambiente virtual
source venv/bin/activate

# Rodastanza servidor
python manage.py runserver

# Em outro terminal, verifica cache (opcional)
python scripts/clean_cache.py --verify
```

### 2. **Durante o Desenvolvimento**
Se mudar templates:
```bash
bash scripts/quick_cache_clean.sh
# Depois: Ctrl+Shift+R no navegador
```

### 3. **Antes de Commitar**
```bash
# Roda testes
pytest core/tests/ -v

# Verifica segurança
python scripts/verify_settings.py --strict
```

### 4. **Antes de Fazer Deploy**
```bash
# Verificação completa
python scripts/verify_settings.py --production

# Se tudo OK:
git add .
git commit -m "feat: descrição"
git push  # Render deploy começa automaticamente
```

---

## 🚨 Troubleshooting

### "❌ Redis não responde"

**Problema:** `redis-cli` mostra `Could not connect`

**Soluções:**

1. **Instalar Redis (se não tiver)**
   ```bash
   # Ubuntu/Debian
   sudo apt install redis-server
   
   # Mac
   brew install redis
   ```

2. **Iniciar Redis**
   ```bash
   redis-server
   ```

3. **Ou desabilitá-lo completamente em DEV**
   - Deixe `.env.local` sem `CACHE_URL` ou `CELERY_BROKER_URL`
   - Django vai usar `LocMemCache` (em memória)

---

### "Cache limpou mas mudanças não apareceu"

**Passos:**

1. Certifique-se de limpar Redis:
   ```bash
   python scripts/clean_cache.py
   # Deve mostrar "Cache limpado"
   ```

2. Limpe cache do navegador:
   - **Windows/Linux:** `Ctrl + Shift + R`
   - **Mac:** `Cmd + Shift + R`
   - Ou: F12 > clique direito reload > "Empty cache and hard refresh"

3. Espere uns segundos e recarregue

4. Se ainda não funciona, reinicie Django:
   ```bash
   Ctrl+C (para o servidor)
   python manage.py runserver
   ```

---

### "LocMemCache vs Redis - qual usar?"

**LocMemCache** (default em DEV):
- ✅ Não precisa instalar Redis
- ✅ Mais rápido para DEV
- ❌ Não compartilha entre workers/processos
- ❌ Perdido ao reiniciar Python

**Redis** (para testar distribuído):
- ✅ Compartilha entre workers
- ✅ Persiste após restart
- ❌ Precisa instalar Redis
- ❌ Mais difícil de debugar

**Recomendação:** Use LocMemCache em DEV, Redis apenas se precisar testar sistema distribuído.

---

### "Meu Django não está rodando depois de `redis-cli FLUSHALL`"

**Não há problema!** `FLUSHALL` só limpa dados do Redis, não afeta Django.

Se Django parou, é por outra razão. Restart:
```bash
python manage.py runserver
```

---

## 🔗 Referências

- [Django Caching Documentation](https://docs.djangoproject.com/en/stable/topics/cache/)
- [Redis CLI Commands](https://redis.io/commands)
- [Deployment Checklist](../DEPLOYMENT_CHECKLIST.md)

---

**Criado em:** 2026-04-11  
**Manutenção:** @joao-luizzz
