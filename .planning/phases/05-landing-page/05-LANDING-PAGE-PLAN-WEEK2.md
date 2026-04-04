# Phase 5: Landing Page Portal - Week 2 Plan
## Interactive Graph & Animation Layer (D3.js, Animations)

**Phase:** 5 - Landing Page Portal
**Week:** 2 of 4
**Duration:** 40 hours estimated
**Mode:** standard
**Status:** PLANNED

---

## Frontmatter

```yaml
wave: 1, 2, 3
depends_on: [05-LANDING-PAGE-PLAN-WEEK1.md]
files_modified:
  - core/templates/landing/partials/hero.html
  - core/templates/landing/partials/how-it-works.html
  - static/js/landing/graph-visualization.js
  - static/js/landing/lazy-loader.js
  - static/css/landing/animations.css
  - static/css/landing/index.css
  - core/templates/landing/partials/graphs-vs-keywords.html
autonomous: true
```

---

## Overview

**Goal:** Integrate D3.js for animated force-directed graph in hero section and "How It Works" section. Implement lazy-loading for below-fold sections. Add scroll-triggered animations.

**Target Metrics:**
- Hero graph renders at 60fps (canvas-based, not SVG)
- Hero graph animation doesn't block FCP (deferred via `async defer`)
- Lazy-loaded sections fade in when visible
- LCP still <2.5s (graph loads after page interactive)
- Lighthouse score >90

**Wave Strategy:**
- **Wave 1 (Days 1-2):** D3.js CDN integration, graph data structure, canvas rendering
- **Wave 2 (Days 3-4):** Hero graph animation, mobile optimization, performance testing
- **Wave 3 (Days 5-6):** How It Works section, lazy-loading, scroll animations, Graphs vs Keywords section

---

## Tasks

### Wave 1: D3.js Graph Foundation

#### Task 1: Load D3.js from CDN with Async/Defer
**Estimate:** 1.5 hours
**Wave:** 1

**Objective:** Add D3.js library to page without blocking rendering.

**Read First:**
- `/home/joao/hrtech/core/templates/landing/base.html` (script loading strategy)
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (Pitfall 3: blocking loads)

**Action:**
1. Update `/home/joao/hrtech/core/templates/landing/base.html`
2. Add D3.js script at END of `<body>` (not in head):
   ```html
   <!-- Load D3.js asynchronously, after page is interactive -->
   <script async defer src="https://cdn.jsdelivr.net/npm/d3@7/+esm"></script>
   ```
3. Do NOT include D3 in critical rendering path
4. Verify page still renders without JavaScript (graceful degradation)
5. Check Network tab in DevTools: D3 should load AFTER DOMContentLoaded

**Acceptance Criteria:**
- D3.js script tag present with `async defer` attributes (grep: `async defer.*d3@7`)
- Script tag is after all page content (at end of body)
- Page renders without JavaScript errors if D3 fails to load
- Network waterfall shows D3 loads after page paint

---

#### Task 2: Create Graph Data Structure & Configuration
**Estimate:** 2 hours
**Wave:** 1

**Objective:** Define skill graph nodes and relationships for hero visualization.

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (Pattern 1: Canvas graph setup, node count)
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-UI-SPEC.md` (Hero graph: 15-20 nodes, gradients)

**Action:**
1. Create `/home/joao/hrtech/static/js/landing/graph-config.js`:
2. Define nodes array (18 nodes for desktop):
   ```javascript
   const heroGraphData = {
     nodes: [
       { id: "Python", group: 1, x: null, y: null },
       { id: "Django", group: 1 },
       { id: "PostgreSQL", group: 2 },
       { id: "Neo4j", group: 2 },
       { id: "Redis", group: 2 },
       { id: "React", group: 1 },
       { id: "JavaScript", group: 1 },
       { id: "AWS", group: 3 },
       { id: "Docker", group: 3 },
       { id: "API", group: 1 },
       { id: "GraphQL", group: 1 },
       { id: "Celery", group: 3 },
       { id: "HTMX", group: 1 },
       { id: "Bootstrap", group: 1 },
       { id: "REST", group: 1 },
       { id: "Git", group: 3 },
       { id: "OpenAI", group: 3 },
       { id: "Matching", group: 1 }
     ],
     links: [
       { source: "Python", target: "Django", distance: 80 },
       { source: "Django", target: "PostgreSQL", distance: 80 },
       { source: "Django", target: "Redis", distance: 80 },
       { source: "Neo4j", target: "Matching", distance: 80 },
       { source: "React", target: "JavaScript", distance: 60 },
       { source: "API", target: "Django", distance: 80 },
       { source: "GraphQL", target: "API", distance: 70 },
       // ... 15-20 more links for natural graph shape
     ]
   };

   // Mobile: reduce to 10 nodes
   const mobileGraphData = {
     nodes: heroGraphData.nodes.slice(0, 10),
     links: heroGraphData.links.filter(link =>
       heroGraphData.nodes.slice(0, 10).map(n => n.id).includes(link.source) &&
       heroGraphData.nodes.slice(0, 10).map(n => n.id).includes(link.target)
     )
   };
   ```
3. Define colors for 3 groups (blue → cyan → teal gradients):
   ```javascript
   const nodeColors = {
     1: "url(#gradient-1)", // Blue→Cyan
     2: "url(#gradient-2)", // Cyan→Teal
     3: "url(#gradient-3)"  // Teal→Blue
   };
   ```
4. Include file in `base.html` before graph-visualization.js

**Acceptance Criteria:**
- File exists at `/home/joao/hrtech/static/js/landing/graph-config.js`
- 18 nodes defined for desktop (grep: count nodes)
- 10 nodes defined for mobile
- Links array has 20+ entries
- Node groups are 1, 2, or 3 (for coloring)
- Desktop nodes include: Python, Django, PostgreSQL, Neo4j, React, OpenAI, Matching
- Mobile data is subset of desktop data
- Each link has source, target, and optional distance

---

#### Task 3: Initialize Canvas & Force Simulation
**Estimate:** 3 hours
**Wave:** 1

**Objective:** Set up D3.js canvas rendering and physics simulation.

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (Pattern 1: Force simulation setup)
- `/home/joao/hrtech/static/js/landing/graph-config.js` (just created)

**Action:**
1. Create `/home/joao/hrtech/static/js/landing/graph-visualization.js`:
2. Main export function:
   ```javascript
   export function initializeHeroGraph() {
     const canvas = document.getElementById('hero-graph-canvas');
     if (!canvas) return; // Graceful degradation if canvas missing

     const width = canvas.clientWidth || window.innerWidth;
     const height = canvas.clientHeight || 600;
     const context = canvas.getContext('2d');

     // Detect mobile
     const isMobile = window.innerWidth < 768;
     const data = isMobile ? mobileGraphData : heroGraphData;

     // Canvas pixel ratio (for retina displays)
     const pixelRatio = Math.min(window.devicePixelRatio, 2);
     canvas.width = width * pixelRatio;
     canvas.height = height * pixelRatio;
     context.scale(pixelRatio, pixelRatio);

     // Force simulation
     const simulation = d3.forceSimulation(data.nodes)
       .force('link', d3.forceLink(data.links)
         .id(d => d.id)
         .distance(d => d.distance || 80))
       .force('charge', d3.forceManyBody()
         .strength(isMobile ? -150 : -300))
       .force('collide', isMobile ? null : d3.forceCollide().radius(35))
       .force('center', d3.forceCenter(width / 2, height / 2));

     // Render loop
     simulation.on('tick', () => {
       // Clear canvas with slight trail effect
       context.fillStyle = 'rgba(15, 20, 25, 0.05)';
       context.fillRect(0, 0, width, height);

       // Draw links
       context.strokeStyle = 'rgba(255, 255, 255, 0.15)';
       context.lineWidth = 2;
       data.links.forEach(link => {
         context.beginPath();
         context.moveTo(link.source.x, link.source.y);
         context.lineTo(link.target.x, link.target.y);
         context.stroke();
       });

       // Draw nodes
       data.nodes.forEach(node => {
         context.beginPath();
         context.arc(node.x, node.y, 15, 0, 2 * Math.PI);
         const color = getNodeColor(node.group);
         context.fillStyle = color;
         context.fill();
         context.strokeStyle = '#FFFFFF';
         context.lineWidth = 2;
         context.stroke();
       });
     });

     // Handle window resize
     window.addEventListener('resize', debounce(() => {
       const newWidth = canvas.clientWidth;
       const newHeight = canvas.clientHeight;
       canvas.width = newWidth * pixelRatio;
       canvas.height = newHeight * pixelRatio;
       context.scale(pixelRatio, pixelRatio);
       simulation.force('center', d3.forceCenter(newWidth / 2, newHeight / 2));
     }, 300));
   }

   function getNodeColor(group) {
     const colors = {
       1: '#0066FF', // Blue
       2: '#00D4AA', // Cyan
       3: '#0099FF'  // Light blue
     };
     return colors[group] || '#0066FF';
   }

   function debounce(fn, delay) {
     let timeout;
     return (...args) => {
       clearTimeout(timeout);
       timeout = setTimeout(() => fn(...args), delay);
     };
   }
   ```
3. Include in base.html after D3: `<script type="module">import { initializeHeroGraph } from "{% static 'js/landing/graph-visualization.js' %}"; window.addEventListener('load', initializeHeroGraph);</script>`

**Acceptance Criteria:**
- File exists at `/home/joao/hrtech/static/js/landing/graph-visualization.js`
- `initializeHeroGraph()` function exported (grep: `export function`)
- Canvas element accessed by ID `hero-graph-canvas`
- D3 force simulation created with link, charge, collide, center forces
- Render loop draws links as lines and nodes as circles
- Mobile uses reduced charge (-150) vs desktop (-300)
- Mobile disables collision detection (for performance)
- Pixel ratio handling for retina displays (devicePixelRatio)
- Resize listener debounced at 300ms
- Function returns early if canvas not found (graceful degradation)

---

### Wave 2: Hero Graph Animation & Performance

#### Task 4: Animate Graph with Gentle Rotation Effect
**Estimate:** 2.5 hours
**Wave:** 2

**Objective:** Add subtle animation to graph without impacting 60fps performance.

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (Pitfall 1: SVG vs canvas)
- `/home/joao/hrtech/static/js/landing/graph-visualization.js` (render loop)

**Action:**
1. Update `graph-visualization.js` render loop:
   ```javascript
   let angle = 0;
   const rotationSpeed = 0.0005; // Slow rotation (20s per full circle)

   simulation.on('tick', () => {
     // ... existing clear and draw code ...

     // Apply subtle rotation for visual interest
     angle += rotationSpeed;
     const rotation = angle % (2 * Math.PI);

     data.nodes.forEach(node => {
       const cos = Math.cos(rotation);
       const sin = Math.sin(rotation);
       const cx = width / 2;
       const cy = height / 2;
       const x = node.x - cx;
       const y = node.y - cy;
       const rotatedX = x * cos - y * sin + cx;
       const rotatedY = x * sin + y * cos + cy;

       // Draw with rotated coordinates
       context.beginPath();
       context.arc(rotatedX, rotatedY, 15, 0, 2 * Math.PI);
       context.fillStyle = getNodeColor(node.group);
       context.fill();
     });
   });
   ```
2. Test FPS: open DevTools Performance tab, record 5 seconds, check frame rate
3. Verify: should stay at 60fps (16.67ms per frame)

**Acceptance Criteria:**
- Rotation code present in render loop (grep: `Math.cos.*Math.sin`)
- Rotation speed is 0.0005 (for ~20s full rotation)
- Chrome DevTools Performance shows 60fps sustained (no dropped frames)
- Graph visibly rotates when viewed in browser
- No console warnings or errors

---

#### Task 5: Test Canvas Graph Performance on Mobile
**Estimate:** 2 hours
**Wave:** 2

**Objective:** Validate 60fps performance on real mobile devices or emulator.

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (Pitfall 4: Mobile FPS)
- `/home/joao/hrtech/static/js/landing/graph-visualization.js` (mobile config)

**Action:**
1. Open DevTools on mobile (Chrome Android or Safari iOS)
2. Test on simulated iPhone 12 (375px width):
   - Open Performance tab
   - Record 5 seconds while graph animates
   - Check frame rate: should be >30fps (mobile target)
3. Test on real device if available:
   - iPhone/Android with latest browser
   - Observe animation smoothness
4. Measure: DevTools → Performance → FCP, LCP
   - FCP should be <1.2s (before graph loads)
   - LCP should be <2.5s (text loads before graph animation)
5. If FPS drops <30: reduce node count further (8 nodes) or disable rotation on very slow devices

**Acceptance Criteria:**
- Mobile (375px) FPS ≥30 (DevTools Performance record)
- FCP <1.2s on mobile
- LCP <2.5s on mobile
- No crashes or hangs on mobile
- Graph renders smaller on mobile (responsive canvas sizing)
- Collision detection disabled on mobile (config shows `isMobile ? null : d3.forceCollide()`)

---

#### Task 6: Optimize LCP with Lazy Graph Initialization
**Estimate:** 2 hours
**Wave:** 2

**Objective:** Defer graph animation to ensure page is interactive before D3 work starts.

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (Pitfall 3: LCP bottleneck)
- `/home/joao/hrtech/core/templates/landing/base.html` (script loading)

**Action:**
1. Update base.html script loading:
   ```html
   <!-- Critical: D3 loads async, no blocking -->
   <script async defer src="https://cdn.jsdelivr.net/npm/d3@7/+esm"></script>

   <!-- Graph init only after page is fully loaded & interactive -->
   <script type="module">
     window.addEventListener('load', () => {
       // Import dynamically after page is ready
       import('/static/js/landing/graph-visualization.js').then(mod => {
         mod.initializeHeroGraph();
       });
     });
   </script>
   ```
2. Verify: Lighthouse should show FCP/LCP unaffected by D3
3. Check Network waterfall: D3.js and graph-visualization.js load AFTER hero text renders

**Acceptance Criteria:**
- D3.js loads with `async defer`
- Graph initialization deferred to `window.load` event
- Hero text (H1) visible before graph animation starts
- Lighthouse FCP <1.2s
- Lighthouse LCP <2.5s
- Network waterfall shows D3 loading after FCP marker

---

### Wave 3: How It Works & Lazy-Loading

#### Task 7: Create "How It Works" Section with Split Layout
**Estimate:** 3.5 hours
**Wave:** 3

**Objective:** Build 3-step explanation with live graph visualization (right side).

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-UI-SPEC.md` (How It Works: split 50/50, 3 steps, graph, code)
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (Pattern 3: Lazy-loading)

**Action:**
1. Create `/home/joao/hrtech/core/templates/landing/partials/how-it-works.html`
2. Build structure (split layout):
   ```html
   <section class="how-it-works lazy-section">
     <div class="container">
       <div class="row align-items-center">
         <!-- Left: Steps -->
         <div class="col-12 col-lg-6 mb-5 mb-lg-0">
           <h2>How It Works</h2>
           <p class="intro">Like Google's PageRank, but for hiring.</p>

           <div class="step">
             <div class="step-number">1</div>
             <h3>Upload CV</h3>
             <p>Extracts skills via GPT-4. Organizes data structurally.</p>
           </div>

           <div class="step">
             <div class="step-number">2</div>
             <h3>Build Knowledge Graph</h3>
             <p>Neo4j organizes skill relationships and proficiency levels.</p>
           </div>

           <div class="step">
             <div class="step-number">3</div>
             <h3>Match with Precision</h3>
             <p>Scoring algorithm finds best candidates in seconds.</p>
           </div>

           <!-- Cypher Query Example -->
           <div class="code-snippet">
             <pre><code>MATCH (c:Candidato)-[:TEM_HABILIDADE]->(h:Habilidade)
 <-[:REQUER]-(v:Vaga)
WHERE v.uuid = $vaga_id
RETURN c, COUNT(h) as skills_match</code></pre>
           </div>
         </div>

         <!-- Right: Graph Visualization -->
         <div class="col-12 col-lg-6">
           <canvas id="how-it-works-graph-canvas" class="how-graph"></canvas>
         </div>
       </div>
     </div>
   </section>
   ```
3. Add CSS to `static/css/landing/index.css`:
   - `.how-it-works`: padding 64px 24px, background `#0F1419`, margin-top 64px
   - `.step`: margin-bottom 32px
   - `.step-number`: width 40px, height 40px, border-radius 50%, background `#0066FF`, color white, display flex, align-items center, justify-content center, font-weight 700, margin-bottom 16px
   - `.step h3`: font-size 24px, font-weight 600, margin-bottom 8px
   - `.how-graph`: height 400px, border-radius 8px, background `#1A1F26`, border 1px solid `#2D3139`
   - `.code-snippet`: background `#1A1F26`, border 1px solid `#2D3139`, padding 16px, border-radius 8px, margin-top 32px, font-family monospace, font-size 12px, color `#A0AAB8`, overflow auto
4. Mobile: stack left/right vertically (col-12 on both)

**Acceptance Criteria:**
- How It Works file exists at `/home/joao/hrtech/core/templates/landing/partials/how-it-works.html`
- H2 text is "How It Works"
- Section class includes `lazy-section` (for fade-in animation)
- 3 step divs present with numbers 1, 2, 3
- Step 1: "Upload CV"
- Step 2: "Build Knowledge Graph"
- Step 3: "Match with Precision"
- Cypher code snippet visible (text matches spec)
- Canvas element with id `how-it-works-graph-canvas`
- Layout uses Bootstrap 12-column grid (col-12 col-lg-6)
- Code snippet has monospace font and dark background

---

#### Task 8: Initialize Second Graph for "How It Works" Section
**Estimate:** 2.5 hours
**Wave:** 3

**Objective:** Create smaller graph visualization for How It Works (8-10 nodes, no collisions).

**Read First:**
- `/home/joao/hrtech/static/js/landing/graph-visualization.js` (canvas setup pattern)
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (Pattern 1: smaller graph)

**Action:**
1. Update `/home/joao/hrtech/static/js/landing/graph-config.js`:
   ```javascript
   export const howItWorksGraphData = {
     nodes: [
       { id: "Candidate", group: 1 },
       { id: "Python", group: 1 },
       { id: "Django", group: 1 },
       { id: "PostgreSQL", group: 2 },
       { id: "Neo4j", group: 2 },
       { id: "Match", group: 3 },
       { id: "Job", group: 3 },
       { id: "Skills", group: 2 }
     ],
     links: [
       { source: "Candidate", target: "Python" },
       { source: "Python", target: "Django" },
       { source: "Django", target: "PostgreSQL" },
       { source: "Neo4j", target: "Skills" },
       { source: "Skills", target: "Match" },
       { source: "Match", target: "Job" }
     ]
   };
   ```
2. Add function to `graph-visualization.js`:
   ```javascript
   export function initializeHowItWorksGraph() {
     const canvas = document.getElementById('how-it-works-graph-canvas');
     if (!canvas) return;

     // Similar setup to hero, but with smaller graph
     const width = canvas.clientWidth;
     const height = 400;
     const context = canvas.getContext('2d');

     const simulation = d3.forceSimulation(howItWorksGraphData.nodes)
       .force('link', d3.forceLink(howItWorksGraphData.links).distance(60))
       .force('charge', d3.forceManyBody().strength(-100))
       .force('center', d3.forceCenter(width / 2, height / 2));

     // Render loop (same as hero)
     simulation.on('tick', () => {
       // ... render nodes and links ...
     });
   }
   ```
3. Call in HTML or defer to Intersection Observer
4. Test: graph should render smoothly without lag

**Acceptance Criteria:**
- `howItWorksGraphData` defined in graph-config.js with 8 nodes
- `initializeHowItWorksGraph()` function exported from graph-visualization.js
- Canvas renders without errors
- Graph displays smaller (height 400px)
- No collisions or overlapping nodes visible
- FPS maintained >30 on mobile

---

#### Task 9: Implement Lazy-Loading with Intersection Observer
**Estimate:** 3 hours
**Wave:** 3

**Objective:** Defer animations and graph initialization for below-fold sections.

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (Pattern 3: Intersection Observer)

**Action:**
1. Create `/home/joao/hrtech/static/js/landing/lazy-loader.js`:
   ```javascript
   export function initializeLazyLoading() {
     const observerOptions = {
       threshold: 0.1,
       rootMargin: '50px'
     };

     const observer = new IntersectionObserver((entries) => {
       entries.forEach(entry => {
         if (entry.isIntersecting) {
           const section = entry.target;

           // Start fade-in animation
           section.classList.add('visible');

           // Initialize section-specific graphs/animations
           if (section.id === 'how-it-works') {
             import('./graph-visualization.js').then(mod => {
               mod.initializeHowItWorksGraph();
             });
           }

           // Unobserve after animation completes
           setTimeout(() => {
             observer.unobserve(section);
           }, 600); // Match transition duration
         }
       });
     }, observerOptions);

     // Observe all lazy sections
     document.querySelectorAll('.lazy-section').forEach(section => {
       observer.observe(section);
     });
   }
   ```
2. Call from base.html:
   ```html
   <script type="module">
     import { initializeLazyLoading } from "{% static 'js/landing/lazy-loader.js' %}";
     window.addEventListener('load', initializeLazyLoading);
   </script>
   ```
3. CSS fade-in transition already in animations.css (from Week 1)

**Acceptance Criteria:**
- `/home/joao/hrtech/static/js/landing/lazy-loader.js` exists
- `initializeLazyLoading()` function exported
- Observes all elements with class `lazy-section` (grep: `.lazy-section`)
- Adds `visible` class on intersection
- Defers graph init until section is visible
- Threshold is 0.1 (10% visible to trigger)
- rootMargin is 50px (start loading 50px before visible)
- No console errors when sections become visible

---

#### Task 10: Create "Graphs vs Keywords" Comparison Section
**Estimate:** 3 hours
**Wave:** 3

**Objective:** Build 2-column comparison table (traditional ATS vs HRTech).

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-UI-SPEC.md` (Comparison section: 4 rows × 2 cols)

**Action:**
1. Create `/home/joao/hrtech/core/templates/landing/partials/graphs-vs-keywords.html`
2. Build comparison grid:
   ```html
   <section class="graphs-vs-keywords lazy-section">
     <div class="container">
       <h2>Graphs > Keywords: Why It Matters</h2>
       <p class="intro">Knowledge graphs understand that Python + Django + PostgreSQL create a complete backend stack.</p>

       <div class="comparison-grid">
         <div class="comparison-row">
           <div class="comparison-item">
             <h4>Traditional ATS</h4>
             <p>Keyword search</p>
           </div>
           <div class="comparison-item better">
             <h4>HRTech</h4>
             <p>Graph traversal</p>
           </div>
         </div>

         <!-- Repeat for 3 more rows -->
         <div class="comparison-row">
           <div class="comparison-item">
             <h4>Traditional ATS</h4>
             <p>Surface-level understanding</p>
           </div>
           <div class="comparison-item better">
             <h4>HRTech</h4>
             <p>Deep relationship understanding</p>
           </div>
         </div>

         <div class="comparison-row">
           <div class="comparison-item">
             <h4>Traditional ATS</h4>
             <p>~65% accuracy</p>
           </div>
           <div class="comparison-item better">
             <h4>HRTech</h4>
             <p>~92% accuracy</p>
           </div>
         </div>

         <div class="comparison-row">
           <div class="comparison-item">
             <h4>Traditional ATS</h4>
             <p>Minutes per match</p>
           </div>
           <div class="comparison-item better">
             <h4>HRTech</h4>
             <p>Seconds per match</p>
           </div>
         </div>
       </div>
     </div>
   </section>
   ```
3. Add CSS:
   - `.graphs-vs-keywords`: padding 64px 24px, background `#0F1419`
   - `.comparison-grid`: display grid, gap 24px
   - `.comparison-row`: display grid, grid-template-columns 1fr 1fr, gap 16px
   - `.comparison-item`: padding 24px, border-radius 12px, border 1px solid `#2D3139`, background `#1A1F26`, text-align center
   - `.comparison-item.better`: border-color `#10B981`, background rgba(16, 185, 129, 0.05), box-shadow subtle green glow
   - Hover: lift effect (transform translateY(-4px))
   - Mobile: stack to 1 column

**Acceptance Criteria:**
- File exists at `/home/joao/hrtech/core/templates/landing/partials/graphs-vs-keywords.html`
- H2 text is "Graphs > Keywords: Why It Matters"
- 4 comparison rows present
- Each row has 2 items (Traditional ATS vs HRTech)
- "Better" items have green border/background (`#10B981`)
- Hover effect applies lift (transform translateY)
- Section is lazy-loaded (class `lazy-section`)
- Mobile stacks to 1 column

---

#### Task 11: Include All Sections in Index & Responsive Testing
**Estimate:** 2 hours
**Wave:** 3

**Objective:** Add new sections to landing page and test full layout.

**Read First:**
- `/home/joao/hrtech/core/templates/landing/index.html` (from Week 1)
- All new partials created in Wave 3

**Action:**
1. Update `/home/joao/hrtech/core/templates/landing/index.html`:
   ```html
   {% extends "landing/base.html" %}

   {% block content %}
     {% include "landing/partials/header.html" %}
     {% include "landing/partials/hero.html" %}
     {% include "landing/partials/problem.html" %}
     {% include "landing/partials/how-it-works.html" %}
     {% include "landing/partials/graphs-vs-keywords.html" %}
   {% endblock %}
   ```
2. Test responsive layout:
   - Desktop (1440px): all sections display 2-3 columns
   - Tablet (768px): sections stack to 1-2 columns
   - Mobile (480px): all sections stack to 1 column
3. Test lazy-loading: scroll to "How It Works", verify graph initializes (no errors in DevTools)
4. Run Lighthouse audit again:
   - FCP should still be <1.2s
   - LCP <2.5s
   - Performance >90

**Acceptance Criteria:**
- All 5 sections included in index.html (grep: include.*header, hero, problem, how-it-works, graphs-vs-keywords)
- Page scrolls smoothly without jank
- Lazy-loaded sections fade in when scrolled into view
- Graph in "How It Works" renders without console errors
- Lighthouse FCP <1.2s
- Lighthouse LCP <2.5s
- Lighthouse Performance score >90

---

## Verification Criteria

**All Week 2 tasks complete when:**
1. Hero graph animates smoothly at 60fps on desktop
2. Hero graph maintains 30+ fps on mobile
3. Graph doesn't block FCP (loads after page interactive)
4. How It Works section displays with smaller graph
5. Lazy-loading works: sections fade in when visible
6. All sections responsive at 480/768/1024/1440px
7. Lighthouse: FCP <1.2s, LCP <2.5s, Performance >90

---

## Must-Haves (Goal Backward Verification)

- [ ] D3.js loads asynchronously (async defer)
- [ ] Hero graph renders at 60fps on desktop
- [ ] Hero graph renders at 30+ fps on mobile
- [ ] Hero text (H1) visible before graph animation
- [ ] Graph animates with gentle rotation (20s loop)
- [ ] How It Works section has live graph
- [ ] Lazy-loading defers below-fold graphs
- [ ] All sections fade in on scroll (CSS transitions)
- [ ] Lighthouse FCP <1.2s (maintained)
- [ ] Lighthouse LCP <2.5s (maintained)
- [ ] No layout shift (CLS <0.1)
