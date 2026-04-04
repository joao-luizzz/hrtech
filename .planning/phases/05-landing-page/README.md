# 🚀 LANDING PAGE - RESUMO EXECUTIVO

**Data:** 2026-04-04
**Status:** ✅ UI-SPEC APPROVED & READY FOR DEVELOPMENT
**Inspiração:** Ashby, Lever, Workable
**Prazo Estimado:** 4 semanas (1 semana por fase)

---

## 📊 VISÃO GERAL

### O Que Você Vai Ter
Uma **landing page moderna, profissional e conversora** que:

✅ Apresenta o HRTech com visual similar a ferramentas SaaS de elite (Ashby, Lever)
✅ Mostra o diferencial: **grafos de conhecimento vs keyword matching**
✅ Explica como o Neo4j torna o matching **92% mais preciso**
✅ Demonstra a arquitetura com visualização de grafo animada
✅ Converte visitantes em usuários (CTAs estratégicos)
✅ 100% otimizada para mobile, SEO, acessibilidade

### Stack de Implementação
```
Frontend:  Django + Bootstrap 5 + HTMX + D3.js
Backend:   Reutilizar Django existente (sem mudanças)
Animations: D3.js (grafos), CSS Transitions (hover)
Colors:    Azul #0066FF (primário) + Teal #00D4AA (accent)
Fonte:     Inter (headings/body) + JetBrains Mono (code)
Modo:      Dark mode nativo (recomendado)
```

---

## 🎯 SEÇÕES PRINCIPAIS (8 no total)

### 1️⃣ HERO (600px height)
- **Fundo:** Grafo animado em D3.js com nós e arestas
- **Headline:** "AI-Powered Recruitment That Actually Works"
- **Subline:** "Built on knowledge graphs. Powered by AI."
- **CTAs:** 2 botões principais (Start Free + Watch Demo)
- **Objetivo:** Impactar em < 2 segundos (primeira impressão)

### 2️⃣ PROBLEMA (3-column comparison)
- **Antes:** Manual CV review, keyword matching, horas de trabalho
- **Depois:** Automático, grafos, inteligente
- **Stats:** 35% missed, 92% accuracy, 10x faster, 30s time
- **Design:** Cards com cores (vermelho + verde)
- **Objetivo:** Criar urgência e desejo de solução

### 3️⃣ COMO FUNCIONA (Split screen)
- **Esquerda:** 3 passos (Upload → Graph → Match)
- **Direita:** Grafo interativo (hover = highlight)
- **Code:** Exemplo Cypher query
- **Objetivo:** Explicar sem ser técnico demais

### 4️⃣ GRAFOS > KEYWORDS (Comparison table)
- **Linhas:** Matching, accuracy, speed, bias detection, relationships, scalability
- **Design:** Table grid, HRTech destaca em verde
- **Objetivo:** Convencer sobre o diferencial técnico

### 5️⃣ FEATURES (4 cards grid)
- **1:** Interview Questions Generator (New badge)
- **2:** Skill Gap Analysis
- **3:** Multi-Tenant Isolation (Enterprise)
- **4:** LGPD Compliance (Trust badge)
- **Objetivo:** Mostrar funcionalidades principais

### 6️⃣ TECH STACK (Architecture diagram)
- **Layout:** 3 layers (Frontend → API → Databases)
- **Logos:** PostgreSQL, Neo4j, Redis, Django, OpenAI, AWS S3, Celery
- **Tagline:** "Deployed on Render. Serverless Redis. Global Performance."
- **Objetivo:** Build trust (tech credibility)

### 7️⃣ PRICING (3-tier pricing)
- **Starter:** Free (30 days) - 50 candidates, 1 user
- **Pro:** $99/month - Unlimited, 5 users, Analytics (Most Popular)
- **Enterprise:** Custom - Everything + SSO + SLA
- **Objetivo:** Capturar leads + revenue streams

### 8️⃣ CTA FINAL + FOOTER
- **Headline:** "Ready to hire smarter?"
- **Copy:** "Join 100+ companies using AI-powered matching."
- **Buttons:** Start Free Trial + Schedule Demo
- **Footer:** Links, socials, legal (Privacy, Terms)
- **Objetivo:** Conversão final

---

## 🎨 DESIGN SYSTEM QUICK REF

### Cores
| Uso | Cor | Hex |
|-----|-----|-----|
| CTA, Links | Brand Blue | `#0066FF` |
| Accents, Badges | Teal | `#00D4AA` |
| Success | Green | `#10B981` |
| Error | Red | `#EF4444` |
| Background | Dark | `#0F1419` |
| Cards | Darker | `#1A1F26` |
| Borders | Subtle | `#2D3139` |
| Text | White | `#FFFFFF` |
| Secondary | Gray | `#A0AAB8` |

### Tipografia
```
H1 (Hero):    56px, bold        → "AI-Powered Recruitment..."
H2 (Sections): 40px, bold        → "Why Graphs Are Better"
H3 (Features): 30px, semibold    → "Skill Gap Analysis"
H4 (Cards):   24px, semibold    → Card titles
Body:         16px, regular     → Main text
Small:        14px, regular     → Captions
Tiny:         12px, medium      → Labels, badges

Font Stack: Inter, -apple-system, BlinkMacSystemFont (sans-serif)
Mono: JetBrains Mono, Monaco (code blocks)
```

### Spacing (4px grid)
```
xs: 4px  | sm: 8px   | md: 16px | lg: 24px | xl: 32px | 2xl: 48px | 3xl: 64px
```

### Shadows
```
Small:  0 1px 2px rgba(0,0,0,0.05)
Medium: 0 4px 12px rgba(0,0,0,0.08)
Large:  0 12px 24px rgba(0,0,0,0.12)
```

---

## 📱 RESPONSIVIDADE

### Desktop (1440px+)
- Full 12-column grid
- Hero: 600px height
- Features: 2×2 grid
- Paddings: 48px
- Animações: 100% enabled

### Tablet (768px - 1024px)
- 8-10 columns
- Hero: 500px height
- Features: 2 columns
- Paddings: 32px
- Animações: Reduced motion

### Mobile (< 768px)
- 4-6 columns
- Hero: 400px height
- All sections: 1 column
- Paddings: 16px
- Animações: Fade-in only
- Touch targets: min 44×44px

---

## 🎬 ANIMAÇÕES & MICRO-INTERAÇÕES

### Hover Effects
```
Links:       2px underline (gray → brand)
Cards:       translateY(-4px) + shadow boost
Buttons:     bg darkening + shadow lift
Graph nodes: glow (opacity 1 → 0.8) + size +5%
```

### Scroll Animations
```
Fade-in sections:  opacity 0 → 1 (300ms)
Number counters:   0 → final (2s, on scroll)
Graph rotation:    360° (20s loop)
```

### Performance
- GPU-accelerated: transform + opacity only
- Debounced scroll: 300ms
- Lazy-load graph below fold
- WebP images with fallbacks
- Target: 60fps on all devices

---

## 📈 MÉTRICAS DE SUCESSO

| Métrica | Target | Como Medir |
|---------|--------|-----------|
| Load Time (Hero visible) | < 2s | Lighthouse |
| FCP (First Contentful Paint) | < 1.2s | Chrome DevTools |
| CLS (Cumulative Layout Shift) | < 0.1 | PageSpeed |
| LCP (Largest Contentful Paint) | < 2.5s | Core Web Vitals |
| Graph FPS | 60fps | Chrome Profiler |
| Accessibility | 95+ | Lighthouse A11y |
| Mobile Score | 90+ | Mobile-Friendly Test |
| CTA Click-through | 8%+ | Google Analytics |
| Bounce Rate | < 35% | GA Behavioral |
| Time on Site | 2-3 min | GA Sessions |

---

## 🔄 FASES DE DESENVOLVIMENTO (4 semanas)

### SEMANA 1: Foundation
- [ ] Setup Django template
- [ ] Header + nav sticky
- [ ] Hero (sem animação)
- [ ] Problem section
- [ ] CSS design system
- [ ] Responsive mobile

**Deliverable:** Hero + Problem, navegável em desktop e mobile

---

### SEMANA 2: Interactividade
- [ ] D3.js graph integration
- [ ] Animação grafo hero
- [ ] How It Works (split screen)
- [ ] Features grid + hover
- [ ] Graphs > Keywords table
- [ ] Animações scroll

**Deliverable:** Seções 1-4 completas + animações

---

### SEMANA 3: Conclusão
- [ ] Tech stack diagram
- [ ] Pricing 3-tiers
- [ ] Footer + legal pages
- [ ] Newsletter form
- [ ] Modal demo video

**Deliverable:** Todas as 8 seções completas

---

### SEMANA 4: Polish + Deployment
- [ ] Performance optimization
- [ ] SEO (meta tags, schema.org)
- [ ] Google Analytics
- [ ] Lighthouse 90+
- [ ] Mobile refinements
- [ ] Deploy Render

**Deliverable:** Versão final pronta para produção

---

## 🛠️ PRÓXIMOS COMANDOS

### 1. Criar Plano de Implementação
```bash
/gsd:plan-phase 5
```
Isso vai quebrar em tasks menores (Day 1, 2, 3...)

### 2. Iniciar Desenvolvimento
```bash
/gsd:execute-phase 5
```
Executor vai rodar as tasks em paralelo

### 3. Revisar Progress
```bash
/gsd:progress
```
Ver quanto avançou

### 4. Debug se Travar
```bash
/gsd:debug
```
Investigar problemas

---

## 📚 ARQUIVOS CRIADOS

```
.planning/phases/05-landing-page/
├── 05-LANDING-PAGE-UI-SPEC.md          ← Design contract (CONSULTE ISSO)
├── VISUAL-REFERENCE-GUIDE.md           ← HTML/CSS examples
└── README.md                           ← Este arquivo

📌 PRÓXIMO: Ler o UI-SPEC.md para entender design em detalhe
```

---

## 🎓 DICAS PARA IMPLEMENTAÇÃO

### Ashby Inspiration Points
✅ **Hero:** Fundo com pattern/grafo + centered text overlay
✅ **Problem:** Before/After cards side-by-side
✅ **Features:** 4-grid com icon + title + description
✅ **Pricing:** 3-tier cards com destaque pro (Most Popular)
✅ **CTA:** Bottom section com texto + 2 buttons
✅ **Color:** Azul + teal (similar à Ashby)

### Lever Inspiration Points
✅ **Tech Stack:** Diagram simples mostrando arquitetura
✅ **Safeties:** Trust badges (LGPD, Enterprise)
✅ **Footer:** Links organizados, não bagunçado

### Performance
🚀 Use CDN para D3.js (jsdelivr, unpkg)
🚀 Comprimir imagens (WebP)
🚀 Cache estático no CloudFront
🚀 Lazy-load sections abaixo do fold

### Acessibilidade (WCAG 2.1 AA)
♿ Alt text em todas imagens
♿ Contrast ratio 4.5:1 (text) / 3:1 (graphics)
♿ Heading hierarchy (H1, H2, H3... sem pulos)
♿ Touch targets 44×44px min
♿ Teste com screen reader (NVDA/JAWS)

---

## ⚠️ CUIDADOS IMPORTANTES

### NÃO FAÇA:
- ❌ Usar ícones que pesam muito (optimize SVGs)
- ❌ Animações que causam motion sickness (prefere-reduced-motion)
- ❌ Colores que não contrastam bem (use https://contrast-ratio.com)
- ❌ Dependência de JavaScript para conteúdo crítico
- ❌ Múltiplas versões da landing (manutém uma única fonte)

### FAÇA:
- ✅ Semantic HTML (`<section>`, `<article>`, `<nav>`)
- ✅ CSS Custom Properties para colores/spacing
- ✅ Mobile-first approach (design mobile primeiro)
- ✅ Test em reais devices (não só browser emulation)
- ✅ Monitor performance com Web Vitals

---

## 🎯 RESULTADO FINAL

Após 4 semanas, você terá:

🎨 **Landing page moderna** - Parece que saiu de Ashby/Lever
🚀 **Alta performante** - Lighthouse 90+
📱 **Responsiva** - Desktop, tablet, mobile
🎬 **Animada** - Grafo D3.js interativo, scroll animations
🔍 **SEO-ready** - Meta tags, schema.org, sitemap
📊 **Rastreável** - Google Analytics + funnel tracking
💰 **Convertível** - CTAs estratégicos, pricing sections
🛡️ **Segura** - HTTPS, CSP headers, input validation

---

## 📞 RESUMO DE ARQUIVOS

| Arquivo | Conteúdo | Próximo Passo |
|---------|----------|--------|
| `05-LANDING-PAGE-UI-SPEC.md` | Design contract completo | **Leia agora** |
| `VISUAL-REFERENCE-GUIDE.md` | HTML/CSS/JS examples | Use na implementação |
| `README.md` | Este arquivo | Guia de projeto |

---

## 🚀 COMECE AQUI

```
1. Leia o UI-SPEC.md (10 min)
   → Entender design em detalhe

2. Revise VISUAL-REFERENCE-GUIDE.md (5 min)
   → Ver exemplos de código

3. Rode /gsd:plan-phase 5 (10 min)
   → Quebrar em tasks de implementação

4. Inicie /gsd:execute-phase 5
   → Começar a codificar!
```

---

**Documentação Completa ✅ | Pronto para Desenvolvimento 🚀**

Qualquer dúvida? Revise o **05-LANDING-PAGE-UI-SPEC.md** - todas as respostas estão lá!
