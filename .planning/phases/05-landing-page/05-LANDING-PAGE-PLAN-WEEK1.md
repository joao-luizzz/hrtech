# Phase 5: Landing Page Portal - Week 1 Plan
## Foundation & Static Structure (Header, Hero, Problem)

**Phase:** 5 - Landing Page Portal
**Week:** 1 of 4
**Duration:** 40 hours estimated
**Mode:** standard
**Status:** PLANNED

---

## Frontmatter

```yaml
wave: 1, 2
depends_on: []
files_modified:
  - core/templates/landing/index.html
  - core/templates/landing/base.html
  - core/templates/landing/partials/header.html
  - core/templates/landing/partials/hero.html
  - core/templates/landing/partials/problem.html
  - static/css/landing/index.css
  - static/css/landing/animations.css
  - core/views.py
  - core/urls.py
autonomous: true
```

---

## Overview

**Goal:** Build the foundational structure of the landing page (header, hero section, problem section) with static content and responsive layout. No animations or interactivity yet.

**Target Metrics:**
- Page renders without JavaScript errors
- Hero section visible in <1.2s (FCP)
- Mobile responsive at 480px, 768px, 1024px breakpoints
- All elements use correct colors, typography, spacing from UI-SPEC

**Wave Strategy:**
- **Wave 1 (Days 1-2):** Header, base template, CSS framework
- **Wave 2 (Days 3-5):** Hero section (static, no graph), Problem section, responsive layout

---

## Tasks

### Wave 1: Header & Template Foundation

#### Task 1: Set Up Django View and URL Routing
**Estimate:** 2 hours
**Wave:** 1

**Objective:** Create Django view to render landing page and wire up URL routing.

**Read First:**
- `/home/joao/hrtech/core/views.py` (existing view patterns)
- `/home/joao/hrtech/core/urls.py` (URL routing structure)
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-UI-SPEC.md` (page structure)

**Action:**
1. Create class-based view `LandingPageView(TemplateView)` in `core/views.py`
2. Set template_name to `'landing/index.html'`
3. Add `get_context_data()` to include: page_title='HRTech: AI-Powered Recruitment', page_description='Intelligent matching using knowledge graphs...'
4. Cache view with `@method_decorator(cache_page(60 * 60 * 24))` (24h cache)
5. Add URL pattern to `core/urls.py`: `path('', LandingPageView.as_view(), name='landing')` (root path)
6. Verify view renders without errors

**Acceptance Criteria:**
- `python manage.py check --deploy` exits 0
- Accessing `http://localhost:8000/` returns 200 status
- Page title in HTML contains 'HRTech: AI-Powered Recruitment'
- View context includes `page_description` in template
- Cache decorator present in view code (verifiable with grep)

---

#### Task 2: Create Landing Page Base Template
**Estimate:** 3 hours
**Wave:** 1

**Objective:** Build the master template with critical CSS, meta tags, and structure.

**Read First:**
- `/home/joao/hrtech/templates/base.html` (existing global base)
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-UI-SPEC.md` (design system, colors)
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (performance strategy)

**Action:**
1. Create `/home/joao/hrtech/core/templates/landing/base.html`
2. Extend from global `base.html` or create independent structure
3. Include critical CSS inline in `<style>` tag (200 lines max):
   - CSS variables: `--color-brand: #0066FF`, `--color-accent: #00D4AA`, `--color-dark: #0F1419`, `--color-light: #FFFFFF`
   - Hero section styles (min-height 600px, relative positioning)
   - Navbar styles (height 64px, sticky positioning)
   - Container and grid layouts (12-column Bootstrap)
4. Add meta tags: charset, viewport (mobile-responsive), description, og:title, og:description, canonical URL
5. Load Bootstrap 5.3 from CDN in `<head>` (or use existing if already included)
6. Load Inter font from Google Fonts: `<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">`
7. Defer non-critical CSS: `<link rel="stylesheet" href="{% static 'css/landing.css' %}" media="print" onload="this.media='all'">`
8. Add `{% block content %}{% endblock %}` and footer include

**Acceptance Criteria:**
- File exists at `/home/joao/hrtech/core/templates/landing/base.html`
- Template contains `<meta charset="utf-8">`
- Template contains `<meta name="viewport" content="width=device-width, initial-scale=1">`
- Template contains CSS variables for all 4 primary colors (grep: `--color-brand`, `--color-accent`, `--color-dark`, `--color-light`)
- Inter font loads from Google Fonts (link tag present)
- Template extends or includes Bootstrap 5
- Page renders without 404 on style/script resources
- Inline CSS is <5KB (performance)

---

#### Task 3: Create Sticky Header/Navigation Component
**Estimate:** 3.5 hours
**Wave:** 1

**Objective:** Build responsive sticky header with navigation links and CTA button.

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-UI-SPEC.md` (Header section, 64px height, links)
- `/home/joao/hrtech/core/templates/base.html` (any existing header patterns)

**Action:**
1. Create `/home/joao/hrtech/core/templates/landing/partials/header.html` (standalone partial)
2. Build HTML structure:
   ```html
   <header class="navbar sticky-top">
     <div class="container">
       <div class="logo">HRTech</div>
       <nav class="nav-links">
         <a href="#hero">Home</a>
         <a href="#features">Features</a>
         <a href="#pricing">Pricing</a>
         <a href="#cta">Get Started</a>
       </nav>
       <button class="btn-cta">Start Free</button>
     </div>
   </header>
   ```
3. Add CSS (in `static/css/landing/index.css`):
   - Height: 64px, background: `#0F1419`
   - Logo: 40×40px, left-aligned
   - Links: right-aligned, 16px font, color `#FFFFFF`
   - Button: primary blue (`#0066FF`), padding 12px 32px, border-radius 8px
   - Position: `position: sticky; top: 0; z-index: 100;`
   - Hover effect on links: underline 2px, color transition
4. Add mobile hamburger menu (display: none on desktop, block on <768px):
   - 3-line hamburger icon (use Bootstrap Icons or SVG)
   - Slide-in overlay menu from right (transform: translateX)
5. Ensure responsive: padding 24px (mobile), 48px (desktop)
6. Include in `index.html` with `{% include "landing/partials/header.html" %}`

**Acceptance Criteria:**
- Header file exists at `/home/joao/hrtech/core/templates/landing/partials/header.html`
- Page displays sticky header (position: sticky present in CSS)
- Header height is 64px (measurable in DevTools)
- Header contains links: Home, Features, Pricing, Get Started (grep for all 4)
- CTA button text is "Start Free"
- Button color is `#0066FF` or equivalent (CSS variable `--color-brand`)
- Hamburger menu appears on mobile (<768px)
- All navigation links have href targets
- Header z-index is 100 (CSS verifiable)

---

### Wave 2: Hero Section & Problem Section

#### Task 4: Create Hero Section Template (Static Graph Placeholder)
**Estimate:** 4.5 hours
**Wave:** 2

**Objective:** Build hero section with text overlay and canvas placeholder for animated graph (no animation yet).

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-UI-SPEC.md` (Hero specs: 600px height, graph background, text overlay)
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (Pattern 2: Text overlay on canvas)

**Action:**
1. Create `/home/joao/hrtech/core/templates/landing/partials/hero.html`
2. Build HTML structure (layers from bottom to top):
   ```html
   <section class="hero">
     <!-- Canvas graph background (z-index: 1) -->
     <canvas id="hero-graph-canvas" class="hero-graph"></canvas>

     <!-- Dark gradient overlay (z-index: 5, pointer-events: none) -->
     <div class="hero-overlay"></div>

     <!-- Text content (z-index: 10) -->
     <div class="hero-content">
       <h1>AI-Powered Recruitment That Actually Works</h1>
       <p>Built on knowledge graphs. Powered by AI. Infinitely more precise than keyword matching.</p>
       <div class="hero-buttons">
         <button class="btn-primary">Start Free Trial</button>
         <button class="btn-secondary">Watch Demo</button>
       </div>
     </div>
   </section>
   ```
3. Add CSS (in `static/css/landing/index.css`):
   - `.hero`: position relative, min-height 600px, overflow hidden
   - `.hero-graph`: position absolute, top 0, left 0, width 100%, height 100%, z-index 1, background solid color `#0F1419` (static fallback, no canvas rendering yet)
   - `.hero-overlay`: position absolute, z-index 5, pointer-events none, background `linear-gradient(180deg, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.5) 50%, rgba(0,0,0,0.3) 100%)`
   - `.hero-content`: position relative, z-index 10, display flex, flex-direction column, align-items center, justify-content center, height 100%, max-width 600px, text-align center, color `#FFFFFF`
   - H1: font-size 56px (3.5rem), font-weight 700, line-height 1.2, margin-bottom 24px, text-shadow 0 2px 10px rgba(0,0,0,0.5)
   - Paragraph: font-size 18px, color `#A0AAB8`, margin-bottom 32px, line-height 1.6, text-shadow 0 1px 4px rgba(0,0,0,0.3)
4. Add responsive sizing:
   - Desktop (1024px+): 600px height, 56px H1, 18px body
   - Tablet (768px-1024px): 500px height, 48px H1, 16px body
   - Mobile (<768px): 400px height, 32px H1, 14px body
5. Button styles inline (or reference task 5)
6. Canvas ID `hero-graph-canvas` (required for D3 init in Week 2)
7. Include in `index.html` after header

**Acceptance Criteria:**
- Hero section file exists at `/home/joao/hrtech/core/templates/landing/partials/hero.html`
- Hero section height is 600px on desktop (DevTools measurement)
- H1 text is "AI-Powered Recruitment That Actually Works" (exact match)
- Subheading text present (grep: "Built on knowledge graphs")
- Two buttons present: "Start Free Trial" and "Watch Demo"
- Canvas element with id `hero-graph-canvas` exists (for future D3 integration)
- Dark overlay present with gradient (CSS gradient property present)
- Text is white (`#FFFFFF`) and centered
- Text-shadow applied to H1 and paragraph
- Mobile height is 400px (<768px breakpoint)
- Tablet height is 500px (768-1024px)

---

#### Task 5: Style Buttons (Primary & Secondary Variants)
**Estimate:** 2 hours
**Wave:** 2

**Objective:** Create reusable button component styles matching UI-SPEC.

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-UI-SPEC.md` (Button specs: colors, padding, hover effects)
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (Animation performance: transform-only)

**Action:**
1. Add button styles to `static/css/landing/index.css`:
   ```css
   .btn-primary {
     background-color: #0066FF;
     color: white;
     padding: 12px 32px;
     border-radius: 8px;
     font-weight: 600;
     font-size: 16px;
     border: none;
     cursor: pointer;
     transition: all 0.2s ease;
     min-height: 44px; /* WCAG touch target */
   }

   .btn-primary:hover {
     background-color: #0052CC;
     box-shadow: 0 8px 16px rgba(0, 102, 255, 0.3);
     transform: translateY(-2px);
   }

   .btn-primary:active {
     transform: translateY(0);
   }

   .btn-secondary {
     background-color: transparent;
     color: #00D4AA;
     padding: 12px 32px;
     border: 2px solid #00D4AA;
     border-radius: 8px;
     font-weight: 600;
     font-size: 16px;
     cursor: pointer;
     transition: all 0.2s ease;
     min-height: 44px;
   }

   .btn-secondary:hover {
     background-color: rgba(0, 212, 170, 0.1);
     border-color: #0066FF;
     color: #0066FF;
   }
   ```
2. Ensure button gap: 16px between buttons (`.hero-buttons { gap: 16px; }`)
3. Test hover states in browser (color, shadow, transform)
4. Mobile button behavior: stack vertically on <480px, full width

**Acceptance Criteria:**
- `.btn-primary` background color is `#0066FF` (grep: `background-color: #0066FF`)
- `.btn-secondary` border color is `#00D4AA` (grep: `border: 2px solid #00D4AA`)
- Hover effect includes `transform: translateY(-2px)` (GPU-accelerated)
- Buttons have minimum height of 44px (WCAG compliant)
- Transition duration is 0.2s (grep: `0.2s ease`)
- Button padding is 12px 32px (matches UI-SPEC)
- Border-radius is 8px

---

#### Task 6: Create Problem Section (Before/After Comparison)
**Estimate:** 4 hours
**Wave:** 2

**Objective:** Build "Why Traditional ATS Falls Short" section with 3-column card layout.

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-UI-SPEC.md` (Problem section: before/after cards, 3 columns)
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (Pattern 4: Responsive grid)

**Action:**
1. Create `/home/joao/hrtech/core/templates/landing/partials/problem.html`
2. Build HTML (3-column grid using Bootstrap):
   ```html
   <section class="problem">
     <div class="container">
       <h2>Why Traditional ATS Falls Short</h2>
       <p class="intro">Keyword-based matching misses 35% of qualified candidates. Knowledge graphs catch them all.</p>

       <div class="row g-4 mt-5">
         <!-- Before Card -->
         <div class="col-12 col-md-4">
           <div class="problem-card problem-before">
             <div class="card-header">❌ Before</div>
             <ul>
               <li>Manual CV review</li>
               <li>Keyword matching</li>
               <li>Hours of analysis</li>
               <li>High bias risk</li>
               <li>Slow hiring pipeline</li>
             </ul>
           </div>
         </div>

         <!-- Arrow (hidden on mobile) -->
         <div class="col-12 col-md-4 arrow-col">
           <div class="arrow">→</div>
         </div>

         <!-- After Card -->
         <div class="col-12 col-md-4">
           <div class="problem-card problem-after">
             <div class="card-header">✅ After</div>
             <ul>
               <li>Automated CV processing</li>
               <li>Graph-based matching</li>
               <li>Minutes to analyze</li>
               <li>Objective scoring</li>
               <li>Fast hiring cycles</li>
             </ul>
           </div>
         </div>
       </div>
     </div>
   </section>
   ```
3. Add CSS to `static/css/landing/index.css`:
   - `.problem`: padding 64px 24px (desktop), 48px 16px (mobile), background `#0F1419`
   - H2: font-size 40px, font-weight 700, text-align center, color `#FFFFFF`, margin-bottom 24px
   - `.intro`: font-size 18px, color `#A0AAB8`, text-align center, max-width 600px, margin 0 auto
   - `.problem-card`: padding 32px, border-radius 12px, border 1px solid `#2D3139`, background `#1A1F26`, shadow-md, height 100%
   - `.problem-before`: border-color `#EF4444`, background `rgba(239, 68, 68, 0.05)`
   - `.problem-after`: border-color `#10B981`, background `rgba(16, 185, 129, 0.05)`
   - `.card-header`: font-weight 700, font-size 18px, margin-bottom 24px
   - `ul li`: list-style none, margin-bottom 12px, padding-left 24px, position relative
   - `ul li:before`: content "•", position absolute, left 0
   - `.arrow`: display flex, align-items center, justify-content center, height 100%, font-size 48px, color `#00D4AA`, opacity 0.5
   - Responsive: hide arrow on <768px, stack cards vertically
4. Section margin-top: 64px (after hero)

**Acceptance Criteria:**
- Problem section file exists at `/home/joao/hrtech/core/templates/landing/partials/problem.html`
- H2 text is "Why Traditional ATS Falls Short" (exact match)
- H2 font-size is 40px (grep: `40px` or `2.5rem`)
- Three card divs present (before, arrow/spacer, after)
- Before card contains "❌ Before" header
- After card contains "✅ After" header
- Before card background includes red tone (EF4444)
- After card background includes green tone (10B981)
- All 5 bullet points in before card visible (Manual CV, Keyword, Hours, Bias, Slow)
- All 5 bullet points in after card visible (Automated, Graph, Minutes, Objective, Fast)
- Arrow element present and styled with cyan color
- Cards use 12-column grid (col-12 col-md-4)
- Section margin-top is 64px

---

#### Task 7: Integrate Partials into Main Landing Page
**Estimate:** 2.5 hours
**Wave:** 2

**Objective:** Create `index.html` that brings together header, hero, and problem sections.

**Read First:**
- `/home/joao/hrtech/core/templates/landing/base.html` (just created)
- `/home/joao/hrtech/core/templates/landing/partials/header.html` (navigation)
- `/home/joao/hrtech/core/templates/landing/partials/hero.html` (hero section)
- `/home/joao/hrtech/core/templates/landing/partials/problem.html` (problem section)

**Action:**
1. Create `/home/joao/hrtech/core/templates/landing/index.html`
2. Build structure:
   ```html
   {% extends "landing/base.html" %}

   {% block content %}
     {% include "landing/partials/header.html" %}
     {% include "landing/partials/hero.html" %}
     {% include "landing/partials/problem.html" %}
   {% endblock %}
   ```
3. Verify no Django template errors (`python manage.py check`)
4. Load page in browser, verify all sections render in correct order
5. Check Lighthouse scores (target: FCP <1.2s at this stage)

**Acceptance Criteria:**
- Index file exists at `/home/joao/hrtech/core/templates/landing/index.html`
- File extends `landing/base.html` (grep: `extends`)
- File includes header partial (grep: `include.*header`)
- File includes hero partial (grep: `include.*hero`)
- File includes problem partial (grep: `include.*problem`)
- `python manage.py check` exits 0
- Page loads without 404 errors
- All three sections visible when scrolling

---

#### Task 8: Create Responsive CSS & Animations Framework
**Estimate:** 3 hours
**Wave:** 2

**Objective:** Establish CSS file structure, responsive breakpoints, and animation foundation.

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-UI-SPEC.md` (breakpoints: 480, 768, 1024, 1440px)
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (animation strategy: fade-in, lazy sections)

**Action:**
1. Create `/home/joao/hrtech/static/css/landing/index.css` with structure:
   - Root CSS variables (colors, shadows, spacing)
   - Base typography (h1-h6, p, ul, li)
   - Component styles (buttons, cards, containers)
   - Responsive breakpoints (media queries at 480px, 768px, 1024px, 1440px)
2. Create `/home/joao/hrtech/static/css/landing/animations.css`:
   ```css
   @keyframes fade-in {
     from {
       opacity: 0;
       transform: translateY(20px);
     }
     to {
       opacity: 1;
       transform: translateY(0);
     }
   }

   .lazy-section {
     opacity: 0;
     transform: translateY(20px);
     transition: opacity 0.6s ease, transform 0.6s ease;
   }

   .lazy-section.visible {
     opacity: 1;
     transform: translateY(0);
   }
   ```
3. Create `/home/joao/hrtech/static/css/landing/responsive.css`:
   ```css
   @media (max-width: 768px) {
     /* Mobile overrides */
     h1 { font-size: 2.5rem; }
     h2 { font-size: 1.875rem; }
     .container { padding: 0 16px; }
   }

   @media (max-width: 480px) {
     /* Small mobile */
     h1 { font-size: 1.75rem; }
     .container { padding: 0 12px; }
   }
   ```
4. Include all three CSS files in base template with correct order (index → responsive → animations)
5. CSS file size <30KB total (performance target)

**Acceptance Criteria:**
- `/home/joao/hrtech/static/css/landing/index.css` exists and is >500 lines
- `/home/joao/hrtech/static/css/landing/animations.css` exists with fade-in keyframe
- `/home/joao/hrtech/static/css/landing/responsive.css` exists with mobile breakpoints
- All three CSS files linked in base.html
- Root CSS variables defined (--color-brand, etc.)
- Media queries exist for 480px and 768px (grep: `@media`)
- fade-in animation defined (grep: `@keyframes fade-in`)
- Total CSS file size <30KB (checked with file size command)

---

#### Task 9: Verify Page Loads & Responsive Design
**Estimate:** 2.5 hours
**Wave:** 2

**Objective:** Full manual testing of page across breakpoints and performance validation.

**Read First:**
- `/home/joao/hrtech/core/templates/landing/base.html`
- `/home/joao/hrtech/core/templates/landing/index.html`
- `/home/joao/hrtech/core/templates/landing/partials/header.html`
- `/home/joao/hrtech/core/templates/landing/partials/hero.html`
- `/home/joao/hrtech/core/templates/landing/partials/problem.html`
- `/home/joao/hrtech/core/static/css/landing/index.css`
- `.planning/phases/05-landing-page/05-LANDING-PAGE-UI-SPEC.md` (design specs for verification)

**Action:**
1. Launch development server: `python manage.py runserver`
2. Open browser to `http://localhost:8000/`
3. Test desktop view (1440px):
   - Header sticky at top when scrolling
   - Hero section 600px height
   - Problem section displays 3 columns (before/arrow/after)
   - All text matches UI-SPEC copy
   - Colors match: primary `#0066FF`, accent `#00D4AA`, dark `#0F1419`
   - All buttons are clickable (href targets or placeholders)
4. Test tablet view (768px):
   - Header responsive, navigation condenses
   - Hero section 500px height
   - Problem section displays 2 columns (before/after stack)
5. Test mobile view (480px):
   - Hamburger menu appears and works
   - Hero section 400px height
   - H1 font-size reduced to ~32px
   - Buttons stack vertically
   - Problem cards stack fully (1 column)
6. Run Lighthouse audit (`npm install -g lighthouse && lighthouse http://localhost:8000 --view`):
   - FCP <1.2s
   - LCP <2.5s (hero text should be LCP)
   - CLS <0.1
   - Performance score should be >85
7. Test in Chrome DevTools mobile emulator and Safari on real device if available

**Acceptance Criteria:**
- Page loads at `http://localhost:8000/` and returns 200 status
- Header remains sticky when scrolling
- Hero section displays correct height at each breakpoint (600/500/400px)
- Problem section cards display in correct columns (3→2→1 layout)
- H1 text is visible within 1.2 seconds (FCP target)
- All colors match UI-SPEC (verifiable with DevTools color picker or screenshot comparison)
- Mobile hamburger menu appears on <768px
- Buttons are all 44px minimum height (WCAG)
- Lighthouse FCP score <1.2s
- Lighthouse LCP score <2.5s
- Lighthouse CLS score <0.1

---

## Verification Criteria

**All Week 1 tasks complete when:**
1. All files created and committed
2. Page renders without Django errors or 404s
3. Header, hero, and problem sections visible and styled correctly
4. Responsive layout confirmed at 480px, 768px, 1024px, 1440px
5. Colors, typography, spacing match UI-SPEC
6. Lighthouse FCP <1.2s, LCP <2.5s (before animation)
7. No JavaScript errors in console

---

## Must-Haves (Goal Backward Verification)

- [ ] Landing page at `/` serves 200
- [ ] Hero section displays in <1.2s (FCP)
- [ ] Page fully responsive (tested at 480/768/1024/1440px)
- [ ] All text copy matches UI-SPEC exactly
- [ ] Colors: primary #0066FF, accent #00D4AA present
- [ ] Header sticky on scroll
- [ ] No layout shift (CLS <0.1)
- [ ] Lighthouse score ≥85 (foundation phase)
