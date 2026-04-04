# Phase 5: Landing Page Portal - Week 4 Plan
## Polish, Performance Optimization & Deployment

**Phase:** 5 - Landing Page Portal
**Week:** 4 of 4
**Duration:** 40 hours estimated
**Mode:** standard
**Status:** PLANNED

---

## Frontmatter

```yaml
wave: 1, 2, 3
depends_on: [05-LANDING-PAGE-PLAN-WEEK1.md, 05-LANDING-PAGE-PLAN-WEEK2.md, 05-LANDING-PAGE-PLAN-WEEK3.md]
files_modified:
  - static/css/landing/index.css
  - static/js/landing/graph-visualization.js
  - static/images/landing/*.webp
  - core/templates/landing/base.html
  - core/templates/landing/partials/*.html
  - static/js/landing/interactions.js
autonomous: true
```

---

## Overview

**Goal:** Optimize landing page for production: image optimization, accessibility compliance, performance tuning, A/B testing setup, and deployment readiness.

**Target Metrics:**
- Lighthouse: 90+ all sections
- FCP: <1.2s
- LCP: <2.5s
- CLS: <0.1
- All pages pass accessibility (WCAG AA)
- Images optimized (WebP, lazy-loading, responsive srcsets)
- Deploy to production with rollback plan

**Wave Strategy:**
- **Wave 1 (Days 1-2):** Image optimization, lazy-loading attributes
- **Wave 2 (Days 3-4):** Accessibility audit, minification, performance tuning
- **Wave 3 (Days 5-6):** A/B testing, analytics setup, deployment verification

---

## Tasks

### Wave 1: Image Optimization

#### Task 1: Optimize & Convert Images to WebP
**Estimate:** 3 hours
**Wave:** 1

**Objective:** Convert PNG/JPG images to WebP format (30-40% smaller) with fallbacks.

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (Image optimization)
- All HTML partials created in Weeks 1-3 (image references)

**Action:**
1. Identify all images referenced in landing templates:
   - Tech stack logos (8+ images): PostgreSQL, Neo4j, Redis, etc.
   - Feature card icons (if any)
   - OpenGraph image (1200×630px)
   - Twitter card image (1200×675px)
2. Create `/home/joao/hrtech/static/images/landing/` directory (if not exists)
3. Use ImageOptim or online tools to convert:
   - Format: PNG/JPG → WebP
   - Compression: 80-90% quality
   - Size target: each <50KB
4. Create `<picture>` tags for each image in HTML:
   ```html
   <picture>
     <source srcset="{% static 'images/landing/tech-postgres.webp' %}" type="image/webp">
     <source srcset="{% static 'images/landing/tech-postgres.png' %}" type="image/png">
     <img src="{% static 'images/landing/tech-postgres.png' %}" alt="PostgreSQL" loading="lazy" width="48" height="48">
   </picture>
   ```
5. Add `loading="lazy"` to all `<img>` tags (native lazy-loading)
6. Add `width` and `height` attributes to prevent layout shift (CLS)
7. Test: DevTools Network tab should show WebP loading (in supported browsers)

**Acceptance Criteria:**
- All PNG/JPG images converted to WebP
- WebP versions <50KB each (grep file size)
- `<picture>` tags with WebP + PNG fallbacks
- All images have `loading="lazy"` attribute
- All images have `width` and `height` attributes
- Images load correctly in Chrome (WebP) and Safari (PNG fallback)
- DevTools Performance shows images lazy-loading (not all at once)

---

#### Task 2: Implement Responsive Images with Srcset
**Estimate:** 2 hours
**Wave:** 1

**Objective:** Add `srcset` and `sizes` for responsive image loading.

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (Responsive images)

**Action:**
1. Update tech logo images with srcset (1x and 2x density):
   ```html
   <img
     src="{% static 'images/landing/tech-postgres.webp' %}"
     srcset="{% static 'images/landing/tech-postgres-1x.webp' %} 1x,
             {% static 'images/landing/tech-postgres-2x.webp' %} 2x"
     alt="PostgreSQL"
     loading="lazy"
     width="48"
     height="48"
   >
   ```
2. For hero or feature images (if any), use responsive width srcset:
   ```html
   <img
     src="{% static 'images/landing/feature-screenshot.webp' %}"
     srcset="{% static 'images/landing/feature-screenshot-480w.webp' %} 480w,
             {% static 'images/landing/feature-screenshot-768w.webp' %} 768w,
             {% static 'images/landing/feature-screenshot-1440w.webp' %} 1440w"
     sizes="(max-width: 768px) 90vw, (max-width: 1440px) 60vw, 800px"
     alt="Feature screenshot"
     loading="lazy"
   >
   ```
3. Test: Inspect Network tab in DevTools at different viewport widths

**Acceptance Criteria:**
- All tech logos have 1x/2x density srcsets
- Large images (if any) have 480w/768w/1440w srcsets
- `sizes` attribute present for responsive images
- Correct image loads at each viewport width (verified in DevTools)
- Retina displays load 2x images

---

#### Task 3: Compress CSS & JavaScript
**Estimate:** 2 hours
**Wave:** 1

**Objective:** Minify CSS and JS files for production.

**Read First:**
- `/home/joao/hrtech/static/css/landing/index.css` (CSS files)
- `/home/joao/hrtech/static/js/landing/*.js` (JS files)

**Action:**
1. Use Django's `compressor` package or manual minification:
   ```bash
   # Install (if not already)
   pip install django-compressor

   # Collect and compress
   python manage.py compress --force
   ```
2. Or manually minify with online tools:
   - CSS: Use CSSNano or online minifier
   - JS: Use Terser or online minifier
   - Output files: `landing.min.css`, `graph-visualization.min.js`, etc.
3. Update base.html to reference minified files in production:
   ```html
   {% if DEBUG %}
     <link rel="stylesheet" href="{% static 'css/landing/index.css' %}">
   {% else %}
     <link rel="stylesheet" href="{% static 'css/landing/index.min.css' %}">
   {% endif %}
   ```
4. Verify: Check file sizes before/after compression
   - Target: CSS <20KB (minified + gzipped)
   - Target: JS <30KB (minified + gzipped)

**Acceptance Criteria:**
- Minified CSS file exists and is <20KB (gzipped)
- Minified JS file exists and is <30KB (gzipped)
- Original files renamed or kept for development
- Production references minified versions
- Page functionality unchanged after minification

---

### Wave 2: Accessibility & Performance Tuning

#### Task 4: Accessibility Audit (WCAG AA)
**Estimate:** 2.5 hours
**Wave:** 2

**Objective:** Verify landing page meets WCAG AA accessibility standards.

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (Contrast ratio, accessibility)

**Action:**
1. Run Lighthouse Accessibility audit (DevTools):
   - Open DevTools → Lighthouse → Accessibility
   - Target: Score 95+
   - Fix any issues found
2. Test with screen reader (NVDA on Windows, VoiceOver on Mac):
   - All headings announced correctly (H1, H2, etc.)
   - Form labels announced with inputs
   - Button text clear and descriptive
   - No "click here" links (use descriptive link text)
3. Color contrast check (WebAIM Contrast Checker):
   - All text must be 4.5:1 or higher (WCAG AA for body text)
   - All large text 3:1 or higher
   - Verify on both light (hero, CTA) and dark sections
4. Keyboard navigation:
   - Tab through all interactive elements
   - Logical tab order (top to bottom)
   - All buttons/links focusable (visible focus indicator)
   - No keyboard traps
5. Form accessibility:
   - Labels associated with inputs (`<label for="email">`)
   - Error messages linked to inputs
   - Success messages announced

**Acceptance Criteria:**
- Lighthouse Accessibility score ≥95
- All headings properly nested (H1 → H2, no H1 → H3)
- All form inputs have labels (grep: `<label for=`)
- All buttons have descriptive text (no empty buttons)
- Color contrast ≥4.5:1 for body text
- Color contrast ≥3:1 for large text (18px+ bold)
- Keyboard navigation works (all interactive elements reachable via Tab)
- Focus indicator visible on all focusable elements
- No keyboard traps (can Tab away from any element)
- Screen reader announces major sections and landmarks

---

#### Task 5: Performance Tuning & Caching
**Estimate:** 2 hours
**Wave:** 2

**Objective:** Implement caching headers and further optimize performance.

**Read First:**
- `/home/joao/hrtech/hrtech/settings.py` (Django settings)
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (Performance)

**Action:**
1. Update Django settings for caching:
   ```python
   # settings.py
   CACHES = {
       'default': {
           'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
           'LOCATION': 'unique-snowflake',
       }
   }

   # Cache landing page for 24 hours
   LANDING_PAGE_CACHE_TIMEOUT = 60 * 60 * 24
   ```
2. Update landing page view:
   ```python
   @method_decorator(cache_page(LANDING_PAGE_CACHE_TIMEOUT), name='dispatch')
   class LandingPageView(TemplateView):
       # Already implemented in Week 1
   ```
3. Add HTTP caching headers (Django middleware or settings):
   ```python
   # settings.py
   SECURE_SSL_REDIRECT = True  # Redirect HTTP to HTTPS
   SESSION_COOKIE_SECURE = True
   CSRF_COOKIE_SECURE = True
   SECURE_HSTS_SECONDS = 31536000  # 1 year
   SECURE_HSTS_INCLUDE_SUBDOMAINS = True
   SECURE_HSTS_PRELOAD = True
   ```
4. Set static file expiry (Render/CDN handles this):
   ```python
   # Static files will be cached by CDN for 1 year
   STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
   ```
5. Test: Lighthouse should show "Serve static assets with an efficient cache policy"

**Acceptance Criteria:**
- Landing page view cached (cache_page decorator present)
- SECURE_SSL_REDIRECT enabled (grep settings.py)
- HSTS headers set (SECURE_HSTS_SECONDS)
- Static file caching configured (STATICFILES_STORAGE)
- Lighthouse shows cache policy for images/CSS/JS
- Page loads from cache on subsequent visits

---

#### Task 6: Production Security Checklist
**Estimate:** 1.5 hours
**Wave:** 2

**Objective:** Verify all security headers and settings for production.

**Read First:**
- `/home/joao/hrtech/hrtech/settings.py` (Django settings)
- OWASP security guidelines

**Action:**
1. Verify security headers in responses:
   - `X-Content-Type-Options: nosniff` (prevent MIME sniffing)
   - `X-Frame-Options: DENY` (prevent clickjacking)
   - `X-XSS-Protection: 1; mode=block` (XSS protection)
   - `Content-Security-Policy` (CSP headers)
   - `Strict-Transport-Security` (HSTS)
2. Django settings security check:
   ```bash
   python manage.py check --deploy
   ```
3. Verify:
   - DEBUG = False in production
   - SECRET_KEY is strong (50+ random characters)
   - ALLOWED_HOSTS configured correctly
   - No hardcoded credentials (all from env vars)
4. Test: curl landing page and verify headers:
   ```bash
   curl -I https://yoursite.com | grep -i "X-Content-Type\|X-Frame\|Strict"
   ```

**Acceptance Criteria:**
- `python manage.py check --deploy` passes (0 issues)
- X-Content-Type-Options header present
- X-Frame-Options header present
- Strict-Transport-Security header present
- DEBUG = False in production settings
- All credentials from environment variables (grep settings.py for no hardcoded keys)
- CSRF protection enabled (forms have {% csrf_token %})

---

### Wave 3: Testing, Analytics & Deployment

#### Task 7: Set Up A/B Testing Framework
**Estimate:** 2 hours
**Wave:** 3

**Objective:** Implement A/B testing infrastructure for CTA buttons and headlines.

**Read First:**
- Django templates system

**Action:**
1. Create A/B test variants:
   - **Variant A (Control):** "Start Free Trial" + "Schedule Demo"
   - **Variant B (Test):** "Get Started Now" + "Book Demo"
   - Alternate CTA colors or sizing
2. Implement simple A/B test in view:
   ```python
   import random

   class LandingPageView(TemplateView):
       def get_context_data(self, **kwargs):
           context = super().get_context_data(**kwargs)
           # 50/50 split
           context['ab_variant'] = 'A' if random.random() < 0.5 else 'B'
           return context
   ```
3. Update templates to use variant:
   ```html
   {% if ab_variant == 'A' %}
     <button>Start Free Trial</button>
   {% else %}
     <button>Get Started Now</button>
   {% endif %}
   ```
4. Track variant in analytics (task 8)

**Acceptance Criteria:**
- A/B variant generated in view context
- CTA buttons change based on variant
- 50/50 split between variants
- Template renders correct variant
- No console errors on load

---

#### Task 8: Set Up Google Analytics & Conversion Tracking
**Estimate:** 1.5 hours
**Wave:** 3

**Objective:** Integrate Google Analytics and track key metrics.

**Read First:**
- Google Analytics documentation

**Action:**
1. Create Google Analytics account (if not exists)
2. Add GA script to base.html:
   ```html
   <!-- Google Analytics -->
   <script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
   <script>
     window.dataLayer = window.dataLayer || [];
     function gtag(){dataLayer.push(arguments);}
     gtag('js', new Date());
     gtag('config', 'GA_MEASUREMENT_ID');
   </script>
   ```
3. Replace `GA_MEASUREMENT_ID` with actual ID from environment variable:
   ```python
   # settings.py
   GA_MEASUREMENT_ID = env('GA_MEASUREMENT_ID', default='')
   ```
4. Track key events:
   ```javascript
   // Track CTA clicks
   document.querySelectorAll('.btn-cta').forEach(btn => {
     btn.addEventListener('click', () => {
       gtag('event', 'cta_click', {
         'button_text': btn.textContent,
         'variant': '{{ ab_variant }}'
       });
     });
   });

   // Track newsletter signup
   document.querySelector('form').addEventListener('submit', () => {
     gtag('event', 'newsletter_signup');
   });
   ```
5. Set up conversion goals in GA:
   - CTA clicks (Start Free, Schedule Demo, Contact Sales)
   - Newsletter signups
   - Demo requests

**Acceptance Criteria:**
- GA script tag present in base.html
- GA measurement ID from environment variable
- CTA clicks tracked as events
- Newsletter signup tracked as conversion
- Real-time events visible in GA dashboard
- No console errors related to GA

---

#### Task 9: Create Deployment Runbook & Checklist
**Estimate:** 2 hours
**Wave:** 3

**Objective:** Document deployment process and pre-deployment checklist.

**Read First:**
- `/home/joao/hrtech/.planning/phases/05-landing-page/05-LANDING-PAGE-RESEARCH.md` (Performance targets)

**Action:**
1. Create `/home/joao/hrtech/.planning/DEPLOYMENT_CHECKLIST_LANDING_PAGE.md`:
   ```markdown
   # Landing Page Deployment Checklist

   ## Pre-Deployment (24h before)

   - [ ] Run full Lighthouse audit (all metrics >90)
   - [ ] Test responsive design (480/768/1024/1440px)
   - [ ] Test HTMX forms (newsletter, CTA buttons)
   - [ ] Verify all images load and display correctly
   - [ ] Check all external links (Twitter, GitHub, etc.)
   - [ ] Run accessibility check (WCAG AA)
   - [ ] Security headers verified (X-Frame, CSP, etc.)
   - [ ] Analytics tracking tested (GA events firing)
   - [ ] A/B variant logic verified (50/50 split)
   - [ ] Cache headers configured (24h for landing page)

   ## Environment Variables

   - [ ] ALLOWED_HOSTS includes production domain
   - [ ] DEBUG = False
   - [ ] SECRET_KEY is strong (50+ chars)
   - [ ] GA_MEASUREMENT_ID set (if using analytics)
   - [ ] All third-party API keys present (OpenAI, etc.)

   ## Deployment Steps

   1. Create git tag: `git tag v5.0.0-landing-page`
   2. Push to GitHub: `git push --tags`
   3. On Render: trigger deployment from GitHub
   4. Monitor: Lighthouse, error logs, uptime checks
   5. Verify: Page loads <2s, all sections visible

   ## Post-Deployment (1h after)

   - [ ] Check production Lighthouse score
   - [ ] Monitor error logs (no 500s, 404s)
   - [ ] Verify GA tracking (events in real-time)
   - [ ] Test HTMX forms (one successful submission)
   - [ ] Spot check responsive design (mobile device)
   - [ ] Confirm CTA buttons work (redirects or modals)

   ## Rollback Plan

   If critical issues found:
   ```bash
   git revert <commit>
   git push
   # Render auto-deploys within 2 minutes
   ```
   ```

2. Create performance baseline report:
   ```markdown
   # Landing Page Performance Baseline

   | Metric | Target | Status |
   |--------|--------|--------|
   | FCP | <1.2s | ✓ |
   | LCP | <2.5s | ✓ |
   | CLS | <0.1 | ✓ |
   | Performance | >90 | ✓ |
   | Accessibility | >95 | ✓ |
   | SEO | >95 | ✓ |
   | Best Practices | >90 | ✓ |

   Date: 2026-04-04
   Device: Desktop / Mobile
   ```

**Acceptance Criteria:**
- Deployment checklist file created with 15+ items
- Checklist covers pre-deployment, environment, deployment, post-deployment
- Performance baseline report documented
- Rollback instructions present
- Estimated deployment time <5 minutes

---

#### Task 10: Final Production Testing & Launch
**Estimate:** 3 hours
**Wave:** 3

**Objective:** Complete final testing and deploy to production.

**Read First:**
- All sections and tasks from Weeks 1-4

**Action:**
1. Run final Lighthouse audit (all pages):
   - Desktop: FCP <1.2s, LCP <2.5s, CLS <0.1, Performance >90
   - Mobile: FCP <2.5s, LCP <4s, CLS <0.1, Performance >85
2. Manual testing checklist:
   - [ ] Page loads without errors (console)
   - [ ] All sections visible (scroll full page)
   - [ ] All interactive elements work (buttons, forms, hover)
   - [ ] Responsive on 480px, 768px, 1024px, 1440px
   - [ ] Dark mode applies (if using prefers-color-scheme)
   - [ ] Hamburger menu works on mobile
   - [ ] Images load with WebP (DevTools Network)
   - [ ] Lazy-loading working (scroll to "How It Works", graph initializes)
   - [ ] HTMX forms don't reload page
   - [ ] Newsletter form validates email
   - [ ] CTA buttons show responses
   - [ ] All links work (internal #anchors, external URLs)
   - [ ] Footer links present
   - [ ] No 404 on CSS/JS/images
3. Cross-browser testing:
   - [ ] Chrome (latest)
   - [ ] Safari (latest)
   - [ ] Firefox (latest)
   - [ ] Edge (latest)
4. Mobile device testing:
   - [ ] iPhone 12/13/14
   - [ ] Android device (Samsung, Pixel)
5. Network throttling test:
   - DevTools → Network → Throttle to "Slow 3G"
   - FCP should still be <3s
6. If all pass: Deploy to production
   ```bash
   git add .
   git commit -m "feat(landing): complete landing page portal with animations and forms"
   git push
   # Render auto-deploys
   ```
7. Monitor for 24 hours:
   - Check error logs hourly
   - Monitor Google Analytics
   - Check Uptime monitoring (synthetic checks)
   - Review Lighthouse scores on production

**Acceptance Criteria:**
- Lighthouse Desktop: FCP <1.2s, LCP <2.5s, CLS <0.1, Performance >90
- Lighthouse Mobile: FCP <2.5s, LCP <4s, CLS <0.1, Performance >85
- All manual testing checklist items pass
- Cross-browser testing passes (4 browsers)
- Mobile device testing passes (2 devices)
- Slow 3G test passes (FCP <3s)
- Production deployment successful
- Error logs clean (no 500s in first 24h)
- GA tracking shows realistic traffic/events

---

## Verification Criteria

**All Week 4 tasks complete when:**
1. All images optimized (WebP with fallbacks, <50KB each)
2. Responsive images with srcset configured
3. CSS and JS minified for production
4. Accessibility audit passed (WCAG AA, Lighthouse >95)
5. Performance headers and caching configured
6. Security checklist passed (`python manage.py check --deploy`)
7. A/B testing framework implemented
8. Analytics tracking configured
9. Deployment checklist and runbook documented
10. Final testing passed on all browsers/devices
11. Production deployment successful

---

## Must-Haves (Goal Backward Verification)

- [ ] Lighthouse Desktop: FCP <1.2s, LCP <2.5s, CLS <0.1
- [ ] Lighthouse Mobile: FCP <2.5s, LCP <4s, CLS <0.1
- [ ] All metrics >90 (Performance, Accessibility, SEO, Best Practices)
- [ ] All images in WebP format with PNG fallbacks
- [ ] Images responsive with srcset and sizes
- [ ] CSS & JS minified for production
- [ ] WCAG AA accessibility (all headings, labels, contrast)
- [ ] Security headers present (X-Frame, CSP, HSTS)
- [ ] Cache headers configured (24h for landing page)
- [ ] Google Analytics tracking events
- [ ] A/B testing framework in place
- [ ] Deployment runbook documented with rollback plan
- [ ] Production deployment successful (no critical errors)
- [ ] Page loads <2.5s in production
- [ ] All 8 sections visible and interactive

---

## Phase 5 Completion Criteria

**Landing Page Portal is COMPLETE when:**

1. **Structure & Content** ✓
   - All 8 sections built (Hero, Problem, How It Works, Graphs vs Keywords, Features, Tech Stack, Pricing, CTA, Footer)
   - All copy matches UI-SPEC exactly
   - All images optimized and responsive
   - All links functional (internal #anchors, external)

2. **Functionality** ✓
   - D3.js graph animates at 60fps (desktop), 30+ fps (mobile)
   - HTMX forms work without page reload (newsletter, CTA buttons)
   - Lazy-loading defers below-fold sections
   - Hamburger menu responsive on mobile
   - All hover effects smooth and accessible

3. **Performance** ✓
   - FCP <1.2s (hero text visible immediately)
   - LCP <2.5s (largest element loaded)
   - CLS <0.1 (no layout shift)
   - Lighthouse Desktop ≥90 all sections
   - Lighthouse Mobile ≥85 all sections
   - Page size <2MB (uncompressed)

4. **Accessibility** ✓
   - WCAG AA compliant (contrast, keyboard nav, screen reader)
   - All form labels associated with inputs
   - Keyboard navigation works (Tab through all interactive elements)
   - Focus indicators visible on all buttons/links
   - No keyboard traps

5. **SEO & Discoverability** ✓
   - Meta tags: title, description, OG, Twitter, canonical
   - Schema.org structured data (SoftwareApplication)
   - H1 for main headline (hero section)
   - All images have alt text
   - Mobile-friendly (responsive)

6. **Security** ✓
   - All security headers present (X-Frame, CSP, HSTS)
   - DEBUG = False in production
   - No hardcoded credentials
   - CSRF protection on forms
   - SSL/HTTPS enforced

7. **Analytics & Testing** ✓
   - Google Analytics tracking key events
   - A/B testing framework implemented
   - Error tracking (Sentry or similar)
   - Deployment checklist documented
   - Rollback plan in place

8. **Deployment** ✓
   - Production deployment successful
   - Monitoring set up (error logs, uptime checks)
   - 24-hour post-deployment review completed
   - No critical issues in production
   - Performance baseline established

---

## Sign-Off

**Phase 5 Landing Page Portal is APPROVED FOR PRODUCTION when:**
- All must-haves verified
- Lighthouse scores meet targets
- Security checklist passed
- No critical bugs in production (first 24h)
- Team sign-off from Product, Engineering, QA
