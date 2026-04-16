# UI DESIGN CONTRACT: Landing Page Portal

**Phase:** 5 - Landing Page & Marketing
**Date:** 2026-04-04
**Status:** APPROVED ✓
**Inspired by:** Ashby, Lever, Workable
**Target Audience:** HR Leaders, Recruiters, Technical Hiring Managers

---

## 🎨 VISUAL IDENTITY

### Brand Personality
- **Primary:** Modern, Technical, Trustworthy
- **Secondary:** Data-driven, Intelligent, User-friendly
- **Tone:** Professional but approachable, slightly innovative

### Design System Reference
- **Grid:** 12-column fluid grid, 16px baseline
- **Breakpoints:** 480px (mobile), 768px (tablet), 1024px (desktop), 1440px (wide)
- **Spacing Scale:** 4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px
- **Border Radius:** 4px (tight), 8px (default), 12px (loose), 20px (full)
- **Shadows:**
  - `shadow-sm`: 0 1px 2px rgba(0,0,0,0.05)
  - `shadow-md`: 0 4px 12px rgba(0,0,0,0.08)
  - `shadow-lg`: 0 12px 24px rgba(0,0,0,0.12)

---

## 🎯 COLOR PALETTE

### Primary Colors
| Color | Token | Hex | Usage |
|-------|-------|-----|-------|
| **Primary** | `--color-brand` | `#0066FF` | CTAs, links, active states |
| **Secondary** | `--color-accent` | `#00D4AA` | Highlights, badges, success states |
| **Dark Base** | `--color-dark` | `#0F1419` | Text, backgrounds |
| **Light Base** | `--color-light` | `#FFFFFF` | Card backgrounds |

### Semantic Colors
| Use Case | Light Mode | Dark Mode |
|----------|-----------|----------|
| **Success** | `#10B981` | `#34D399` |
| **Warning** | `#F59E0B` | `#FBBF24` |
| **Error** | `#EF4444` | `#F87171` |
| **Info** | `#0066FF` | `#60A5FA` |
| **Neutral** | `#6B7280` | `#9CA3AF` |

### Gradients (Neo4j Graph Visualization)
```css
/* Graph nodes background */
--gradient-node-1: linear-gradient(135deg, #0066FF 0%, #00D4AA 100%);
--gradient-node-2: linear-gradient(135deg, #00D4AA 0%, #0099FF 100%);
--gradient-node-3: linear-gradient(135deg, #0099FF 0%, #0066FF 100%);

/* Hero background */
--gradient-hero: radial-gradient(circle at 20% 50%, rgba(0, 102, 255, 0.1) 0%, transparent 50%);
```

### Dark Mode
- **Background:** `#0F1419`
- **Surface:** `#1A1F26`
- **Border:** `#2D3139`
- **Text Primary:** `#FFFFFF`
- **Text Secondary:** `#A0AAB8`

---

## 📐 TYPOGRAPHY

### Font Stack
```css
/* Headings */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
font-weight: 700; /* Bold */

/* Body */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
font-weight: 400; /* Regular */

/* Mono (code snippets) */
font-family: 'JetBrains Mono', 'Monaco', monospace;
font-weight: 400;
```

### Type Scale
| Level | Size | Weight | Line Height | Letter Spacing | Usage |
|-------|------|--------|------------|----------------|-------|
| **H1** | 3.5rem (56px) | 700 | 1.2 | -0.02em | Hero title |
| **H2** | 2.5rem (40px) | 700 | 1.3 | -0.01em | Section headers |
| **H3** | 1.875rem (30px) | 700 | 1.4 | 0 | Feature titles |
| **H4** | 1.5rem (24px) | 600 | 1.4 | 0 | Card titles |
| **Body** | 1rem (16px) | 400 | 1.5 | 0 | Body copy |
| **Small** | 0.875rem (14px) | 400 | 1.5 | 0 | Secondary text |
| **Tiny** | 0.75rem (12px) | 500 | 1.4 | 0.02em | Labels, badges |

### Text Hierarchy
```html
<!-- H1: Hero main message -->
<h1>AI-Powered Recruitment That Actually Works</h1>

<!-- H2: Section headlines -->
<h2>Why Matching Algorithms Fail (And How Ours Don't)</h2>

<!-- H3: Feature or benefit headers -->
<h3>Powered by Knowledge Graphs</h3>

<!-- Body: Supporting text -->
<p>Traditional ATS systems match keywords...</p>

<!-- Small: Captions, metadata -->
<small>Deploy in minutes, get matching scores in seconds</small>
```

---

## 🏗️ LAYOUT & STRUCTURE

### Page Grid System
```
┌─────────────────────────────────────────────────┐
│           HEADER (sticky nav)                   │
├─────────────────────────────────────────────────┤
│                                                  │
│  SECTION 1: HERO                                │
│  ├─ Graph visualization (animated background)  │
│  ├─ Main headline (H1)                          │
│  ├─ Subheadline (Body)                          │
│  └─ Primary CTA button                          │
│                                                  │
├─────────────────────────────────────────────────┤
│                                                  │
│  SECTION 2: THE PROBLEM                         │
│  ├─ Before/After comparison (3 columns)        │
│  └─ Stats (traditional ATS vs HRTech)          │
│                                                  │
├─────────────────────────────────────────────────┤
│                                                  │
│  SECTION 3: HOW IT WORKS (WITH LIVE GRAPH)     │
│  ├─ 3-step explanation                         │
│  ├─ Interactive graph visualization            │
│  └─ Cypher query example                       │
│                                                  │
├─────────────────────────────────────────────────┤
│                                                  │
│  SECTION 4: WHY GRAPHS > KEYWORDS               │
│  ├─ Comparison grid (4 rows × 2 cols)          │
│  ├─ Skill relationships visualization          │
│  └─ Matching precision metrics                 │
│                                                  │
├─────────────────────────────────────────────────┤
│                                                  │
│  SECTION 5: KEY FEATURES (4 cards)              │
│  ├─ Interview Questions Generator              │
│  ├─ Skill Gap Analysis                         │
│  ├─ Multi-Tenant Isolation                     │
│  └─ LGPD Compliance                            │
│                                                  │
├─────────────────────────────────────────────────┤
│                                                  │
│  SECTION 6: TECH STACK                          │
│  ├─ 3-layer architecture diagram               │
│  ├─ Technology badges (PostgreSQL, Neo4j, etc)│
│  └─ "Built for scale" subheading               │
│                                                  │
├─────────────────────────────────────────────────┤
│                                                  │
│  SECTION 7: SERVICES & PRICING                 │
│  ├─ 3 pricing tiers (cards)                    │
│  └─ Feature comparison table                   │
│                                                  │
├─────────────────────────────────────────────────┤
│                                                  │
│  SECTION 8: CTA SECTION                        │
│  ├─ "Ready to hire smarter?"                   │
│  ├─ Primary CTA (Start Free Trial)             │
│  └─ Secondary CTA (Schedule Demo)              │
│                                                  │
├─────────────────────────────────────────────────┤
│         FOOTER (Links, socials, legal)         │
└─────────────────────────────────────────────────┘
```

### Spacing Standards
- **Page padding:** 24px (mobile), 32px (tablet), 48px (desktop)
- **Section top margin:** 64px (mobile), 96px (tablet/desktop)
- **Component gap:** 16px (default), 12px (compact cards), 24px (generous spacing)
- **Text margin bottom:** 12px (p → h), 24px (section spacing)

---

## 🎬 KEY SECTIONS DETAILED

### 1. HERO SECTION (Above the fold)

**Height:** 600px (desktop), 500px (tablet), 400px (mobile)

**Layout:**
```
┌──────────────────────────────────────────────────┐
│        [ANIMATED GRAPH BACKGROUND]               │
│                                                   │
│   AI-Powered Recruitment That Actually Works    │
│                                                   │
│   Built on knowledge graphs. Powered by AI.      │
│   Infinitely more precise than keyword matching. │
│                                                   │
│   [Start Free Trial]  [Watch Demo]               │
│                                                   │
└──────────────────────────────────────────────────┘
```

**Graph Background Specs:**
- D3.js or Three.js animated force-directed graph
- 15-20 visible nodes (skills: Python, React, PostgreSQL, etc.)
- 25-30 visible edges (relationships)
- Node colors: Blue, Cyan, Teal gradient
- Line colors: Semi-transparent white
- Animation: Gentle rotation + physics simulation
- Overlay: Dark gradient (rgba(0,0,0,0.4)) to ensure text readability
- Performance: Rendered on canvas, 60fps target

**Text Positioning:**
- Center-aligned over graph
- Z-index: 10
- Max width: 600px
- H1 margin bottom: 24px
- Subtext: color `#A0AAB8`, font-size 18px

**CTA Buttons:**
- Primary: `#0066FF`, padding 12px 32px, rounded 8px
- Secondary: outlined, border `#00D4AA`, text color same
- Button spacing: 16px gap

---

### 2. PROBLEM SECTION

**Grid:** 3 columns on desktop, 1 column on mobile

**Card Layout:**
```
┌─────────────────────────┐
│  ❌ Before              │
├─────────────────────────┤
│ • Manual CV review      │
│ • Keyword matching      │
│ • Hours of analysis     │
│ • High bias risk        │
│ • Slow hiring pipeline  │
└─────────────────────────┘
```

**Design:**
- Before card: Light red accent (`#FEE2E2` background, `#EF4444` border)
- After card: Light green accent (`#ECFDF5` background, `#10B981` border)
- Arrow between: Large, animated (scale 1 → 1.2 on hover)
- Card shadow: `shadow-md`
- Card padding: 32px

---

### 3. INTERACTIVE GRAPH SECTION

**Layout:** Split screen (50/50 on desktop, stacked on mobile)

**Left Side:**
- H2: "How It Works"
- 3 steps with numbers in circles (24x24px)
- Step 1: "Upload CV" → extracts skills via GPT-4
- Step 2: "Build Knowledge Graph" → Neo4j organizes relationships
- Step 3: "Match with Precision" → scoring algorithm runs

**Right Side:**
- Live graph visualization (similar to hero but ≤ 400px height)
- Interactive: hover nodes → highlight relationships
- Small code snippet: Example Cypher query
  ```cypher
  MATCH (c:Candidato)-[:TEM_HABILIDADE]->(h:Habilidade)<-[:REQUER]-(v:Vaga)
  WHERE v.uuid = $vaga_id
  RETURN c, COUNT(h) as skills_match
  ```

---

### 4. GRAPHS > KEYWORDS SECTION

**Grid:** 2 columns (comparison table style)

| Aspect | Traditional ATS | HRTech |
|--------|-----------------|--------|
| **Matching** | Keyword search | Graph traversal |
| **Understanding** | Surface-level | Deep relationships |
| **Precision** | ~65% accuracy | ~92% accuracy |
| **Time to match** | Minutes | Seconds |
| **Bias detection** | No | Yes |
| **Skill relationships** | No | Yes (similar skills) |
| **Scalability** | Limited | Infinite |

**Visual Design:**
- Each row is a comparison card
- HRTech side: green border, checkmark icon
- Traditional side: gray border, X icon
- Hover effect: slight lift (transform: translateY(-4px))

---

### 5. FEATURES SECTION (4-Feature Grid)

**Layout:** 2×2 grid (desktop), 1 column (mobile)

**Cards:**
1. **Interview Questions Generator**
   - Icon: Brain with lightning bolt
   - Text: "Generate 3 personalized interview questions based on skill gaps"
   - Tag: "New" (green)
   - Screenshot: Candidate profile with Questions button

2. **Skill Gap Analysis**
   - Icon: Chart with trending up
   - Text: "Deep dive into what skills candidates are missing"
   - Demo: Simple graph showing gaps

3. **Multi-Tenant Isolation**
   - Icon: Lock with shield
   - Text: "Enterprise-grade data isolation for multiple companies"
   - Security badge

4. **LGPD Compliance**
   - Icon: Checkbox
   - Text: "PII masking, audit trails, data deletion on demand"
   - Regulatory badge

**Card Style:**
- Padding: 32px
- Border: 1px solid `#2D3139` (dark mode)
- Border-radius: 12px
- Background: `#1A1F26`
- Shadow: `shadow-md`
- Hover: border-color changes to `#0066FF`, shadow increases

---

### 6. TECH STACK SECTION

**Architecture Diagram:**
```
┌─────────────────────────────────────────┐
│              FRONTEND LAYER             │
│    Django + Bootstrap + HTMX + D3.js    │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────┴──────────────────────┐
│              API LAYER                  │
│        Django REST, Redis Caching       │
└──────────────┬─────────────────────────┘
               │
  ┌────────────┼────────────┐
  │            │            │
┌─┴──┐    ┌───┴───┐    ┌───┴────┐
│PG │    │Neo4j  │    │ S3+OCR │
│   │    │       │    │        │
└───┘    └───────┘    └────────┘
```

**Technology Badges Grid:**
- Display 8-10 major tech logos in 2 rows
- Logos with labels: PostgreSQL, Neo4j, Redis, OpenAI, Django, Celery, AWS S3, Bootstrap, HTMX
- Gray text below: "Deployed on Render | Serverless Redis on Upstash"

---

### 7. SERVICES/PRICING SECTION

**Grid:** 3 columns (desktop), 1 column (mobile)

**Tier 1: Starter**
- Price: Free (for 30 days)
- Features: Up to 50 candidates, 1 team member
- CTA: "Start Free"

**Tier 2: Pro**
- Price: $99/month
- Features: Unlimited candidates, 5 team members, Analytics
- CTA: "Upgrade to Pro" (highlighted)
- Badge: "Most Popular" (top-right corner)

**Tier 3: Enterprise**
- Price: Custom
- Features: Everything + SLA, SSO, Custom integrations
- CTA: "Contact Sales"

**Design:**
- Each card: border, rounded 12px, padding 32px
- Pro card: border color `#0066FF`, slight lift effect
- Feature list: checkmark icons, text 14px
- CTA button blocks: full-width, height 44px

---

## 🎨 COMPONENT SPECIFICATIONS

### BUTTON VARIANTS

**Primary Button**
```css
background-color: #0066FF;
color: white;
padding: 12px 32px;
border-radius: 8px;
font-weight: 600;
font-size: 16px;
border: none;
cursor: pointer;
transition: all 0.2s ease;

&:hover {
  background-color: #0052CC;
  box-shadow: 0 8px 16px rgba(0, 102, 255, 0.3);
  transform: translateY(-2px);
}

&:active {
  transform: translateY(0);
}
```

**Secondary Button**
```css
background-color: transparent;
color: #00D4AA;
padding: 12px 32px;
border: 2px solid #00D4AA;
border-radius: 8px;
font-weight: 600;
font-size: 16px;
cursor: pointer;
transition: all 0.2s ease;

&:hover {
  background-color: rgba(0, 212, 170, 0.1);
  border-color: #0066FF;
  color: #0066FF;
}
```

### CARD COMPONENTS

**Feature Card**
- Padding: 24px
- Border-radius: 12px
- Background: `#1A1F26` (dark)
- Border: 1px solid `#2D3139`
- Shadow: `shadow-md`
- Gap between icon & text: 16px
- Icon size: 48×48px

**Stat Card**
- Large number: H2 (40px, brand color)
- Small label: 14px, gray
- Padding: 24px
- Centered text

### NAVIGATION

**Header (Sticky)**
- Height: 64px
- Background: `#0F1419` (with backdrop blur in dark mode)
- Logo: 40×40px, left-aligned
- Links: Right-aligned
  - Home, Features, Pricing, Blog, Docs
  - CTA: "Start Free" button
- Z-index: 100

**Mobile menu (hamburger)**
- Slide-in from right on mobile
- Overlay: semi-transparent dark
- Links stack vertically

---

## 🎬 INTERACTION & ANIMATION

### Hover Effects
- **Links:** 2px underline color change (gray → brand)
- **Cards:** Slight lift (translateY: -4px), shadow increase
- **Buttons:** Background darkening, shadow lift
- **Graph nodes:** Highlight (glow effect), increase size 5%

### Scroll Animations
- **Fade-in sections:** opacity 0 → 1 as they enter viewport
- **Number counters:** Animate from 0 to final number (2s duration)
- **Graph animation:** Slow rotation (20s loop)

### Micro-interactions
- **Button click:** Brief scale (0.95 → 1) + ripple effect
- **Form input:** Border color change on focus (gray → brand)
- **Tooltips:** Appear with subtle scale animation

### Performance
- **GPU acceleration:** transform, opacity only
- **Debounced events:** scroll, resize (300ms)
- **Lazy loading:** Graph visualization below fold
- **Image optimization:** WebP with fallbacks

---

## 📱 RESPONSIVE BEHAVIOR

### Desktop (1440px+)
- Full 12-column grid
- Hero height: 600px
- Features: 2×2 grid
- Full animations enabled

### Tablet (768px - 1024px)
- Paddings: 32px sides
- Hero height: 500px
- Features: 2 columns
- Lighter animations (reduced scale/translate)

### Mobile (< 768px)
- Paddings: 16px sides
- Hero height: 400px
- All sections: 1 column
- Minimal animations (fade-in only)
- Touch targets: min 44×44px
- Font sizes: Slightly reduced (H1: 2.5rem)

---

## 🎯 COPY & MESSAGING

### Hero Section
**Headline:** "AI-Powered Recruitment That Actually Works"
**Subheadline:** "Built on knowledge graphs. Powered by AI. Infinitely more precise than keyword matching."

### Section 2
**Headline:** "Why Traditional ATS Falls Short"
**Intro:** "Keyword-based matching misses 35% of qualified candidates. Knowledge graphs catch them all."

### Section 3
**Headline:** "Built on Graph Technology"
**Intro:** "Like Google's PageRank, but for hiring. Neo4j tracks skill relationships, not just keywords."

### Section 4
**Headline:** "Graphs > Keywords: Why It Matters"
**Intro:** "Knowledge graphs understand that Python + Django + PostgreSQL create a complete backend stack."

### Section 5
**Headline:** "Supercharge Your Hiring"

### Section 6
**Headline:** "Enterprise-Grade Architecture"
**Intro:** "Deployed on Render, secured with LGPD compliance, scaled to millions of matches."

### Section 7
**Headline:** "Get Started with HRTech"

### CTA Section
**Headline:** "Ready to hire smarter?"
**Copy:** "Join 100+ companies using AI-powered matching."

---

## ✅ DESIGN CONSISTENCY CHECKLIST

- [ ] All blues are `#0066FF` (primary)
- [ ] All accents are `#00D4AA` (secondary)
- [ ] All spacing is on 4px/8px grid
- [ ] All shadows follow the 3-tier scale (sm/md/lg)
- [ ] All border-radius is 4px/8px/12px (no random values)
- [ ] All animations use 0.2s-0.3s duration
- [ ] All text is Inter or monospace
- [ ] Dark mode: text never below `#A0AAB8` (gray)
- [ ] All CTAs are 44px minimum height
- [ ] SVG icons are 48px or 24px (no odd sizes)

---

## 🎨 VISUAL REFERENCE SITES

- **Ashby:** ashby.com (hero, problem statement, feature cards)
- **Lever:** lever.com (services section, pricing)
- **Workable:** workable.com (architecture diagram, tech stack)
- **PostHog:** posthog.com (interactive graph, animations)

---

## 📊 SUCCESS METRICS

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Load Time (Hero visible)** | < 2 seconds | Lighthouse, WebPageTest |
| **First Contentful Paint** | < 1.2s | Chrome DevTools |
| **Accessibility Score** | 95+ | Lighthouse A11y |
| **Mobile Usability** | 100% | Mobile-Friendly Test |
| **Graph Animation FPS** | 60fps | Chrome Profiler |
| **CTA Click-through** | 8%+ | Google Analytics |
| **Bounce Rate** | < 35% | GA, session tracking |
| **Time on Site** | 2-3 min | GA behavioral metrics |

---

## 🚀 IMPLEMENTATION PRIORITY

### Phase 1 (Week 1)
- [ ] Header + navigation
- [ ] Hero section (static graph, no animation)
- [ ] Problem section (before/after)
- [ ] Main CTA buttons

### Phase 2 (Week 2)
- [ ] Graph animation (D3.js integration)
- [ ] How It Works section
- [ ] Features grid
- [ ] Tech stack section

### Phase 3 (Week 3)
- [ ] Services/Pricing section
- [ ] Footer + legal pages
- [ ] Form submission
- [ ] Analytics integration

### Phase 4 (Week 4)
- [ ] Performance optimization
- [ ] A/B testing setup
- [ ] SEO & meta tags
- [ ] Mobile refinements

---

## 📝 NOTES FOR DEVELOPERS

1. **Graph Visualization:**
   - Use D3.js v7+ or Three.js
   - Keep node count < 30 for performance
   - Use WebGL renderer for 60fps on mobile

2. **Dark Mode:**
   - CSS custom properties in `:root`
   - Prefers-color-scheme media query
   - No hardcoded colors

3. **Bootstrap Integration:**
   - Use Bootstrap 5 grid only (no component overrides)
   - Custom CSS for styling on top
   - Tailwind optional for utility classes

4. **HTMX:**
   - Not needed for static landing page
   - Only use if implementing newsletter signup (hx-post to backend)

5. **SEO:**
   - Meta tags: title, description, OG image, schema.org
   - H1 for hero headline only
   - Alt text for all images

---

**UI-SPEC Status:** ✅ APPROVED FOR IMPLEMENTATION
**Designer:** Claude Code - AI Design Contract
**Last Reviewed:** 2026-04-04
