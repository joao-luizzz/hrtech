# Phase 5: Landing Page Portal - Week 3 Plan
## Content Completion (Features, Tech Stack, Pricing, Footer)

**Phase:** 5 - Landing Page Portal
**Week:** 3 of 4
**Duration:** 40 hours estimated
**Mode:** standard
**Status:** PLANNED

---

## Frontmatter

```yaml
wave: 1, 2, 3
depends_on: [05-LANDING-PAGE-PLAN-WEEK1.md, 05-LANDING-PAGE-PLAN-WEEK2.md]
files_modified:
  - core/templates/landing/partials/features.html
  - core/templates/landing/partials/tech-stack.html
  - core/templates/landing/partials/pricing.html
  - core/templates/landing/partials/cta.html
  - core/templates/landing/partials/footer.html
  - core/templates/landing/partials/newsletter-form.html
  - core/views.py
  - core/urls.py
  - static/css/landing/index.css
  - static/js/landing/interactions.js
autonomous: true
```

---

## Overview

**Goal:** Complete all remaining sections of the landing page: Features (4 cards), Tech Stack (architecture + logos), Pricing (3 tiers), CTA section, and Footer. Implement HTMX newsletter form submission.

**Target Metrics:**
- All 8 landing page sections complete
- Pricing cards interactive (hover effects)
- Newsletter form submits via HTMX (no page reload)
- All content SEO-optimized (headings, alt text, schema markup)
- Page load time <2.5s (LCP)

**Wave Strategy:**
- **Wave 1 (Days 1-2):** Features section, Tech stack section
- **Wave 2 (Days 3-4):** Pricing section with feature matrix, CTA section
- **Wave 3 (Days 5-6):** Footer, newsletter form, form handling, integration testing

---

## Tasks

### Wave 1: Features & Tech Stack

#### Task 1: Create Features Section (4-Card Grid)
**Estimate:** 3 hours
**Wave:** 1

**Objective:** Build 2×2 feature card grid with icons, descriptions, and "New" badges.

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-UI-SPEC.md` (Features: 4 cards, 2×2 grid, icons, tags)
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (Pattern 4: Grid system)

**Action:**
1. Create `/home/joao/hrtech/core/templates/landing/partials/features.html`
2. Build 2×2 card grid:
   ```html
   <section class="features lazy-section">
     <div class="container">
       <h2>Supercharge Your Hiring</h2>

       <div class="row g-4 mt-5">
         <!-- Card 1: Interview Questions -->
         <div class="col-12 col-md-6 col-lg-6">
           <div class="feature-card">
             <div class="feature-icon">🧠</div>
             <h3>Interview Questions Generator</h3>
             <p>Generate 3 personalized interview questions based on skill gaps</p>
             <span class="badge badge-success">New</span>
           </div>
         </div>

         <!-- Card 2: Skill Gap Analysis -->
         <div class="col-12 col-md-6 col-lg-6">
           <div class="feature-card">
             <div class="feature-icon">📊</div>
             <h3>Skill Gap Analysis</h3>
             <p>Deep dive into what skills candidates are missing</p>
           </div>
         </div>

         <!-- Card 3: Multi-Tenant Isolation -->
         <div class="col-12 col-md-6 col-lg-6">
           <div class="feature-card">
             <div class="feature-icon">🔒</div>
             <h3>Multi-Tenant Isolation</h3>
             <p>Enterprise-grade data isolation for multiple companies</p>
             <span class="badge badge-secondary">Security</span>
           </div>
         </div>

         <!-- Card 4: LGPD Compliance -->
         <div class="col-12 col-md-6 col-lg-6">
           <div class="feature-card">
             <div class="feature-icon">✅</div>
             <h3>LGPD Compliance</h3>
             <p>PII masking, audit trails, data deletion on demand</p>
             <span class="badge badge-secondary">Compliance</span>
           </div>
         </div>
       </div>
     </div>
   </section>
   ```
3. Add CSS to `static/css/landing/index.css`:
   - `.features`: padding 64px 24px, background `#0F1419`, margin-top 64px
   - `.feature-card`: padding 32px, border 1px solid `#2D3139`, border-radius 12px, background `#1A1F26`, shadow-md, transition all 0.3s ease, min-height 300px
   - `.feature-card:hover`: border-color `#0066FF`, box-shadow 0 12px 24px rgba(0, 102, 255, 0.15), transform translateY(-4px)
   - `.feature-icon`: font-size 48px, margin-bottom 16px, display block
   - `.feature-card h3`: font-size 24px, font-weight 600, margin-bottom 12px, color `#FFFFFF`
   - `.feature-card p`: font-size 16px, color `#A0AAB8`, line-height 1.6
   - `.badge`: display inline-block, margin-top 16px, padding 4px 12px, border-radius 4px, font-size 12px, font-weight 500
   - `.badge-success`: background `#10B981`, color white
   - `.badge-secondary`: background `#6B7280`, color white
   - Mobile: col-12 (1 column)

**Acceptance Criteria:**
- File exists at `/home/joao/hrtech/core/templates/landing/partials/features.html`
- H2 text is "Supercharge Your Hiring"
- 4 feature cards present with correct icons
- Card 1: "Interview Questions Generator" with "New" badge
- Card 2: "Skill Gap Analysis"
- Card 3: "Multi-Tenant Isolation" with "Security" badge
- Card 4: "LGPD Compliance" with "Compliance" badge
- Hover effect applies blue border and lift (transform translateY(-4px))
- Grid is 2×2 on desktop (col-12 col-md-6 col-lg-6)
- Mobile layout is 1 column (col-12)
- All cards same height or nearly same (min-height prevents skew)

---

#### Task 2: Create Tech Stack Section with Architecture Diagram
**Estimate:** 3.5 hours
**Wave:** 1

**Objective:** Display 3-layer architecture diagram and technology logos.

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-UI-SPEC.md` (Tech Stack: 3-layer, logos, 8-10 badges)
- `/home/joao/hrtech/README.md` (tech stack list)

**Action:**
1. Create `/home/joao/hrtech/core/templates/landing/partials/tech-stack.html`
2. Build architecture diagram (SVG or ASCII art for simplicity):
   ```html
   <section class="tech-stack lazy-section">
     <div class="container">
       <h2>Enterprise-Grade Architecture</h2>
       <p class="intro">Deployed on Render, secured with LGPD compliance, scaled to millions of matches.</p>

       <!-- Architecture Diagram -->
       <div class="architecture-diagram">
         <div class="architecture-layer frontend">
           <div class="layer-label">FRONTEND LAYER</div>
           <div class="layer-content">Django + Bootstrap + HTMX + D3.js</div>
         </div>

         <div class="connection"></div>

         <div class="architecture-layer api">
           <div class="layer-label">API LAYER</div>
           <div class="layer-content">Django REST + Redis Caching</div>
         </div>

         <div class="connection"></div>

         <div class="architecture-databases">
           <div class="database">
             <div class="db-icon">🐘</div>
             <div class="db-name">PostgreSQL</div>
           </div>
           <div class="database">
             <div class="db-icon">🕸️</div>
             <div class="db-name">Neo4j</div>
           </div>
           <div class="database">
             <div class="db-icon">💾</div>
             <div class="db-name">S3+OCR</div>
           </div>
         </div>
       </div>

       <!-- Technology Logos/Badges -->
       <div class="tech-logos mt-5">
         <h3 class="text-center mb-4">Powered by Industry Leaders</h3>
         <div class="row g-3">
           <div class="col-6 col-md-3 tech-badge">
             <img src="{% static 'images/landing/tech-postgres.svg' %}" alt="PostgreSQL" loading="lazy">
             <span>PostgreSQL</span>
           </div>
           <div class="col-6 col-md-3 tech-badge">
             <img src="{% static 'images/landing/tech-neo4j.svg' %}" alt="Neo4j" loading="lazy">
             <span>Neo4j</span>
           </div>
           <div class="col-6 col-md-3 tech-badge">
             <img src="{% static 'images/landing/tech-redis.svg' %}" alt="Redis" loading="lazy">
             <span>Redis</span>
           </div>
           <div class="col-6 col-md-3 tech-badge">
             <img src="{% static 'images/landing/tech-openai.svg' %}" alt="OpenAI" loading="lazy">
             <span>OpenAI</span>
           </div>
           <!-- 4 more tech logos -->
         </div>
       </div>
     </div>
   </section>
   ```
3. Add CSS:
   - `.tech-stack`: padding 64px 24px, background `#0F1419`, margin-top 64px
   - `.architecture-diagram`: max-width 600px, margin 0 auto 48px, display flex, flex-direction column, align-items center, gap 24px
   - `.architecture-layer`: padding 32px, border 1px solid `#2D3139`, border-radius 8px, background `#1A1F26`, text-align center, width 100%, max-width 500px
   - `.layer-label`: font-size 12px, font-weight 700, color `#00D4AA`, margin-bottom 8px
   - `.layer-content`: font-size 14px, color `#A0AAB8`
   - `.connection`: width 2px, height 24px, background `#00D4AA`, margin 12px 0
   - `.architecture-databases`: display grid, grid-template-columns repeat(3, 1fr), gap 24px, width 100%, max-width 500px, margin 0 auto
   - `.database`: text-align center
   - `.db-icon`: font-size 32px, margin-bottom 8px
   - `.db-name`: font-size 14px, color `#A0AAB8`
   - `.tech-logos`: padding-top 32px, border-top 1px solid `#2D3139`
   - `.tech-badge`: display flex, flex-direction column, align-items center, gap 8px, text-align center
   - `.tech-badge img`: height 48px, object-fit contain
   - `.tech-badge span`: font-size 12px, color `#A0AAB8`

**Acceptance Criteria:**
- File exists at `/home/joao/hrtech/core/templates/landing/partials/tech-stack.html`
- H2 text is "Enterprise-Grade Architecture"
- Architecture diagram displays 3 layers (Frontend, API, Databases)
- Cyan connection lines between layers
- 3 database icons/names: PostgreSQL, Neo4j, S3
- Technology badges section with 8+ tech logos
- All images use `loading="lazy"` attribute
- Mobile: badges stack to 2 columns (col-6 col-md-3)
- Architecture diagram responsive (max-width 500px on desktop)

---

### Wave 2: Pricing & CTA

#### Task 3: Create Pricing Section (3-Tier Cards)
**Estimate:** 3.5 hours
**Wave:** 2

**Objective:** Build 3-column pricing cards with feature comparison and "Most Popular" badge.

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-UI-SPEC.md` (Pricing: 3 tiers, Pro highlighted, CTAs)

**Action:**
1. Create `/home/joao/hrtech/core/templates/landing/partials/pricing.html`
2. Build 3-tier pricing grid:
   ```html
   <section class="pricing lazy-section">
     <div class="container">
       <h2>Get Started with HRTech</h2>
       <p class="intro">Flexible plans for teams of all sizes</p>

       <div class="row g-4 mt-5">
         <!-- Starter Plan -->
         <div class="col-12 col-md-6 col-lg-4">
           <div class="pricing-card">
             <h3>Starter</h3>
             <div class="price">Free</div>
             <p class="price-period">for 30 days</p>

             <button class="btn-primary w-100 my-4" hx-post="{% url 'landing:start-free' %}" hx-target="#cta-response">
               Start Free
             </button>

             <ul class="features">
               <li>Up to 50 candidates</li>
               <li>1 team member</li>
               <li>Basic matching</li>
             </ul>
           </div>
         </div>

         <!-- Pro Plan (Highlighted) -->
         <div class="col-12 col-md-6 col-lg-4">
           <div class="pricing-card pricing-pro">
             <div class="badge-most-popular">Most Popular</div>
             <h3>Pro</h3>
             <div class="price">$99</div>
             <p class="price-period">per month</p>

             <button class="btn-primary w-100 my-4" hx-post="{% url 'landing:upgrade-pro' %}" hx-target="#cta-response">
               Upgrade to Pro
             </button>

             <ul class="features">
               <li>Unlimited candidates</li>
               <li>5 team members</li>
               <li>Advanced analytics</li>
               <li>Interview questions</li>
             </ul>
           </div>
         </div>

         <!-- Enterprise Plan -->
         <div class="col-12 col-md-6 col-lg-4">
           <div class="pricing-card">
             <h3>Enterprise</h3>
             <div class="price">Custom</div>
             <p class="price-period">tailored to your needs</p>

             <button class="btn-primary w-100 my-4" hx-post="{% url 'landing:contact-sales' %}" hx-target="#cta-response">
               Contact Sales
             </button>

             <ul class="features">
               <li>Everything in Pro</li>
               <li>Custom integrations</li>
               <li>Dedicated support</li>
               <li>SLA & uptime guarantees</li>
             </ul>
           </div>
         </div>
       </div>

       <!-- Feature Comparison Table (Optional) -->
       <div class="feature-matrix mt-5">
         <table>
           <thead>
             <tr>
               <th>Feature</th>
               <th>Starter</th>
               <th>Pro</th>
               <th>Enterprise</th>
             </tr>
           </thead>
           <tbody>
             <tr>
               <td>Candidates</td>
               <td>Up to 50</td>
               <td>Unlimited</td>
               <td>Unlimited</td>
             </tr>
             <tr>
               <td>Interview Questions</td>
               <td>❌</td>
               <td>✅</td>
               <td>✅</td>
             </tr>
             <tr>
               <td>Support</td>
               <td>Email</td>
               <td>Email + Chat</td>
               <td>24/7 Dedicated</td>
             </tr>
           </tbody>
         </table>
       </div>
     </div>
   </section>
   ```
3. Add CSS:
   - `.pricing`: padding 64px 24px, background `#0F1419`, margin-top 64px
   - `.pricing-card`: padding 32px, border 1px solid `#2D3139`, border-radius 12px, background `#1A1F26`, display flex, flex-direction column, height 100%
   - `.pricing-card h3`: font-size 24px, font-weight 600, margin-bottom 16px
   - `.price`: font-size 48px, font-weight 700, color `#0066FF`, margin-bottom 4px
   - `.price-period`: font-size 14px, color `#A0AAB8`, margin-bottom 24px
   - `.pricing-card.pricing-pro`: border-color `#0066FF`, background linear-gradient(135deg, rgba(0, 102, 255, 0.05) 0%, rgba(0, 212, 170, 0.05) 100%), box-shadow 0 8px 32px rgba(0, 102, 255, 0.1)
   - `.badge-most-popular`: position absolute, top -12px, right 24px, background `#0066FF`, color white, padding 4px 16px, border-radius 4px, font-size 12px, font-weight 700
   - `.features`: list-style none, padding 0, margin 24px 0 0 0
   - `.features li`: margin-bottom 12px, padding-left 24px, position relative, color `#A0AAB8`
   - `.features li:before`: content "✓", position absolute, left 0, color `#00D4AA`, font-weight 700
   - `.feature-matrix`: margin-top 48px, border-top 1px solid `#2D3139`, padding-top 32px
   - `.feature-matrix table`: width 100%, border-collapse collapse
   - `.feature-matrix th, td`: padding 12px, text-align left, border-bottom 1px solid `#2D3139`, font-size 14px
   - Mobile: cards stack to 1 column, Pro card loses highlighted styling

**Acceptance Criteria:**
- File exists at `/home/joao/hrtech/core/templates/landing/partials/pricing.html`
- H2 text is "Get Started with HRTech"
- 3 pricing cards present: Starter, Pro, Enterprise
- Starter: "Free for 30 days"
- Pro: "$99 per month" with "Most Popular" badge
- Enterprise: "Custom"
- Pro card has blue border and highlighted background
- All cards have 3+ features listed (checkmarks visible)
- Feature comparison table visible (6+ rows)
- CTA buttons use HTMX (hx-post attributes present)
- Mobile layout is 1 column (col-12)

---

#### Task 4: Create CTA Section (Call-to-Action)
**Estimate:** 2 hours
**Wave:** 2

**Objective:** Build final "Ready to hire smarter?" section with primary and secondary CTAs.

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-UI-SPEC.md` (CTA section: copy, buttons)

**Action:**
1. Create `/home/joao/hrtech/core/templates/landing/partials/cta.html`
2. Build CTA section:
   ```html
   <section class="cta lazy-section">
     <div class="container text-center">
       <h2>Ready to hire smarter?</h2>
       <p class="cta-subtitle">Join 100+ companies using AI-powered matching.</p>

       <div class="cta-buttons mt-5">
         <button class="btn-primary btn-lg me-3" hx-post="{% url 'landing:start-free' %}" hx-target="#cta-response">
           Start Free Trial
         </button>
         <button class="btn-secondary btn-lg" hx-post="{% url 'landing:schedule-demo' %}" hx-target="#cta-response">
           Schedule Demo
         </button>
       </div>

       <!-- Response area for HTMX -->
       <div id="cta-response"></div>
     </div>
   </section>
   ```
3. Add CSS:
   - `.cta`: padding 96px 24px, background linear-gradient(135deg, rgba(0, 102, 255, 0.1) 0%, rgba(0, 212, 170, 0.1) 100%), margin-top 64px
   - `.cta h2`: font-size 48px, font-weight 700, color `#FFFFFF`, margin-bottom 24px
   - `.cta-subtitle`: font-size 20px, color `#A0AAB8`, max-width 500px, margin 0 auto
   - `.cta-buttons`: display flex, justify-content center, gap 24px, flex-wrap wrap
   - `.btn-lg`: padding 16px 48px, font-size 18px, min-height 56px

**Acceptance Criteria:**
- File exists at `/home/joao/hrtech/core/templates/landing/partials/cta.html`
- H2 text is "Ready to hire smarter?"
- Subtitle text is "Join 100+ companies using AI-powered matching."
- Two buttons present: "Start Free Trial" and "Schedule Demo"
- Buttons use HTMX (hx-post attributes)
- Background has gradient (blue + cyan)
- Large button sizing (padding 16px 48px)
- Responsive button layout (flex-wrap on mobile)

---

### Wave 3: Footer & Form Integration

#### Task 5: Create Footer with Links & Legal
**Estimate:** 2 hours
**Wave:** 3

**Objective:** Build sticky footer with navigation links, social icons, and legal pages.

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-UI-SPEC.md` (Footer mentioned)

**Action:**
1. Create `/home/joao/hrtech/core/templates/landing/partials/footer.html`
2. Build footer:
   ```html
   <footer class="footer">
     <div class="container">
       <div class="row">
         <!-- Brand & About -->
         <div class="col-12 col-md-3 mb-4 mb-md-0">
           <h5>HRTech</h5>
           <p>AI-powered recruitment for modern HR teams.</p>
           <div class="social-links">
             <a href="#" title="GitHub">GitHub</a>
             <a href="#" title="Twitter">Twitter</a>
             <a href="#" title="LinkedIn">LinkedIn</a>
           </div>
         </div>

         <!-- Product Links -->
         <div class="col-12 col-md-3 mb-4 mb-md-0">
           <h5>Product</h5>
           <ul>
             <li><a href="#features">Features</a></li>
             <li><a href="#pricing">Pricing</a></li>
             <li><a href="#">Blog</a></li>
             <li><a href="#">Docs</a></li>
           </ul>
         </div>

         <!-- Company Links -->
         <div class="col-12 col-md-3 mb-4 mb-md-0">
           <h5>Company</h5>
           <ul>
             <li><a href="#">About</a></li>
             <li><a href="#">Careers</a></li>
             <li><a href="#">Contact</a></li>
           </ul>
         </div>

         <!-- Legal Links -->
         <div class="col-12 col-md-3 mb-4 mb-md-0">
           <h5>Legal</h5>
           <ul>
             <li><a href="#">Privacy Policy</a></li>
             <li><a href="#">Terms of Service</a></li>
             <li><a href="#">LGPD Compliance</a></li>
           </ul>
         </div>
       </div>

       <hr class="my-4">

       <div class="footer-bottom text-center">
         <p>&copy; 2026 HRTech. All rights reserved. LGPD Compliant.</p>
       </div>
     </div>
   </footer>
   ```
3. Add CSS:
   - `.footer`: background `#0A0D12` (darker than main), border-top 1px solid `#2D3139`, padding 48px 24px 24px, margin-top 96px
   - `.footer h5`: font-size 16px, font-weight 700, color `#FFFFFF`, margin-bottom 16px
   - `.footer p`: font-size 14px, color `#A0AAB8`, line-height 1.6
   - `.footer ul`: list-style none, padding 0
   - `.footer li`: margin-bottom 8px
   - `.footer a`: color `#A0AAB8`, text-decoration none, transition color 0.2s
   - `.footer a:hover`: color `#00D4AA`
   - `.social-links`: display flex, gap 12px, margin-top 12px
   - `.footer-bottom`: font-size 12px, color `#6B7280`

**Acceptance Criteria:**
- File exists at `/home/joao/hrtech/core/templates/landing/partials/footer.html`
- 4 columns: Brand, Product, Company, Legal
- Footer links: GitHub, Twitter, LinkedIn, Features, Pricing, Blog, Docs, About, Careers, Contact, Privacy, Terms, LGPD
- Copyright text visible
- Links are clickable and styled
- Background is darker than main content
- Footer responsive (stacks on mobile)

---

#### Task 6: Create Newsletter Signup Form (HTMX)
**Estimate:** 2 hours
**Wave:** 3

**Objective:** Build HTMX newsletter form with email validation and submission.

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (Pattern: HTMX form submission)

**Action:**
1. Create `/home/joao/hrtech/core/templates/landing/partials/newsletter-form.html`:
   ```html
   <form class="newsletter-form"
         hx-post="{% url 'landing:newsletter-signup' %}"
         hx-target="#newsletter-response"
         hx-on="htmx:responseError: showError(event)">
     {% csrf_token %}

     <div class="form-group">
       <input type="email"
              name="email"
              class="form-control"
              placeholder="Enter your email"
              required>
     </div>

     <button type="submit" class="btn-primary" hx-indicator="#loading">
       <span>Subscribe</span>
       <span id="loading" class="htmx-indicator spinner"></span>
     </button>
   </form>

   <div id="newsletter-response"></div>
   ```
2. Add CSS:
   - `.newsletter-form`: display flex, gap 8px, flex-wrap wrap
   - `.form-control`: flex 1, padding 12px 16px, border 1px solid `#2D3139`, border-radius 8px, background `#1A1F26`, color `#FFFFFF`, font-size 16px, min-width 200px
   - `.form-control:focus`: border-color `#0066FF`, outline none, box-shadow 0 0 0 3px rgba(0, 102, 255, 0.1)
   - `.htmx-indicator`: display none
   - `.htmx-request .htmx-indicator`: display inline-block
   - `.spinner`: display inline-block, width 16px, height 16px, border 2px solid `#0066FF`, border-top-color transparent, border-radius 50%, animation spin 0.6s linear infinite
3. Create Django view `/home/joao/hrtech/core/views.py`:
   ```python
   from django.views.decorators.http import require_http_methods
   from django.http import HttpResponse

   @require_http_methods(["POST"])
   def newsletter_signup(request):
       email = request.POST.get("email", "").strip()

       if not email or "@" not in email:
           return HttpResponse(
               '<div class="alert alert-danger">Please enter a valid email address</div>',
               status=400
           )

       # Save to database (placeholder)
       # Newsletter.objects.get_or_create(email=email)

       return HttpResponse(
           '<div class="alert alert-success">Thank you for subscribing! Check your email for confirmation.</div>'
       )
   ```
4. Add URL to `/home/joao/hrtech/core/urls.py`:
   ```python
   path('api/newsletter-signup/', views.newsletter_signup, name='newsletter-signup'),
   ```

**Acceptance Criteria:**
- Newsletter form file exists at `/home/joao/hrtech/core/templates/landing/partials/newsletter-form.html`
- Form has email input field (required)
- Form uses HTMX (hx-post attribute)
- Submit button shows spinner during request (htmx-indicator)
- Success message returned: "Thank you for subscribing..."
- Error message on invalid email: "Please enter a valid email address"
- Form styling matches design (input padding, button colors)
- Form submits without page reload

---

#### Task 7: Implement HTMX Endpoints for CTA Buttons
**Estimate:** 2 hours
**Wave:** 3

**Objective:** Create Django views for Start Free, Upgrade Pro, Schedule Demo, Contact Sales.

**Read First:**
- `/home/joao/hrtech/core/views.py` (existing view patterns)
- All pricing card buttons created in Task 3

**Action:**
1. Add views to `/home/joao/hrtech/core/views.py`:
   ```python
   @require_http_methods(["POST"])
   def start_free(request):
       return HttpResponse(
           '<div class="alert alert-success">Redirecting to signup...</div>'
       )

   @require_http_methods(["POST"])
   def upgrade_pro(request):
       return HttpResponse(
           '<div class="alert alert-info">Take me to pricing page...</div>'
       )

   @require_http_methods(["POST"])
   def schedule_demo(request):
       return HttpResponse(
           '<div class="alert alert-info">Calendar will open shortly...</div>'
       )

   @require_http_methods(["POST"])
   def contact_sales(request):
       return HttpResponse(
           '<div class="alert alert-info">Sales team will contact you soon.</div>'
       )
   ```
2. Add URLs to `/home/joao/hrtech/core/urls.py`:
   ```python
   path('api/start-free/', views.start_free, name='start-free'),
   path('api/upgrade-pro/', views.upgrade_pro, name='upgrade-pro'),
   path('api/schedule-demo/', views.schedule_demo, name='schedule-demo'),
   path('api/contact-sales/', views.contact_sales, name='contact-sales'),
   ```
3. Test each button in browser: click, verify HTMX response shows in `#cta-response` div

**Acceptance Criteria:**
- All 4 views present in `core/views.py` (start_free, upgrade_pro, schedule_demo, contact_sales)
- All 4 URLs registered in `core/urls.py`
- Each view returns HTTP 200 with success/info message
- HTMX requests don't trigger full page reload
- Response appears in targeted div (`#cta-response`)
- No console errors on button click

---

#### Task 8: Integrate All Sections into Final Landing Page
**Estimate:** 1.5 hours
**Wave:** 3

**Objective:** Add all new sections to index.html and verify complete page.

**Read First:**
- `/home/joao/hrtech/core/templates/landing/index.html` (from Week 2)
- All new partials created in Week 3

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
     {% include "landing/partials/features.html" %}
     {% include "landing/partials/tech-stack.html" %}
     {% include "landing/partials/pricing.html" %}
     {% include "landing/partials/cta.html" %}
     {% include "landing/partials/footer.html" %}
   {% endblock %}
   ```
2. Scroll through entire page, verify all 8 sections visible
3. Test responsive layout: 480px, 768px, 1024px, 1440px
4. Test HTMX interactions: click pricing buttons, newsletter form
5. Run Lighthouse audit (full page)

**Acceptance Criteria:**
- All 10 sections included in index.html (grep: include statements)
- Page scrolls smoothly from top to footer
- All sections visible without errors
- Responsive layout confirmed at all breakpoints
- HTMX buttons respond without page reload
- Lighthouse score >90 (all metrics)

---

#### Task 9: SEO & Meta Tags
**Estimate:** 1.5 hours
**Wave:** 3

**Objective:** Add meta tags, Open Graph, and structured data for SEO.

**Read First:**
- `/home/joao/hrtech/core/templates/landing/base.html` (head section)

**Action:**
1. Update base.html `<head>`:
   ```html
   <meta charset="utf-8">
   <meta name="viewport" content="width=device-width, initial-scale=1">
   <meta name="description" content="HRTech: AI-powered recruitment matching using knowledge graphs. Find the perfect candidates in seconds, not hours.">
   <meta name="keywords" content="recruitment, ATS, AI matching, knowledge graphs, Neo4j, hiring">
   <meta name="author" content="HRTech">
   <meta name="canonical" href="https://hrtech.com">

   <!-- Open Graph -->
   <meta property="og:title" content="HRTech: AI-Powered Recruitment">
   <meta property="og:description" content="Intelligent matching using knowledge graphs. Powered by AI.">
   <meta property="og:image" content="{% static 'images/landing/og-image.png' %}">
   <meta property="og:url" content="https://hrtech.com">
   <meta property="og:type" content="website">

   <!-- Twitter Card -->
   <meta name="twitter:card" content="summary_large_image">
   <meta name="twitter:title" content="HRTech: AI-Powered Recruitment">
   <meta name="twitter:description" content="Find perfect candidates in seconds">
   <meta name="twitter:image" content="{% static 'images/landing/twitter-image.png' %}">

   <!-- Structured Data (Schema.org) -->
   <script type="application/ld+json">
   {
     "@context": "https://schema.org",
     "@type": "SoftwareApplication",
     "name": "HRTech",
     "description": "AI-powered recruitment matching using knowledge graphs",
     "applicationCategory": "BusinessApplication",
     "aggregateRating": {
       "@type": "AggregateRating",
       "ratingValue": "4.8",
       "ratingCount": "100"
     }
   }
   </script>
   ```
2. Verify: Google Search Console can crawl page with correct title/description

**Acceptance Criteria:**
- Meta description present and <160 characters
- og:title, og:description, og:image present
- twitter:card meta tag present
- Schema.org structured data for SoftwareApplication present
- Canonical URL set (grep: `rel="canonical"`)
- All keywords present (recruitment, ATS, AI, knowledge graphs)

---

#### Task 10: Final QA & Full-Page Testing
**Estimate:** 4 hours
**Wave:** 3

**Objective:** Comprehensive testing of entire landing page.

**Read First:**
- All sections created in Week 1-3

**Action:**
1. Desktop testing (1440px):
   - Scroll through entire page
   - Verify all text legible, colors correct
   - Check all links navigate (internal #anchors + external)
   - Test CTA buttons (HTMX responses appear)
   - Test newsletter form (error on invalid email, success on valid)
   - Verify images load (if any)
2. Tablet testing (768px):
   - Verify cards/layout responsive
   - Hamburger menu works
   - Button sizing appropriate
   - Text readable
3. Mobile testing (480px):
   - One-column layout
   - Touch targets 44px minimum
   - Hamburger menu functional
   - Forms usable
4. Lighthouse audit:
   - FCP <1.2s
   - LCP <2.5s
   - CLS <0.1
   - Performance >90
   - Accessibility >95
   - SEO >95
5. No console errors or warnings

**Acceptance Criteria:**
- Page loads without errors across all breakpoints
- All sections visible and readable
- Colors match UI-SPEC (#0066FF primary, #00D4AA accent)
- Button clicks work (HTMX responses appear)
- Form submission works
- Lighthouse FCP <1.2s
- Lighthouse LCP <2.5s
- Lighthouse CLS <0.1
- Lighthouse Performance >90
- Lighthouse Accessibility >95
- Lighthouse SEO >95
- No JavaScript errors in console

---

## Verification Criteria

**All Week 3 tasks complete when:**
1. All 8 landing page sections complete and integrated
2. Pricing section with 3 tiers and feature matrix
3. Tech stack diagram and logo badges
4. Newsletter form and CTA endpoints working
5. HTMX interactions functioning (no page reload)
6. All sections responsive at 480/768/1024/1440px
7. Full page Lighthouse score >90 across all metrics
8. SEO meta tags and structured data present

---

## Must-Haves (Goal Backward Verification)

- [ ] 8 complete sections: Hero, Problem, How It Works, Graphs vs Keywords, Features, Tech Stack, Pricing, CTA, Footer
- [ ] Features: 4-card grid with icons and badges
- [ ] Tech Stack: 3-layer diagram + 8+ logo badges
- [ ] Pricing: 3 tiers (Starter Free, Pro $99, Enterprise Custom)
- [ ] CTA buttons: Start Free, Schedule Demo, Contact Sales (HTMX)
- [ ] Newsletter signup form (HTMX, email validation)
- [ ] All sections responsive (480/768/1024/1440px)
- [ ] Lighthouse FCP <1.2s, LCP <2.5s
- [ ] Lighthouse Performance >90
- [ ] SEO meta tags present (title, description, OG, Twitter, schema)
- [ ] No layout shift (CLS <0.1)
