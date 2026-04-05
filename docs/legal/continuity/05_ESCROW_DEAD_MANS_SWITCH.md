# Escrow & Dead Man's Switch Protocol

**PlanO Pro Ltd** -- Malta Company Number [C-XXXXX]

**Version:** 1.0 | **Date:** [DATE] | **Classification:** CONFIDENTIAL

---

## 1. Purpose

1.1. Ensure that if both founders become simultaneously unavailable, a designated successor can access all credentials needed to maintain PlanO operations.

1.2. Prevent permanent loss of access to infrastructure, domains, payment processors, and customer data.

## 2. Credential Escrow

### 2.1. Escrow Method

**Primary:** A hardware-encrypted USB drive (e.g., Apricorn Aegis or IronKey) stored in a bank safe deposit box in Malta.

**Secondary:** A KeePass or Bitwarden vault exported as an encrypted `.kdbx` file, stored on a separate encrypted USB at a second physical location (e.g., a trusted family member's safe, or a second bank).

**Tertiary:** A sealed paper document in a lawyer's custody containing the master decryption passphrase for the primary USB.

### 2.2. Escrow Contents

| Credential | Type | Notes |
|-----------|------|-------|
| GPU server SSH private key | File (.pem/.key) | Plus server IP and port |
| GPU server sudo password | Text | |
| Domain registrar login | URL + email + password + 2FA recovery | [REGISTRAR_NAME] |
| Cloudflare login | Email + password + 2FA recovery | |
| Stripe dashboard login | Email + password + 2FA recovery | Both Stripe accounts if backup exists |
| BTCPay admin login | URL + username + password | |
| BTCPay wallet seed phrase | 12/24 words | CRITICAL -- loss = loss of BTC funds |
| Supabase dashboard login | Email + password | |
| GitHub account | Username + password + 2FA recovery codes | Or a deploy key for the repo |
| Resend API key | Text | For transactional email |
| BDO Malta contact | Name, phone, email, engagement reference | |
| Company bank details | Bank, IBAN, online banking credentials | |
| Backup domain registrar login | If backup domain registered | |
| Ollama / AI agent config | Location of config files on server | |

### 2.3. Update Schedule

- [ ] Escrow contents reviewed and updated every 6 months (January and July)
- [ ] After any credential rotation, escrow must be updated within 7 days
- [ ] Both founders verify escrow accessibility annually

## 3. Dead Man's Switch

### 3.1. Mechanism

A dead man's switch ensures that if no founder checks in for a defined period, credentials are released to a designated successor.

**Implementation options (choose one):**

**Option A -- Manual (simplest, recommended for now):**
- Each founder sends a monthly "alive" email to [SUCCESSOR_EMAIL] with a pre-agreed subject line
- If no email received for 30 consecutive days, the successor contacts the other founder
- If neither founder responds within 7 additional days, the successor opens the escrow

**Option B -- Automated (future):**
- A cron job or cloud function sends a check-in prompt to both founders weekly
- If no response for 30 days, an automated email with escrow access instructions is sent to the designated successor
- Service: use a dead man's switch provider (e.g., Google Inactive Account Manager, or a self-hosted solution)

**Option C -- Lawyer-held (most formal):**
- A Malta-based lawyer holds sealed escrow access instructions
- Standing instructions: if neither founder contacts the lawyer for 60 days and cannot be reached, the lawyer releases escrow to the designated successor
- Cost: [EUR_AMOUNT] annual retainer

### 3.2. Designated Successor

| Role | Name | Relationship | Contact | Backup |
|------|------|-------------|---------|--------|
| Primary successor | [NAME] | [RELATIONSHIP] | [PHONE, EMAIL] | [BACKUP_CONTACT] |
| Secondary successor | [NAME] | [RELATIONSHIP] | [PHONE, EMAIL] | |

**Successor requirements:**
- Trustworthy, reachable, basic computer literacy
- NOT required to operate the business -- only required to provide access to a technical contractor
- Receives a sealed instruction letter explaining: what PlanO is, who BDO is, who the technical backup contractor is, and what to do (essentially: open escrow, call BDO, call technical contractor)

### 3.3. Successor Instruction Letter

A sealed letter to the successor should contain:

1. "PlanO Pro Ltd is a Malta software company. It runs automatically. Your job is to ensure the following people have access to keep it running."
2. BDO contact details and engagement reference number
3. Technical backup contractor contact details (from Document 02)
4. Location of escrow USB and passphrase
5. "Open the escrow USB and provide the technical contractor with the SSH key and server credentials. Provide BDO with confirmation that you are acting as emergency contact."
6. Contact details for each founder's lawyer and executor

## 4. Infrastructure Auto-Maintenance

### 4.1. Already Automated

| System | Auto-mechanism | Human intervention needed? |
|--------|---------------|---------------------------|
| Docker containers | `restart: always` policy | No |
| Caddy TLS certificates | ACME auto-renewal (Let's Encrypt) | No |
| Self-healing watchdog | systemd timer, 5-min checks | No |
| AI agent cycles | systemd user timers (2h/4h/6h/12h) | No |
| Stripe subscription billing | Stripe handles automatically | No |
| Supabase auth | Cloud-hosted, managed | No |

### 4.2. Requires Human Action (Automate or Pre-Pay)

| System | Risk | Mitigation |
|--------|------|------------|
| Domain renewal | Expiry = total outage | [ ] Register for 10 years. Enable auto-renew with valid payment method. |
| GPU server rental | Non-payment = shutdown | [ ] Pre-pay 12 months or ensure auto-billing on a company card with sufficient limit. Set up billing alerts. |
| Cloudflare | Account suspension | [ ] Free tier, low risk. Ensure valid email on account. |
| Stripe account | Requires identity verification updates periodically | [ ] Ensure BDO Nominee is listed as account representative so Stripe can contact them. |
| BTCPay Server | Bitcoin node sync can break after major updates | Low priority. Restart container usually fixes. |

### 4.3. Escalation Path (When Self-Healing Fails)

1. Self-healing watchdog attempts auto-restart (5 min cycle)
2. If 3 consecutive failures: watchdog sends alert email to both founders
3. If no founder responds in 24 hours: alert sent to designated successor
4. Successor contacts technical backup contractor
5. Contractor uses escrow credentials to diagnose and fix

[ ] Implement step 3 (successor alerting) as an automated escalation.

---

**Approved:**

| Party | Signature | Date |
|-------|-----------|------|
| Ognyan Ignatov | _________________ | [DATE] |
| Hadrien Majoie | _________________ | [DATE] |
