# PlanO -- Privacy Policy

**Effective Date:** [DATE]
**Last Updated:** 5 April 2026
**Version:** 1.0
**Data Controller:** [COMPANY LEGAL NAME], [ADDRESS], Malta
**Data Protection Officer:** dpo@[DOMAIN]

This Privacy Policy explains what data we collect, why we collect it, how we use it, and your rights. It applies to all users of PlanO's website, applications, and services.

---

## 1. Who We Are

PlanO is operated by [COMPANY LEGAL NAME], a company registered in Malta under number [NUMBER]. For the purposes of the General Data Protection Regulation (EU) 2016/679 ("GDPR") and Maltese data protection law, we are the data controller.

**Data Protection Officer (DPO):** You can reach our DPO at dpo@[DOMAIN] for any data protection queries.

---

## 2. Data We Collect

### 2.1. Data You Provide

| Data Category | Examples | Purpose |
|---------------|----------|---------|
| **Account data** | Name, email, password (hashed), phone number | Account creation, authentication, communication |
| **Profile data** | Company name, role, location, preferences | Service customisation, Provider matching |
| **Floor plans and project data** | Uploaded images, drawn floor plans, room labels, measurements, service selections, cost estimates | Core service delivery |
| **Payment data** | Billing address, subscription tier | Payment processing (card details handled by Stripe; Bitcoin by BTCPay -- we never see full card numbers) |
| **Communication data** | Support messages, feedback, survey responses | Customer support, service improvement |

### 2.2. Data We Collect Automatically

| Data Category | Examples | Purpose |
|---------------|----------|---------|
| **Usage data** | Pages visited, features used, session duration, actions taken | Service improvement, analytics |
| **Device data** | Browser type, operating system, screen resolution, device identifiers | Compatibility, debugging |
| **Network data** | IP address, approximate location (city-level from IP) | Security, fraud prevention, regional pricing |
| **Log data** | Server logs, error reports, API request metadata | System reliability, debugging |

### 2.3. Data from Third Parties

| Source | Data | Purpose |
|--------|------|---------|
| **Supabase** (authentication) | Login events, session tokens | Authentication |
| **Stripe** (payments) | Transaction status, payment confirmations | Billing |
| **Vetted Providers** | Project status updates, completion confirmations | Platform coordination |

---

## 3. Legal Basis for Processing (GDPR Article 6)

| Legal Basis | Data | Explanation |
|-------------|------|-------------|
| **Contract performance** (Art. 6(1)(b)) | Account data, floor plans, project data, payment data | Necessary to provide PlanO's services to you |
| **Legitimate interest** (Art. 6(1)(f)) | Usage data, device data, log data | Service improvement, security, fraud prevention. Balanced against your privacy through data minimisation and pseudonymisation |
| **Consent** (Art. 6(1)(a)) | AI training opt-in, marketing emails, non-essential cookies | Only with your explicit, freely given consent, which you may withdraw at any time |
| **Legal obligation** (Art. 6(1)(c)) | Transaction records, invoices | Tax compliance, anti-money laundering regulations |

---

## 4. How We Use Your Data

4.1. **To provide PlanO's services:** Processing floor plans, generating measurements and estimates, matching you with Providers, managing your subscription.

4.2. **To improve PlanO:** Analysing usage patterns to improve features, fix bugs, and optimise performance. We use anonymised and aggregated data for this purpose.

4.3. **To communicate with you:** Transactional emails (receipts, project updates, subscription reminders), and marketing communications only with your consent.

4.4. **To ensure security:** Detecting and preventing fraud, abuse, and unauthorised access.

4.5. **AI model improvement:** Only with your explicit opt-in consent (see Section 7).

---

## 5. Data Sharing

### 5.1. We Share Data With:

| Recipient | Data Shared | Purpose | Safeguards |
|-----------|-------------|---------|------------|
| **Vetted Providers** (when you request an estimate) | Floor plan, project scope, contact details | To generate and deliver estimates | Provider Terms, data processing agreement |
| **Stripe** | Payment data | Payment processing | PCI-DSS Level 1 certified, EU data processing |
| **BTCPay Server** | Bitcoin transaction data | Payment processing | Self-hosted, no third-party data sharing |
| **Supabase** | Authentication data | User authentication | SOC2 certified, EU region hosting |
| **Hosting providers** | All data (encrypted at rest) | Infrastructure | EU-based servers, data processing agreements |

### 5.2. We Do NOT:

- Sell your personal data to anyone, ever.
- Share your floor plans or project data with advertisers.
- Provide your data to data brokers.
- Allow third parties to use your data for their AI training.

### 5.3. We May Disclose Data:

- When required by law, court order, or regulatory authority.
- To protect the rights, safety, or property of PlanO, our users, or the public.
- In connection with a merger, acquisition, or sale of assets (with 30 days' notice to you).

---

## 6. Cookies and Tracking

### 6.1. Essential Cookies (No Consent Required)

| Cookie | Purpose | Duration |
|--------|---------|----------|
| Session cookie | Authentication, keeping you logged in | Session |
| CSRF token | Security, preventing cross-site request forgery | Session |
| Cookie preference | Remembering your cookie choices | 12 months |

### 6.2. Analytics Cookies (Consent Required)

| Cookie | Purpose | Duration |
|--------|---------|----------|
| Usage analytics | Understanding how PlanO is used, improving features | 12 months |

6.3. We do NOT use advertising cookies or third-party tracking pixels.

6.4. You can manage cookie preferences at any time via the cookie banner or your account settings.

---

## 7. AI and Your Data

7.1. **Processing your floor plans.** When you upload a floor plan, our AI processes it to detect walls, rooms, doors, and windows. This processing is necessary to deliver PlanO's core service and is covered by our contractual legal basis (Art. 6(1)(b)).

7.2. **AI training is opt-in only.** We do not use your identifiable floor plans or project data to train our AI models unless you explicitly opt in via your account settings. This consent is covered by Art. 6(1)(a) GDPR.

7.3. **Anonymised data.** We may use fully anonymised, aggregated statistical data (e.g., average room sizes across all users in a region) to improve our measurement algorithms. This data cannot identify you or reconstruct your floor plans.

7.4. **Opt-in controls.** You can enable or disable AI training participation at any time in Settings > Privacy > AI Training. Disabling it takes effect immediately for future processing. It does not retroactively remove your data from models already trained.

7.5. **Automated decision-making.** PlanO uses automated processing to generate measurements and cost estimates. These are provided as informational tools, not binding decisions. You are not subject to decisions based solely on automated processing that produce legal effects or similarly significant effects (Art. 22 GDPR).

---

## 8. International Data Transfers

8.1. PlanO's servers are located in the European Union. We process and store your data within the EU wherever possible.

8.2. Where data is transferred outside the EEA (e.g., if a sub-processor operates outside the EU), we ensure adequate protection through:
- (a) European Commission adequacy decisions (Art. 45 GDPR).
- (b) Standard Contractual Clauses (Art. 46(2)(c) GDPR).
- (c) Supplementary measures as required by the CJEU Schrems II decision.

8.3. You may request a copy of the applicable transfer safeguards by contacting our DPO.

---

## 9. Data Retention

| Data Category | Retention Period | Reason |
|---------------|-----------------|--------|
| **Account data** | Duration of account + 30 days after deletion | Service provision, reactivation window |
| **Floor plans and project data** | Duration of account + 30 days | Service provision, data export window |
| **Payment records and invoices** | 7 years after transaction | Maltese tax law, VAT regulations |
| **Server logs** | 12 months | Security, debugging |
| **Usage analytics** | 24 months (anonymised after 12 months) | Service improvement |
| **Support correspondence** | 3 years after last contact | Quality assurance, dispute resolution |
| **Backup copies** | 90 days after deletion from active systems | Disaster recovery (encrypted, not accessible) |

---

## 10. Your Rights (GDPR Articles 15-22)

You have the following rights regarding your personal data. To exercise any of them, contact dpo@[DOMAIN] or use the controls in your account settings.

| Right | What It Means | How to Exercise |
|-------|---------------|-----------------|
| **Access** (Art. 15) | Request a copy of all data we hold about you | Account Settings > Privacy > Download My Data |
| **Rectification** (Art. 16) | Correct inaccurate data | Edit in account settings, or contact DPO |
| **Erasure** (Art. 17) | Request deletion of your data ("right to be forgotten") | Account Settings > Delete Account, or contact DPO |
| **Restriction** (Art. 18) | Limit how we process your data | Contact DPO |
| **Portability** (Art. 20) | Receive your data in a machine-readable format (JSON) | Account Settings > Privacy > Export My Data |
| **Object** (Art. 21) | Object to processing based on legitimate interest | Contact DPO |
| **Withdraw consent** (Art. 7(3)) | Withdraw consent for optional processing (AI training, marketing) | Account Settings > Privacy |
| **Complaint** | Lodge a complaint with a supervisory authority | Malta IDPC: https://idpc.org.mt |

**Response time:** We will respond to all data subject requests within 30 days, as required by GDPR. If a request is complex, we may extend this by up to 60 additional days, with notice to you.

---

## 11. Children

PlanO is not directed at children under 18. We do not knowingly collect data from anyone under 18. If we discover that we have, we will delete it promptly.

---

## 12. Security

12.1. We implement appropriate technical and organisational measures to protect your data, including:
- Encryption in transit (TLS 1.3) and at rest (AES-256).
- Access controls and authentication.
- Regular security audits.
- Incident response procedures.

12.2. **Breach notification.** In the event of a personal data breach that poses a risk to your rights, we will notify the Malta Information and Data Protection Commissioner (IDPC) within 72 hours and notify affected users without undue delay, as required by GDPR Articles 33-34.

---

## 13. Changes to This Policy

13.1. We may update this Privacy Policy. For material changes, we will:
- Notify you by email at least 30 days in advance.
- Post a summary of changes on our website.
- Update the "Last Updated" date above.

13.2. Minor changes (clarifications, formatting) may be made without notice.

---

## 14. Contact

**Data Controller:** [COMPANY LEGAL NAME], [ADDRESS], Malta
**Data Protection Officer:** dpo@[DOMAIN]
**General Inquiries:** privacy@[DOMAIN]

**Supervisory Authority:**
Office of the Information and Data Protection Commissioner (IDPC)
Floor 2, Airways House, High Street, Sliema SLM 1549, Malta
https://idpc.org.mt

**EU Online Dispute Resolution:** https://ec.europa.eu/odr

---

*This Privacy Policy is written in plain English. In the event of conflict between a translated version and this English version, the English version prevails.*
