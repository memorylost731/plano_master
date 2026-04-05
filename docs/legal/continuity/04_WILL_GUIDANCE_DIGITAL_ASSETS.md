# Last Will & Testament Guidance -- Digital Assets and PlanO Shares

**PlanO Pro Ltd** -- Malta Company Number [C-XXXXX]

**Version:** 1.0 | **Date:** [DATE] | **Classification:** CONFIDENTIAL

**DISCLAIMER:** This document provides guidance only. Each founder must engage their own lawyer to draft an enforceable will. Malta-resident founders use Malta law; Ogi should also consult Bulgarian counsel.

---

## 1. Purpose

1.1. Ensure that PlanO shares and digital assets are handled properly upon a founder's death, minimizing business disruption during estate settlement.

## 2. Recommended Will Clauses for PlanO Shares

### 2.1. Specific Bequest of Shares

Each founder's will should include a specific clause for PlanO shares, separate from the general residuary estate:

> "I bequeath my [NUMBER] ordinary shares in PlanO Pro Ltd (Malta Company Number [C-XXXXX]) to [BENEFICIARY NAME/RELATIONSHIP], subject to the Company's right of first refusal as set out in the Shareholders Agreement dated [DATE]."

### 2.2. Right of First Refusal Acknowledgment

> "My executor shall, before transferring any shares in PlanO Pro Ltd to any beneficiary, first offer such shares to the Company or to the surviving shareholder(s) in accordance with the Shareholders Agreement. The purchase price shall be Fair Market Value as defined therein."

### 2.3. Cooperation Clause

> "I direct my executor to cooperate fully with the surviving shareholder(s) and the Company's director(s) to ensure business continuity during the administration of my estate. This includes providing timely written consents for Reserved Matters where my executor is satisfied that such consent is in the interest of the Company and the estate."

### 2.4. Voting Proxy During Administration

> "Until my shares in PlanO Pro Ltd are formally transferred, I authorize my executor to grant a voting proxy to [SURVIVING FOUNDER NAME / the surviving shareholder] for ordinary business decisions of the Company, excluding decisions requiring 75% or unanimous shareholder approval under the Shareholders Agreement."

## 3. Digital Asset Instructions for Executors

### 3.1. Digital Asset Schedule

Each founder should attach a sealed schedule to their will (updated annually) listing:

| Asset Type | Details for Executor |
|-----------|---------------------|
| **Credential escrow** | Location, access method, and dead man's switch details (see Document 05) |
| **Domain registrar** | Registrar name, account email, 2FA recovery method |
| **SSH keys** | Location of encrypted USB backup, passphrase location |
| **Cryptocurrency wallets** | Wallet type, seed phrase location (sealed envelope at [LOCATION]), which wallets are personal vs Company |
| **API keys** | Stored in credential escrow -- no action needed beyond accessing escrow |
| **GitHub account** | Username, recovery email, 2FA backup codes |
| **Email accounts** | List of business-critical email accounts and recovery methods |

### 3.2. Executor Instructions

> "My executor should immediately contact [SURVIVING FOUNDER NAME] at [PHONE] and [EMAIL] upon my death. My executor should then access the credential escrow described in the sealed schedule attached hereto and provide the surviving founder with access to all Company-related credentials within 7 days."

### 3.3. Separation of Personal and Company Assets

Executors must distinguish:
- **Company assets** (PlanO code, models, training data, customer data, domains used for PlanO): these belong to the Company per the IP Assignment Agreement, NOT to the estate
- **Personal assets** (personal crypto wallets, personal domains, personal code not assigned to PlanO): these are estate property
- **Infrastructure** (GPU server rental): the rental contract should be in the Company's name. If currently in a personal name, transfer to Company.

## 4. Jurisdiction-Specific Considerations

### 4.1. Malta Inheritance Law

- Malta applies the Civil Code (Cap 16) for succession
- **Forced heirship:** Malta law reserves a portion of the estate for descendants and surviving spouse (the "reserved portion"). For a person with children: 1/3 to children, 1/4 to surviving spouse. The testator can freely dispose of the remainder.
- **Shares in a Malta company** are movable property governed by the law of the testator's domicile at death (not the law of Malta where the company is registered)
- **Probate:** Application to the Malta Court of Voluntary Jurisdiction. Typical timeline: 3-6 months.
- If Hadrien is domiciled in Malta, Malta succession law applies to his entire estate including PlanO shares

### 4.2. Bulgarian Inheritance Law (for Ogi)

- Bulgaria applies the Inheritance Act (Zakon za Nasledstvoto)
- **Forced heirship:** Surviving spouse and children have reserved shares. One child + spouse: each gets 1/3, leaving 1/3 freely disposable. Two+ children + spouse: reserved portion increases.
- **EU Succession Regulation 650/2012:** As both Malta and Bulgaria are EU members and have adopted this regulation, Ogi may choose in his will that Bulgarian law (law of nationality) governs his entire succession, rather than the law of habitual residence. This is recommended if Bulgarian forced heirship rules are more favorable.
- **Cross-border probate:** A European Certificate of Succession issued in Bulgaria is recognized in Malta without further procedure.
- [ ] Ogi should include a choice-of-law clause in his will: "I choose Bulgarian law to govern my entire succession pursuant to Article 22 of EU Regulation 650/2012."

### 4.3. Practical Cross-Border Steps

1. Each founder makes a will in their country of domicile/nationality
2. The will specifically addresses PlanO shares and digital assets
3. Both wills reference the Shareholders Agreement ROFR
4. Both wills include the cooperation and voting proxy clauses above
5. Each founder provides the other with: executor name, executor contact details, and lawyer contact details (sealed envelope, updated annually)

## 5. During Probate -- Business Continuity

5.1. The SaaS platform operates autonomously. No human action is required for daily operations.

5.2. The surviving founder + BDO Nominee handle all operational decisions.

5.3. Financial: Stripe revenue continues to collect. Company bank account remains accessible by BDO Nominee (signatory).

5.4. The executor's primary obligations toward the Company are:
- Provide voting proxy to surviving founder (if will includes the recommended clause)
- Cooperate on any Reserved Matters that arise
- Complete share transfer (to beneficiary or to Company under ROFR) promptly

5.5. Target: all Company-related estate matters resolved within 6 months of death.

---

**This document is guidance only. Each founder must engage qualified legal counsel.**

| Party | Acknowledged | Date |
|-------|-------------|------|
| Ognyan Ignatov | _________________ | [DATE] |
| Hadrien Majoie | _________________ | [DATE] |
