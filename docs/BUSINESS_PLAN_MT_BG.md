# PlanO Business Plan — Malta + Bulgaria to Self-Sustaining Profitability

## Mission
Build a fully autonomous renovation SaaS that operates with zero human intervention.

## Phase 1: Malta + Bulgaria (Month 1-6)

### Why these two markets

| Factor | Malta | Bulgaria |
|--------|-------|----------|
| **Population** | 520K | 6.5M |
| **Renovation market** | €300M/yr | €1.5B/yr |
| **Avg project value** | €15-50K | €3-10K |
| **Digital plan adoption** | 60% | 25% (= blue ocean) |
| **SaaS competitors** | None | None |
| **Construction labor/hr** | €18-25 | €5-8 |
| **Language** | English | Bulgarian (bg) |
| **Currency** | EUR | BGN (EUR-pegged 1.96:1) |
| **EU renovation funds** | Limited | Significant (structural funds) |
| **Building stock** | Limestone terraced + apartments | Soviet prefab (panelák) + new |
| **Plan standard** | BS-influenced | GOST-legacy → EU harmonizing |

### Pricing (localized)

| Tier | Malta (EUR) | Bulgaria (BGN/EUR) |
|------|-------------|---------------------|
| Free | €0 | €0 |
| Starter | €9/mo | €5/mo (~10 BGN) |
| Pro | €19/mo | €9/mo (~18 BGN) |
| Agency | €49/mo | €25/mo (~49 BGN) |
| Homeowner | €4.99/plan | €2.49/plan (~5 BGN) |

Bulgaria priced at ~50% of Malta to match local purchasing power.

### Revenue targets

| Milestone | Users | MRR | Timeline |
|-----------|-------|-----|----------|
| Break-even | 1 | €9 | Week 1 |
| Validate | 20 | €180 | Month 1 |
| Traction | 100 | €900 | Month 3 |
| Self-sustaining | 500 | €4,500 | Month 6 |
| Scale trigger | 1,000 | €9,000 | Month 9 |

### Customer acquisition (zero human intervention)

| Channel | Agent | Frequency | Target |
|---------|-------|-----------|--------|
| SEO content | Content Creator + SEO Optimizer | 3x/week | Rank for "renovation cost Malta", "ремонт цена София" |
| Social media | Marketing Strategist | Daily | Facebook (MT: 75% penetration, BG: 60%) |
| Google Ads | Pricing Analyst (budget allocation) | Continuous | €5/day initial, scale with CAC data |
| Referral | Referral Manager | Automatic | Contractor refers contractor, both get 1 month free |
| Cold outreach | Sales Hunter | Weekly | Malta MBR contractor list, BG KSB registry |
| Review farming | Feedback Analyst | Per completed project | NPS → Trustpilot/Google Reviews |

### Content strategy (per market)

**Malta (English):**
- "How much does a bathroom renovation cost in Malta?"
- "Best floor tiles for Maltese apartments"
- "Planning permission for renovation in Malta"
- "Fort Cambridge renovation — limestone restoration guide"

**Bulgaria (Bulgarian + English):**
- "Колко струва ремонт на апартамент в София?"
- "Панелно жилище ремонт — цени 2026"
- "Субсидии за енергийна ефективност на сгради в България"
- "Renovation cost calculator Bulgaria"

### Contractor onboarding

**Malta:**
- Target: 20 contractors in first 3 months
- Source: Malta MBR (company registry), Yellow Pages MT, word of mouth
- Value prop: "Free leads from homeowners using PlanO"

**Bulgaria:**
- Target: 50 contractors in first 3 months
- Source: KSB (Камара на строителите в България), olx.bg, imot.bg
- Value prop: "Безплатни клиенти от PlanO" (Free clients from PlanO)

---

## Zero Human Intervention Architecture

### Current state (April 2026)
```
HUMAN TASKS:
- Product decisions (Hadrien + Ogi)
- Legal review (BDO + lawyer)
- Agent strategy (Ogi)
- Partnership negotiations
- Emergency bug fixes

AI AGENT TASKS (15 agents, 4 cycles):
- Content generation
- SEO optimization
- Social media posts
- Lead generation
- Customer support
- Onboarding guides
- QA testing
- API monitoring
- DevOps
- Revenue analytics
- Growth experiments
```

### Target state (Month 12+)
```
HUMAN TASKS:
- Strategic direction (quarterly)
- Legal compliance (annual)
- Agent tuning (monthly)

EVERYTHING ELSE = AUTONOMOUS:
- Customer acquisition → agents
- Onboarding → automated tutorials + AI support
- Billing → Stripe + BTCPay (fully automated)
- Support → AI chatbot + escalation to human only for legal issues
- Content → AI-generated, AI-reviewed, auto-published
- SEO → agents monitor rankings, generate content, optimize
- Bug detection → automated testing + monitoring
- Deployment → CI/CD pipeline
- Training data → pipeline auto-collects, anonymizes, retrains
- Financial reporting → automated dashboards
- Tax compliance → BDO (outsourced)
```

### Agent autonomy levels

| Level | Description | Timeline |
|-------|-------------|----------|
| L0 | Agent generates, human reviews and publishes | Now |
| L1 | Agent generates and publishes, human spot-checks weekly | Month 2 |
| L2 | Agent generates, publishes, monitors results, self-corrects | Month 4 |
| L3 | Agent operates fully autonomously, human reviews monthly | Month 8 |
| L4 | Agent improves its own prompts based on performance data | Month 12 |

---

## Phase 2: Mediterranean expansion (Month 7-12)

After Malta + Bulgaria reach self-sustaining profitability:
- Italy (€75B market, similar construction to Malta)
- Greece (€3B, similar to Bulgaria's building stock)
- Croatia (€2B, Dalmatian coast stone buildings)

### Phase 3: Full EU (Year 2+)
- France, Germany, Spain, Netherlands
- Requires: multi-language UI, per-country legal compliance, localized pricing
- Target: 10,000+ users, fully autonomous operation

---

## Financial model

### Fixed costs
| Item | Monthly |
|------|---------|
| GPU server | €0 (owned) |
| Domain + Caddy | €1 |
| BDO fiduciary | ~€200 (annual compliance) |
| **Total** | **~€17/mo** (amortized) |

### Variable costs
| Item | Per unit |
|------|----------|
| Stripe fees | 1.5% + €0.25/txn |
| BTCPay | 0% |
| Google Ads | €5-50/day (budget-controlled) |
| Transactional email | €0 (Resend free tier) |

### Unit economics
| Metric | Malta | Bulgaria |
|--------|-------|----------|
| ARPU (Starter) | €9/mo | €5/mo |
| CAC (organic) | €0 | €0 |
| CAC (paid, est.) | €15 | €5 |
| LTV (12-month) | €108 | €60 |
| LTV:CAC ratio | 7:1 | 12:1 |
| Payback period | 1.7 months | 1.0 months |

### Profitability threshold
- Malta: 2 Starter users cover fixed costs
- Bulgaria: 4 Starter users cover fixed costs
- Combined target: 100 users = €700/mo profit

---

## Key metrics for agents to track

1. **MRR** (Monthly Recurring Revenue)
2. **Active users** (daily/weekly/monthly)
3. **Plans created** per user per month
4. **Conversion rate** (free → paid)
5. **Churn rate** (monthly)
6. **CAC** by channel (organic, paid, referral)
7. **NPS** (Net Promoter Score)
8. **Rasta accuracy** per country
9. **Support ticket volume** (target: zero with AI)
10. **Content output** (articles/social posts per week)
