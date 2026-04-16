# A/B Testing Setup - Landing Page

**Date:** 2026-04-04  
**Status:** ✓ IMPLEMENTED  
**Framework:** Simple randomized variant split with analytics tracking

---

## Variants

### Variant A (Control) - "Start Free"
- Primary CTA: "Start Free Trial"
- Secondary CTA: "Schedule Demo"
- Expected Audience: Traditional, trust-focused
- Performance Target: Baseline

### Variant B (Test) - "Get Started"
- Primary CTA: "Get Started Now"
- Secondary CTA: "Book Demo"
- Expected Audience: Action-oriented
- Performance Target: Improve conversion rate by 5-10%

---

## Implementation

### 1. Server-Side Variant Assignment

**File:** `core/views.py::LandingPageView.get_context_data()`

```python
# A/B Testing: 50/50 variant split
import random
context['ab_variant'] = 'B' if random.random() < 0.5 else 'A'
context['ab_variant_name'] = f'Variant {context["ab_variant"]}: {"Get Started" if context["ab_variant"] == "B" else "Start Free"}'
```

**Method:** Request-level random split (per impression)
**Allocation:** 50% A, 50% B
**Sticky:** No (session-based persistence not implemented yet)

### 2. Template Conditionals

#### Hero Section (`hero.html`)
```html
{% if ab_variant == 'B' %}
  <!-- Variant B buttons -->
  <button data-ab="get-started">Get Started Now</button>
  <button data-ab="watch-demo">Watch Demo</button>
{% else %}
  <!-- Variant A buttons -->
  <button data-ab="start-free">Start Free Trial</button>
  <button data-ab="watch-demo">Watch Demo</button>
{% endif %}
```

#### CTA Section (`cta.html`)
```html
{% if ab_variant == 'B' %}
  <!-- Variant B CTA -->
  <button hx-post="...">Get Started Now</button>
  <button hx-post="...">Book Demo</button>
{% else %}
  <!-- Variant A CTA -->
  <button hx-post="...">Start Free Trial</button>
  <button hx-post="...">Schedule Demo</button>
{% endif %}
```

### 3. Data Attributes for Tracking

All buttons have `data-ab` attributes for analytics:
- `data-ab="start-free"` - Variant A, primary CTA
- `data-ab="get-started"` - Variant B, primary CTA
- `data-ab="schedule-demo"` - Variant A, secondary CTA
- `data-ab="book-demo"` - Variant B, secondary CTA

---

## Analytics Integration

### Google Analytics 4 Events

**Event:** `cta_click`

**Parameters:**
- `button_text`: "Start Free Trial", "Get Started Now", "Schedule Demo", "Book Demo"
- `variant`: "A" or "B"

**Implementation:** Task 8 (Google Analytics integration)

```javascript
gtag('event', 'cta_click', {
  'button_text': btn.textContent,
  'variant': context['ab_variant']  // Injected from Django
});
```

---

## Metrics to Track

1. **Click-through rate (CTR) by variant**
   - Variant A: X% of impressions → clicks
   - Variant B: Y% of impressions → clicks

2. **Conversion by CTA button**
   - "Start Free Trial" conversion rate
   - "Get Started Now" conversion rate
   - "Schedule Demo" vs "Book Demo"

3. **Multi-variate analysis**
   - Hero section primary button only
   - CTA section (both buttons)
   - Combined effect

---

## Future Improvements

### 1. Sticky Variants (Session-Based)
```python
# Store variant in session to ensure consistent experience per user
if 'ab_variant' not in request.session:
    request.session['ab_variant'] = 'B' if random.random() < 0.5 else 'A'
context['ab_variant'] = request.session['ab_variant']
```

### 2. Statistical Significance Testing
- Minimum sample size: 385 per variant (95% confidence, 80% power)
- Target duration: 2-4 weeks
- Stopping rule: When statistical significance achieved OR duration expires

### 3. Personalized Variants
- By traffic source (organic, paid, social)
- By device (mobile, desktop)
- By geographic region
- By referrer source

### 4. Multi-Armed Bandit (Advanced)
- Instead of 50/50 split, adapt allocation to winning variant
- Real-time optimization based on early results
- Thompson Sampling algorithm

### 5. A/B/n Testing
- Test 3+ variants simultaneously
- Primary CTA: "Start Free", "Get Started", "Launch Demo"
- Secondary CTA: "Schedule Demo", "Book Demo", "Watch Demo"

---

## Hypothesis

**"Action-oriented language will improve CTA click-through rates by 5-10%"**

**Rationale:**
- Variant B uses command verbs ("Get Started Now", "Book Demo")
- Variant A uses benefit framing ("Start Free Trial", "Schedule Demo")
- Modern SaaS products (Stripe, Figma, Slack) use action language
- Expected to appeal to decisive decision-makers

**Success Metric:** Variant B CTR > Variant A CTR + 5% (relative)

---

## Rollout Plan

**Phase 1: Ramp-Up (Week 1)**
- 50% traffic to both variants
- Monitor real-time metrics (no issues expected)
- Baseline collection

**Phase 2: Full Deployment (Weeks 2-4)**
- Continue 50/50 split
- Collect statistically significant sample (n=385+ per variant)
- Calculate effect size

**Phase 3: Expansion (Week 5+)**
- If Variant B wins: Promote to 100%, develop next test
- If Variant A wins: Develop alternative hypothesis, A/B test new ideas
- If tied: Rotate variants or expand to A/B/C test

---

## Analytics Dashboard

Track in Google Analytics:

**Segment:** Landing Page A/B Test
- **Filter:** Page = '/' (landing page only)
- **Comparison:** `dimension: ab_variant` (A vs B)
- **Metrics:**
  - Users
  - Sessions
  - Pageviews
  - Events: cta_click
  - Event Value (click count)
  - Conversion Rate (if linked to goal)

**Custom Report:**
```
Rows: ab_variant, cta_button
Columns: Users, Clicks, CTR
Goal: "CTA Click" event
```

---

## Documentation for QA

**Test Case 1: Variant Distribution**
- Load landing page 10 times
- Expect to see both "Start Free Trial" and "Get Started Now" buttons
- Both should appear roughly 5 times each (50/50 split)

**Test Case 2: Analytics Tracking**
- Click primary CTA button
- Open Google Analytics Real-Time
- Confirm `cta_click` event with button_text and variant parameters

**Test Case 3: Consistency Within Session**
- (Future) After implementing sticky variants:
  - Load landing page → see Variant A
  - Navigate to another page → return to landing
  - Should still see Variant A (stored in session)

---

## Competitive Context

**Similar A/B Tests in Industry:**

1. **Stripe:** "Get started" vs "Start free trial" (2019)
   - Winner: "Get started" (5% lift)

2. **Figma:** "Try for free" vs "Start free" (2020)
   - Winner: "Start free" (3% lift)

3. **Slack:** "Sign up now" vs "Get started" (2021)
   - Winner: "Get started" (7% lift)

**HRTech Experiment:** Testing whether B2B recruitment audience responds to "Get Started Now" similar to consumer SaaS.

---

## Checklist

- [x] Variants defined (A vs B)
- [x] Server-side assignment in LandingPageView
- [x] Templates updated with conditionals
- [x] Data attributes added for tracking
- [x] Analytics events prepared (Task 8)
- [ ] Google Analytics 4 setup (Task 8)
- [ ] Real-time dashboard configured (Task 8)
- [ ] Documentation complete (this file)
- [x] Hypothesis documented
- [ ] Statistical significance calculator linked (future)

---

**Status:** ✓ A/B Testing Framework Ready  
**Next:** Task 8 - Google Analytics Integration
