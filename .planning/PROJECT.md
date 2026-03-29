# PROJECT: HRTech ATS - AI Interview Assistant

**Status:** Active | **Version:** 1.0 | **Last Updated:** 2025-03-29

## 🎯 Vision & Problem Statement

We are building a **modern, high-performance Applicant Tracking System (ATS)** for HR departments to automate resume processing and empower recruiters with AI-driven insights while strictly maintaining **LGPD compliance** and data privacy.

**Core Problem:** Traditional resume screening is manual, time-consuming, and error-prone. Recruiters spend hours reviewing resumes and preparing interview questions, diverting focus from the human aspect of hiring.

**Our Solution:** Intelligent automation that handles resume processing, skill extraction, skill-gap analysis, and now **AI-powered interview question generation**.

---

## 📊 Current State (Stabilized Core)

✅ **Resume Processing Pipeline**
- Asynchronous CV uploads to AWS S3
- PDF text extraction with pdfplumber/OCR
- PII masking for LGPD compliance
- Skill parsing via OpenAI

✅ **Data Storage & Matching**
- PostgreSQL for structured data (candidates, jobs, parsed skills)
- Neo4j Graph Database for skill relationships and gap calculation
- Redis for caching and Celery broker

✅ **Frontend & UX**
- Django templates with HTMX for reactive UI
- Role-based access control (Recruiter, Admin, Staff)
- Candidate profile views with skill gap visualization

✅ **Infrastructure**
- Celery for async background tasks
- AWS S3 for file storage with presigned URLs
- Render for CI/CD deployment
- Upstash for Redis in production

---

## 🚀 Immediate Goal: Phase 7 - AI Interview Assistant

**Objective:** Build an AI-powered Interview Assistant that generates 3 highly personalized technical interview questions based on candidate skill gaps, helping non-technical recruiters assess technical candidates effectively.

**Scope:**
- Recruiter-only feature (role-based access)
- Integrated into candidate profile view
- Questions generated on-demand via OpenAI API
- Persistent storage in PostgreSQL (audit trail)
- Error resilience and cost optimization

**Success Criteria:**
- Recruiters can generate interview questions with 1 click
- Questions are cached to optimize API costs
- LGPD compliance maintained (audit trail, no PII exposure)
- ~80% test coverage for new module
- Robust error handling and user feedback

---

## 🏗️ Architecture Principles

1. **Service Layer Isolation** — Separate business logic (interview_service) from views
2. **Neo4j Integration** — Query skill gaps to inform question generation
3. **Error Resilience** — Graceful degradation with user-friendly error messages
4. **Cost Optimization** — Caching + smart retry strategies to minimize OpenAI API calls
5. **Audit & Compliance** — All question generation tracked with user + timestamp
6. **LGPD Privacy** — No candidate PII exposed to OpenAI; masked data only

---

## 📋 Stakeholders

- **Product:** Non-technical HR department users
- **Tech Lead:** Oversees architecture and compliance
- **Recruiters:** Primary users (generating questions)
- **Data Privacy:** LGPD compliance officer
- **Budget:** Cost control on OpenAI API usage

---

## 🔗 Key Dependencies

- **Django 5.0** — Web framework
- **PostgreSQL 15+** — Primary database
- **Neo4j AuraDB** — Graph database for skill gaps
- **OpenAI GPT-4o-mini** — Question generation
- **Celery** — Async task queue
- **HTMX** — Frontend interactivity
- **unittest.mock** — Testing framework

---

## ⚠️ Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| OpenAI API cost overruns | Implement caching + daily budget alerts |
| API timeouts/failures | 15s timeout + circuit breaker pattern |
| LGPD compliance violations | Audit trail + automatic PII masking |
| Discriminatory questions | Bias detection filter + legal review |
| Database integrity | Transactional saves only on success |

---

## 📅 Timeline

- **Phase 7 Duration:** 1 milestone (coarse-grained phases)
- **Execution Model:** Parallel plan execution
- **Testing Target:** 80% coverage
- **Deployment:** Incremental with verification gates

---

## 🔐 Compliance & Security

- **LGPD Compliance:** Audit trails, data retention policies, right-to-deletion
- **Auth:** Django staff/recruiter role checks
- **Secrets:** All API keys via environment variables (python-decouple)
- **Logging:** LGPD-safe logging (no PII or sensitive data)
- **Data Handling:** All candidate data masked before API calls

---

## 📚 Reference Documents

- `.planning/codebase/STACK.md` — Technology stack details
- `.planning/codebase/ARCHITECTURE.md` — Existing system architecture
- `.planning/codebase/CONCERNS.md` — Known issues and technical debt
- `.planning/research/AI_INTERVIEW_ASSISTANCE_RESEARCH.md` — Research on best practices
- `.planning/config.json` — Workflow configuration
