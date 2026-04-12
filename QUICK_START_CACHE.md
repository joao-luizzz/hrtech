# 🚀 Quick Start Guide - Cache & Deploy

Guia rápido para resolv problemas de cache e fazer deploy seguro.

---

## ⚡ 3 Segundos: Cache não atualiza no navegador?

```bash
# Passo 1: Limpar Redis
python scripts/clean_cache.py

# Passo 2: No navegador
# Windows/Linux: Ctrl + Shift + R
# Mac: Cmd + Shift + R

# Pronto! ✨
```

---

## 🎯 10 Minutos: Resumo da Configuração

### O Problema (Resume)
- Mudou template/HTML → não vê mudança na tela
- Culpado: Redis cache persistente
- Solução: limpar Redis + hard refresh navegador

### Configuração Inteligente
- **Desenvolvimento**: LocMemCache (memória, sem Redis)
- **Produção**: Redis (distribuído, compartilhado)

### Arquivos Importantes
| Arquivo | Propósito |
|---------|-----------|
| `.env.local` | Variáveis DEV (NÃO commitar) |
| `hrtech/settings.py` | Detecta ENVIRONMENT, escolhe cache |
| `scripts/clean_cache.py` | Limpa cache com segurança |
| `scripts/quick_cache_clean.sh` | Limpeza rápida |
| `scripts/verify_settings.py` | Checa antes de deploy |

---

## 📋 Antes de Fazer Deploy

### 1. Verificação Rápida
```bash
python scripts/verify_settings.py
```
- Deve mostrar: `✅ 9/9 verificações ok`
- Se falhar: leia os errors e corrija

### 2. Testes
```bash
pytest core/tests/ -v
```
- Todos passam?

### 3. Secrets
```bash
git grep -i "password\|secret\|token\|api_key" -- '*.py'
```
- Deve retornar 0 matches (ou apenas em tests/mocks)

### 4. Commit e Push
```bash
git add . && git commit -m "feat: descrição"  && git push
```
- Render deploy começa automaticamente

---

## 🆘 Problemas Comuns

### "Mudança em template não aparece"
```bash
python scripts/clean_cache.py
# Depois: Ctrl+Shift+R no navegador
```

### "500 Error em produção"
1. Abra logs Render: `Render Dashboard > Logs > Stdout`
2. Se DEBUG=True: mude para False no .env produção
3. Se ALLOWED_HOSTS: adicione seu domínio

### "Redis não encontrado"
- Linux: `sudo apt install redis-server`
- Mac: `brew install redis`
- Ou deixe CACHE_URL vazio para usar LocMemCache

### "Testes falhando depois de mudar cache"
```bash
# Limpa cache
python scripts/clean_cache.py

# Roda testes de novo
pytest core/tests/ -v
```

---

## 📚 Documentação Completa

- **Cache em detalhes**: [scripts/README_CACHE.md](README_CACHE.md)
- **Deploy checklist**: [docs/DEPLOYMENT_CHECKLIST.md](../docs/DEPLOYMENT_CHECKLIST.md)
- **Deploy runbook**: [docs/DEPLOYMENT_RUNBOOK.md](../docs/DEPLOYMENT_RUNBOOK.md)
- **Agentes/Segurança**: [AGENTS.MD](../AGENTS.MD)

---

## 🎓 Entender a Arquitetura

### Como funciona o cache?

```
┌─────────────────────────────────────────────────────┐
│                    NAVEGADOR                         │
│         (também tem seu próprio cache)               │
└────────────────────────┬────────────────────────────┘
                         │ Ctrl+Shift+R limpa isso
                         ↓
┌─────────────────────────────────────────────────────┐
│               DJANGO (Python)                        │
│  ┌──────────────────────────────────────────────┐  │
│  │ Cache Backend (escolhido em settings.py)     │  │
│  │                                              │  │
│  │  DEV: LocMemCache (memória do Python)       │  │
│  │  PROD: Redis (database externo)             │  │
│  └──────────────────────────────────────────────┘  │
│         ↓                                           │
│   python scripts/clean_cache.py                    │
│         ↓                                           │
│   redis-cli FLUSHALL                              │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│               REDIS (C/Redis)                        │
│        (apenas em PROD/STAGING)                     │
└─────────────────────────────────────────────────────┘
```

### Quando cada um é limpo?

| Cache | Como Limpar | Quando |
|-------|-----------|--------|
| **Navegador** | Ctrl+Shift+R | Mudança em HTML/CSS/JS |
| **LocMemCache** | `python scripts/clean_cache.py` ou reiniciar Django | Mudança em templates em DEV |
| **Redis** | `redis-cli FLUSHALL` ou `python scripts/clean_cache.py --all` | Antes de testar em PROD/STAGING |

---

## ✅ Checklist Antes de Push

```bash
# 1. Ambiente virtual ativo?
source venv/bin/activate

# 2. Testes passam?
pytest core/tests/ -v

# 3. Verificação pré-deploy?
python scripts/verify_settings.py

# 4. Nenhum secret no código?
git grep -i "password\|secret\|token\|api_key" -- '*.py'

# 5. .env.local não vai ser commitado?
git status | grep .env

# 6. Tudo ok?
git add . && git commit -m "feat: descrição" && git push

# Deploy começa automaticamente no Render!
```

---

## 🎯 Próximas Ações

Escolha uma:

**▶ Quero entender cache em detalhes**
→ Leia [scripts/README_CACHE.md](README_CACHE.md)

**▶ Preciso fazer deploy seguro**
→ Siga [docs/DEPLOYMENT_CHECKLIST.md](../docs/DEPLOYMENT_CHECKLIST.md)

**▶ Tenho um problema en produção**
→ Veja [docs/DEPLOYMENT_RUNBOOK.md](../docs/DEPLOYMENT_RUNBOOK.md)

**▶ Preciso debuggar algo**
→ Use [AGENTS.MD](../AGENTS.MD) ← instruções de segurança

---

**Última atualização:** 2026-04-11  
**Criado para:** @joao-luizzz
