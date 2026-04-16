# 🏗️ Landing Page - Estrutura Organizacional

## 📁 Diretórios e Arquivos

```
hrtech/
├── core/
│   ├── templates/
│   │   ├── landing/
│   │   │   ├── base.html                    ← Estende /templates/base.html
│   │   │   ├── index.html                   ← Página principal (switch logado/público)
│   │   │   └── partials/                    ← Componentes reutilizáveis
│   │   │       ├── navbar-unified.html      ← Navbar único (landing only)
│   │   │       ├── header.html              ← Meta tags + logo
│   │   │       ├── hero.html                ← Hero section (público)
│   │   │       ├── hero-logged.html         ← Hero section (logado)
│   │   │       ├── vision.html              ← 3-phase timeline section
│   │   │       ├── problem.html             ← Before/After cards
│   │   │       ├── how-it-works.html        ← 3 steps + D3 canvas
│   │   │       ├── graphs-vs-keywords.html  ← Feature comparison
│   │   │       ├── features.html            ← 4 feature cards grid
│   │   │       ├── tech-stack.html          ← 3-layer architecture
│   │   │       ├── pricing.html             ← 3 pricing tiers
│   │   │       ├── cta.html                 ← Call-to-action (público)
│   │   │       ├── cta-dashboard.html       ← CTA (logado)
│   │   │       ├── footer.html              ← Footer
│   │   │       └── newsletter-form.html     ← Newsletter signup
│   │
│   ├── views.py
│   │   └── home(request)                    ← Render landing/index.html
│   │
│   └── urls.py
│       └── path('', views.home)             ← Route raiz /
│
├── static/
│   ├── css/
│   │   ├── design-system.css                ← Design tokens compartilhados
│   │   └── landing/
│   │       ├── index.css                    ← Landing-specific styles (1154 linhas)
│   │       ├── responsive.css               ← Media queries (breakpoints)
│   │       ├── animations.css               ← Scroll/fade animations
│   │       └── *.min.css                    ← Minified versions (cache-busted)
│   │
│   ├── js/
│   │   └── landing/
│   │       ├── graph-visualization.js       ← D3.js graph rendering
│   │       ├── graph-config.js              ← D3 configuration
│   │       ├── lazy-loader.js               ← Lazy-load images/sections
│   │       └── *.min.js                     ← Minified versions
│   │
│   └── img/
│       └── (landing images, favicons, etc.)
│
└── templates/
    └── base.html                            ← Base layout
        └── Imports: design-system.css + landing navbar
```

---

## 🔄 Fluxo de Renderização

```
┌─────────────────────────────────────────────────────────────┐
│                    GET / (home view)                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────────────────────────┐
        │  Check user.is_authenticated          │
        └───────────────────────────────────────┘
                            ↓
              ┌─────────────┴─────────────┐
              ↓                           ↓
      ┌───────────────────┐    ┌──────────────────────┐
      │   LOGGED IN       │    │   PUBLIC (Anonymous) │
      │   user.profile    │    │                      │
      └───────────────────┘    └──────────────────────┘
              ↓                           ↓
      Fetch organization        No stats needed
           stats                        ↓
              ↓                   ┌──────────────┐
              └──────────┬────────┤  context={}  │
                         ↓        └──────────────┘
              render(landing/index.html, context)
                         ↓
      ┌────────────────────────────────────────────┐
      │     landing/index.html extends             │
      │     landing/base.html extends              │
      │     templates/base.html                    │
      └────────────────────────────────────────────┘
                         ↓
      ┌────────────────────────────────────────────┐
      │     {% if user.is_authenticated %}         │
      │       include hero-logged.html             │
      │       include cta-dashboard.html           │
      │     {% else %}                             │
      │       include hero.html (8 partials)       │
      │       include pricing.html                 │
      │       include cta.html                     │
      │     {% endif %}                            │
      │     include footer.html                    │
      └────────────────────────────────────────────┘
                         ↓
              Final HTML rendered to browser
```

---

## 📊 Landing Page Sections (Ordem)

| # | Nome | Template Partial | Descrição | Status |
|---|------|------------------|-----------|--------|
| 0 | Navbar | `navbar-unified.html` | Navbar condicional (auth-based) | ✅ Unified |
| 1 | Header | `header.html` | Meta info + logo | ✅ Complete |
| **PÚBLICO** | | | | |
| 2 | Hero | `hero.html` | "Intelligent Hiring at Scale" | ✅ Complete |
| 3 | Vision | `vision.html` | 3-phase timeline (NEW) | ✅ NEW |
| 4 | Problem | `problem.html` | Before/After cards | ✅ Fixed |
| 5 | How-it-Works | `how-it-works.html` | 3 steps + D3 canvas | ✅ Fixed |
| 6 | Graphs vs Keywords | `graphs-vs-keywords.html` | Feature comparison | ✅ Complete |
| 7 | Features | `features.html` | 4 feature cards | ✅ Fixed icons |
| 8 | Tech Stack | `tech-stack.html` | 3-layer architecture | ✅ Fixed icons |
| 9 | Pricing | `pricing.html` | 3 pricing tiers | ✅ Verified |
| 10 | CTA | `cta.html` | Call-to-action | ✅ Complete |
| **LOGADO** | | | | |
| 2alt | Hero-Logged | `hero-logged.html` | Dashboard redirect | ✅ Complete |
| 10alt | CTA-Dashboard | `cta-dashboard.html` | Dashboard link | ✅ Complete |
| 11 | Footer | `footer.html` | Links + copyright | ✅ Complete |

---

## 🎨 CSS Organization

### `design-system.css` (Shared)
```css
:root {
  /* Colors */
  --color-brand: #0066FF
  --color-accent: #00D4AA
  --color-dark: #0F1419
  
  /* Typography */
  --font-family: 'Inter', sans-serif
  --font-size-h1: 3.5rem
  
  /* Spacing, shadows, etc. */
}
```

### `landing/index.css` (1154 linhas)
```css
.hero { }
.problem-card { }
.how-graph { height: 300px; }
.feature-icon { font-size: 36px; }
.pricing-card { }
...
```

### `landing/responsive.css` (Media queries)
```css
@media (max-width: 768px) {
  .hero { padding: 20px; }
  .tech-icon { font-size: 28px; }
  ...
}
```

### `landing/animations.css` (Scroll animations)
```css
@keyframes fadeInUp { }
.fade-in { animation: fadeInUp 0.8s ease-out; }
...
```

---

## ⚡ JavaScript Stack

### `graph-visualization.js`
- Usa D3.js v7 (unpkg ESM)
- Renderiza grafo no canvas `#how-it-works-graph-canvas`
- Exemplo de nó: `{id: "cv", label: "CV Input", x: 0, y: 0}`

### `graph-config.js`
- Define nodes e edges para visualização
- Cores: brand blue (#0066FF) e accent teal (#00D4AA)
- Layout: força-direcionado

### `lazy-loader.js`
- Lazy-loads imagens com Intersection Observer
- Reduz LCP (Largest Contentful Paint)

---

## 🌐 Routing & Views

| URL | View | Template | Descrição |
|-----|------|----------|----------|
| `/` | `home()` | `landing/index.html` | Landing page pública/logada |
| `/upload/` | `upload_cv()` | Landing + upload form | Upload CV público |
| `api/start-free/` | `start_free()` | JSON response | CTA button → signin |

---

## 📱 Responsive Breakpoints

```
480px  (Mobile)     → Stack vertical, 1-col
768px  (Tablet)     → 2-col cards, medium fonts
1024px (Laptop)     → 3-4 col grids, full width features
1440px (Desktop)    → Max 1200px container, centered
```

---

## 🔐 Design System Integration

✅ **Shared across landing + internal dashboards:**
- Colors: #0066FF (brand), #00D4AA (accent)
- Font: Google Fonts - Inter
- Shadows: sm/md/lg/xl
- Spacing: 8px scale
- Components: buttons, cards, badges, navbar

✅ **Landing uses `design-system.css`:**
```html
<link rel="stylesheet" href="{% static 'css/design-system.css' %}">
```

---

## 📊 Performance Metrics

| Métrica | Target | Status |
|---------|--------|--------|
| LCP | < 2.5s | ✅ |
| FCP | < 1.2s | ✅ |
| Lighthouse | 90+ | ✅ |
| D3 Canvas | 300px height | ✅ (Fixed) |
| Emoji sizes | Professional | ✅ (Fixed) |

---

## 🚀 Asset Pipeline

```
SOURCE (dev)           PROCESSED              SERVED (prod)
─────────────         ──────────             ──────────────
index.css        →    CSSO minify       →    index.min.css
                      WhiteNoise + cache-bust
                      
graph-viz.js     →    Terser minify     →    graph-viz.min.js
                      Fingerprinting
```

**Cache Busting:** Django `staticfiles` + WhiteNoise manifest versioning

---

## 📋 Deployment Stack

```
Git repo
  ↓
collectstatic (gather /static to /staticfiles)
  ↓
minify CSS/JS (CSSO + Terser)
  ↓
fingerprint assets (cache-busting)
  ↓
WhiteNoise serves (/ static files
  ↓
CDN optional (jsdelivr for Bootstrap, D3, fonts)
```

---

## ✅ Recent Fixes (2026-04-12)

| Item | Before | After | Status |
|------|--------|-------|--------|
| Problem cards layout | Flex issues | CSS Grid fixed | ✅ |
| How-it-works canvas | 400px gray | 300px transparent | ✅ |
| Feature icons | 48px (infantil) | 36px (professional) | ✅ |
| Tech icons | 48px | 32px (desktop), 28px (mobile) | ✅ |
| Navbar on dashboard | Breaking (white overlay) | Removed, Bootstrap nav | ✅ |
| Design system colors | Verified | Consistent #0066FF + #00D4AA | ✅ |

---

**Conclusão:** Landing page organizada em **17 templates + 3 CSS files + 3 JS files**, com design system unificado e responsive em 4 breakpoints. Pronta para produção com Lighthouse 90+.
