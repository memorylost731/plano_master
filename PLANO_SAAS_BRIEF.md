# PlanO SaaS Brief — Sprint April 5-9 (Malta)

**For:** Ogi | **From:** Hadrien | **Date:** 5 April 2026

---

## What PlanO Is

PlanO is a floor plan SaaS for contractors, architects, and homeowners. Users upload a floor plan image (or draw from scratch), the system auto-detects walls/rooms/doors using GPU-accelerated computer vision, then presents an editable 2D/3D editor where they select renovation services and get cost estimates.

**User flow:** Select building on 3D map → Upload or draw floor plan → Edit in 2D/3D → Select services → Get cost estimate → Pay → Get report

---

## What's Built & Working Right Now

| Component | Status | URL/Port |
|-----------|--------|----------|
| React 19 frontend (plano-ui) | LIVE | :5174 (dev), :8031 (prod) |
| 3D MapLibre building selector | LIVE | / (landing page) |
| React-Planner 2D/3D editor | LIVE | /planner (iframe bridge) |
| Rasta floor plan detection (FastAPI + OpenCV) | LIVE | :8011 (dev), :8020 (prod GPU) |
| GPU-accelerated inference (RTX 6000 Ada) | LIVE | Celery + Redis workers |
| Docker production deployment (nginx) | LIVE | :8031 on GPU server |
| Caddy HTTPS + auth gate | LIVE | hacking.eu/plano/ |
| 15 AI business agents (Ollama) | LIVE | 4 cycle timers running |
| SaaS Dashboard (new) | LIVE | /saas |
| BTCPay Server | AVAILABLE | :8032 (needs store config) |
| Service selection (7 trades, 43 sub-services) | LIVE | 3D view left panel |
| Project save/load (JSON) | LIVE | File download/upload |

**Stack:** React 19 + Vite + Tailwind | React-Planner (Webpack, iframe) | FastAPI + Uvicorn | Docker + nginx | Caddy | Ollama (Mistral-Small 24B)

---

## What's NOT Built Yet (Sprint Priorities)

### P0 — Must Ship (no revenue without these)
1. **User authentication** — Supabase Auth (free to 50K MAU, Google/email social login)
2. **Stripe payment processing** — Hosted Checkout (zero PCI burden), webhooks
3. **Subscription tier enforcement** — middleware blocks over-limit usage

### P1 — Should Ship
4. **BTCPay integration** — Bitcoin on-chain + Lightning, 10% discount, 0% fees
5. **Usage metering** — plan count, export count, API calls per billing period
6. **Landing / marketing page** — SEO-optimized, conversion-focused
7. **PDF export** — watermarked for free tier, clean for paid
8. **Transactional email** — Resend (free: 100/day)

### P2 — Nice to Have (post-launch OK)
9. **Service pricing database** — labor rates by trade, by region
10. **Shareable project URLs** — viral loop ("Made with PlanO" badge)
11. **Referral program** — Stripe coupons, both get 1 month free
12. **Review farming** — automated NPS + redirect to G2/Capterra

---

## Pricing Model

| Tier | Monthly | Annual (20% off) | Target |
|------|---------|-------------------|--------|
| **Free** | $0 | — | Trial users |
| **Starter** | $9 | $86/yr ($7.17/mo) | Solo contractors |
| **Pro** | $19 | $182/yr ($15.17/mo) | Active contractors |
| **Agency** | $49 | $470/yr ($39.17/mo) | Firms (5 seats) |
| **Homeowner** | $4.99/plan | — | One-time B2C |

**Positioning:** Cheaper than MagicPlan ($10), more powerful than Floorplanner ($5/plan), contractor-focused.

**BTC discount:** 10% off all tiers. Net margin higher than card (0% vs 1.5% fees).

---

## Cost Structure

| Item | Monthly |
|------|---------|
| GPU server (Docker, Ollama, BTCPay) | $0 (already rented) |
| Domain, Caddy, Cloudflare | ~$1 |
| Supabase Auth | $0 (free tier) |
| **Total fixed** | **~$1/mo** |

**Break-even: 1 paying Starter user.**

---

## Architecture (simplified)

```
hacking.eu/plano/
  → Caddy (TLS + auth)
    → Docker nginx (:8031)
      → / = React frontend (built static)
      → /engine/ = React-Planner (iframe, built static)
      → /api/raster → proxy → Rasta GPU (:8020)
        → Redis → Celery → RTX 6000 Ada → scene JSON
      → /saas = SaaS Dashboard
```

**GPU server:** RTX 6000 Ada 48GB, runs: Docker (PlanO), Ollama (AI agents), Rasta (floor plan ML), BTCPay (Bitcoin payments), Auth gate (JWT/bcrypt)

---

## AI Agent Team (15 agents, 4 cycles)

All powered by Ollama (Mistral-Small 24B abliterated) running on GPU.

| Cycle | Interval | Agents |
|-------|----------|--------|
| Revenue | 6h | Sales Hunter, Marketing Strategist, Content Creator, SEO Optimizer, Pricing Analyst, Referral Manager |
| Engineering | 2h | DevOps Engineer, QA Tester, API Monitor |
| Customer | 4h | Support Agent, Onboarding Guide, Feedback Analyst |
| Executive | 12h | CEO Agent, CTO Agent, Growth Hacker |

Running as systemd user timers. Each cycle queries Ollama, generates outputs, stores in SQLite event bus.

---

## Sprint Plan (April 5-9)

### Day 1-2: Auth + Payments
- [ ] Set up Supabase project, configure auth
- [ ] Create Stripe account, products, prices
- [ ] Wire Supabase JWT to FastAPI middleware
- [ ] Build login/signup UI (replace placeholder)
- [ ] Stripe Checkout integration + webhook handler

### Day 3: Tier Enforcement + Metering
- [ ] Usage tracking middleware (plans, exports, API calls)
- [ ] Tier limit enforcement (402 responses → upgrade CTA)
- [ ] Project persistence in DB (replace JSON file download)

### Day 4: Polish + Launch Prep
- [ ] Landing page with pricing
- [ ] PDF export with tier-based watermark
- [ ] BTCPay store configuration
- [ ] Transactional email setup (Resend)

### Day 5: Testing + Deploy
- [ ] End-to-end user journey test
- [ ] Production deployment
- [ ] Soft launch

---

## Key Decisions for Ogi

1. **Supabase vs custom auth?** — Recommend Supabase (free, handles social login, JWT, self-hostable later)
2. **Stripe vs Paddle?** — Recommend Stripe (lower fees in EU, more control, BTC complement)
3. **Launch market?** — Malta contractors first (local network), expand EU
4. **Pricing too low/high?** — $9 Starter undercuts competition, room to raise after traction
5. **Self-host vs cloud?** — Stay self-hosted as long as possible ($1/mo vs $50+/mo cloud)

---

## Access

- **Dev:** http://localhost:5174 (plano-ui), http://localhost:5173 (engine), http://localhost:8011 (rasta)
- **Prod:** https://hacking.eu/plano/ (auth required)
- **Dashboard:** /saas (new — shows health, pricing, agents, architecture, sprint)
- **Repo:** github.com/memorylost731/plano_master (branch: import/ogi-drop-2026-01-31)
- **SaaS Plan (full):** PLANO_SAAS_PLAN.md (39KB detailed architecture)
