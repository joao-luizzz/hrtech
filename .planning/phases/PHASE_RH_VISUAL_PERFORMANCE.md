# 🚀 PLANO: Padrão Visual RH + Performance Fast-Track

**Objetivo:** Padrão visual landing + Performance otimizada nas telas RH  
**Prioridade:** MÁXIMA  
**Estimativa:** 2-3 semanas (fases paralelas)  
**Status:** PLANEJAMENTO  

---

## 📊 Telas Identificadas

| Tela | Status | Prioridade | Impacto Performance |
|------|--------|-----------|---------------------|
| `dashboard_rh.html` | Cru | ⚡⚡⚡ | Alto (charts, queries) |
| `pipeline_kanban.html` | Cru | ⚡⚡⚡ | Alto (grid, drag-drop) |
| `dashboard_geral.html` | Cru | ⚡⚡ | Médio (charts) |
| `lista_vagas.html` | Cru | ⚡⚡ | Médio (tabela) |
| `upload.html` | Cru | ⚡ | Baixo (simples) |
| `ranking_candidatos.html` | Cru | ⚡⚡ | Médio (scroll) |
| `detalhe_match.html` | Cru | ⚡ | Baixo (modal) |
| `historico.html` | Cru | ⚡ | Baixo (tabela) |
| `dashboard_candidato.html` | Semi-ok | - | - |

---

## 🎨 O Que Falta (Comparado Landing)

### Colors & Gradients
- [ ] Gradientes bonito (landing usa azul-roxo)
- [ ] Componentes coloridos (cards com bg-gradient)
- [ ] Hover states modernos

### Typography
- [ ] Hierarquia clara (landing tem H1, H2, H3 bem separados)
- [ ] Font weights inconsistent (landing é sistema)
- [ ] Line-height adequado

### Spacing & Components
- [ ] Cards com shadow/border-radius (landing é clean)
- [ ] Grid layouts limpos (landing é 12-col)
- [ ] Buttons com icons + variações (landing é completo)

### Performance (CRÍTICO)
- [ ] N+1 queries em django_rh (cada row faz query?)
- [ ] CSS não minificado / duplicado
- [ ] JS inline vs externo
- [ ] Asset lazy-loading faltando
- [ ] Cache headers inadequado

---

## 🔧 Diagnóstico Rápido

### Backend (Django Views)
```python
dashboard_rh():        # Line 277
  ├─ N+1? Vagas list com relacionamentos 
  ├─ Charts queries? 5+ queries separadas
  └─ Sem select_related/prefetch_related

dashboard_geral():     # Line 1157
  ├─ N+1? Scores por vágas
  ├─ Neo4j calls? Não cacheado?
  └─ Sem paginação adequada

lista_vagas():         # Line 366
  ├─ Sem pag natural? 10 itens OK
  ├─ Filtros sem cache
  └─ Good: select OK
```

### Frontend (Templates)
```html
<!-- Problemas comuns -->
├─ Inline styles (should be CSS classes) 
├─ Bootstrap classes + custom CSS conflito
├─ Charts renders sem otimização
├─ Sem lazy-loading em images
└─ HTMX requests sem swap optimization
```

---

## 📋 Fases de Execução

### FASE 1: Diagnóstico & Quick Wins (2 dias)
**Objetivo:** Entender baseline performance

- [ ] Profile Django views com django-debug-toolbar
- [ ] Medir tempo de carga (Lighthouse, browser DevTools)
- [ ] Identificar N+1 queries mais óbvias
- [ ] Revisar CSS/JS assets (tamanho, duplicatas)

**Deliverables:**
- `PERFORMANCE_BASELINE.md` (já existe!)
- Relatório de N+1 queries
- Lista de otimizações diretas

---

### FASE 2: CSS/Componentes Padrão (3 dias)
**Objetivo:** Aplicar visual landing (cores, cards, buttons)

**Escopo:**
- [ ] Criar sistema de cores base (landing palette)
- [ ] Componentes CSS reutilizáveis (cards, buttons, badges)
- [ ] Aplicar a `dashboard_rh.html` (mais importante)  
- [ ] Aplicar a `pipeline_kanban.html` (mais importante)
- [ ] Aplicar a `dashboard_geral.html`

**Output:**
- `css/components.css` (novo arquivo com padrões)
- Telas modernizadas em Bootstrap 5.3

---

### FASE 3: Backend Otimizações (2 dias)
**Objetivo:** Remover N+1 queries

**Escopo (por tela):**
```python
dashboard_rh:
  ├─ select_related Vaga.skills_obrigatorias
  ├─ prefetch_related Vaga.candidatos
  ├─ Cache charts (Redis 5 min)
  └─ Query inline instead of 5 separatas

lista_vagas:
  ├─ select_related em tudo
  ├─ Paginação otimizada (20 itens)
  └─ Filter caching (Redis 10 min)

pipeline_kanban:
  ├─ Pré-load candidatos por etapa (1 query)
  └─ Cache estrutura do pipeline (Redis)
```

**Output:**
- Django views otimizadas
- Cache layer com Redis
- Queries reduzidas 30%+

---

### FASE 4: Frontend Performance (2 dias)
**Objetivo:** Assets rápidos, interatividade ágil

**Escopo:**
- [ ] Minify CSS (remove duplicatas Bootstrap)
- [ ] Lazy-load charts (render on scroll)
- [ ] HTMX swap otimizado (innerHTML vs outerHTML)
- [ ] Service Worker light (não é SPA, então apenas statics)
- [ ] Async/Defer em JS scripts

**Output:**
- CSS < 50KB (atualmente ~200KB?)
- Página carga < 2s (Lighthouse 85+)
- HTMX responses < 100KB

---

## 🎯 Success Metrics

### Performance
- [ ] Dashboard RH: < 2s load (was 4s+) ⚡
- [ ] Pipeline Kanban: < 1.5s load + smooth drag ⚡
- [ ] Lighthouse Score: 85+ (was 60-70?)
- [ ] Queries reduzidas: 20+ → 5 per page

### Visual
- [ ] Consistência com landing 100%
- [ ] Componentes reutilizáveis 80%+
- [ ] Accessibility score AA

### UX
- [ ] Sem layout shift (CLS < 0.1)
- [ ] Interatividade FID < 100ms
- [ ] Drag-drop kanban 60fps

---

## 🛠️ Tech Stack Proposto

| Layer | Tech | Desc |
|-------|------|------|
| **CSS** | Bootstrap 5.3 + custom `components.css` | Reutilizável |
| **JS** | HTMX 1.9 (já tem) + htmx.ajax otimizado | Menos JS custom |
| **Backend** | Django QuerySet.select_related + Redis | Queries otimizadas |
| **Monitoring** | Django Debug Toolbar (dev) + Sentry (prod) | Visibilidade |
| **Assets** | Minify + CDN CloudFlare | Rápido |

---

## 📌 Próxima Ação

**Qual você quer atacar primeiro?**

1. **RÁPIDO:** Já fazer FASE 1 (diagnóstico) → 1 dia
2. **BONITO:** Já fazer FASE 2 (visual) → 3 dias  
3. **RÁPIDO + BONITO:** Ambas paralelas → 4-5 dias

**Meu feedback:** Comece em paralelo:
- **Você:** Passa padrões visuais (landing colors, components que quer copiar)
- **Eu:** Rodo diagnóstico + começo otimizações backend

---

**Status:** AGUARDANDO GO  
**Criado:** 2026-04-11
