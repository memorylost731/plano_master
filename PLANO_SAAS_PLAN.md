# PlanO SaaS Business Plan -- Complete Architecture

Date: 2026-04-04
Authors: Claude (architect), for review with Ogi (April 5-9 sprint)
Status: DRAFT -- awaiting sprint validation

---

## 0. CURRENT STATE AUDIT

What exists today:

| Component | Status | Path |
|-----------|--------|------|
| plano-ui (React 19 + Vite + Tailwind) | Working | `00_frontend_skeleton/plano-ui/` |
| React-Planner engine (2D/3D editor) | Working, iframe | `02_react_planner/react-planner/` |
| Rasta (FastAPI floor plan detection) | Working, port 8020 | `01_raster/server/app.py` |
| Docker deployment (nginx) | Working, port 8031 | `deploy/docker-compose.yml` |
| Caddy reverse proxy + auth | Working | hacking.eu/plano/ |
| 15 AI agents (Ollama-powered) | Working | `plano_agents.py` + SQLite |
| Estimate page (BOQ table) | UI only, hardcoded | `pages/client/Estimate.tsx` |
| User auth | STUB (`/login` = placeholder div) | App.tsx line 28 |
| Payment | NONE | -- |
| Usage tracking | NONE | -- |
| Subscription management | NONE | -- |

What does NOT exist and must be built:
1. User authentication (real, not placeholder)
2. Payment processing (Stripe + BTCPay)
3. Subscription/tier enforcement
4. Usage metering
5. Landing page / marketing site
6. Service pricing database (labor rates by trade, by region)

---

## 1. PRICING MODEL

### Competitive Analysis (April 2026)

| Competitor | Free Tier | Paid | Target |
|------------|-----------|------|--------|
| RoomSketcher | View-only | $49/mo (Pro), $99/mo (VIP) | B2C homeowners |
| Floorplanner | 1 project | $5/plan export | B2C casual |
| Planner5D | Limited | $7/mo ($84/yr) | B2C design |
| MagicPlan | 2 projects | $10/mo ($96/yr) | B2B contractors |
| CubiCasa | None | POA (enterprise) | B2B real estate |
| Cedreo | None | $79/mo | B2B builders |

### PlanO Pricing Tiers

**Positioning: cheaper than MagicPlan, more powerful than Floorplanner, contractor-focused.**

```
TIER           MONTHLY    ANNUAL     PER-PROJECT    FEATURES
-----------    -------    ------     -----------    --------
Free           $0         $0         --             1 project, watermarked exports,
                                                    basic 2D only, no API,
                                                    max 200m2 floor area

Starter        $9         $86/yr     --             5 active projects, HD exports,
               (save 20%  = $7.17/mo)               2D + 3D, area calculation,
                                                    basic cost estimate, email support

Pro            $19        $182/yr    --             Unlimited projects, no watermark,
               (save 20%  = $15.17/mo)              full cost estimates with local rates,
                                                    PDF reports, priority support,
                                                    API access (1000 calls/mo)

Agency         $49        $470/yr    --             Everything in Pro, plus:
               (save 20%  = $39.17/mo)              5 team seats (+$9/seat/mo),
                                                    white-label exports,
                                                    client portal, API (10K calls/mo),
                                                    bulk upload, custom branding

Homeowner      --         --         $4.99/plan     One-time per project,
(B2C)                                               includes export + cost estimate,
                                                    no subscription needed
```

**Why these numbers:**
- $9/mo Starter undercuts MagicPlan ($10) and Planner5D ($7 but no contractor features)
- $19/mo Pro is the volume tier -- contractors doing 5+ renovations/month happily pay this
- $49/mo Agency captures firms with 3-10 employees who would pay RoomSketcher $99
- $4.99/plan captures homeowners who refuse subscriptions (Floorplanner charges $5/plan)
- Annual discount is exactly 20% -- aggressive enough to convert, simple enough to explain

**Currency:**
- All prices displayed in EUR (Malta base, EU market)
- USD toggle for non-EU visitors (auto-detect via IP geolocation, Cloudflare header)
- BTC accepted on all tiers (see section 10)

---

## 2. PAYMENT INFRASTRUCTURE

### Architecture

```
User clicks "Upgrade"
       |
       v
  +-----------+     +-----------+
  | Stripe    |     | BTCPay    |
  | Checkout  |     | Server    |
  | (hosted)  |     | (self)    |
  +-----+-----+     +-----+-----+
        |                  |
        v                  v
  webhook POST /api/payments/stripe/webhook
  webhook POST /api/payments/btcpay/webhook
        |                  |
        +--------+---------+
                 |
                 v
     +------------------------+
     | PaymentService         |
     | - validate webhook sig |
     | - update user tier     |
     | - emit event to bus    |
     | - log to append-only   |
     +------------------------+
                 |
                 v
        PostgreSQL (users table)
```

### Stripe Setup (cards + SEPA + Apple Pay + Google Pay)

Cost: 1.5% + 0.25 EUR (EU cards), 2.9% + 0.30 USD (non-EU).

Implementation:
1. Stripe Checkout (hosted) -- NOT embedded. Hosted checkout means:
   - Zero PCI compliance burden
   - Apple Pay / Google Pay / SEPA / Bancontact / iDEAL free
   - Stripe handles 3D Secure, SCA, retry logic
   - We only handle webhooks
2. Stripe Products: create 4 products (Starter monthly, Starter annual, Pro monthly, Pro annual, Agency monthly, Agency annual) + 1 one-time price (Homeowner plan)
3. Stripe Customer Portal: self-service cancel, upgrade, download invoices -- zero support needed
4. Webhook events to handle:
   - `checkout.session.completed` -- provision user tier
   - `customer.subscription.updated` -- tier change
   - `customer.subscription.deleted` -- downgrade to free
   - `invoice.payment_failed` -- trigger dunning sequence
   - `invoice.paid` -- reset dunning counter

### BTCPay Server Setup (0% fees)

Already have: bitcoind on GPU server, Caddy for HTTPS.

Implementation:
1. BTCPay Server Docker on GPU (port 8032, proxied through Caddy)
2. Lightning Network via LND (for $4.99 homeowner payments -- sub-cent fees)
3. Store configured with: BTC on-chain + Lightning
4. Invoice flow: user selects BTC -> redirect to BTCPay invoice page -> webhook on payment
5. 10% discount on BTC (still saves money vs Stripe 2.9% fee)

### Dunning Sequence (automated churn prevention)

```
Payment fails
  -> Stripe retries (3 attempts over 7 days, built-in)
  -> Day 1: Email "payment failed, update card" (link to Stripe portal)
  -> Day 3: Email "your Pro features expire in 4 days"
  -> Day 7: Downgrade to Free tier, email "we saved your projects, upgrade anytime"
  -> Day 90: Delete project data (GDPR compliance)
```

All emails sent via transactional email (see cost section). Zero human intervention.

### Usage Metering

Track per user per billing period:
- `plans_created` -- count of new floor plans
- `exports_generated` -- PDF/PNG/DXF exports
- `api_calls` -- for Pro/Agency API access
- `storage_mb` -- total floor plan storage

Enforcement middleware (FastAPI):

```python
@app.middleware("http")
async def enforce_tier_limits(request: Request, call_next):
    user = get_current_user(request)
    if not user:
        return await call_next(request)

    limits = TIER_LIMITS[user.tier]

    if request.url.path.startswith("/api/plans") and request.method == "POST":
        count = await get_plan_count(user.id)
        if count >= limits["max_plans"]:
            return JSONResponse(
                status_code=402,
                content={"error": "plan_limit", "upgrade_url": "/pricing"}
            )

    return await call_next(request)
```

---

## 3. USER SYSTEM

### ADR-001: Auth Provider Selection

**Status:** Proposed

**Context:** Need user auth with social login, email/password, team management. Must be automatable with zero ops overhead. Current stack is React + FastAPI.

**Options:**

| Option | Cost | Pros | Cons |
|--------|------|------|------|
| Supabase Auth | Free to 50K MAU | Postgres-native, row-level security, self-hostable | Adds Supabase dependency |
| Firebase Auth | Free to 10K MAU | Battle-tested, all social providers | Google lock-in, Firestore pull |
| Clerk | Free to 10K MAU | Best DX, org management built-in | $25/mo at scale, US-hosted |
| Custom (JWT + bcrypt) | $0 | Full control, no dependency | Must build everything, security risk |

**Decision:** Supabase Auth (hosted free tier, migrate to self-hosted later).

**Rationale:**
- Free for 50K monthly active users (we won't hit this for 12+ months)
- Native PostgreSQL -- user data lives in same DB as our app data
- Built-in Row Level Security -- tier enforcement at DB level
- Social login (Google, GitHub, Apple) with zero config
- Self-hostable when we outgrow free tier (Docker, already have infra)
- Python client (`supabase-py`) works with FastAPI
- JWT tokens validated server-side, no session state needed

**Consequences:**
- Adds supabase-py dependency to backend
- Must handle Supabase JWT in FastAPI middleware
- User metadata (tier, usage) stored in our own `users` table, linked by Supabase UID

### User Data Model

```sql
-- Supabase handles auth.users internally. We extend with:

CREATE TABLE public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id),
    email TEXT NOT NULL,
    display_name TEXT,
    tier TEXT NOT NULL DEFAULT 'free'
        CHECK (tier IN ('free', 'starter', 'pro', 'agency', 'homeowner')),
    stripe_customer_id TEXT,
    btcpay_customer_id TEXT,
    org_id UUID REFERENCES public.orgs(id),
    plan_count INTEGER DEFAULT 0,
    export_count INTEGER DEFAULT 0,
    api_calls_this_period INTEGER DEFAULT 0,
    current_period_start TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE public.orgs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    owner_id UUID NOT NULL REFERENCES public.users(id),
    max_seats INTEGER DEFAULT 5,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE public.org_members (
    org_id UUID REFERENCES public.orgs(id),
    user_id UUID REFERENCES public.users(id),
    role TEXT DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member')),
    PRIMARY KEY (org_id, user_id)
);

CREATE TABLE public.projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id),
    org_id UUID REFERENCES public.orgs(id),
    name TEXT NOT NULL,
    scene_json JSONB,          -- react-planner scene
    detection_json JSONB,      -- rasta raw output
    thumbnail_url TEXT,
    area_sqm REAL,
    status TEXT DEFAULT 'draft',
    is_template BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE public.usage_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.users(id),
    event_type TEXT NOT NULL,  -- plan_created, export, api_call
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_projects_user ON public.projects(user_id);
CREATE INDEX idx_projects_org ON public.projects(org_id);
CREATE INDEX idx_usage_user_period ON public.usage_events(user_id, created_at);
```

### Tier Limits (enforced in middleware + frontend)

```python
TIER_LIMITS = {
    "free":      {"max_plans": 1,  "exports": 3,    "api_calls": 0,     "max_area_sqm": 200, "watermark": True,  "3d": False, "teams": False},
    "starter":   {"max_plans": 5,  "exports": 50,   "api_calls": 0,     "max_area_sqm": 999, "watermark": False, "3d": True,  "teams": False},
    "pro":       {"max_plans": -1, "exports": -1,    "api_calls": 1000,  "max_area_sqm": -1,  "watermark": False, "3d": True,  "teams": False},
    "agency":    {"max_plans": -1, "exports": -1,    "api_calls": 10000, "max_area_sqm": -1,  "watermark": False, "3d": True,  "teams": True},
    "homeowner": {"max_plans": 1,  "exports": 5,     "api_calls": 0,     "max_area_sqm": 500, "watermark": False, "3d": True,  "teams": False},
}
# -1 = unlimited
```

---

## 4. COST OPTIMIZATION

### Fixed Costs (current infrastructure, already paid)

| Item | Monthly Cost | Notes |
|------|-------------|-------|
| GPU server (hadrien-skoed-mt) | $0 | Already rented/owned, runs Docker + Ollama + BTCPay |
| Dell server (503GB RAM) | $0 | Already owned, can run raster API |
| Domain (hacking.eu) | ~$1/mo amortized | Already owned |
| Caddy (HTTPS) | $0 | Auto-cert, free |
| Supabase Auth | $0 | Free to 50K MAU |
| GitHub (repo + Actions) | $0 | Free tier, 2000 min/mo CI |
| Cloudflare (CDN) | $0 | Free tier for static assets |
| Ollama (AI agents) | $0 | Already running on GPU |
| BTCPay Server | $0 | Self-hosted, no fees |
| Monitoring (self-heal) | $0 | Already running |
| **TOTAL** | **~$1/mo** | |

### Variable Costs

| Item | Unit Cost | Trigger |
|------|-----------|---------|
| Stripe fees | 1.5% + 0.25 EUR per txn (EU) | Every card payment |
| Transactional email | $0 to ~100/day | Resend free tier: 100 emails/day, 3000/mo |
| Supabase (if >50K MAU) | $25/mo | Switch to self-hosted instead |
| Bandwidth (Cloudflare) | $0 | Unlimited on free tier |

### Cost Per User

At $9/mo Starter (annual): Stripe takes ~0.39 EUR/mo. Net revenue = $8.61/user/mo.
At $19/mo Pro (annual): Stripe takes ~0.54 EUR/mo. Net revenue = $18.46/user/mo.
BTC payments: 0% fees. Net revenue = full price minus 10% discount = $8.10 or $17.10.

**Break-even: 1 paying user.** Fixed costs are essentially zero.

### Scale Triggers

| Users | Action | Why |
|-------|--------|-----|
| 0-500 | Stay on GPU server | $0 marginal cost, server handles it |
| 500-2000 | Move raster API to Dell | CPU-heavy detection, free up GPU for Ollama |
| 2000-5000 | Add Cloudflare CDN caching for static + plan thumbnails | Reduce server bandwidth |
| 5000+ | Evaluate AWS ECS Fargate for raster API | Only pay per invocation, ~$0.01/plan |
| 10000+ | Self-host Supabase on Dell (503GB RAM, overkill) | Eliminate $25/mo Supabase fee |

**Do NOT move to AWS prematurely.** The GPU server can handle thousands of concurrent users for a static nginx site + occasional raster API calls. The raster detection is the only CPU-intensive part, and it takes <5 seconds per plan.

---

## 5. AUTOMATED GROWTH ENGINE

### SEO (auto-generated, AI-written)

Landing pages to generate (one per renovation type, one per city):

```
/bathroom-planner          -- "Free Bathroom Floor Plan Tool"
/kitchen-planner           -- "Kitchen Renovation Planner"
/office-layout             -- "Office Layout Designer"
/apartment-planner         -- "Apartment Floor Plan Creator"
/renovation-cost-estimator -- "Renovation Cost Calculator"
/planner/malta             -- "Floor Plan Tool for Malta Contractors"
/planner/london            -- "London Renovation Planning"
/planner/dubai             -- "Dubai Interior Design Planner"
```

Each page: H1 with keyword, 800-word AI-generated article, embedded free-tier tool demo, CTA to sign up. Generated by content agent (already exists in plano_agents.py), published via static site generation.

**Implementation:** Add a `marketing/` directory with MDX templates. Cael generates content via Ollama. Vite builds them as static pages. Zero runtime cost.

### Content Pipeline

```
Weekly (automated by content agent):
  Monday:    Blog post (renovation tips, case study, how-to)
  Wednesday: Social media post (before/after render, tip card)
  Friday:    Email newsletter to subscribers (Resend, free tier)

Monthly:
  Renovation cost report by region (AI-generated from rate database)
  Competitor comparison page update
```

All content generated by Cael (Ollama), reviewed by CEO agent, published automatically. The 15 agents already exist -- they just need output channels connected.

### Product-Led Growth

```
Free user creates plan
  -> Plan gets shareable URL (e.g., plano.hacking.eu/p/abc123)
  -> Shared link shows read-only view with "Made with PlanO" badge
  -> Badge links to signup page
  -> Recipient signs up (free) -> creates their own plan -> shares -> viral loop
```

**Referral program:**
- Contractor refers contractor via unique link
- Both get 1 month of current tier free (applied as Stripe coupon)
- Tracked in `referrals` table, capped at 12 months free per user (abuse prevention)

### Review Farming

```
Project completed (user exports final plan)
  -> 24h later: email "How was your experience? Rate us"
  -> If 4-5 stars: "Thanks! Would you leave a review on [G2/Capterra/Trustpilot]?"
  -> If 1-3 stars: "Sorry to hear that. What can we improve?" (routes to feedback agent)
```

### Partnerships (Phase 2, post-launch)

- Tile suppliers: embed their catalog in the material picker (they pay for placement)
- Paint brands: color picker linked to real paint codes (affiliate commission)
- Contractor directories: API integration (HomeAdvisor, MyBuilder, Houzz)
- Real estate agencies: bulk pricing for property listings (CubiCasa competitor play)

---

## 6. AUTOMATION PIPELINE

### Complete User Lifecycle (zero human touch)

```
SIGNUP:
  User lands on plano.hacking.eu
  -> Clicks "Start Free"
  -> Supabase Auth (Google/email)
  -> users table row created (tier=free, plan_count=0)
  -> Welcome email (Resend, template #1)
  -> Free tier active immediately
  -> ZERO HUMAN TOUCH

FIRST PROJECT:
  User uploads floor plan image
  -> Rasta API detects walls
  -> Scene loaded in react-planner
  -> User edits, saves
  -> project row created, scene_json stored
  -> plan_count incremented
  -> ZERO HUMAN TOUCH

UPGRADE:
  User hits limit (e.g., tries to create 2nd plan on Free)
  -> Frontend shows upgrade modal with tier comparison
  -> User clicks "Upgrade to Starter"
  -> Redirect to Stripe Checkout (or BTCPay)
  -> Payment completes
  -> Webhook fires -> PaymentService updates tier
  -> User refreshed, new features unlocked
  -> ZERO HUMAN TOUCH

CANCEL:
  User clicks "Cancel" in Stripe Customer Portal
  -> Webhook: subscription_deleted
  -> Dunning sequence (3 emails over 7 days)
  -> If no reactivation: tier = free, projects retained (read-only)
  -> Day 90: data deletion warning email
  -> Day 97: final warning
  -> Day 100: delete project data (GDPR)
  -> ZERO HUMAN TOUCH

BUG REPORT:
  User submits bug via in-app form
  -> QA agent triages (severity, category)
  -> Creates GitHub issue via API
  -> Labels auto-assigned
  -> If critical: Slack/email notification to dev
  -> ZERO HUMAN TOUCH

FEATURE REQUEST:
  User submits via feedback form
  -> Feedback agent logs to event_bus
  -> CEO agent reviews weekly batch
  -> Prioritized in backlog
  -> ZERO HUMAN TOUCH
```

---

## 7. REVENUE PROJECTIONS

### Conservative Model

Assumptions:
- 20% free-to-paid conversion (industry avg for PLG tools: 2-5%, but we're niche B2B)
- Revised to 5% conversion for conservatism
- Average revenue per paying user (ARPU): $15/mo (weighted across tiers)
- Monthly user growth: 30% M/M for first year (organic + SEO + referrals)

```
MONTH   SIGNUPS   CUMUL.USERS   PAYING(5%)   MRR        COSTS    NET
------  -------   -----------   ----------   --------   ------   --------
  1        20          20           1          $15        $1      $14
  2        26          46           2          $30        $1      $29
  3        34          80           4          $60        $1      $59
  4        44         124           6          $90        $5      $85
  5        57         181          9          $135        $5      $130
  6        74         255          13         $195        $5      $190
  7        96         351          18         $270        $5      $265
  8       125         476          24         $360        $10     $350
  9       163         639          32         $480        $10     $470
 10       212         851          43         $645        $10     $635
 11       276        1127          56         $840        $15     $825
 12       359        1486          74        $1,110       $15    $1,095
```

**Year 1 total revenue: ~$4,230** (conservative).
**Year 1 total costs: ~$83.**
**Year 1 profit: ~$4,147.**

Break-even: Month 1 (costs are near zero).

### Optimistic Model (10% conversion, viral coefficient 1.2)

```
Month 6:   500 users,  50 paying,  $750/mo MRR
Month 12: 3000 users, 300 paying, $4,500/mo MRR
Month 18: 8000 users, 800 paying, $12,000/mo MRR
Month 24: 15000 users, 1500 paying, $22,500/mo MRR
```

### Revenue Levers (ordered by impact)

1. **Contractor partnerships** -- one renovation firm with 10 seats = $49 + 9*$9 = $130/mo
2. **Per-project B2C** -- homeowner pays $4.99 once, zero retention cost
3. **Service rate database** -- charge suppliers to list their rates (lead gen)
4. **API licensing** -- real estate portals pay for floor plan API ($0.50/call)
5. **White-label** -- property management firms embed PlanO in their portal

---

## 8. SPRINT PLAN (April 5-9 with Ogi)

### Pre-Sprint Prep (April 4, today)

- [ ] Create Stripe account (test mode), get API keys
- [ ] Create Supabase project (free tier), get anon key + service key
- [ ] Create Resend account (transactional email), get API key
- [ ] Set up BTCPay Server Docker on GPU (can run in parallel)
- [ ] Prepare this document for Ogi review

### Day 1 (April 5): Auth + Database

**Morning (4h):**
- Supabase project configured (auth providers: Google, email/password)
- FastAPI backend: new `/api/auth/` routes
  - `POST /api/auth/signup` -- create user, insert into `users` table
  - `POST /api/auth/login` -- return JWT
  - `GET /api/auth/me` -- return user profile + tier + usage
- Supabase JWT validation middleware in FastAPI
- Database schema deployed (users, orgs, projects, usage_events tables)

**Afternoon (4h):**
- Frontend: replace placeholder `/login` with real auth flow
  - Login page: email + Google OAuth
  - Signup page: email + Google OAuth
  - Auth context provider (React context, stores JWT + user)
  - Protected routes: `/planner`, `/estimate` require auth
  - Persist session in localStorage (Supabase handles refresh)

**Deliverable:** Users can sign up, log in, and see their tier on a profile page.

### Day 2 (April 6): Stripe + Tier Enforcement

**Morning (4h):**
- Stripe products and prices created (test mode):
  - Starter monthly ($9), Starter annual ($86)
  - Pro monthly ($19), Pro annual ($182)
  - Agency monthly ($49), Agency annual ($470)
  - Homeowner one-time ($4.99)
- FastAPI: `POST /api/payments/create-checkout` -- creates Stripe Checkout session
- FastAPI: `POST /api/payments/webhook` -- handles Stripe webhooks
- FastAPI: `GET /api/payments/portal` -- returns Stripe Customer Portal URL

**Afternoon (4h):**
- Frontend: pricing page component (`/pricing`)
  - Tier comparison table (Free vs Starter vs Pro vs Agency)
  - "Upgrade" buttons -> Stripe Checkout
  - "Manage Subscription" -> Stripe Portal
- Tier enforcement middleware in FastAPI:
  - Check plan_count against tier limit on `POST /api/plans`
  - Check export_count on export endpoints
  - Return 402 with upgrade prompt
- Frontend: upgrade modal when 402 received

**Deliverable:** Full payment flow works in test mode. Tiers enforced.

### Day 3 (April 7): Landing Page + SEO Foundation

**Morning (4h):**
- Landing page redesign (`/` route):
  - Hero: "Plan Your Renovation in Minutes" + demo screenshot
  - 3 value props: Upload -> Edit -> Estimate
  - Pricing section (embedded from `/pricing`)
  - Social proof section (placeholder for reviews)
  - CTA: "Start Free" -> signup
- Meta tags, OpenGraph, structured data (JSON-LD for SoftwareApplication)

**Afternoon (4h):**
- `/bathroom-planner`, `/kitchen-planner`, `/office-layout` static pages
  - AI-generated content (Cael via Ollama, batch generate before sprint)
  - Each page: keyword-optimized H1, 800 words, embedded free CTA
- Sitemap.xml + robots.txt
- Google Search Console submission
- Cloudflare DNS + CDN activation (if not already done)

**Deliverable:** Marketing site live with 4+ indexable pages.

### Day 4 (April 8): Service Pricing Backend

**Morning (4h):**
- Service rates database schema:
  ```sql
  CREATE TABLE service_rates (
      id SERIAL PRIMARY KEY,
      category TEXT NOT NULL,     -- 'painting', 'tiling', 'plumbing', etc.
      service TEXT NOT NULL,      -- 'internal wall paint', '60x60 porcelain tile'
      unit TEXT NOT NULL,         -- 'm2', 'linear_m', 'unit', 'hour'
      rate_min NUMERIC(10,2),
      rate_max NUMERIC(10,2),
      rate_avg NUMERIC(10,2),
      currency TEXT DEFAULT 'EUR',
      region TEXT DEFAULT 'MT',   -- ISO country code
      source TEXT,
      updated_at TIMESTAMPTZ DEFAULT now()
  );
  ```
- Seed with Malta renovation rates (painting, tiling, plumbing, electrical, carpentry)
  - Data sources: local contractor quotes, online rate guides
  - 50-100 line items minimum

**Afternoon (4h):**
- Connect Estimate page to real data:
  - `GET /api/rates?category=painting&region=MT` -> returns rate range
  - Estimate page reads room areas from react-planner scene
  - Auto-calculates: area * rate = cost per room per trade
  - Total estimate with min/max range
- PDF export of estimate (WeasyPrint or reportlab, runs server-side)

**Deliverable:** Upload plan -> detect rooms -> get real cost estimate -> export PDF.

### Day 5 (April 9): Polish + Beta Launch

**Morning (4h):**
- Bug fixes from Days 1-4
- Error handling: loading states, error boundaries, 404 page
- Mobile responsiveness check (landing page must work on phone)
- Stripe switch from test mode to live mode
- BTCPay Server: configure store, test BTC payment flow
- Usage tracking: verify metering works (create plan, export, check counts)

**Afternoon (4h):**
- Beta launch:
  - Remove Caddy auth gate (site now has its own auth)
  - Announce to 10 target beta users (contractors Ogi knows)
  - Set up feedback form (in-app, routes to feedback agent)
  - Monitor: check raster API performance, auth flow, payment flow
  - Fix any launch-day issues
- Post-launch:
  - Google Analytics or Plausible (privacy-respecting, self-hostable)
  - Uptime monitoring (self-heal watchdog already exists)

**Deliverable:** PlanO is live, accepting signups and payments.

---

## 9. TECH ARCHITECTURE

### System Diagram (C4 Level 2 -- Container)

```
                    INTERNET
                       |
                   [Cloudflare CDN]
                       |
                   [Caddy Reverse Proxy]
                   hacking.eu/plano/
                       |
            +----------+----------+
            |                     |
     [nginx container]     [FastAPI Backend]
     port 8031/80          port 8020
            |                     |
     +------+------+        +----+----+
     |             |         |         |
  [plano-ui]  [react-       |    [Supabase Auth]
   React 19    planner]     |     (hosted, free)
   Vite/TW     iframe      |         |
                            |    [PostgreSQL]
                            |     (Supabase hosted DB)
                            |         |
                      [Rasta Engine]  |
                      OpenCV detect   |
                            |         |
                      +-----+---------+---+
                      |                    |
                [Stripe API]        [BTCPay Server]
                 (webhooks)          port 8032
                                    (self-hosted)
                                         |
                                    [bitcoind]
                                    (GPU server)
```

### Component Responsibilities

| Component | Runs On | Purpose |
|-----------|---------|---------|
| Caddy | GPU server | HTTPS termination, reverse proxy, rate limiting |
| nginx (Docker) | GPU server | Serve static frontend, proxy to raster API |
| plano-ui | Static (nginx) | User-facing SPA |
| react-planner | Static (nginx) | 2D/3D floor plan editor (iframe) |
| FastAPI (Rasta) | GPU server (or Dell at scale) | Floor plan detection + business API |
| Supabase | Hosted (free) | Auth, user DB, row-level security |
| Stripe | Hosted | Payment processing |
| BTCPay Server | GPU server (Docker) | BTC/Lightning payments |
| Ollama | GPU server | AI agents (content, support, CEO, etc.) |
| plano_agents.py | GPU server (cron) | 15 autonomous business agents |
| Resend | Hosted (free) | Transactional email (dunning, welcome, etc.) |

### What Changes from Current Architecture

Minimal changes. This is intentional.

1. **Add:** Supabase client to frontend (npm package) and backend (pip package)
2. **Add:** Stripe checkout redirect from frontend, webhook handler in FastAPI
3. **Add:** BTCPay Server as new Docker container
4. **Add:** `service_rates` table and `/api/rates` endpoint in FastAPI
5. **Add:** `/api/payments/*` routes in FastAPI
6. **Add:** Auth middleware in FastAPI (validate Supabase JWT)
7. **Modify:** `App.tsx` to add auth context, protected routes, pricing page
8. **Modify:** nginx config to proxy new API routes
9. **Modify:** docker-compose.yml to add BTCPay container
10. **Remove:** Caddy basic auth (replaced by Supabase auth)

Total new code estimate: ~1500 lines Python (backend), ~1000 lines TypeScript (frontend).

### Dependency Direction (critical for maintainability)

```
Frontend -> Auth (Supabase) -> never depends on payment
Frontend -> API (FastAPI) -> never calls Stripe directly
API -> Auth (validates JWT) -> never stores passwords
API -> Payment (Stripe/BTCPay) -> webhook handlers only
API -> DB (Supabase Postgres) -> parameterized SQL only
Payment -> API (webhooks) -> API is the single source of truth for tiers
```

No circular dependencies. Payment providers are replaceable (Stripe could be swapped for Paddle or LemonSqueezy by changing only the webhook handler and checkout redirect).

---

## 10. BTC OPTIMIZATION

### Setup

```
GPU Server already has:
  - bitcoind (full node, synced)
  - Caddy (HTTPS)
  - Docker

Add:
  - BTCPay Server (Docker)
  - LND (Lightning, Docker)
```

### Docker Compose Addition

```yaml
  btcpay:
    image: btcpayserver/btcpayserver:1.13
    container_name: plano-btcpay
    restart: unless-stopped
    environment:
      BTCPAY_POSTGRES: "Host=host-gateway;Database=btcpay;..."
      BTCPAY_NETWORK: mainnet
      BTCPAY_BIND: "0.0.0.0:8032"
    ports:
      - "127.0.0.1:8032:8032"
    volumes:
      - btcpay_data:/datadir

  lnd:
    image: lightninglabs/lnd:v0.18
    container_name: plano-lnd
    restart: unless-stopped
    volumes:
      - lnd_data:/root/.lnd
    command: >
      --bitcoin.active
      --bitcoin.mainnet
      --bitcoin.node=bitcoind
      --bitcoind.rpchost=host-gateway
```

### BTC Pricing Strategy

| Fiat Price | BTC Price | Discount | Stripe Fee Saved | Net Gain |
|-----------|-----------|----------|-----------------|----------|
| $9/mo | $8.10/mo | 10% | $0.39 | -$0.51 (discount > fee, but acquires BTC) |
| $19/mo | $17.10/mo | 10% | $0.54 | -$1.36 (acquiring BTC at 10% discount) |
| $49/mo | $44.10/mo | 10% | $0.96 | -$3.94 |
| $4.99 | $4.49 | 10% | $0.32 | -$0.18 |

**The 10% BTC discount is a deliberate investment in BTC accumulation, not a cost optimization.** At scale, reduce to 5% discount. The real savings are: zero chargebacks, zero Stripe dependency, no payment processor can freeze funds.

### Lightning for Microtransactions

Homeowner $4.99 plans over Lightning:
- On-chain BTC fee: ~$0.50-2.00 (uneconomical for $4.99)
- Lightning fee: ~$0.01 (200x cheaper)
- Settlement: instant (vs 10-60 min on-chain)

Lightning is mandatory for the Homeowner tier. On-chain for subscriptions (larger amounts).

### Auto-Convert Fiat to BTC

```python
# Monthly cron: convert 50% of Stripe revenue to BTC
# Via Kraken API (lowest fees in EU: 0.16% maker)
# Keep 50% EUR for operational expenses

async def monthly_btc_conversion():
    stripe_revenue = await get_stripe_revenue_this_month()
    convert_amount = stripe_revenue * 0.50
    if convert_amount > 50:  # minimum threshold
        await kraken_buy_btc(eur_amount=convert_amount)
        await log_conversion(convert_amount)
```

---

## 11. ARCHITECTURAL DECISION RECORDS

### ADR-002: Monolith vs Microservices

**Status:** Accepted

**Context:** PlanO has a frontend, a raster engine, payment processing, and AI agents. Should these be separate services?

**Decision:** Keep everything as a modular monolith behind nginx. The FastAPI app handles all API routes. The raster engine is a module within the same FastAPI app (already is). AI agents are a separate cron-driven process (already is).

**Rationale:**
- Two people (you and Ogi) cannot maintain microservices
- All components run on one server anyway
- nginx already handles routing
- Splitting would add Docker networking complexity with zero benefit
- If a component needs to scale independently (raster API), move it to Dell with a single config change

**Consequences:**
- Simpler deployment (one docker-compose up)
- All state in one Postgres database
- Cannot scale raster API independently without code change (acceptable until 2000+ users)

### ADR-003: Supabase Hosted vs Self-Hosted

**Status:** Accepted

**Context:** Need auth + Postgres. Self-hosting Supabase is possible (Docker) but adds ops burden.

**Decision:** Start with Supabase hosted (free tier). Migrate to self-hosted on Dell when we exceed 50K MAU or need to reduce latency.

**Consequences:**
- Zero ops for auth and DB for the first year+
- Data lives on Supabase servers (EU region available, GDPR compliant)
- Migration path is clear: `supabase db dump` + Docker on Dell
- Slight latency for DB queries (network hop to Supabase), acceptable for this workload

### ADR-004: Stripe Checkout (Hosted) vs Stripe Elements (Embedded)

**Status:** Accepted

**Decision:** Stripe Checkout (hosted page redirect), NOT Stripe Elements.

**Rationale:**
- Hosted checkout = zero PCI scope
- Apple Pay, Google Pay, SEPA, Bancontact, iDEAL all work automatically
- Stripe handles 3D Secure / SCA compliance
- We write ~50 lines of code instead of ~500
- Conversion rate is comparable (Stripe optimizes their checkout page continuously)
- Only downside: user leaves our site briefly (acceptable for a B2B tool)

---

## 12. RISK REGISTER

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Low initial signups | High | Medium | Free tier removes friction. SEO pages drive organic traffic. Zero customer acquisition cost. |
| Raster API quality issues | Medium | High | Already working. Iterative improvement. Users can manually edit detected walls. |
| Stripe account freeze | Low | Critical | BTCPay as backup payment rail. Keep Stripe volume under review thresholds. |
| Competitor copies features | Medium | Low | Our moat = local service rates DB + contractor relationships + BTC payments |
| GPU server downtime | Low | High | Self-heal watchdog. Dell as fallback. Static frontend works without raster API. |
| Supabase outage | Low | Medium | Auth tokens are JWTs (stateless). App works in degraded mode. Migrate to self-hosted if chronic. |
| Ogi sprint scope creep | High | Medium | This document defines scope. Day 5 is buffer. Cut features, never cut quality. |

---

## 13. POST-SPRINT ROADMAP

### Month 1 (April): Foundation
- Sprint deliverables live
- 10 beta users providing feedback
- 5 SEO pages indexed
- First paying customer

### Month 2 (May): Growth
- 10 more SEO landing pages (city-specific)
- Contractor onboarding flow (guided tutorial)
- Material/texture library expansion
- Mobile-responsive editor improvements
- Blog launched (AI-generated, weekly)

### Month 3 (June): Monetization
- Agency tier launched with team features
- API documentation published (for Pro/Agency)
- Referral program activated
- Integration with 1 supplier catalog (tiles or paint)
- First $500 MRR target

### Month 4-6 (Q3): Scale
- DXF/DWG export (architects need this)
- AR view (phone camera + floor plan overlay, experimental)
- Multi-language support (start with French, Italian, Arabic for Malta/EU/MENA)
- Partnership with 1 real estate agency
- Target: $1,000-2,000 MRR

### Month 7-12 (Q4 + Q1 2027): Expansion
- Self-hosted Supabase migration (if needed)
- Raster API on Dell (if needed)
- White-label offering for property management firms
- CubiCasa-style API for real estate listings
- Target: $5,000-10,000 MRR

---

## 14. FILES TO CREATE/MODIFY DURING SPRINT

### New Files

```
plano_master/
  backend/
    main.py                    -- FastAPI app (auth, payments, rates, plans)
    auth.py                    -- Supabase JWT middleware
    payments/
      stripe_handler.py        -- Stripe webhook + checkout session creation
      btcpay_handler.py        -- BTCPay webhook handler
    models.py                  -- Pydantic models (User, Plan, Rate, etc.)
    db.py                      -- Supabase client + direct SQL helpers
    tier_enforcement.py        -- Middleware for plan/export/API limits
    email.py                   -- Resend transactional email
    requirements.txt           -- fastapi, supabase, stripe, resend, etc.

  00_frontend_skeleton/plano-ui/src/
    lib/
      supabase.ts              -- Supabase client init
      stripe.ts                -- Stripe checkout redirect
      api.ts                   -- Backend API client
    context/
      AuthContext.tsx           -- Auth state provider
    pages/
      client/
        Login.tsx              -- Real login page (replaces placeholder)
        Signup.tsx             -- Registration page
        Pricing.tsx            -- Tier comparison + upgrade CTAs
        Dashboard.tsx          -- User dashboard (projects + usage)
        Profile.tsx            -- Account settings + subscription management
      marketing/
        Landing.tsx            -- Public landing page
        BathroomPlanner.tsx    -- SEO page
        KitchenPlanner.tsx     -- SEO page
    components/
      auth/
        AuthGuard.tsx          -- Protected route wrapper
        UpgradeModal.tsx       -- Shown when tier limit hit

  deploy/
    btcpay/
      docker-compose.btcpay.yml -- BTCPay + LND containers

  sql/
    001_schema.sql             -- Users, orgs, projects, usage, rates tables
    002_seed_rates.sql         -- Malta service rates seed data
```

### Modified Files

```
App.tsx                        -- Add auth context, protected routes, new pages
deploy/docker-compose.yml      -- Add backend service, BTCPay reference
deploy/nginx/default.conf      -- Add /api/auth, /api/payments, /api/rates proxies
deploy/Dockerfile              -- Add backend build stage
01_raster/server/app.py        -- Add auth middleware, usage tracking
plano_agents.py                -- Connect content agent to blog publishing
```

---

## 15. EXECUTIVE SUMMARY FOR OGI

**What we're building this week:**
A floor plan SaaS that makes money while we sleep.

**How it works:**
1. Contractor signs up (free, 10 seconds)
2. Uploads floor plan photo -> AI detects walls -> edits in 2D/3D
3. Gets instant renovation cost estimate
4. Hits free tier limit -> pays $9-49/month
5. Payment is automated (Stripe or Bitcoin)
6. Content, SEO, support, and growth are automated (15 AI agents)
7. We fix bugs and add features. Everything else runs itself.

**What it costs us:**
~$1/month in fixed costs. Stripe takes 1.5% per transaction. That's it.

**What it makes:**
Conservative: $1,100/month by end of Year 1.
Optimistic: $4,500/month by end of Year 1.

**What makes this different from competitors:**
- Cheapest in market ($9 vs MagicPlan $10, RoomSketcher $49)
- Only tool with built-in cost estimation using real local rates
- Accepts Bitcoin (no other floor plan tool does)
- AI-powered wall detection (upload photo, get floor plan)
- Near-zero operating costs (self-hosted everything)

**What we need from the sprint:**
5 focused days. Auth on Day 1, payments on Day 2, marketing on Day 3, pricing engine on Day 4, launch on Day 5. No scope creep.
