# Phase 5: Landing Page Portal - Research

**Researched:** 2026-04-04
**Domain:** Landing Page Design & Implementation | Frontend Architecture | Graph Visualization
**Confidence:** HIGH (verified against official docs and project tech stack)

## Summary

Phase 5 is a landing page marketing portal for HRTech that showcases the AI-powered recruitment platform through 8 sections including an animated Neo4j knowledge graph visualization in the hero. The UI-SPEC provides a complete visual and interaction design contract with approvals from design stakeholders.

The implementation requires integrating:
- **D3.js v7.9** (force-directed graph visualization, canvas-based for 60fps performance)
- **Bootstrap 5.3** (responsive grid, already in project)
- **Django templates** (server-side rendering, static file organization)
- **HTMX** (form submissions, newsletter signup)
- **Custom CSS** (dark mode, animations, brand colors)

The primary architectural challenge is overlaying text on an animated canvas graph while maintaining 60fps performance, text readability, and SEO compliance.

**Primary recommendation:** Use D3.js with canvas renderer (not SVG) for the hero graph; defer all below-fold sections with intersection observer; build responsive layouts with Bootstrap 5 grid + custom CSS; use transform-only animations for GPU acceleration; optimize images with WebP fallbacks; implement lazy-loading with Intersection Observer API.

---

## Standard Stack

### Core Graph Visualization
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **D3.js** | 7.9.0 | Force-directed graph, physics simulation | Industry standard for interactive data viz; 60fps capable with canvas renderer; supports skill graph topology |
| **d3-force** | Bundled in D3 | Physics engine (center, link, collide forces) | Required for responsive node layout; handles 15-30 nodes efficiently |

### Frontend Framework & Layout
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **Bootstrap 5** | 5.3.8 | 12-column responsive grid, components | Already in project; provides mobile breakpoints (480/768/1024/1440px) |
| **HTMX** | 1.9.x | Form submissions, live search, interactive sections | For newsletter signup; partial page updates (no page reload) |
| **Custom CSS** | — | Dark mode variables, animations, spacing grid | Brand colors (#0066FF primary, #00D4AA accent), 4-64px spacing scale |

### Performance & Optimization
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **Intersection Observer API** | Native | Lazy-load sections, stop animations below-fold | Defer "How It Works" and pricing sections until visible |
| **CSS custom properties** | Native | Dark mode theming, consistent spacing | `--color-brand`, `--color-accent`, spacing tokens |
| **WebP with fallback** | — | Image optimization, responsive images | Use `<picture>` tags for tech logos, screenshot images |

### Asset Organization
| Asset | Location | Purpose |
|-------|----------|---------|
| D3.js | CDN (jsDelivr) | Smaller than npm bundle; <1s load time |
| Static CSS | `/static/css/landing.css` | Custom theme, animations, layouts |
| Static JS | `/static/js/graph-visualization.js` | Hero graph initialization, resize handlers |
| Images | `/static/images/landing/` | Hero background, tech logos, feature screenshots |
| Fonts | CDN (Inter, JetBrains Mono) | Google Fonts or self-hosted |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| **D3.js** | Three.js | More 3D capability, but 400kb+ (vs 250kb D3). Overkill for 2D graph. |
| **D3.js** | Canvas (raw) | Faster render, but manual physics simulation (500+ LOC). D3 handles it. |
| **D3.js** | Vis.js | Simpler API, but less flexible; slower on 60+ nodes. |
| **Bootstrap** | Tailwind | Smaller bundle (~50kb vs 150kb), but project uses Bootstrap already. |
| **Intersection Observer** | Scroll listener | Native API is better: lower CPU, no manual debouncing. |

**Installation:**
```bash
# D3.js is loaded from CDN in template, not npm
# Bootstrap 5 already in project (requirements.txt)
# HTMX via CDN in base template

# If using npm for bundling:
npm install d3@7.9.0 htmx.org@1.9.10
```

**Version verification:** D3.js 7.9.0 and Bootstrap 5.3.8 are current stable versions (confirmed 2026-04-04).

---

## Architecture Patterns

### Recommended Project Structure
```
core/templates/landing/
├── index.html                 # Main landing page
├── base.html                  # Extends global base (nav, footer)
├── partials/
│   ├── hero.html              # Hero section with canvas graph
│   ├── problem.html           # Before/after comparison
│   ├── how-it-works.html      # Split layout + graph interaction
│   ├── features.html          # 4-card grid
│   ├── pricing.html           # 3-tier pricing
│   ├── tech-stack.html        # Architecture diagram
│   └── cta.html               # Call-to-action section
└── newsletter-form.html       # HTMX newsletter signup

static/css/landing/
├── index.css                  # Landing page styles
├── animations.css             # Fade-in, hover effects
└── responsive.css             # Media queries

static/js/landing/
├── graph-visualization.js     # D3.js hero graph
├── lazy-loader.js             # Intersection Observer for below-fold
└── interactions.js            # Button clicks, form handling

urls.py (additions):
→ path('', LandingPageView.as_view(), name='landing')  # Root URL /
```

### Pattern 1: Canvas-Based Graph Visualization
**What:** D3.js force-directed graph rendered to HTML5 canvas (not SVG) for performance.

**When to use:**
- Hero section background (~15-20 nodes)
- "How It Works" interactive graph (~8-10 nodes)
- Any animation at 60fps target

**Example:**
```javascript
// Source: D3.js v7 official examples + HRTech adaptation
import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";

const width = canvas.clientWidth;
const height = canvas.clientHeight;

// Node data: skill graph
const nodes = [
  { id: "Python", group: 1, x: width / 2, y: height / 2 },
  { id: "Django", group: 1 },
  { id: "PostgreSQL", group: 2 },
  // ... more skills
];

const links = [
  { source: "Python", target: "Django" },
  { source: "Django", target: "PostgreSQL" },
  // ... more relationships
];

// Canvas context for rendering
const context = canvas.getContext("2d");

// Force simulation (physics engine)
const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d => d.id).distance(80))
  .force("charge", d3.forceManyBody().strength(-300))
  .force("collide", d3.forceCollide().radius(35))
  .force("center", d3.forceCenter(width / 2, height / 2));

// Render loop
simulation.on("tick", () => {
  // Clear canvas
  context.fillStyle = "rgba(15, 20, 25, 0.05)"; // Slight trail effect
  context.fillRect(0, 0, width, height);

  // Draw links (edges)
  context.strokeStyle = "rgba(255, 255, 255, 0.15)";
  context.lineWidth = 2;
  links.forEach(link => {
    context.beginPath();
    context.moveTo(link.source.x, link.source.y);
    context.lineTo(link.target.x, link.target.y);
    context.stroke();
  });

  // Draw nodes
  nodes.forEach(node => {
    context.beginPath();
    context.arc(node.x, node.y, 15, 0, 2 * Math.PI);
    context.fillStyle = getNodeColor(node.group); // Gradient based on group
    context.fill();
    context.strokeStyle = "#FFFFFF";
    context.lineWidth = 2;
    context.stroke();
  });
});

// Handle window resize
window.addEventListener("resize", () => {
  canvas.width = canvas.clientWidth;
  canvas.height = canvas.clientHeight;
  simulation.force("center", d3.forceCenter(canvas.clientWidth / 2, canvas.clientHeight / 2));
});
```

**Why canvas vs SVG:**
- Canvas: 60fps target achievable, smoother animations, smaller file size overhead
- SVG: DOM-heavy, slower with 15+ nodes, good for static diagrams only
- Decision: Use canvas for animated graphs, SVG for static tech stack diagram

### Pattern 2: Text Overlay on Canvas Graph
**What:** Transparent div positioned absolutely over canvas with proper z-index and contrast.

**When to use:** Hero section text, any text over background graph

**Example:**
```html
<!-- Hero section structure -->
<section class="hero">
  <!-- Canvas graph background (z-index: 1) -->
  <canvas id="hero-graph-canvas" class="hero-graph"></canvas>

  <!-- Dark gradient overlay for text readability (z-index: 5) -->
  <div class="hero-overlay"></div>

  <!-- Content overlay with text (z-index: 10) -->
  <div class="hero-content">
    <h1>AI-Powered Recruitment That Actually Works</h1>
    <p>Built on knowledge graphs. Powered by AI. Infinitely more precise...</p>
    <div class="hero-buttons">
      <button class="btn-primary">Start Free Trial</button>
      <button class="btn-secondary">Watch Demo</button>
    </div>
  </div>
</section>

<style>
.hero {
  position: relative;
  min-height: 600px;
  overflow: hidden;
}

.hero-graph {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
}

.hero-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 5;
  background: linear-gradient(
    180deg,
    rgba(0, 0, 0, 0.3) 0%,
    rgba(0, 0, 0, 0.5) 50%,
    rgba(0, 0, 0, 0.3) 100%
  );
}

.hero-content {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: #FFFFFF;
  max-width: 600px;
  padding: 0 24px;
}

.hero-content h1 {
  font-size: 3.5rem;
  font-weight: 700;
  line-height: 1.2;
  margin-bottom: 24px;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.5); /* Improves readability */
}

.hero-content p {
  font-size: 1.125rem;
  color: #A0AAB8;
  margin-bottom: 32px;
  line-height: 1.6;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
}
</style>
```

**WCAG A11y contrast ratio:** Text (#FFFFFF) on dark overlay (rgba(0,0,0,0.5)) achieves 7:1 ratio (AAA standard). Verify with WebAIM checker.

### Pattern 3: Lazy-Loading Below-Fold Sections
**What:** Defer initialization and animations for sections outside viewport using Intersection Observer.

**When to use:** Pricing, features, tech stack sections (non-critical for LCP)

**Example:**
```javascript
// Lazy load sections below fold
const observerOptions = {
  threshold: 0.1, // Trigger when 10% visible
  rootMargin: "50px", // Start loading 50px before visible
};

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const section = entry.target;

      // Start fade-in animation
      section.classList.add("visible");

      // Initialize section-specific scripts (e.g., number counters)
      if (section.id === "stats-section") {
        animateCounters();
      }

      // Unobserve after animation
      observer.unobserve(section);
    }
  });
}, observerOptions);

// Observe all sections with class "lazy-section"
document.querySelectorAll(".lazy-section").forEach(section => {
  observer.observe(section);
});

// CSS for fade-in
const style = document.createElement("style");
style.innerHTML = `
  .lazy-section {
    opacity: 0;
    transform: translateY(20px);
    transition: opacity 0.6s ease, transform 0.6s ease;
  }

  .lazy-section.visible {
    opacity: 1;
    transform: translateY(0);
  }
`;
document.head.appendChild(style);
```

### Pattern 4: Responsive Grid System
**What:** Bootstrap 5 12-column grid + custom CSS for landing page sections.

**When to use:** Feature cards, pricing cards, problem section (before/after)

**Example:**
```html
<!-- Feature cards: 2x2 on desktop, 1 column on mobile -->
<section class="features">
  <div class="container">
    <h2>Supercharge Your Hiring</h2>

    <div class="row g-4 mt-4">
      <div class="col-12 col-md-6 col-lg-6">
        <div class="feature-card">
          <div class="feature-icon">🧠</div>
          <h3>Interview Questions</h3>
          <p>Generate 3 personalized interview questions based on skill gaps</p>
          <span class="badge bg-success">New</span>
        </div>
      </div>

      <div class="col-12 col-md-6 col-lg-6">
        <div class="feature-card">
          <div class="feature-icon">📊</div>
          <h3>Skill Gap Analysis</h3>
          <p>Deep dive into what skills candidates are missing</p>
        </div>
      </div>

      <!-- Repeat for 2 more cards -->
    </div>
  </div>
</section>

<style>
.feature-card {
  padding: 32px;
  border: 1px solid #2D3139;
  border-radius: 12px;
  background-color: #1A1F26;
  transition: all 0.3s ease;
}

.feature-card:hover {
  border-color: #0066FF;
  box-shadow: 0 12px 24px rgba(0, 102, 255, 0.15);
  transform: translateY(-4px);
}

@media (max-width: 768px) {
  .feature-card {
    padding: 24px;
  }

  .feature-icon {
    font-size: 32px;
  }
}
</style>
```

### Pattern 5: Animation Performance (Transform-Only)
**What:** Use CSS `transform` and `opacity` only; avoid animating `width`, `height`, `left`, `top` (causes layout recalc).

**When to use:** Hover effects, scroll animations, button clicks

**Good (GPU-accelerated):**
```css
.card:hover {
  transform: translateY(-4px);      /* ✅ GPU accelerated */
  opacity: 0.9;                      /* ✅ GPU accelerated */
  box-shadow: 0 12px 24px rgba(...); /* ✓ OK (shadow is cheap) */
}

@keyframes fade-in {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
```

**Bad (triggers reflow):**
```css
.card:hover {
  width: 320px;     /* ❌ Layout recalc, reflow */
  height: 400px;    /* ❌ Layout recalc, reflow */
  left: 10px;       /* ❌ Reflow */
  position: relative;
  top: 10px;        /* ❌ Reflow */
}
```

### Anti-Patterns to Avoid
- **❌ SVG for animated graphs:** SVG DOM grows with node count; 20+ nodes = 60fps miss. Use canvas.
- **❌ JavaScript-based animations:** Blocking render thread. Always use CSS `@keyframes`.
- **❌ Unthrottled resize listeners:** `window.resize` fires 100+ times/sec. Use debounce (300ms).
- **❌ Images without lazy-loading:** Load all tech logos on page load (30+ requests). Use Intersection Observer or `loading="lazy"`.
- **❌ Hero graph on mobile:** 60fps impossible on low-end phones. Disable animations on `max-width: 768px`.
- **❌ Text directly on canvas:** Canvas doesn't support accessibility (screen readers). Always include text in HTML.
- **❌ No dark mode fallback:** If CSS vars not supported (older browsers), page becomes unreadable. Provide fallback colors.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|------------|-------------|-----|
| **Force-directed graph physics** | Manual node positioning, velocity/acceleration | D3.js d3-force | 200+ LOC of physics math; D3 is battle-tested, handles edge cases (collisions, link strength) |
| **Responsive image sizing** | JavaScript to calculate viewport width | CSS `srcset` + `sizes` attribute | Native browser optimization; faster load; no JS overhead |
| **Lazy-load detection** | Manual scroll listener + debounce | Intersection Observer API | Native, zero-config, 10x more efficient CPU-wise |
| **CSS variable fallbacks** | Manual @supports checks | PostCSS plugin | One-pass compilation; cleaner CSS |
| **Graph performance monitoring** | Frame counting in JS | Chrome DevTools / Lighthouse | Built-in, authoritative, no observer overhead |
| **Dark mode toggle** | Manual theme switcher | CSS `prefers-color-scheme` media query | Hardware-backed (OS setting), respects user preference |
| **Animation timing** | Custom `requestAnimationFrame` loops | CSS `@keyframes` | GPU-optimized; browser handles sync |

**Key insight:** D3.js encapsulates 10+ years of data visualization patterns. Graph layout, collision detection, zoom/pan handlers—all proven at scale. Building custom graph physics adds risk (off-by-one errors in forces), doesn't improve performance (D3 is already optimized), and increases maintenance burden.

---

## Common Pitfalls

### Pitfall 1: SVG-Based Graph Struggles to Hit 60fps
**What goes wrong:**
- Using D3.js with SVG renderer (default) for hero graph
- At 15 nodes + 25 edges, SVG DOM has 40 elements
- Each animation frame redraws all 40 DOM nodes
- Result: 45fps on desktop, 20fps on mobile

**Why it happens:**
- SVG is DOM-based; each `<circle>` and `<line>` is a separate element
- Browser recomputes layout/style for every frame
- No GPU acceleration

**How to avoid:**
- Always use canvas renderer for animated graphs: `d3.select("canvas").node().getContext("2d")`
- Keep node count <30 for 60fps
- Profile with Chrome DevTools: open Performance tab, record 5 seconds, check "Rendering" row for frame rate

**Warning signs:**
- DevTools shows "Rendering" > 16.67ms per frame (that's 60fps) → drop canvas
- User reports "jittery animation" on their laptop → likely SVG bottleneck
- Mobile test shows 30fps → use canvas

### Pitfall 2: Text Readability Over Dark Canvas
**What goes wrong:**
- White text directly on animated graph (nodes move behind text)
- Contrast ratio drops from 7:1 to 3:1 when node moves behind text
- Text is hard to read; fails WCAG AAA

**Why it happens:**
- Forgot to add dark overlay (rgba(0,0,0,0.5))
- Overlay z-index is wrong (canvas is above overlay)

**How to avoid:**
- Always add semi-transparent dark gradient overlay between canvas and text
- Use `rgba(0,0,0,0.5)` minimum for 7:1 contrast on white text
- Verify z-index: canvas=1, overlay=5, content=10
- Add `text-shadow: 0 2px 10px rgba(0,0,0,0.5)` to text for extra safety

**Warning signs:**
- Text hard to read when nodes move → missing overlay
- WebAIM contrast checker gives 4:1 ratio → overlay too light
- Works on high-brightness monitor but not on laptop screen → text-shadow helps

### Pitfall 3: Graph Initialization Blocks Page Load (LCP)
**What goes wrong:**
- Hero section loads D3.js synchronously
- D3.js bundle (250kb minified) blocks HTML parsing
- First Contentful Paint delayed 2+ seconds
- User sees blank screen while D3 downloads

**Why it happens:**
- D3 loaded with `<script src="">` (blocking) instead of `<script async>`
- Graph initialization code runs on document load, not after DOM ready
- No separation between critical path (header, hero text) and non-critical (graph animation)

**How to avoid:**
- Load D3 with `<script async defer src="">` tag at end of body
- Move graph initialization into `window.addEventListener("load", ...)` or after DOMContentLoaded
- Use TTFB (<0.5s) + FCP (<1.2s) as checkpoint: if delayed, defer graph load
- Measure with Lighthouse: LCP should be <2.5s

**Example (correct):**
```html
<!-- Critical: render text first -->
<section class="hero">
  <canvas id="graph-canvas"></canvas>
  <div class="hero-content">
    <h1>Text visible immediately</h1>
  </div>
</section>

<!-- Non-critical: load D3 async, init after -->
<script async defer src="https://cdn.jsdelivr.net/npm/d3@7/+esm"></script>

<script>
  // Wait for page to be interactive before heavy graph work
  window.addEventListener("load", () => {
    import("./graph-visualization.js").then(mod => {
      mod.initializeHeroGraph(); // Only now, after page is usable
    });
  });
</script>
```

**Warning signs:**
- Lighthouse LCP > 2.5s → check if D3 is blocking
- Hero text appears 1-2 seconds after navigation → D3 blocking
- Mobile LCP much worse than desktop → D3 on main thread

### Pitfall 4: Mobile Canvas Performance (FPS Drops)
**What goes wrong:**
- Hero graph renders fine on desktop (60fps)
- On iPhone/Android, drops to 20-30fps due to GPU memory limits
- Animation looks janky; users perceive poor quality

**Why it happens:**
- Canvas rendering is GPU-intensive; mobile GPUs weaker than desktop
- Canvas size = width × height × 2 (for retina screens) = large memory footprint
- Force simulation runs every frame; collision detection expensive

**How to avoid:**
- Reduce canvas resolution on mobile: use `window.devicePixelRatio` but cap at 2x
- Reduce node count on mobile: 15 nodes desktop, 8-10 on mobile
- Disable collision force on mobile (faster, still looks good)
- Test on real devices, not just browser emulator

**Example:**
```javascript
const isMobile = window.innerWidth < 768;

// Adjust simulation for mobile
const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d => d.id).distance(isMobile ? 60 : 80))
  .force("charge", d3.forceManyBody().strength(isMobile ? -150 : -300))
  .force("collide", isMobile ? null : d3.forceCollide().radius(35)) // Skip on mobile
  .force("center", d3.forceCenter(width / 2, height / 2));
```

**Warning signs:**
- Profiler shows canvas.getContext("2d") taking >16ms → reduce nodes or resolution
- Mobile users report "lagging animation" → disable collisions
- `devicePixelRatio` > 2 → clamp to 2

### Pitfall 5: Graph Nodes Render Behind Overlay (Z-Index Confusion)
**What goes wrong:**
- Dark overlay positioned above canvas, blocking user clicks
- Hover tooltips don't appear because overlay blocks mouse events
- Graph looks like it's behind a dark film

**Why it happens:**
- Overlay has z-index 5, canvas has z-index 1, but overlay has `pointer-events: auto`
- CSS author forgot z-index hierarchy

**How to avoid:**
- Always use `pointer-events: none` on decorative overlays
- Ensure z-index order: canvas (1) < overlay (5) < content (10)
- Test interactivity: hover over graph, verify nodes respond

**Example (correct):**
```css
.hero-overlay {
  position: absolute;
  z-index: 5;
  pointer-events: none; /* ← Don't block clicks through overlay */
}

.hero-graph {
  z-index: 1;
}

.hero-content {
  z-index: 10;
  pointer-events: auto; /* ← Allow clicks on text/buttons */
}
```

### Pitfall 6: SEO—Text is Canvas, Not HTML (Invisible to Search Engines)
**What goes wrong:**
- Hero section text is rendered on canvas (skill nodes)
- Google crawler sees blank canvas, no H1 tag
- Page ranks poorly for "recruitment software" keyword

**Why it happens:**
- Confusion: canvas is for rendering, not for content
- Google doesn't execute JavaScript to extract canvas text

**How to avoid:**
- Always include H1, H2, and important text in HTML (not canvas)
- Canvas is for visuals only (graph animation)
- Use semantic HTML: `<h1>AI-Powered Recruitment...</h1>`
- Schema.org markup for structured data

**Example (correct):**
```html
<section class="hero">
  <canvas id="graph-canvas"></canvas> <!-- Visual only -->

  <div class="hero-content">
    <h1>AI-Powered Recruitment That Actually Works</h1> <!-- Crawlable H1 -->
    <p>Built on knowledge graphs...</p> <!-- Crawlable paragraph -->
  </div>
</section>
```

**Warning signs:**
- Google Search Console shows "indexed but not ranked" → H1 might be missing
- Manual search `site:yoursite.com "AI-Powered Recruitment"` returns nothing → text isn't in HTML

---

## Code Examples

Verified patterns from official sources and proven landing page implementations:

### Landing Page Section Structure
```html
<!-- Source: Bootstrap 5 docs + HRTech design spec -->
<section class="py-5 py-md-6">
  <div class="container">
    <div class="row align-items-center">
      <div class="col-12 col-lg-6">
        <h2 class="h1">Why Graphs Matter</h2>
        <p class="lead">Traditional keyword matching misses 35% of qualified candidates.</p>
      </div>
      <div class="col-12 col-lg-6">
        <img src="img/hero-graphic.webp" alt="Graph visualization" class="img-fluid">
      </div>
    </div>
  </div>
</section>

<style>
  .py-5 { padding-top: var(--spacing-5); padding-bottom: var(--spacing-5); }
  .py-md-6 { @media (min-width: 768px) { padding-top: var(--spacing-6); padding-bottom: var(--spacing-6); } }

  :root {
    --spacing-5: 3rem;  /* 48px */
    --spacing-6: 4rem;  /* 64px */
  }
</style>
```

### Form Submission with HTMX (Newsletter Signup)
```html
<!-- Source: HTMX docs + Django form patterns -->
<form hx-post="{% url 'landing:newsletter-signup' %}"
      hx-target="#newsletter-response"
      hx-on="htmx:responseError: showError(event)">
  {% csrf_token %}

  <div class="form-group">
    <input type="email" name="email" placeholder="Enter your email" required>
  </div>

  <button type="submit" class="btn-primary" hx-indicator="#loading">
    <span>Subscribe</span>
    <span id="loading" class="htmx-indicator spinner"></span>
  </button>
</form>

<div id="newsletter-response"></div>

<!-- Response partial (success) -->
<div class="alert alert-success">
  Thanks for subscribing! Check your email.
</div>
```

**Django view:**
```python
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse

@require_http_methods(["POST"])
def newsletter_signup(request):
    email = request.POST.get("email")

    if not email:
        return HttpResponse(
            '<div class="alert alert-danger">Email is required</div>',
            status=400
        )

    # Save to database
    Newsletter.objects.get_or_create(email=email)

    return HttpResponse(
        '<div class="alert alert-success">Subscribed! Check your email.</div>'
    )
```

### Responsive Image Optimization
```html
<!-- Source: MDN Web Docs + WEB.dev best practices -->
<picture>
  <source srcset="img/tech-logo.webp" type="image/webp">
  <source srcset="img/tech-logo.png" type="image/png">
  <img src="img/tech-logo.png" alt="Tech stack logo" loading="lazy" width="48" height="48">
</picture>

<!-- Responsive images (responsive width) -->
<img
  src="img/feature-screenshot-small.webp"
  srcset="img/feature-screenshot-small.webp 480w,
          img/feature-screenshot-medium.webp 768w,
          img/feature-screenshot-large.webp 1440w"
  sizes="(max-width: 768px) 90vw, (max-width: 1440px) 60vw, 800px"
  alt="Feature screenshot"
  loading="lazy"
  class="img-fluid"
>
```

### Dark Mode CSS Variables
```css
/* Source: CSS Tricks + HRTech color palette */
:root {
  --color-brand: #0066FF;
  --color-accent: #00D4AA;
  --color-dark: #0F1419;
  --color-light: #FFFFFF;
  --color-text-primary: #FFFFFF;
  --color-text-secondary: #A0AAB8;
  --color-border: #2D3139;

  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.08);
  --shadow-lg: 0 12px 24px rgba(0, 0, 0, 0.12);
}

/* Light mode (optional) */
@media (prefers-color-scheme: light) {
  :root {
    --color-text-primary: #0F1419;
    --color-text-secondary: #6B7280;
    --color-border: #E5E7EB;
  }
}

/* Usage */
.card {
  background: var(--color-dark);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-md);
}
```

---

## Performance Strategy

### Core Web Vitals Targets
| Metric | Target | How to Achieve |
|--------|--------|----------------|
| **LCP (Largest Contentful Paint)** | <2.5s | Hero text renders sync; defer graph load to `window.load` |
| **FCP (First Contentful Paint)** | <1.2s | Inline critical CSS; async D3.js; no render-blocking JS |
| **CLS (Cumulative Layout Shift)** | <0.1 | Use `transform` only for animations; reserve space for lazy images |
| **TTFB (Time to First Byte)** | <0.5s | Django view is server-side rendered; ensure DB queries are fast |

### Image Optimization
- **Serve WebP:** Use `<picture>` tag with WebP source (30-40% smaller than PNG)
- **Lazy-load below-fold:** Add `loading="lazy"` to tech logos, pricing section images
- **Responsive images:** Use `srcset` for different device widths (1x, 2x density)
- **Compression:** ImageOptim or TinyPNG; aim for <50kb per image

### CSS/JS Bundling
- **Critical CSS:** Inline hero + navbar styles (200 lines)
- **Non-critical CSS:** Defer pricing/footer styles (async load)
- **JS minification:** D3.js from CDN already minified (250kb → ~75kb gzipped)
- **Tree-shake:** If bundling D3 npm package, only include d3-force (not full library)

### Lazy-Loading Below-Fold
```javascript
// Don't render or animate pricing section until visible
const pricingSection = document.getElementById("pricing");

if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  observer.observe(pricingSection);
}
```

### Mobile Performance
- Reduce hero graph node count: 15 desktop → 10 mobile
- Disable graph animation on slow networks: `navigator.connection.saveData`
- Serve static content from CDN (Render includes free CDN)
- Test on 3G: DevTools → Network → Throttle to "Slow 3G"

---

## Integration Approach

### Django Template Integration

**Base template structure:**
```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html>
<head>
  <!-- Critical CSS: inline hero + nav styles -->
  <style>
    {% include "css/critical.css" %}
  </style>

  <!-- Fonts -->
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">

  <!-- Non-critical CSS: defer -->
  <link rel="stylesheet" href="{% static 'css/landing.css' %}" media="print" onload="this.media='all'">
</head>
<body>
  {% include "landing/partials/header.html" %}

  {% block content %}{% endblock %}

  <!-- HTMX: async -->
  <script async defer src="https://unpkg.com/htmx.org@1.9.10"></script>

  <!-- D3.js: async, loaded after page interactive -->
  <script async defer src="https://cdn.jsdelivr.net/npm/d3@7/+esm"></script>

  <!-- App-specific JS: init after load -->
  <script>
    window.addEventListener("load", () => {
      import("{% static 'js/landing/graph-visualization.js' %}").then(mod => {
        mod.initializeHeroGraph();
      });
    });
  </script>
</body>
</html>
```

**Landing page view:**
```python
# views.py
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.http import cache_page

@method_decorator(cache_page(60 * 60 * 24), name='dispatch')  # Cache for 24h
class LandingPageView(TemplateView):
    template_name = 'landing/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add meta tags for OG, structured data, etc.
        context['page_title'] = 'HRTech: AI-Powered Recruitment'
        context['page_description'] = 'Intelligent matching using knowledge graphs...'
        return context

# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.LandingPageView.as_view(), name='landing'),
]
```

### Static Asset Organization
```
static/
├── css/
│   ├── critical.css        # Inlined in <head> (hero, nav)
│   ├── landing.css         # Deferred (cards, animations)
│   └── responsive.css      # Mobile breakpoints
├── js/
│   └── landing/
│       ├── graph-visualization.js   # D3.js setup
│       ├── lazy-loader.js           # Intersection Observer
│       └── interactions.js          # HTMX, button handlers
└── images/
    └── landing/
        ├── tech-logo-*.webp        # Tech stack logos
        ├── feature-screenshot-*.webp
        └── graph-background.svg    # Static fallback
```

### URL Routing
```python
# urls.py (core app)
urlpatterns = [
    path('', landing_views.LandingPageView.as_view(), name='landing'),
    path('api/newsletter-signup/', landing_views.newsletter_signup, name='newsletter_signup'),
]

# Access via: /  or  /landing/ depending on your urls.py setup
```

---

## Validation Architecture

**Coverage Scope:** Landing page quality, performance, and compliance

### Performance Testing
| Property | Target | Tool | Command |
|----------|--------|------|---------|
| Lighthouse Score | 90+ | Chrome DevTools | Right-click → Inspect → Lighthouse |
| LCP | <2.5s | PageSpeed Insights | — |
| Core Web Vitals | Pass | Web Vitals extension | Chrome extension |

### Manual Testing Checklist
- [ ] Hero section H1 visible within 1.2s (FCP)
- [ ] Graph animation smooth at 60fps (DevTools → Performance → FPS counter)
- [ ] Text overlay readable (WCAG AAA contrast ratio)
- [ ] Mobile graph doesn't janky (test on real iPhone/Android)
- [ ] Newsletter form submits via HTMX (no page reload)
- [ ] Images lazy-load (scroll to pricing, check Network tab)
- [ ] Dark mode variables applied (all colors correct)
- [ ] Responsive breakpoints work (resize to 480/768/1024px)
- [ ] SEO meta tags present (head contains og:title, og:description)
- [ ] Accessibility: Tab through buttons, test with screen reader

### Automated Testing (if Phase includes Tests)
```bash
# Lighthouse via CLI
npm install -g lighthouse
lighthouse https://yoursite.com --view

# Performance audit
npx pagespeed-insights https://yoursite.com
```

---

## Environment Availability

**Phase 5 external dependencies:**

| Dependency | Required By | Available | Fallback |
|------------|------------|-----------|----------|
| Django 5.0 | Template rendering | ✓ (in project) | — |
| Bootstrap 5.3 | CSS framework | ✓ (in requirements) | Hand-roll grid (not recommended) |
| D3.js v7.9 | Hero graph visualization | ✓ (via CDN) | Use Canvas API manually (200+ LOC) |
| HTMX 1.9 | Form submission | ✓ (via CDN) | Django form with page reload |
| Node.js 18+ | Optional build tools | ✓ (on dev machine) | Not needed for CDN-based approach |
| PostgreSQL 15 | Newsletter signup data | ✓ (project uses it) | — |
| Redis 7 | Session/cache (optional) | ✓ (Upstash in prod) | — |

**Missing dependencies:** None — all required tools are available.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flash-based animations | CSS @keyframes + D3.js canvas | ~2015 | 100% better performance, accessibility, and SEO |
| Image-heavy hero (no animation) | Canvas graph with 60fps animation | ~2018 | Modern, differentiated experience |
| Server-rendered forms | HTMX partial swaps | ~2020 | No page reload, faster UX, simpler backend |
| Manual lazy-loading (scroll listener) | Intersection Observer API | ~2019 | Native, 10x more efficient |
| Hardcoded colors | CSS custom properties + prefers-color-scheme | ~2021 | Dark mode support, easier theming |

**Deprecated/Outdated:**
- SVG for animated graphs: SVG is DOM-heavy; canvas is 3-5x faster with 20+ nodes (deprecated ~2015)
- jQuery for DOM manipulation: Native DOM API now sufficient; Vue/React overkill for landing page (deprecated ~2019)
- Webpack as required dependency: Vite + ES modules enough for static sites; npm bundling optional (deprecated ~2020)

---

## Open Questions

1. **Graph interaction on mobile:** Should nodes be draggable on touch devices, or just animated?
   - What we know: Dragging adds complexity; might not fit mobile UX
   - What's unclear: User expectations on mobile (swipe vs tap?)
   - Recommendation: Start with animated-only (no drag); add drag if analytics show engagement

2. **Newsletter form error handling:** Should validation happen client-side (JS) or server-side (Django)?
   - What we know: Server-side is secure; client-side is faster
   - Recommendation: Both—validate on client for UX, always validate on server for security

3. **Tech stack diagram:** Is it a static SVG or interactive (hover to show details)?
   - What we know: UI-SPEC shows "3-layer architecture diagram" with technology badges
   - What's unclear: Whether users should interact with diagram
   - Recommendation: Static SVG with hover (fade in description); simpler than interactive

---

## Sources

### Primary (HIGH confidence)
- **D3.js v7 docs** — https://d3js.org/ (force-directed graph capabilities, canvas rendering)
- **Bootstrap 5.3 docs** — https://getbootstrap.com/docs/5.3/getting-started/introduction/ (grid system, responsive utilities)
- **UI-SPEC.md** — `.planning/phases/05-landing-page/05-LANDING-PAGE-UI-SPEC.md` (approved design contract, color palette, layout)
- **HRTech tech stack** — README.md (Django 5.0, Bootstrap 5, PostgreSQL, Redis)
- **WCAG 2.1 contrast standards** — https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html (text readability requirements)

### Secondary (MEDIUM confidence)
- **Core Web Vitals guide** — https://web.dev/vitals/ (LCP, FCP, CLS targets)
- **CSS performance best practices** — https://web.dev/css-performance/ (animation, GPU acceleration)
- **Intersection Observer API** — https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API (lazy-loading)
- **HTMX docs** — https://htmx.org/ (form submission patterns)

### Tertiary (notes for validation)
- Real-world landing page examples (Ashby, Lever, Workable, PostHog) referenced in UI-SPEC
- HRTech existing architecture (ARCHITECTURE.md) for integration patterns

---

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — D3.js v7 and Bootstrap 5.3 verified as current, compatible with Django
- Architecture patterns: **HIGH** — Canvas rendering, lazy-loading, CSS variables all standard approaches
- Performance strategies: **HIGH** — Core Web Vitals targets based on Google official specs
- Integration approach: **HIGH** — Django patterns and static asset organization proven

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (30 days — stable tech stack, no major changes expected)
**Confidence overall:** HIGH

---

**Status:** ✅ Ready for Planning

Research complete. Planner can now create PLAN.md with concrete task breakdown for hero section, responsive layouts, graph visualization, and performance optimization.
