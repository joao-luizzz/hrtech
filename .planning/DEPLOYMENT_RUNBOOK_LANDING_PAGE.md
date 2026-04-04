# Landing Page Deployment Runbook

**Version:** 1.0  
**Date:** 2026-04-04  
**Platforms:** Render.com (recommended), Heroku, AWS, DigitalOcean  
**Environment:** Production (DEBUG=False)  
**Estimated Time:** 15 minutes

---

## Pre-Deployment Checklist (24h before)

### Performance & Quality
- [ ] Run full Lighthouse audit (all metrics >90)
  ```bash
  npm install -g lighthouse
  lighthouse https://staging.hrtech.com --view
  ```
  - Performance: ≥90
  - Accessibility: ≥95
  - SEO: ≥95
  - Best Practices: ≥90

- [ ] Responsive design verified (480/768/1024/1440px)
  - Test on Chrome DevTools device emulation
  - Test on real mobile devices (iPhone, Android)

- [ ] All sections load correctly
  - Hero (D3.js graph animates)
  - Problem (comparison cards visible)
  - How It Works (split layout)
  - Features (4 cards grid)
  - Tech Stack (8 logos)
  - Pricing (3 tiers)
  - CTA (buttons visible)
  - Footer (links present)

### Forms & Interactions
- [ ] Newsletter form works (HTMX submission)
  - Enter valid email → Success message
  - Enter invalid email → Error message
  - Form doesn't reload page

- [ ] CTA buttons functional
  - All buttons clickable
  - HTMX post requests working
  - Response displays correctly

- [ ] Links all functional
  - Internal anchors (#hero, #pricing, etc.)
  - External links (GitHub, Twitter, LinkedIn)
  - No 404 errors

### Images & Assets
- [ ] All images load and display
  - og-image.webp (1200×630px)
  - twitter-image.webp (1200×675px)
  - PNG fallbacks available

- [ ] Emoji icons render correctly (browser-dependent)
  - Tech stack emojis visible
  - Feature icons visible

- [ ] CSS/JS files load without errors
  - DevTools Console: No errors
  - DevTools Network: All 200 status codes
  - No 404 on static files

### Accessibility & SEO
- [ ] Accessibility audit passed (WCAG AA)
  - Lighthouse score ≥95
  - Keyboard navigation works
  - Screen reader compatible (test with NVDA or VoiceOver)
  - Color contrast ≥4.5:1

- [ ] SEO meta tags present
  - Title: `<title>HRTech: AI-Powered Recruitment...`
  - Description: `<meta name="description">`
  - OG tags: og:title, og:description, og:image, og:url
  - Twitter card: twitter:card, twitter:title, twitter:image
  - Schema.org: `<script type="application/ld+json">`

### Security
- [ ] Security headers present
  - Verify with: `curl -I https://staging.hrtech.com`
  ```
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Strict-Transport-Security: max-age=31536000
  Content-Security-Policy: ...
  ```

- [ ] Forms have CSRF protection
  - Newsletter form includes `{% csrf_token %}`
  - All POST requests protected

- [ ] No hardcoded credentials
  - Check: `grep -r "SECRET_KEY\|PASSWORD" core/`
  - All secrets from environment variables

### Analytics & A/B Testing
- [ ] A/B variant assignment working
  - Load page multiple times
  - See both "Start Free Trial" and "Get Started Now" buttons
  - Roughly 50/50 distribution

- [ ] Google Analytics ready (if GA_MEASUREMENT_ID set)
  - GA script loads (check Network tab)
  - gtag function defined (check Console)
  - Real-time dashboard accessible
  - Test event tracking (click button → check Real-time)

### Performance Baseline
- [ ] Measure Core Web Vitals
  - FCP (First Contentful Paint): <1.2s ✓
  - LCP (Largest Contentful Paint): <2.5s ✓
  - CLS (Cumulative Layout Shift): <0.1 ✓
  - TTFB (Time to First Byte): <0.5s ✓

- [ ] Test on slow network (3G)
  - DevTools → Network → "Slow 3G"
  - FCP should be <3s

---

## Environment Variables (Production)

Create `.env.production` or set in Render environment:

```bash
# Django Core
DEBUG=False
SECRET_KEY=<50+ random characters, generated with: python -c "import secrets; print(secrets.token_urlsafe(50))">
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,render.com

# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname
# Or if using separate variables:
DB_HOST=db.c.yourdomain.com
DB_USER=postgres
DB_PASSWORD=<secure password>
DB_NAME=hrtech_prod

# Redis/Cache
CACHE_URL=redis://user:password@cache.upstash.io:6379/0
# Or:
REDIS_URL=redis://user:password@cache.upstash.io:6379/0

# OpenAI (for interview questions feature)
OPENAI_API_KEY=sk-...

# AWS S3 (for CV storage)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=hrtech-cvs
AWS_S3_REGION_NAME=us-east-1

# Email (for newsletter, future)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@hrtech.com
EMAIL_HOST_PASSWORD=<app password>

# Google Analytics (optional)
GA_MEASUREMENT_ID=G-XXXXXXXXXX

# Security
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
X_FRAME_OPTIONS=DENY

# Sentry (error tracking, optional)
SENTRY_DSN=https://...
```

**Security:**
- [ ] Generate new `SECRET_KEY` (use: `python -c "import secrets; print(secrets.token_urlsafe(50))"`)
- [ ] Never commit `.env.production` (add to .gitignore)
- [ ] Store secrets in Render environment variables (not in code)
- [ ] Use strong passwords for DB and Redis (20+ characters, mixed case/numbers/symbols)

---

## Deployment Steps

### 1. Pre-Deployment Verification

```bash
# Pull latest code
git pull origin main

# Check git status (should be clean)
git status

# Verify all changes committed
git log --oneline -5

# Run tests (if any)
python manage.py test core

# Run Django security check
python manage.py check --deploy
```

**Expected output:**
- Git status: `nothing to commit, working tree clean`
- Tests: `OK` (or `Ran X tests in Y seconds`)
- Security check: `System check identified 0 issues in X.XXs.` (0 errors in production mode)

### 2. Create Release Tag

```bash
# Tag version (format: v5.0.0-landing-page or v1.0.0)
git tag v1.0.0-landing-page -m "Release: Landing Page Portal v1.0.0"

# Push tag to remote
git push origin v1.0.0-landing-page

# Verify tag pushed
git tag -l | grep landing-page
```

### 3. Deploy to Render (Recommended)

**Prerequisites:**
- Account at https://render.com
- Project linked to GitHub repository
- Environment variables set in Render dashboard

**Option A: Automatic via GitHub (Recommended)**
1. Go to Render dashboard
2. Select your service
3. Verify Environment variables are set
4. Click "Deploy" (or push to main → auto-deploy if configured)
5. Wait for build to complete (2-5 minutes)
6. Monitor: Logs → look for "Listening on" confirmation

**Option B: Manual via Render CLI**
```bash
# Install render CLI (if not installed)
npm install -g @render-oss/command

# Deploy
render deploy --name your-service-name
```

### 4. Post-Deployment Verification (Immediate)

```bash
# Test landing page loads
curl -I https://yourdomain.com/
# Expected: 200 OK, with security headers

# Check critical sections (should not be 404)
curl -s https://yourdomain.com/ | grep -c "<h1" # Should be 1
curl -s https://yourdomain.com/ | grep -c "cta-response" # Should be 1
curl -s https://yourdomain.com/ | grep -c "hero-graph-canvas" # Should be 1
```

### 5. Smoke Testing (Manual, 10-15 minutes)

**Browser Testing:**

1. **Load Landing Page**
   - [ ] Page loads in <2.5s
   - [ ] All sections visible (scroll through)
   - [ ] No console errors (DevTools → Console)

2. **Hero Section**
   - [ ] H1 visible: "AI-Powered Recruitment That Actually Works"
   - [ ] D3.js graph animates (if enabled)
   - [ ] CTA buttons clickable
   - [ ] Button text shows either "Start Free Trial" or "Get Started Now"

3. **Form Submission**
   - [ ] Newsletter form email input works
   - [ ] Valid email (e.g., test@example.com) → Success message
   - [ ] Invalid email (e.g., "notanemail") → Error message
   - [ ] Form doesn't reload page (HTMX working)

4. **Responsive Design**
   - [ ] DevTools → Toggle device toolbar (mobile view)
   - [ ] All sections stack correctly
   - [ ] Hamburger menu works (if mobile nav present)
   - [ ] Buttons full-width on mobile

5. **Links & Navigation**
   - [ ] Footer links work (Privacy, Terms, etc.)
   - [ ] External links open in new tab (GitHub, Twitter, LinkedIn)
   - [ ] Internal anchors work (#hero → jumps to hero)

6. **Performance**
   - [ ] Lighthouse report: All metrics ≥90
     - Run: Right-click → Inspect → Lighthouse → Analyze page load
   - [ ] FCP <1.2s
   - [ ] LCP <2.5s
   - [ ] CLS <0.1

7. **Security Headers**
   - [ ] Right-click → Inspect → Network → (any request) → Headers
   - [ ] Response headers present:
     ```
     X-Content-Type-Options: nosniff
     X-Frame-Options: DENY
     Strict-Transport-Security: ...
     Content-Security-Policy: ...
     ```

8. **Analytics (if GA_MEASUREMENT_ID set)**
   - [ ] GA script loads (Network tab → filter "gtag")
   - [ ] Real-time events visible (Google Analytics → Real-time)
   - [ ] Click CTA button → `cta_click` event appears in Real-time
   - [ ] Newsletter signup → `newsletter_signup` event appears

---

## Monitoring & Alerting (24h post-deployment)

### Hourly Checks (First 24h)

- [ ] **Hour 1:** Check error logs
  - Render: Logs → Filter: "error" or "500"
  - Expected: Clean (0 errors)

- [ ] **Hour 2:** Monitor uptime
  - Uptime checker: https://uptimerobot.com (setup beforehand)
  - Expected: 100% uptime

- [ ] **Hour 4:** Verify analytics data
  - Google Analytics → Real-time → Active users
  - Expected: Real users (if site is public)

- [ ] **Hour 8, 12, 24:** Re-run Lighthouse
  - Check performance doesn't degrade
  - Expected: Consistent scores (±5 points is normal)

### Daily Checks (Week 1)

- [ ] No critical errors in logs
- [ ] Uptime >99%
- [ ] Core Web Vitals healthy
- [ ] Analytics events firing
- [ ] No spike in 404/500 errors

### Weekly Checks (Ongoing)

- [ ] Performance baseline stable
- [ ] No increase in error rate
- [ ] User feedback (if available)
- [ ] A/B test results (2+ weeks of data)

---

## Rollback Plan

### If Critical Issues Found

**Immediate Action:**
```bash
# Option 1: Revert last commit
git revert <commit-hash>
git push origin main
# Render auto-deploys within 2 minutes

# Option 2: Revert to previous version
git checkout v0.9.0  # Previous working version
git push -f origin main  # Force push to main
# Render auto-deploys
```

**Investigation:**
- Check Render logs for errors
- Compare current code vs previous version
- Identify breaking changes
- Fix and re-deploy

**Communication:**
- Notify team of rollback
- Document issue in GitHub issue tracker
- Schedule post-mortem if critical

### Acceptable Issues (Monitor, Don't Rollback)

- Minor UI misalignment on specific devices (< 5% of users)
- Slow initial load on first-time visitors (TTFB OK, cache misses)
- Newsletter form submission slowness (API dependent)
- GA events delayed by 1-2 seconds (GA lag normal)

---

## DNS & Custom Domain Setup

### Configure Custom Domain (if applicable)

1. **Render Dashboard:**
   - Service → Settings → Custom Domains
   - Add your domain: `yourdomain.com` and `www.yourdomain.com`
   - Copy CNAME record

2. **DNS Provider (GoDaddy, Cloudflare, etc.):**
   - Add CNAME record:
     ```
     Name: yourdomain.com
     Type: CNAME
     Value: yourdomain.onrender.com
     ```

3. **SSL Certificate:**
   - Render auto-provisions Let's Encrypt cert (free)
   - HTTPS enabled automatically
   - Wait 5-10 minutes for cert to activate

4. **Verify:**
   ```bash
   curl -I https://yourdomain.com
   # Should return 200 OK with Render server header
   ```

---

## Performance Optimization (Week 1)

### After Collecting Real Data

1. **Analyze Lighthouse reports:**
   - Identify slowest elements
   - Check Network tab for bottlenecks

2. **Optimize database queries:**
   - If LCP >2.5s, check Django query count
   - Add `.select_related()` or `.prefetch_related()`

3. **Cache optimization:**
   - Verify landing page cache is working
   - Check: `curl -I -H "Cache-Control: max-age=0" https://yourdomain.com | grep -i age`

4. **Image optimization:**
   - Verify WebP images loading (not PNG fallbacks)
   - Check: DevTools Network → filter by image files

---

## A/B Testing Monitoring

### Week 1-2: Baseline Collection

- [ ] Collect at least 100 unique users per variant
- [ ] Monitor CTR (click-through rate)
- [ ] Monitor newsletter conversion
- [ ] No statistical analysis yet (too early)

### Week 2-4: Analysis Phase

- [ ] Collect 385+ users per variant (statistical significance)
- [ ] Calculate CTR for each variant
- [ ] Determine winner (if >5% difference)
- [ ] Document results

### Week 4+: Decision

- [ ] If Variant B wins: Keep B, develop new test
- [ ] If Variant A wins: Keep A, develop alternative
- [ ] If tied: Extend test or rotate variants

---

## Future Deployments (After v1.0)

### Deployment Frequency

**Recommended:** 1-2 times per week
- Minor fixes: 24h approval cycle
- Major features: 48h review + testing
- Hotfixes (critical bugs): Immediate

### Version Numbering

```
v1.0.0-landing-page    # Initial release
v1.0.1-landing-page    # Bug fix (patch)
v1.1.0-landing-page    # New feature (minor)
v2.0.0-landing-page    # Breaking change (major)
```

### Changelog Template

```markdown
## v1.0.1 - 2026-04-11
- fix: Newsletter form validation issue on Firefox
- perf: Reduce CSS bundle size by 2%
- docs: Update deployment guide

## v1.1.0 - 2026-04-18
- feat: Add dark mode toggle
- feat: A/B test results dashboard
- perf: Improve LCP by 0.3s via lazy-loading optimization
```

---

## Troubleshooting

### Landing page returns 500 error

**Checklist:**
1. Check Render logs for Python error
2. Verify DATABASE_URL is correct
3. Check SECRET_KEY is set
4. Run migrations: `python manage.py migrate`
5. Rollback to previous version

### Pages load slowly (LCP >3s)

**Checklist:**
1. Check Render CPU/RAM usage
2. Verify database queries (Django Debug Toolbar)
3. Check D3.js graph initialization (may be slow on mobile)
4. Enable caching: `CACHE_TIMEOUT=86400`

### GA events not firing

**Checklist:**
1. Verify GA_MEASUREMENT_ID is set
2. Check gtag.js loads (Network tab)
3. Verify event parameters in GA Real-time
4. Check browser console for JavaScript errors

### Form submission returns 403 Forbidden

**Checklist:**
1. Verify CSRF token in form: `{% csrf_token %}`
2. Check CSRF_MIDDLEWARE is in settings.py
3. Verify CSRF_COOKIE_SECURE=True in production
4. Check form method is POST (not GET)

---

## Sign-Off Checklist

**Before marking deployment as complete:**

- [ ] All pre-deployment checks passed
- [ ] Deployment completed successfully
- [ ] Post-deployment smoke tests passed
- [ ] Security headers verified
- [ ] Performance baseline established
- [ ] Analytics tracking confirmed
- [ ] No errors in production logs
- [ ] Team notified of deployment
- [ ] Status page updated (if applicable)

---

**Deployment Status:** ✓ Ready for Production  
**Last Updated:** 2026-04-04  
**Next Review:** After first production deployment

**Questions?** Contact DevOps or refer to Render documentation at https://render.com/docs
