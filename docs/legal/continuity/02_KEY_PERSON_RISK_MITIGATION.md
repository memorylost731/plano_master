# Key Person Risk Mitigation Plan

**PlanO Pro Ltd** -- Malta Company Number [C-XXXXX]

**Version:** 1.0 | **Date:** [DATE] | **Classification:** CONFIDENTIAL

---

## 1. Purpose

1.1. PlanO Pro Ltd has two founders and one nominee director. If any of these individuals become unavailable, the business must continue operating autonomously. This document maps critical knowledge, defines succession for each role, and establishes cross-training requirements.

## 2. Critical Knowledge Map

### 2.1. Hadrien Majoie (40% -- Technical Founder)

| Knowledge Area | Criticality | Documented? | Autonomous? |
|---------------|-------------|-------------|-------------|
| Server infrastructure (GPU, Docker, Caddy) | CRITICAL | Partial (SaaS Brief) | Yes (self-healing) |
| AI model training and deployment | HIGH | Partial | Yes (agents run on timers) |
| Rasta ML engine (floor plan detection) | CRITICAL | Code in git | Yes (API, no human needed) |
| React frontend development | HIGH | Code in git | Yes (deployed, static) |
| SSH keys and server access | CRITICAL | No | No |
| Domain/DNS management | CRITICAL | No | Partial (auto-renew) |
| BTCPay Server administration | MEDIUM | No | Yes (runs autonomously) |
| Stripe integration | MEDIUM | Code in git | Yes (webhooks) |
| Security and incident response | HIGH | This document | No |

### 2.2. Ognyan Ignatov (60% -- Strategy/Business Founder)

| Knowledge Area | Criticality | Documented? | Autonomous? |
|---------------|-------------|-------------|-------------|
| Business strategy and market positioning | HIGH | Project Definition PDF | N/A |
| Contractor relationships (Malta/Bulgaria) | HIGH | No | No |
| Pricing strategy | MEDIUM | SaaS Brief | Yes (AI Pricing Analyst) |
| Marketing direction | MEDIUM | Business Plan | Yes (AI agents) |
| Financial planning and budgeting | HIGH | No | Partial |
| Legal/regulatory coordination with BDO | HIGH | No | No |
| Bulgarian market knowledge | HIGH | Business Plan | Partial |

### 2.3. BDO Nominee Director

| Knowledge Area | Criticality | Documented? | Autonomous? |
|---------------|-------------|-------------|-------------|
| Malta Companies Act compliance | HIGH | BDO internal | N/A |
| Annual filings and statutory obligations | CRITICAL | BDO engagement letter | N/A |
| Company bank account signatory | CRITICAL | Bank mandate | No |
| Tax refund applications (5% rate) | HIGH | BDO process | N/A |

## 3. Incapacity Scenarios and Response

### 3.1. Hadrien Incapacitated (Tech Founder)

**Immediate (0-7 days):**
- All systems continue running autonomously (self-healing watchdog, Docker restart policies, Caddy auto-TLS)
- AI agents continue their cycles (systemd timers)
- Stripe and Supabase are cloud-hosted, unaffected

**Short-term (7-30 days):**
- Ogi accesses credential escrow (see Document 05) to obtain SSH keys and admin passwords
- [ ] Ogi completes cross-training checklist (Section 5) to handle basic server operations
- [ ] Engage a pre-identified freelance DevOps contractor for emergency support

**Long-term (30+ days):**
- [ ] Engage a managed DevOps service (e.g., [PROVIDER]) under NDA to maintain infrastructure
- [ ] Consider migrating to fully managed cloud (AWS/GCP) to reduce single-person dependency
- Ogi exercises full voting control (60%) for all business decisions

**Pre-identified technical backup contacts:**
- [ ] [DEVOPS_CONTRACTOR_1]: [NAME], [CONTACT], NDA signed [DATE]
- [ ] [DEVOPS_CONTRACTOR_2]: [NAME], [CONTACT], NDA signed [DATE]

### 3.2. Ogi Incapacitated (Strategy Founder)

**Immediate (0-30 days):**
- All systems continue autonomously. No business decision is needed for daily operations.
- Hadrien exercises all shareholder votes (holds 40%, but is sole active shareholder for operational decisions)
- BDO Nominee continues statutory duties independently

**Short-term (30-90 days):**
- Hadrien coordinates with BDO for any required filings, bank transactions
- AI agents (CEO Agent, Sales Hunter, Marketing Strategist) continue executing strategy
- [ ] Hadrien has power of attorney or written instructions to act as sole operational decision-maker during Ogi's absence (see Shareholders Agreement amendment recommendation below)

**Long-term (90+ days):**
- Evaluate whether to hire a business development contractor
- Shareholders Agreement Section 7 (Good Leaver) governs share treatment if permanent

### 3.3. BOTH Founders Incapacitated Simultaneously

**This is the highest risk scenario. Mitigation must be pre-configured.**

**Automated continuity (0-30 days):**
- SaaS platform runs autonomously: frontend serves, API processes, payments collect, agents run
- Stripe continues collecting subscription revenue
- Domain auto-renews, TLS auto-renews (Caddy)
- Self-healing watchdog restarts crashed services

**Dead man's switch activation (30 days):**
- Credential escrow released to designated successor (see Document 05)
- [ ] Pre-designated emergency contact: [NAME], [RELATIONSHIP], [CONTACT]
- This person receives: server access, domain registrar access, Stripe dashboard access, BDO contact details, and a copy of this BCP

**Legal continuity:**
- BDO Nominee remains as director and can take necessary corporate actions
- BDO cannot make Reserved Matter decisions without shareholder approval -- this is a limitation
- [ ] RECOMMENDATION: Amend Shareholders Agreement to add an emergency clause granting BDO Nominee limited authority to maintain operations (pay server bills, renew subscriptions, maintain employee/contractor agreements) for up to 180 days if both shareholders are unreachable

### 3.4. BDO Nominee Resigns or BDO Withdraws

**Prevention:**
- Maintain good relationship with BDO Malta
- Pay all BDO fees on time
- Keep statutory filings current

**Recovery:**
1. BDO engagement letters typically require 30-90 days notice
2. During notice period: appoint replacement nominee from another licensed Malta fiduciary (e.g., CSB Group, Fenech & Fenech, KPMG Malta, Deloitte Malta)
3. [ ] Maintain a shortlist of 2 alternative nominee providers with initial contact made
4. Bank mandate must be updated with new signatory -- allow 2-4 weeks for Malta bank procedures

## 4. Credential Escrow Summary

All credentials listed below must be stored in the escrow system described in Document 05.

| Credential | Held By | In Escrow? |
|-----------|---------|------------|
| GPU server SSH key | Hadrien | [ ] |
| GPU server sudo password | Hadrien | [ ] |
| Domain registrar login | Hadrien | [ ] |
| Cloudflare account | Hadrien | [ ] |
| Stripe dashboard | Both | [ ] |
| BTCPay admin | Hadrien | [ ] |
| Supabase dashboard | Both | [ ] |
| GitHub repo access | Hadrien | [ ] |
| BDO contact + engagement letter | Both | [ ] |
| Company bank account details | BDO + Both | [ ] |
| Resend (email) API key | Hadrien | [ ] |

## 5. Cross-Training Checklist

### 5.1. Ogi Must Learn (Minimum)

- [ ] How to SSH into GPU server (key-based auth)
- [ ] How to restart Docker containers (`docker compose restart`)
- [ ] How to check service health (`docker ps`, `curl` health endpoints)
- [ ] How to update DNS in Cloudflare (change A record)
- [ ] How to access Stripe dashboard and issue refunds
- [ ] How to access Supabase dashboard
- [ ] How to read server logs (`docker compose logs`)
- [ ] Location of all backups and how to trigger restore

**Target completion:** [DATE + 30 DAYS]

### 5.2. Hadrien Must Learn (Minimum)

- [ ] BDO engagement terms and contact procedures
- [ ] Malta Companies Act annual filing requirements (deadlines, forms)
- [ ] Company bank account access and payment procedures
- [ ] Contractor relationship list (Malta, Bulgaria) with contacts
- [ ] Financial model and unit economics
- [ ] How to submit VAT returns or instruct BDO to do so

**Target completion:** [DATE + 30 DAYS]

---

**Approved:**

| Party | Signature | Date |
|-------|-----------|------|
| Ognyan Ignatov | _________________ | [DATE] |
| Hadrien Majoie | _________________ | [DATE] |
