# Autonomous Operations Readiness Checklist

**PlanO Pro Ltd** -- Malta Company Number [C-XXXXX]

**Version:** 1.0 | **Date:** [DATE] | **Classification:** CONFIDENTIAL

---

## 1. The 30-Day Test

**Question:** Can PlanO survive 30 days with zero human intervention -- no founder touches a keyboard, no one answers an email, no one makes a decision?

### 1.1. System-by-System Scoring

| System | Autonomous? | 30-Day Survival | Score | Blocker |
|--------|------------|-----------------|-------|---------|
| Frontend (React + nginx) | Yes | Survives | 10/10 | None |
| Rasta ML engine | Yes | Survives | 10/10 | None |
| Caddy TLS + reverse proxy | Yes | Survives (auto-renew) | 10/10 | None |
| Docker containers | Yes | Survives (restart: always) | 9/10 | Disk full could kill it |
| Self-healing watchdog | Yes | Survives (systemd) | 9/10 | No escalation if it fails itself |
| AI agent cycles | Yes | Survives (systemd timers) | 8/10 | Ollama model may need re-pull after OOM |
| Stripe payments | Yes | Survives | 10/10 | Payment method expiry (yearly risk) |
| Supabase auth | Yes | Survives | 10/10 | None (cloud-hosted) |
| BTCPay Server | Mostly | Survives | 7/10 | Bitcoin node can desync |
| Domain + DNS | Yes | Survives | 10/10 | Only if auto-renew is on and paid |
| SSL certificates | Yes | Survives (Caddy ACME) | 10/10 | None |
| Email (Resend) | Yes | Survives | 9/10 | Free tier limits (100/day) |
| Customer support | Partial | Degrades | 4/10 | No human escalation path |
| New feature development | No | Paused | 0/10 | Expected -- not a survival issue |
| Legal/compliance | No | Deferred | 3/10 | BDO handles statutory, but no shareholder input |
| Financial (bank, VAT) | Partial | Survives 30 days | 6/10 | No invoices generated, no VAT filed |

**Overall 30-day autonomy score: 78/100**

**Verdict:** PlanO survives 30 days of zero human intervention for core SaaS operations (users can sign up, use the tool, and pay). Revenue collection continues. The business does not die.

**What degrades:** Customer support, new feature releases, financial administration, and edge-case infrastructure recovery.

### 1.2. Critical Failures That Could Kill a 30-Day Unattended Run

| Failure | Probability (30 days) | Impact | Mitigation |
|---------|----------------------|--------|------------|
| GPU server hardware failure | Low (~2%) | Total outage | Pre-configured failover (BCP Section 3.1.1) |
| Disk full (logs, uploads) | Medium (~10%) | Services crash | [ ] Configure log rotation, disk space alerts |
| Ollama OOM kills | Medium (~15%) | AI agents stop | [ ] Set memory limits, auto-restart on OOM |
| Domain expiry | Near zero | Total outage | [ ] Register 10 years, auto-renew on |
| Stripe payment method expiry | Near zero (30 days) | Revenue stops | [ ] Use company card, check expiry annually |
| DDoS attack | Low (~5%) | Temporary outage | [ ] Cloudflare free tier provides basic DDoS protection |
| Hosting provider billing failure | Low (~3%) | Server shutdown | [ ] Pre-pay or ensure auto-billing works |

## 2. Minimum Human Intervention Required

### 2.1. Monthly

| Task | Time | Who | Can Be Automated? |
|------|------|-----|-------------------|
| Check server health dashboard | 15 min | Hadrien | Yes (automated alerts replace this) |
| Review Stripe revenue and chargebacks | 15 min | Ogi | Partially (Stripe sends alerts) |
| Dead man's switch check-in email | 2 min | Both | No (that is the point) |
| Review AI agent outputs for quality | 30 min | Ogi | No (judgment call) |
| **Total monthly** | **~1 hour** | | |

### 2.2. Quarterly

| Task | Time | Who | Can Be Automated? |
|------|------|-----|-------------------|
| Backup restore test | 1 hour | Hadrien | Partially |
| Escrow contents review | 30 min | Both | No |
| Insurance policy review | 30 min | Ogi | No |
| Review and respond to customer feedback | 1 hour | Ogi | Partially (AI triage) |
| Update dependencies and security patches | 2 hours | Hadrien | Partially (Dependabot) |
| **Total quarterly** | **~5 hours** | | |

### 2.3. Annually

| Task | Time | Who | Can Be Automated? |
|------|------|-----|-------------------|
| BDO coordination: annual return, audit | 4 hours | Both + BDO | No |
| VAT returns (if applicable) | 2 hours | BDO | BDO handles |
| Key person insurance review and renewal | 1 hour | Ogi | No |
| Domain renewal verification | 15 min | Hadrien | Yes (if multi-year) |
| Update will schedules (digital assets) | 1 hour | Both | No |
| Pricing review | 2 hours | Ogi | Partially (AI Pricing Analyst) |
| **Total annually** | **~10 hours** | | |

### 2.4. Summary

**Minimum annual human time to keep PlanO alive: approximately 30 hours/year (2.5 hours/month).**

This is consistent with the "fully autonomous SaaS" goal. The business does not require anyone's full-time attention to operate.

## 3. Automation Roadmap (Reduce the 30 Hours Further)

| Current Manual Task | Automation Plan | Priority | Effort |
|--------------------|----------------|----------|--------|
| Server health monitoring | Uptime monitoring + PagerDuty/email alerts | HIGH | 2 hours to set up |
| Log rotation and disk management | `logrotate` + Docker prune cron | HIGH | 1 hour |
| Dependency security updates | Dependabot + auto-merge for patch versions | MEDIUM | 2 hours |
| Customer support triage | AI Support Agent already exists; add email integration | MEDIUM | 4 hours |
| Backup restore verification | Scripted restore test with pass/fail alert | LOW | 4 hours |
| Financial reporting | Stripe revenue dashboard + automated monthly email | LOW | 2 hours |

**After automation roadmap:** Minimum human time drops to approximately 15-20 hours/year, almost entirely legal/compliance/insurance tasks that cannot be automated.

## 4. Readiness Checklist (Pre-Launch)

Before declaring PlanO "autonomous-ready," complete the following:

| Item | Status | Owner |
|------|--------|-------|
| [ ] Docker restart policies set to `always` for all containers | | Hadrien |
| [ ] Self-healing watchdog running and tested | | Hadrien |
| [ ] Log rotation configured (prevent disk full) | | Hadrien |
| [ ] Domain registered for 5+ years with auto-renew | | Hadrien |
| [ ] Stripe billing on company card with 12+ month expiry | | Ogi |
| [ ] GPU server pre-paid or auto-billed reliably | | Both |
| [ ] Uptime monitoring configured (UptimeRobot or similar) | | Hadrien |
| [ ] Backup cron job running and tested | | Hadrien |
| [ ] Credential escrow created and stored | | Both |
| [ ] Dead man's switch activated (monthly check-in) | | Both |
| [ ] Designated successor briefed and has sealed instructions | | Both |
| [ ] BDO Nominee has current contact details for both founders | | Both |
| [ ] Failover deployment tested on backup infrastructure | | Hadrien |
| [ ] All insurance policies bound | | Both |
| [ ] Cross-training checklists completed (Document 02) | | Both |
| [ ] Wills updated with PlanO share clauses (Document 04) | | Both |

**Target: all items completed by [DATE + 90 DAYS]**

---

**Approved:**

| Party | Signature | Date |
|-------|-----------|------|
| Ognyan Ignatov | _________________ | [DATE] |
| Hadrien Majoie | _________________ | [DATE] |
