# Business Continuity Plan (BCP)

**PlanO Pro Ltd** -- Malta Company Number [C-XXXXX]

**Version:** 1.0 | **Date:** [DATE] | **Classification:** CONFIDENTIAL

**Owner:** Hadrien Majoie (Technical), Ognyan Ignatov (Business)

**Review cycle:** Every 6 months or after any incident

---

## 1. Scope

1.1. This plan covers all systems required to operate the PlanO SaaS platform as described in the PlanO SaaS Brief and Project Definition documents.

1.2. Goal: maintain autonomous SaaS operations with zero human intervention under normal conditions and restore service within defined RTOs under failure conditions.

## 2. System Inventory and Recovery Targets

| System | Location | RTO | RPO | Priority |
|--------|----------|-----|-----|----------|
| Frontend (React + nginx) | Docker on GPU server | 1 hour | 0 (stateless, rebuilt from git) | P0 |
| Rasta ML engine (FastAPI) | Docker on GPU server | 2 hours | 0 (stateless) | P0 |
| Caddy reverse proxy + TLS | GPU server host | 30 min | 0 (config in git) | P0 |
| Supabase Auth | Supabase cloud (hosted) | N/A (vendor SLA) | N/A | P0 |
| Stripe payments | Stripe cloud (hosted) | N/A (vendor SLA) | N/A | P0 |
| BTCPay Server | Docker on GPU server | 4 hours | 24 hours (wallet backup) | P1 |
| Ollama + AI agents | GPU server | 4 hours | 0 (models re-pullable) | P1 |
| SQLite event bus | GPU server | 4 hours | 24 hours | P2 |
| Domain (hacking.eu) | Registrar: [REGISTRAR] | 24 hours | N/A | P0 |
| DNS (Cloudflare) | Cloudflare hosted | 1 hour (repoint) | N/A | P0 |
| Git repository | GitHub (memorylost731) | 0 (always available) | 0 | P0 |

## 3. Infrastructure Failure Scenarios

### 3.1. GPU Server Total Failure

**Trigger:** Hardware failure, hosting provider issue, power loss.

**Automated response:**
- Self-healing watchdog detects service down within 5 minutes
- Uptime monitoring (e.g., UptimeRobot) alerts both founders via SMS + email

**Manual recovery procedure:**
1. SSH to GPU server, diagnose. If hardware: contact hosting provider.
2. If unrecoverable within RTO: deploy to fallback (see 3.1.1).

**3.1.1. Fallback deployment (pre-configured):**
- [ ] Maintain a `docker-compose.yml` and `.env.production` in the git repo capable of deploying the full stack to any machine with an NVIDIA GPU
- [ ] Pre-register a Hetzner/OVH account with a GPU instance on standby (not running, zero cost)
- [ ] DNS failover: update Cloudflare A record to new IP (scripted, < 5 minutes)
- [ ] Estimated total recovery: 1-2 hours from decision to deploy

### 3.2. Domain Compromise (hacking.eu)

**Trigger:** Registrar account hijacked, domain expired, legal seizure.

**Prevention:**
- [ ] Enable registrar lock (clientTransferProhibited)
- [ ] 2FA on registrar account (hardware key preferred)
- [ ] Register domain for maximum available years (5-10)
- [ ] Register a backup domain: [plano-app.com] or [planopro.eu], pre-configured in Cloudflare

**Recovery:**
1. If hijacked: contact registrar abuse team + ICANN dispute (UDRP). Timeline: days to weeks.
2. Immediate: switch all services to backup domain. Update Stripe webhook URLs, Supabase redirect URLs, and BTCPay callbacks.
3. Notify customers via email (Resend transactional).

### 3.3. Caddy/Docker/Application Crash

**Automated recovery:**
- Docker containers configured with `restart: always`
- Caddy auto-restarts via systemd
- Self-healing watchdog checks every 5 minutes, restarts failed services

**If auto-recovery fails:**
1. SSH to server, run `docker compose down && docker compose up -d`
2. Check logs: `docker compose logs --tail=100`
3. If persistent: rebuild containers from git (`docker compose build --no-cache`)

### 3.4. Payment Processor Failure

**Stripe outage:**
- Stripe SLA: 99.99% uptime. Outages are rare and short.
- During outage: display "Payment temporarily unavailable" banner. Queue payment intents.
- Stripe webhooks have built-in retry (up to 72 hours).

**BTCPay outage:**
- Non-critical (supplementary payment method). Display "Card payment only" temporarily.
- Recovery: restart BTCPay container.

**Stripe account suspension:**
- [ ] Maintain a second Stripe account (different legal entity or Stripe Atlas) as cold backup
- [ ] Alternative: integrate Paddle as backup processor (handles EU VAT)

### 3.5. Data Backup and Recovery

**What is backed up:**

| Data | Method | Frequency | Location | Retention |
|------|--------|-----------|----------|-----------|
| Git repo (all code + config) | GitHub | Every push | GitHub cloud | Permanent |
| SQLite databases | Automated rsync | Daily | [BACKUP_SERVER] | 90 days |
| BTCPay wallet + config | Docker volume backup | Daily | Encrypted off-site | Permanent |
| Supabase data | Supabase automatic | Continuous | Supabase cloud | Per plan |
| Customer uploads (floor plans) | rsync to backup | Daily | [BACKUP_SERVER] | 1 year |
| AI agent outputs | Append-only logs | Continuous | GPU server + backup | Permanent |

**Recovery test:** [ ] Schedule quarterly backup restore test. Document results.

### 3.6. Physical Disaster (Fire, Flood, Theft at Fort Cambridge)

3.6.1. GPU server is NOT at Fort Cambridge. It is at a hosting provider facility. Physical disaster at the founders' premises does not affect server operations.

3.6.2. Risk: loss of laptops containing SSH keys and local development environments.

**Mitigation:**
- All code is in GitHub (nothing exists only locally)
- SSH keys are recoverable from credential escrow (see Document 05)
- Development environment is reproducible from `package.json` + `docker-compose.yml`
- [ ] Both founders maintain encrypted USB backup of SSH keys and critical credentials at a separate physical location

### 3.7. Cyber Incident Response

**Ransomware:**
1. Isolate: disconnect server from network immediately
2. Assess: determine entry point and scope
3. Do NOT pay ransom
4. Restore from clean backups (see 3.5)
5. Rotate ALL credentials (SSH keys, API keys, database passwords)
6. Notify: MDIA (Malta Digital Innovation Authority) within 72 hours if personal data affected (GDPR Article 33)
7. Notify affected users without undue delay if high risk to their rights (GDPR Article 34)

**Data breach:**
1. Contain and assess scope
2. Document: what data, how many users, what happened
3. GDPR notification: Malta IDPC (Information and Data Protection Commissioner) within 72 hours
4. User notification if high risk
5. Post-incident: root cause analysis, implement fixes, update this BCP

---

## 4. Testing Schedule

| Test | Frequency | Owner |
|------|-----------|-------|
| Backup restore drill | Quarterly | Hadrien |
| Failover deployment to backup | Annually | Hadrien |
| Domain failover to backup domain | Annually | Hadrien |
| Credential escrow access verification | Every 6 months | Both founders |
| Full BCP review and update | Every 6 months | Both founders |

---

**Approved:**

| Party | Signature | Date |
|-------|-----------|------|
| Ognyan Ignatov | _________________ | [DATE] |
| Hadrien Majoie | _________________ | [DATE] |
