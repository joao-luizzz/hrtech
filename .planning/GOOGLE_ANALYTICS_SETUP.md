# Google Analytics 4 Setup - Landing Page

**Date:** 2026-04-04  
**Status:** ✓ IMPLEMENTED  
**Measurement Version:** GA4 (Google Analytics 4)  
**Compliance:** LGPD-compliant (anonymized, no PII)

---

## Configuration

### 1. Environment Variable

Add to `.env`:
```bash
GA_MEASUREMENT_ID=G-XXXXXXXXXX  # Replace with your actual Measurement ID
```

**How to get Measurement ID:**
1. Create Google Analytics 4 property at https://analytics.google.com
2. Create web data stream
3. Measurement ID format: G-XXXXXXXXXX (10 characters after G-)

### 2. Django Settings

**File:** `hrtech/settings.py`

```python
GA_MEASUREMENT_ID = config('GA_MEASUREMENT_ID', default='')
```

**Default:** Empty string (GA disabled if not set)
**Behavior:** If GA_MEASUREMENT_ID not in environment, GA script not loaded

### 3. Template Integration

**File:** `core/templates/landing/base.html`

```html
<!-- Google Analytics 4 -->
{% if GA_MEASUREMENT_ID %}
    <script async src="https://www.googletagmanager.com/gtag/js?id={{ GA_MEASUREMENT_ID }}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());
        
        gtag('config', '{{ GA_MEASUREMENT_ID }}', {
            'allow_google_signals': false,  // LGPD: Disable Google Signals
            'anonymize_ip': true,           // LGPD: Anonymize IPs
            'cookie_flags': 'SameSite=None;Secure'
        });
    </script>
{% endif %}
```

---

## Events Tracked

### 1. CTA Click - `cta_click`

**Trigger:** User clicks CTA button

**Parameters:**
- `button_text` - Button label (string)
  - "Start Free Trial"
  - "Get Started Now"
  - "Schedule Demo"
  - "Book Demo"
  - "Watch Demo"
- `variant` - A/B test variant (string)
  - "A" (control)
  - "B" (test)
- `page_path` - Current page (string)
  - "/" (landing page)

**Implementation:**
```javascript
// Automatic click tracking on buttons with data-ab attribute
window.addEventListener('click', function(e) {
    const btn = e.target.closest('button[data-ab]');
    if (btn) {
        const buttonText = btn.textContent.trim();
        const variant = btn.getAttribute('data-variant') || '{{ ab_variant }}';
        gtag('event', 'cta_click', {
            'button_text': buttonText,
            'variant': variant,
            'page_path': window.location.pathname
        });
    }
});
```

**Buttons tracked:**
- ✓ Hero section: "Start Free Trial" or "Get Started Now"
- ✓ Hero section: "Watch Demo"
- ✓ CTA section: "Start Free Trial" or "Get Started Now"
- ✓ CTA section: "Schedule Demo" or "Book Demo"

**Data attributes:**
```html
<button data-ab="start-free">Start Free Trial</button>
<button data-ab="get-started">Get Started Now</button>
<button data-ab="schedule-demo">Schedule Demo</button>
<button data-ab="book-demo">Book Demo</button>
<button data-ab="watch-demo">Watch Demo</button>
```

### 2. Newsletter Signup - `newsletter_signup`

**Trigger:** User successfully subscribes to newsletter via HTMX form

**Parameters:**
- `page_path` - Current page (string)
- `variant` - A/B test variant (string)

**Implementation:**
```javascript
// Track on HTMX successful response
document.addEventListener('htmx:responseEnd', function(event) {
    if (event.detail.xhr.responseURL.includes('newsletter-signup')) {
        if (event.detail.xhr.status === 200) {
            gtag('event', 'newsletter_signup', {
                'page_path': window.location.pathname,
                'variant': '{{ ab_variant }}'
            });
        }
    }
});
```

**Form tracked:**
- ✓ Newsletter subscription form in footer/hero
- ✓ Fires only on successful (200) response
- ✓ Tracks which variant user saw when subscribing

### 3. Page View - Automatic

**Trigger:** Page load

**Parameters:**
- `page_title` - Page title (automatic)
- `page_path` - URL path (automatic)
- `page_location` - Full URL (automatic)

**Scope:** GA4 tracks page views automatically
**No additional implementation needed**

---

## Conversion Goals

### Goal 1: CTA Engagement

**Definition:** User clicks any CTA button
**Metric:** `cta_click` event count
**Target:** 8%+ CTR (clicks per 100 users)

**Dimensions:**
- By variant (A vs B)
- By button type
- By traffic source
- By device (mobile vs desktop)

### Goal 2: Newsletter Conversion

**Definition:** User subscribes to newsletter
**Metric:** `newsletter_signup` event count
**Target:** 2%+ conversion rate

**Dimensions:**
- By variant (A vs B)
- By referrer source
- By new vs returning user

### Goal 3: Demo Request (Future)

**Definition:** User books a demo (not yet implemented)
**Metric:** Demo booking conversion
**Target:** 1%+ conversion rate

---

## Dashboard Configuration

### Real-Time Dashboard (Monitor Live Data)

1. Go to Google Analytics → Reports → Real-time
2. Watch events as users interact with landing page
3. Useful for QA: verify events fire correctly

### Custom Report: CTA Performance by Variant

**Path:** Analytics → Reports → Exploration → Create New

**Configuration:**
- **Tab:** Dimensions
  - Rows: `Custom parameter: variant` (A or B)
  - Columns: `Custom parameter: button_text`
- **Values:** `Event count` (cta_click)
- **Filters:** `Page path = /` AND `Event name = cta_click`

**Expected output:**
```
Variant | Start Free Trial | Get Started Now | Schedule Demo | Book Demo | Total
   A    |       500        |        0        |      450      |     0     |  950
   B    |       0          |       520       |       0       |    480    | 1000
```

### A/B Test Report: Variant Comparison

**Configuration:**
- **Tab:** Metrics
  - Rows: `Custom parameter: variant`
  - Values: 
    - `Users` (impressions)
    - `Event count: cta_click` (clicks)
    - Calculated: `CTR = cta_click / Users`

**Analysis:**
- Variant B CTR vs Variant A CTR
- If Variant B > Variant A + 5%: Variant B wins
- If Variant A > Variant B + 5%: Variant A wins
- If difference < 5%: inconclusive (continue test)

### Newsletter Conversion Report

**Configuration:**
- **Tab:** Metrics
  - Rows: `Custom parameter: variant`
  - Values:
    - `Users` (unique visitors)
    - `Event count: newsletter_signup` (signups)
    - Calculated: `Conversion Rate = newsletter_signup / Users`

---

## LGPD Compliance Features

### 1. IP Anonymization
```python
'anonymize_ip': true
```
**Effect:** Last octet of IP address masked (e.g., 192.168.x.x → 192.168.x.0)
**Compliance:** LGPD Article 5 (personal data minimization)

### 2. Google Signals Disabled
```python
'allow_google_signals': false
```
**Effect:** No demographic/interest data from Google's network
**Compliance:** LGPD Article 7 (explicit consent)

### 3. Secure Cookies
```python
'cookie_flags': 'SameSite=None;Secure'
```
**Effect:** Cookies only sent over HTTPS, protected from CSRF
**Compliance:** Data in transit security

### 4. No PII Tracking
**Implementation:**
- ✓ Button text tracked (not user ID)
- ✓ No email address collected
- ✓ No personal device identifiers
- ✓ No behavioral profiles created

**Data minimization:**
- Event: `cta_click` → {button_text, variant, page_path}
- Event: `newsletter_signup` → {page_path, variant}
- User ID: GA Session ID (anonymous, encrypted)

### 5. Data Retention
**Default:** 14 months (GA4 default)
**Can be configured:** Admin → Property Settings → Data Retention → Month
**Compliance:** LGPD Article 17 (right to deletion)

---

## Testing Checklist

### 1. Local Development (DEBUG=True)

- [ ] GA script NOT loaded (GA_MEASUREMENT_ID empty in .env)
- [ ] Page loads normally
- [ ] No GA-related errors in console

### 2. QA Environment (With GA_MEASUREMENT_ID)

- [ ] GA script loads (check Network tab → gtag.js)
- [ ] GA4 initializes (check Console → `window.dataLayer` populated)
- [ ] Page view tracked (check Real-time → Active users)
- [ ] Click button → cta_click event appears in Real-time (within 1s)
- [ ] Fill newsletter form → newsletter_signup event appears in Real-time (after submit)

### 3. Verification Commands

```bash
# Check GA script in Network tab
curl -I https://yoursite.com | grep gtag

# Verify GA_MEASUREMENT_ID in page source
curl https://yoursite.com | grep GA_MEASUREMENT_ID

# Monitor Real-time in browser
# - Open Google Analytics
# - Reports → Real-time → Events
# - Click landing page buttons
# - Confirm cta_click events appear
```

### 4. Production Verification

- [ ] GA_MEASUREMENT_ID set in production environment (Render)
- [ ] Events fire on production landing page
- [ ] Real-time dashboard shows traffic
- [ ] No data collection errors in logs

---

## Privacy & Consent

### LGPD Compliance Status

**Current Implementation:** ✓ COMPLIANT

- [x] IP anonymization enabled
- [x] No Google Signals (no profiling)
- [x] Secure cookies only
- [x] No PII in event parameters
- [x] 14-month data retention
- [x] User can delete data (GA Data Deletion feature)

**Optional Enhancement:** Cookie Consent Banner
- If targeting EU (GDPR), consider consent banner
- For Brazilian users (LGPD), consent optional but recommended
- Implementation: Can use Simple Analytics or Plausible for privacy-first alternative

### Privacy Policy Update Required

**Add to privacy policy:**

> We use Google Analytics 4 to measure landing page engagement. We have configured GA to be LGPD-compliant:
> - IP addresses are anonymized
> - No personally identifiable information is collected
> - Google Signals are disabled
> - Cookies are secure (HTTPS only)
> - Retention period: 14 months

---

## Troubleshooting

### Issue: GA events not appearing in Real-time

**Checklist:**
1. [ ] GA_MEASUREMENT_ID is valid (format: G-XXXXXXXXXX)
2. [ ] GA_MEASUREMENT_ID set in environment (not hardcoded)
3. [ ] Page loads gtag.js script (Network tab)
4. [ ] window.dataLayer populated (Console)
5. [ ] Sufficient time passed (Real-time has 1s latency)
6. [ ] AdBlock not blocking GA

**Fix:**
- Disable AdBlock temporarily
- Open Incognito/Private mode (no extensions)
- Check Google Analytics Admin → Property → Streams → Web → Measurement ID matches

### Issue: Newsletter event not firing

**Checklist:**
1. [ ] Form submit returns HTTP 200
2. [ ] htmx:responseEnd listener attached
3. [ ] Response URL includes 'newsletter-signup'
4. [ ] Form has `hx-post="{% url 'newsletter-signup' %}"`

**Fix:**
- Check Network tab: POST to /api/newsletter-signup/ returns 200
- Check Console: No JavaScript errors
- Verify HTMX version supports htmx:responseEnd event

### Issue: CTA click event not firing

**Checklist:**
1. [ ] Button has `data-ab="*"` attribute
2. [ ] Button is within click event target scope
3. [ ] gtag function is defined (GA script loaded)

**Fix:**
- Verify button HTML: `<button data-ab="start-free">Start Free Trial</button>`
- Check Console: No errors in click handler
- Verify GA script loaded before button clicks

---

## Roadmap

### Phase 1: Foundation ✓
- [x] GA4 setup
- [x] LGPD compliance
- [x] Event tracking (CTA clicks, newsletter)
- [x] A/B variant tracking

### Phase 2: Analysis (Week 2-4)
- [ ] Collect 385+ impressions per variant
- [ ] Calculate CTR by variant
- [ ] Determine winner (Variant A or B)
- [ ] Document results

### Phase 3: Optimization (Week 5+)
- [ ] Implement winner at 100%
- [ ] Test new hypothesis
- [ ] Expand events (demo requests, form submissions)
- [ ] Integrate with CRM (Hubspot, Pipedrive)

### Phase 4: Advanced
- [ ] E-commerce tracking (if pricing changes)
- [ ] User ID tracking (after signup, optional)
- [ ] Cohort analysis (new vs returning)
- [ ] Attribution modeling (multi-touch)

---

## References

- **GA4 Documentation:** https://support.google.com/analytics/answer/10089681
- **LGPD Guide:** Lei Geral de Proteção de Dados (Law 13,709/2018)
- **Event Tracking Best Practices:** https://developers.google.com/analytics/devguides/collection/ga4/events

---

**Status:** ✓ Google Analytics 4 Configured  
**Measurement ID Variable:** GA_MEASUREMENT_ID (from environment)  
**Default:** Disabled (empty string) - No tracking in dev  
**Next:** Task 9 - Deployment Checklist
