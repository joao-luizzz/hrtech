# 🎨 LANDING PAGE - IMPLEMENTAÇÃO VISUAL

## 📋 Estrutura Completa da Página

```
┌───────────────────────────────────────────────────────────────┐
│                    HEADER (Fixed/Sticky)                     │
│  Logo | Home | Features | Pricing | Blog | [Start Free]      │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│    ╔═══════════════════════════════════════════════════╗      │
│    ║          HERO SECTION (600px height)             ║      │
│    ║                                                  ║      │
│    ║  [ANIMATED NEO4J GRAPH BACKGROUND]              ║      │
│    ║      (D3.js nodes + edges, gentle rotation)     ║      │
│    ║                                                  ║      │
│    ║    AI-Powered Recruitment That Actually Works   ║      │
│    ║                                                  ║      │
│    ║    Built on knowledge graphs. Powered by AI.    ║      │
│    ║    Infinitely more precise than keyword matching║      │
│    ║                                                  ║      │
│    ║    [Primary CTA: Start Free Trial]  [Watch Demo]║      │
│    ╚═══════════════════════════════════════════════════╝      │
│                                                                │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│              SECTION 2: THE PROBLEM                           │
│              Why Traditional ATS Falls Short                  │
│                                                                │
│    ┌────────────┐      ┌────────────┐      ┌────────────┐   │
│    │ ❌ Before  │  →   │ Traditional│  →   │ ✓ After    │   │
│    │            │      │    ATS      │      │            │   │
│    │ • Manual   │      │            │      │ • Instant  │   │
│    │ • Keywords │      │  Outdated  │      │ • Graphs   │   │
│    │ • Hours    │      │  & Biased  │      │ • Smart    │   │
│    │ • Bias     │      │            │      │ • Precise  │   │
│    └────────────┘      └────────────┘      └────────────┘   │
│                                                                │
│    📊 Stat Cards:                                            │
│    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│    │   35%    │  │    92%   │  │   10x    │  │   30s    │  │
│    │ Missed   │  │ Accuracy │  │ Faster   │  │ Time     │  │
│    │qualified │  │          │  │          │  │          │  │
│    └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│                                                                │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│         SECTION 3: HOW IT WORKS (SPLIT SCREEN)               │
│                                                                │
│  Left: 3 Steps          │  Right: Live Graph Visualization  │
│  ┌─────────────────┐    │  ┌───────────────────────────┐    │
│  │ 1️⃣ Upload CV     │    │  │  (Python)──TEM_HAB──┐     │    │
│  │    GPT-4 extract │    │  │        ↓              │     │    │
│  │    skills        │    │  │    [Backend]        │     │    │
│  │                  │    │  │        ↓              │     │    │
│  │ 2️⃣ Build Graph    │    │  │   (Django)──────┘    │     │    │
│  │    Neo4j link    │    │  │                       │     │    │
│  │    relationships │    │  │  Hover to highlight!  │     │    │
│  │                  │    │  └───────────────────────┘    │    │
│  │ 3️⃣ Match Score    │    │                              │    │
│  │    Precision     │    │  Code Example (Cypher):       │    │
│  │                  │    │  MATCH (c)-[:TEM_HABILI...]  │    │
│  └─────────────────┘    │                               │    │
│                         │                               │    │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│         SECTION 4: GRAPHS > KEYWORDS (Comparison Table)      │
│                                                                │
│    ┌─────────────────┬──────────┬──────────────────────┐    │
│    │ Traditional ATS │ HRTech  │                       │    │
│    ├─────────────────┼──────────┤────────────────────────┤    │
│    │ Keyword Search  │ ✓ Graph Traversal       │    │
│    │ 65% accuracy    │ ✓ 92% accuracy          │    │
│    │ Minutes         │ ✓ Seconds               │    │
│    │ No bias detect  │ ✓ Smart filtering       │    │
│    │ Flat matching   │ ✓ Relationship aware    │    │
│    └─────────────────┴──────────┴────────────────────────┘    │
│                                                                │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│         SECTION 5: KEY FEATURES (4 Feature Cards)            │
│                                                                │
│    ┌─────────────────────┐    ┌─────────────────────┐        │
│    │ 🧠 Interview Q Gen  │    │ 📊 Skill Gap        │        │
│    │                     │    │                     │        │
│    │ Generate 3 custom   │    │ Deep dive into      │        │
│    │ interview questions │    │ missing skills      │        │
│    │ based on gaps       │    │ [New] [Free]        │        │
│    └─────────────────────┘    └─────────────────────┘        │
│                                                                │
│    ┌─────────────────────┐    ┌─────────────────────┐        │
│    │ 🔒 Multi-Tenant     │    │ ✅ LGPD Compliant   │        │
│    │                     │    │                     │        │
│    │ Enterprise data     │    │ PII masking, audit  │        │
│    │ isolation           │    │ trails, deletion    │        │
│    │ [Enterprise]        │    │ [Trusted Badge]     │        │
│    └─────────────────────┘    └─────────────────────┘        │
│                                                                │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│    SECTION 6: TECH STACK (3-Layer Architecture)              │
│                                                                │
│              ┌────────────────────────┐                      │
│              │  FRONTEND: Django + ╋  │                      │
│              │  Bootstrap + HTMX      │                      │
│              └──────────┬─────────────┘                      │
│                         │                                     │
│              ┌──────────┴─────────────┐                      │
│              │  API Layer + Caching   │                      │
│              │  Redis + Celery        │                      │
│              └──────────┬─────────────┘                      │
│                    │    │    │                               │
│         ┌──────────┴┐ ┌─┴───┘ ┌──────────────┐             │
│         │  PostgreSQL│ │Neo4j  │ AWS S3 + OCR │             │
│         │            │ │       │              │             │
│         └────────────┘ └───────┘──────────────┘             │
│                                                                │
│    💾 Tech Badges Grid:                                      │
│    ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐            │
│    │ PG   │ │Neo4j │ │Redis │ │  AI  │ │Django│            │
│    └──────┘ └──────┘ └──────┘ └──────┘ └──────┘            │
│                                                                │
│    🚀 "Deployed on Render | Serverless Redis | Global CDN"   │
│                                                                │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│    SECTION 7: PRICING (3-Tier Card Layout)                   │
│                                                                │
│    ┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│    │ STARTER        │  │ PRO ⭐        │  │ ENTERPRISE     │
│    │ Free (30 days) │  │ $99/month      │  │ Custom         │
│    ├────────────────┤  ├────────────────┤  ├────────────────┤
│    │ ✓ 50 candidates│  │ ✓ Unlimited    │  │ ✓ Everything + │
│    │ ✓ 1 user       │  │ ✓ 5 users      │  │ ✓ SSO + SLA    │
│    │ ✓ Dashboard    │  │ ✓ Analytics    │  │ ✓ Custom API   │
│    │ ✓ Skills       │  │ ✓ Integrations │  │ ✓ Dedicated    │
│    │                │  │ ✓ Interview Q  │  │                │
│    │[Start Free]    │  │[Most Popular]  │  │[Contact Sales] │
│    │                │  │[Upgrade to Pro]│  │                │
│    └────────────────┘  └────────────────┘  └────────────────┘
│                                                                │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│    SECTION 8: CTA FINAL                                      │
│                                                                │
│         Ready to hire smarter?                               │
│    Join 100+ companies using AI-powered matching             │
│                                                                │
│         [Start Free Trial]  [Schedule Demo]                  │
│                                                                │
├───────────────────────────────────────────────────────────────┤
│                      FOOTER                                   │
│  Product | Pricing | Blog | Docs | Security | Legal |©2026   │
└───────────────────────────────────────────────────────────────┘
```

---

## 🎨 COLOR & SPACING QUICK REFERENCE

### Color Tokens
```
Primary Blue:     #0066FF  (CTAs, links, highlights)
Secondary Teal:   #00D4AA  (Accents, badges, success)
Dark Background:  #0F1419  (Main bg)
Card bg:          #1A1F26  (Card bg)
Border:           #2D3139  (Subtle dividers)
Text Primary:     #FFFFFF  (Main text)
Text Secondary:   #A0AAB8  (Secondary, meta)
```

### Spacing Grid
```
xs: 4px  | sm: 8px  | md: 16px | lg: 24px | xl: 32px | 2xl: 48px | 3xl: 64px
```

### Typography
```
H1: 3.5rem (56px) - Hero titles
H2: 2.5rem (40px) - Section titles
H3: 1.875rem (30px) - Feature titles
H4: 1.5rem (24px) - Card titles
Body: 1rem (16px) - Normal text
Small: 0.875rem (14px) - Captions
Tiny: 0.75rem (12px) - Labels
```

---

## 🚀 QUICK START HTML STRUCTURE

### Hero Section (Example)
```html
<section class="hero" style="
  min-height: 600px;
  background: linear-gradient(135deg, rgba(0,102,255,0.1) 0%, transparent 50%),
              url('graph-bg.svg') center/cover;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: white;
  position: relative;
">
  <!-- Graph Animation Canvas -->
  <canvas id="graph-canvas" style="
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 1;
    opacity: 0.8;
  "></canvas>

  <!-- Content Overlay (z-index: 10) -->
  <div style="position: relative; z-index: 10; max-width: 600px;">
    <h1 style="
      font-size: 3.5rem;
      font-weight: 700;
      margin-bottom: 24px;
      line-height: 1.2;
    ">
      AI-Powered Recruitment That Actually Works
    </h1>

    <p style="
      font-size: 1.125rem;
      color: #A0AAB8;
      margin-bottom: 32px;
      line-height: 1.6;
    ">
      Built on knowledge graphs. Powered by AI.
      <br>
      Infinitely more precise than keyword matching.
    </p>

    <div style="display: flex; gap: 16px; justify-content: center;">
      <button class="btn-primary">Start Free Trial</button>
      <button class="btn-secondary">Watch Demo</button>
    </div>
  </div>
</section>
```

### Feature Cards Grid (Example)
```html
<section class="features">
  <h2>Supercharge Your Hiring</h2>

  <div style="
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 24px;
    margin-top: 48px;
  ">
    <div class="feature-card">
      <div class="feature-icon">🧠</div>
      <h3>Interview Questions</h3>
      <p>Generate 3 personalized interview questions based on skill gaps</p>
      <span class="badge">New</span>
    </div>

    <div class="feature-card">
      <div class="feature-icon">📊</div>
      <h3>Skill Gap Analysis</h3>
      <p>Deep dive into what skills candidates are missing</p>
    </div>

    <div class="feature-card">
      <div class="feature-icon">🔒</div>
      <h3>Multi-Tenant Isolation</h3>
      <p>Enterprise-grade data isolation for multiple companies</p>
    </div>

    <div class="feature-card">
      <div class="feature-icon">✅</div>
      <h3>LGPD Compliant</h3>
      <p>PII masking, audit trails, data deletion on demand</p>
    </div>
  </div>
</section>
```

### CSS for Feature Cards
```css
.feature-card {
  padding: 32px;
  border: 1px solid #2D3139;
  border-radius: 12px;
  background-color: #1A1F26;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
}

.feature-card:hover {
  border-color: #0066FF;
  box-shadow: 0 12px 24px rgba(0, 102, 255, 0.15);
  transform: translateY(-4px);
}

.feature-icon {
  font-size: 40px;
  margin-bottom: 16px;
  display: block;
}

.feature-card h3 {
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: 12px;
  color: white;
}

.feature-card p {
  font-size: 0.875rem;
  color: #A0AAB8;
  line-height: 1.6;
}

.badge {
  display: inline-block;
  background-color: #10B981;
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-top: 12px;
}
```

---

## 📊 PRICING SECTION EXAMPLE

```html
<section class="pricing">
  <h2>Get Started with HRTech</h2>

  <div class="pricing-grid">
    <div class="pricing-card">
      <h3>Starter</h3>
      <div class="price">FREE</div>
      <span class="duration">for 30 days</span>

      <ul class="features-list">
        <li>✓ Up to 50 candidates</li>
        <li>✓ 1 team member</li>
        <li>✓ Dashboard basics</li>
        <li>✗ Analytics</li>
      </ul>

      <button class="btn-primary-full">Start Free</button>
    </div>

    <div class="pricing-card featured">
      <div class="badge-popular">Most Popular</div>
      <h3>Pro</h3>
      <div class="price">$99<span class="per-month">/month</span></div>

      <ul class="features-list">
        <li>✓ Unlimited candidates</li>
        <li>✓ 5 team members</li>
        <li>✓ Advanced analytics</li>
        <li>✓ Interview questions</li>
      </ul>

      <button class="btn-primary-full">Upgrade to Pro</button>
    </div>

    <div class="pricing-card">
      <h3>Enterprise</h3>
      <div class="price">Custom</div>
      <span class="duration">For large teams</span>

      <ul class="features-list">
        <li>✓ Everything + SSO</li>
        <li>✓ SLA guarantee</li>
        <li>✓ Custom integrations</li>
        <li>✓ Dedicated support</li>
      </ul>

      <button class="btn-secondary-full">Contact Sales</button>
    </div>
  </div>
</section>
```

### Pricing CSS
```css
.pricing-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 32px;
  margin-top: 48px;
}

.pricing-card {
  padding: 32px;
  border: 1px solid #2D3139;
  border-radius: 12px;
  background-color: #1A1F26;
  position: relative;
}

.pricing-card.featured {
  border-color: #0066FF;
  box-shadow: 0 12px 24px rgba(0, 102, 255, 0.15);
  transform: scale(1.05);
}

.pricing-card h3 {
  font-size: 1.5rem;
  margin-bottom: 16px;
  color: white;
}

.price {
  font-size: 2.5rem;
  font-weight: 700;
  color: #0066FF;
  margin-bottom: 8px;
}

.per-month {
  font-size: 1rem;
  color: #A0AAB8;
  font-weight: 400;
}

.duration {
  display: block;
  font-size: 0.875rem;
  color: #A0AAB8;
  margin-bottom: 24px;
}

.features-list {
  list-style: none;
  padding: 0;
  margin-bottom: 32px;
}

.features-list li {
  padding: 8px 0;
  font-size: 0.875rem;
  color: #A0AAB8;
  border-bottom: 1px solid #2D3139;
}

.btn-primary-full,
.btn-secondary-full {
  width: 100%;
  padding: 12px 32px;
  height: 44px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.2s ease;
}

.btn-primary-full {
  background-color: #0066FF;
  color: white;
}

.btn-primary-full:hover {
  background-color: #0052CC;
}

.btn-secondary-full {
  background-color: transparent;
  border: 2px solid #00D4AA;
  color: #00D4AA;
}

.btn-secondary-full:hover {
  background-color: rgba(0, 212, 170, 0.1);
}
```

---

## 📱 RESPONSIVE MOBILE ADJUSTMENTS

```css
@media (max-width: 768px) {
  h1 {
    font-size: 2.5rem;
  }

  h2 {
    font-size: 1.875rem;
  }

  .hero {
    min-height: 400px;
    padding: 16px;
  }

  .pricing-card.featured {
    transform: none;
    scale: 1;
  }

  .pricing-grid {
    grid-template-columns: 1fr;
  }

  [class*="btn"] {
    min-height: 44px;
    font-size: 16px;
  }
}
```

---

## 🎬 GRAPH ANIMATION (D3.js Example)

```javascript
// Simple force-directed graph with D3.js
import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";

const width = document.getElementById('graph-canvas').clientWidth;
const height = document.getElementById('graph-canvas').clientHeight;

// Sample data: skill nodes and relationships
const nodes = [
  { id: "Python", group: 1 },
  { id: "Django", group: 1 },
  { id: "PostgreSQL", group: 2 },
  { id: "React", group: 3 },
  { id: "JavaScript", group: 3 },
  { id: "Neo4j", group: 2 },
  { id: "Redis", group: 2 },
  { id: "Docker", group: 4 },
];

const links = [
  { source: "Python", target: "Django" },
  { source: "Django", target: "PostgreSQL" },
  { source: "React", target: "JavaScript" },
  { source: "Python", target: "Neo4j" },
  { source: "Docker", target: "PostgreSQL" },
];

const svg = d3.select("#graph-canvas")
  .attr("width", width)
  .attr("height", height);

const colorScale = d3.scaleOrdinal(d3.schemeCategory10);

const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d => d.id).distance(100))
  .force("charge", d3.forceManyBody().strength(-300))
  .force("center", d3.forceCenter(width / 2, height / 2));

const link = svg.append("g")
  .selectAll("line")
  .data(links)
  .enter()
  .append("line")
  .attr("stroke", "rgba(255,255,255,0.2)")
  .attr("stroke-width", 2);

const node = svg.append("g")
  .selectAll("circle")
  .data(nodes)
  .enter()
  .append("circle")
  .attr("r", 20)
  .attr("fill", d => colorScale(d.group))
  .call(drag(simulation));

simulation.on("tick", () => {
  link
    .attr("x1", d => d.source.x)
    .attr("y1", d => d.source.y)
    .attr("x2", d => d.target.x)
    .attr("y2", d => d.target.y);

  node
    .attr("cx", d => d.x)
    .attr("cy", d => d.y);
});

function drag(simulation) {
  function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }

  function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
  }

  function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }

  return d3.drag()
    .on("start", dragstarted)
    .on("drag", dragged)
    .on("end", dragended);
}
```

---

## ✅ IMPLEMENTATION CHECKLIST

### Phase 1 (Week 1)
- [ ] Setup Django project structure
- [ ] Create base template with Bootstrap 5
- [ ] Header & navigation (sticky)
- [ ] Hero section (static, no animation)
- [ ] Problem section (3-column cards)
- [ ] Basic CSS custom properties (colors, spacing)
- [ ] Responsive mobile menu

### Phase 2 (Week 2)
- [ ] Integrate D3.js for graph visualization
- [ ] Animated graph background in hero
- [ ] How It Works section (split layout)
- [ ] Features grid (4 cards)
- [ ] Graphs > Keywords comparison table
- [ ] Hover animations on cards

### Phase 3 (Week 3)
- [ ] Tech stack section (architecture diagram)
- [ ] Pricing section (3-tier cards)
- [ ] CTA section
- [ ] Footer + legal pages
- [ ] Form submission (newsletter signup)

### Phase 4 (Week 4)
- [ ] Performance optimization (image lazy-loading)
- [ ] SEO meta tags
- [ ] Google Analytics integration
- [ ] Mobile refinements
- [ ] A/B testing setup
- [ ] Dark mode toggle (if needed)

---

## 🚀 NEXT STEPS

Once this UI-SPEC is approved:

1. **Create Planning Phase:**
   - `/gsd:plan-phase` for landing page implementation

2. **Development Stack:**
   - Framework: Django + Bootstrap 5 + HTMX
   - Graph: D3.js v7+
   - Build: Vite (optional) or Django collectstatic
   - Analytics: Google Tag Manager + GA4

3. **Deployment:**
   - Deploy to Render alongside existing app
   - CDN for static assets
   - SEO optimization

---

**This UI-SPEC is ready for development!** 🎨✨
