#!/usr/bin/env python3
"""
PlanO — Advertising & Marketing Automation Engine

Manages ALL paid + organic marketing channels autonomously.
Self-optimizes budgets based on CAC/LTV data from metrics_dashboard.

Usage:
    python3 ad_manager.py status          # all channels overview
    python3 ad_manager.py budget          # compute optimal budget allocation
    python3 ad_manager.py campaigns       # list active campaigns
    python3 ad_manager.py seo-audit       # technical SEO audit
    python3 ad_manager.py content-calendar # show publishing schedule
    python3 ad_manager.py utm-report      # campaign attribution
    python3 ad_manager.py train-export    # SFT pairs for marketing agents
"""

import json
import logging
import os
import sqlite3
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "marketing"
DB_PATH = DATA_DIR / "marketing.db"

logging.basicConfig(
    level=logging.DEBUG if os.environ.get("PLANO_DEBUG") else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("plano.marketing")


# ═══════════════════════════════════════════════════════════
# CHANNEL DEFINITIONS
# ═══════════════════════════════════════════════════════════

CHANNELS = {
    # ── PAID ──
    "google_ads": {
        "name": "Google Ads",
        "type": "paid",
        "markets": ["MT", "BG"],
        "monthly_budget_eur": 150,
        "cpc_estimate": {"MT": 0.80, "BG": 0.20},
        "conversion_rate": 0.03,
        "setup": "Google Ads account → campaigns per country → keyword groups",
        "keywords": {
            "MT": [
                "renovation cost malta", "floor plan malta", "bathroom renovation sliema",
                "kitchen renovation malta", "renovation planner", "construction estimate malta",
                "apartment renovation valletta", "contractor malta",
            ],
            "BG": [
                "ремонт цена", "ремонт апартамент софия", "баня ремонт цена",
                "строителен план", "ремонт калкулатор", "ремонт кухня цена",
                "строителна фирма софия", "ремонт пловдив",
            ],
        },
        "status": "planned",
        "api": "Google Ads API (needs account)",
    },
    "facebook_ads": {
        "name": "Facebook/Meta Ads",
        "type": "paid",
        "markets": ["MT", "BG"],
        "monthly_budget_eur": 100,
        "cpm_estimate": {"MT": 5.0, "BG": 1.5},
        "conversion_rate": 0.02,
        "setup": "Meta Business Suite → pixel on PlanO → campaigns",
        "audiences": {
            "MT": "Age 30-55, interests: home renovation, interior design, construction, property Malta",
            "BG": "Age 25-45, interests: ремонт, интериорен дизайн, строителство, имоти",
        },
        "retargeting": "Pixel tracks visitors → retarget non-converters after 3 days",
        "lookalike": "Build from first 100 converters → expand to 1% lookalike",
        "status": "planned",
        "api": "Meta Marketing API (needs account)",
    },
    "instagram_ads": {
        "name": "Instagram Ads (via Meta)",
        "type": "paid",
        "markets": ["MT", "BG"],
        "monthly_budget_eur": 50,
        "content": "Before/after renovation photos, 3D renders from PlanO, stories",
        "status": "planned",
    },

    # ── ORGANIC SEO ──
    "seo_content": {
        "name": "SEO Content Marketing",
        "type": "organic",
        "markets": ["MT", "BG", "EU"],
        "monthly_budget_eur": 0,
        "content_per_week": 3,
        "content_types": ["blog_article", "cost_guide", "how_to", "case_study"],
        "keyword_clusters": {
            "MT": {
                "renovation_cost": ["renovation cost malta", "bathroom cost malta", "kitchen cost malta"],
                "planning": ["floor plan malta", "building permit malta", "renovation planner"],
                "materials": ["tiles malta", "paint malta", "flooring malta prices"],
                "contractors": ["best contractor malta", "renovation company malta"],
            },
            "BG": {
                "renovation_cost": ["ремонт цена", "ремонт баня цена", "ремонт кухня цена"],
                "planning": ["план на апартамент", "строително разрешение", "калкулатор ремонт"],
                "materials": ["плочки цени", "боя за стени цени", "ламинат цена"],
                "contractors": ["строителна фирма софия", "ремонт фирма пловдив"],
            },
        },
        "technical_seo": {
            "schema_markup": "LocalBusiness + SoftwareApplication + FAQPage",
            "sitemap": "/plano/sitemap.xml",
            "robots": "/plano/robots.txt",
            "canonical_urls": True,
            "hreflang": {"en": "/plano/", "bg": "/plano/bg/"},
            "page_speed": "target < 3s LCP",
            "core_web_vitals": "all green",
        },
        "status": "partial",
    },

    # ── EMAIL ──
    "email_marketing": {
        "name": "Email Marketing (Resend)",
        "type": "organic",
        "markets": ["MT", "BG"],
        "monthly_budget_eur": 0,
        "provider": "Resend (free: 100 emails/day, 3000/month)",
        "sequences": {
            "welcome": "Day 0: Welcome + how to upload first plan. Day 1: Video tutorial. Day 3: Case study. Day 7: Upgrade CTA.",
            "onboarding": "Triggered on signup. 5-email sequence over 14 days. Personalized by country.",
            "dunning": "Payment failed → Day 0: Card update link. Day 3: Features expire warning. Day 7: Downgrade to free.",
            "winback": "Churned user → Day 0: We miss you. Day 7: New feature announcement. Day 30: Special offer.",
            "newsletter": "Weekly: renovation tips, cost updates, new features. Segmented by country.",
        },
        "status": "planned",
    },

    # ── SOCIAL ──
    "social_organic": {
        "name": "Social Media (Organic)",
        "type": "organic",
        "markets": ["MT", "BG"],
        "monthly_budget_eur": 0,
        "platforms": ["Facebook", "Instagram", "LinkedIn"],
        "posting_schedule": "Daily: 1 post/platform. Types: renovation tips, before/after, cost facts, product features.",
        "content_source": "AI-generated by Content Creator agent → auto-published",
        "status": "planned",
    },

    # ── LOCAL ──
    "local_seo": {
        "name": "Local SEO",
        "type": "organic",
        "markets": ["MT", "BG"],
        "monthly_budget_eur": 0,
        "actions": {
            "google_business": "Register PlanO on Google Business Profile for Malta + Bulgaria",
            "directories": "List on: Yellow Pages MT, olx.bg, imot.bg, MaltaPark, bazaraki.com",
            "citations": "NAP consistency across all listings (Name, Address, Phone)",
            "reviews": "Prompt users to review on Google after first project completion",
        },
        "status": "planned",
    },

    # ── REFERRAL ──
    "referral_program": {
        "name": "Referral Program",
        "type": "viral",
        "markets": ["MT", "BG"],
        "monthly_budget_eur": 0,
        "mechanism": "Contractor refers contractor → both get 1 month Pro free (Stripe coupon)",
        "tracking": "Unique referral links with UTM codes → track in metrics_dashboard",
        "viral_coefficient_target": 0.2,
        "status": "planned",
    },

    # ── PARTNERSHIPS ──
    "partnerships": {
        "name": "Material Supplier Partnerships",
        "type": "organic",
        "markets": ["MT", "BG"],
        "monthly_budget_eur": 0,
        "targets": {
            "MT": ["Sliema Tiles", "Home Depot Malta", "Tigne Hardware", "Vassallo Builders"],
            "BG": ["Praktiker BG", "Mr. Bricolage BG", "Bauhaus BG", "Bricoman BG"],
        },
        "model": "Embed supplier catalog in material picker → affiliate commission",
        "status": "planned",
    },
}


# ═══════════════════════════════════════════════════════════
# ANALYTICS & TRACKING
# ═══════════════════════════════════════════════════════════

TRACKING_SETUP = {
    "analytics": {
        "provider": "Plausible Analytics (self-hosted, GDPR compliant, no cookie consent needed)",
        "alternative": "Matomo (self-hosted) if more detail needed",
        "events": [
            "page_view", "signup", "login", "plan_upload", "plan_created",
            "estimate_viewed", "subscription_started", "subscription_cancelled",
            "referral_sent", "referral_converted",
        ],
    },
    "utm_system": {
        "format": "?utm_source={source}&utm_medium={medium}&utm_campaign={campaign}&utm_content={content}",
        "sources": ["google", "facebook", "instagram", "email", "referral", "organic", "direct"],
        "mediums": ["cpc", "cpm", "social", "email", "referral", "organic"],
    },
    "conversion_funnel": [
        "visit → signup (target: 3-5%)",
        "signup → active (target: 60%)",
        "active → plan_created (target: 40%)",
        "plan_created → paid (target: 8-12%)",
        "paid → retained_m2 (target: 92-96%)",
    ],
    "heatmap": {
        "provider": "Microsoft Clarity (free, GDPR compliant with consent)",
        "tracks": "clicks, scrolls, rage clicks, dead clicks, session recordings",
    },
}


# ═══════════════════════════════════════════════════════════
# BUDGET OPTIMIZER
# ═══════════════════════════════════════════════════════════

def compute_budget_allocation(mrr: float = 0, total_budget: float = 300) -> dict:
    """Compute optimal budget allocation across channels.

    Rules:
    - Spend max 30% of MRR on acquisition (if MRR > 0)
    - Organic channels = free, always active
    - Paid channels: allocate by expected ROI (LTV/CAC per channel)
    - Bulgaria gets more budget per dollar (lower CPC)
    - 25% budget reserve for experiments
    """
    if mrr > 0:
        total_budget = min(total_budget, mrr * 0.30)

    reserve = total_budget * 0.25  # Black Parade margin
    available = total_budget - reserve

    # Allocation by expected ROI
    allocation = {
        "google_ads_mt": available * 0.25,
        "google_ads_bg": available * 0.20,
        "facebook_ads_mt": available * 0.15,
        "facebook_ads_bg": available * 0.15,
        "instagram_bg": available * 0.05,
        "instagram_mt": available * 0.05,
        "experiment_reserve": reserve,
        "organic_seo": 0,  # free
        "email": 0,  # free (Resend)
        "social_organic": 0,  # free
        "referral": 0,  # free (costs = Stripe coupons)
    }

    # Estimate results
    clicks_mt = allocation["google_ads_mt"] / 0.80 + allocation["facebook_ads_mt"] / (5.0 / 1000 * 3)
    clicks_bg = allocation["google_ads_bg"] / 0.20 + allocation["facebook_ads_bg"] / (1.5 / 1000 * 3)
    signups_mt = clicks_mt * 0.03
    signups_bg = clicks_bg * 0.03
    paid_mt = signups_mt * 0.05
    paid_bg = signups_bg * 0.05

    return {
        "total_budget": total_budget,
        "available_after_reserve": available,
        "allocation": allocation,
        "estimated_clicks": {"MT": int(clicks_mt), "BG": int(clicks_bg)},
        "estimated_signups": {"MT": int(signups_mt), "BG": int(signups_bg)},
        "estimated_conversions": {"MT": int(paid_mt), "BG": int(paid_bg)},
        "estimated_cac": {
            "MT": round(allocation["google_ads_mt"] / max(paid_mt, 1), 2),
            "BG": round(allocation["google_ads_bg"] / max(paid_bg, 1), 2),
        },
    }


# ═══════════════════════════════════════════════════════════
# CONTENT CALENDAR
# ═══════════════════════════════════════════════════════════

def generate_content_calendar(weeks: int = 4) -> list:
    """Generate a content calendar for the next N weeks."""
    calendar = []
    topics_mt = [
        "How Much Does a Bathroom Renovation Cost in Malta?",
        "Kitchen Renovation Guide Malta 2026",
        "Malta Planning Permission: What You Need to Know",
        "Best Floor Tiles for Maltese Apartments",
        "Renovation Cost Calculator: Get Instant Estimates",
        "5 Mistakes to Avoid When Renovating in Malta",
        "Limestone Restoration: A Maltese Building Guide",
        "Smart Home Renovation on a Budget in Malta",
    ]
    topics_bg = [
        "Колко струва ремонт на апартамент в София 2026?",
        "Ремонт на баня — пълен справочник на цените",
        "Панелно жилище ремонт: какво трябва да знаете",
        "Най-добрите плочки за баня на достъпна цена",
        "Калкулатор за ремонт: безплатна оценка за минути",
        "5 грешки при ремонт, които да избягвате",
        "Субсидии за енергийна ефективност на жилища в България",
        "Ремонт на кухня — материали и цени 2026",
    ]
    social_types = ["renovation_tip", "before_after", "cost_fact", "product_feature", "user_story"]

    from datetime import date
    start = date.today()
    for week in range(weeks):
        week_start = start + timedelta(weeks=week)
        calendar.append({
            "week": week + 1,
            "start": str(week_start),
            "blog_mt": topics_mt[week % len(topics_mt)],
            "blog_bg": topics_bg[week % len(topics_bg)],
            "social_posts": 7,
            "social_types": social_types[:3],
            "email": "weekly_newsletter" if week % 1 == 0 else None,
        })
    return calendar


# ═══════════════════════════════════════════════════════════
# SEO AUDIT
# ═══════════════════════════════════════════════════════════

def seo_audit() -> list:
    """Technical SEO audit for PlanO."""
    checks = []

    # Check robots.txt
    import subprocess
    try:
        r = subprocess.run(["ssh", "gpu", "curl -s http://localhost:8031/plano/robots.txt"],
                          capture_output=True, text=True, timeout=10)
        has_robots = "User-agent" in r.stdout
        checks.append(("robots.txt", has_robots, r.stdout[:100] if has_robots else "MISSING"))
    except Exception:
        checks.append(("robots.txt", False, "Cannot check"))

    # Check sitemap
    try:
        r = subprocess.run(["ssh", "gpu", "curl -s -o /dev/null -w '%{http_code}' http://localhost:8031/plano/sitemap.xml"],
                          capture_output=True, text=True, timeout=10)
        checks.append(("sitemap.xml", r.stdout.strip() == "200", f"HTTP {r.stdout.strip()}"))
    except Exception:
        checks.append(("sitemap.xml", False, "Cannot check"))

    # Check meta tags
    try:
        r = subprocess.run(["ssh", "gpu", "curl -s http://localhost:8031/plano/ | grep -c 'meta'"],
                          capture_output=True, text=True, timeout=10)
        meta_count = int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0
        checks.append(("meta_tags", meta_count >= 3, f"{meta_count} meta tags"))
    except Exception:
        checks.append(("meta_tags", False, "Cannot check"))

    # Check title
    try:
        r = subprocess.run(["ssh", "gpu", "curl -s http://localhost:8031/plano/ | grep -oP '<title>.*?</title>'"],
                          capture_output=True, text=True, timeout=10)
        checks.append(("page_title", bool(r.stdout.strip()), r.stdout.strip()[:50]))
    except Exception:
        checks.append(("page_title", False, "Cannot check"))

    # Schema markup
    checks.append(("schema_markup", False, "NOT IMPLEMENTED — need JSON-LD for SoftwareApplication"))
    checks.append(("hreflang", False, "NOT IMPLEMENTED — need bg/en language tags"))
    checks.append(("canonical_url", False, "NOT IMPLEMENTED — need <link rel=canonical>"))
    checks.append(("open_graph", False, "NOT IMPLEMENTED — need og: meta tags for social sharing"))

    return checks


# ═══════════════════════════════════════════════════════════
# SFT EXPORT
# ═══════════════════════════════════════════════════════════

def generate_training_data() -> list:
    """Generate SFT pairs for marketing agents."""
    pairs = []

    budget = compute_budget_allocation(500, 300)
    pairs.append({
        "messages": [
            {"role": "system", "content": "You are the Marketing Strategist for PlanO, a renovation SaaS targeting Malta and Bulgaria."},
            {"role": "user", "content": f"MRR is €500. Budget €300/month. How should we allocate across channels?"},
            {"role": "assistant", "content": json.dumps(budget["allocation"], indent=2)},
        ]
    })

    calendar = generate_content_calendar(4)
    pairs.append({
        "messages": [
            {"role": "system", "content": "You are the Content Creator for PlanO."},
            {"role": "user", "content": "Generate a 4-week content calendar for Malta and Bulgaria."},
            {"role": "assistant", "content": json.dumps(calendar, indent=2)},
        ]
    })

    seo = seo_audit()
    pairs.append({
        "messages": [
            {"role": "system", "content": "You are the SEO Optimizer for PlanO."},
            {"role": "user", "content": "Run a technical SEO audit on hacking.eu/plano/."},
            {"role": "assistant", "content": "\n".join(f"{'PASS' if c[1] else 'FAIL'}: {c[0]} — {c[2]}" for c in seo)},
        ]
    })

    return pairs


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "status":
        print("\n" + "=" * 70)
        print("  PlanO Marketing Automation — Channel Overview")
        print("=" * 70)
        total = 0
        for cid, ch in CHANNELS.items():
            budget = ch.get("monthly_budget_eur", 0)
            total += budget
            status = ch.get("status", "unknown")
            print(f"  {ch['name']:35} €{budget:>6}/mo  [{ch['type']:8}]  {status}")
        print(f"\n  Total monthly ad spend: €{total}")
        print(f"  Organic channels: {sum(1 for c in CHANNELS.values() if c.get('monthly_budget_eur', 0) == 0)}")

    elif cmd == "budget":
        budget = compute_budget_allocation()
        print(json.dumps(budget, indent=2))

    elif cmd == "campaigns":
        print("\nActive campaigns: NONE (pre-launch)")
        print("Planned:")
        for cid, ch in CHANNELS.items():
            if ch["type"] == "paid":
                for market in ch.get("markets", []):
                    print(f"  {ch['name']} ({market}): €{ch.get('monthly_budget_eur', 0)/len(ch.get('markets', [1])):.0f}/mo")

    elif cmd == "seo-audit":
        checks = seo_audit()
        print(f"\n{'Check':25} {'Status':8} Details")
        print("-" * 60)
        for name, passed, details in checks:
            status = "PASS" if passed else "FAIL"
            print(f"  {name:23} {status:8} {details}")
        passed = sum(1 for _, p, _ in checks if p)
        print(f"\n  SEO Score: {passed}/{len(checks)}")

    elif cmd == "content-calendar":
        cal = generate_content_calendar()
        for w in cal:
            print(f"\n  Week {w['week']} ({w['start']}):")
            print(f"    MT: {w['blog_mt']}")
            print(f"    BG: {w['blog_bg']}")
            print(f"    Social: {w['social_posts']} posts ({', '.join(w['social_types'])})")

    elif cmd == "utm-report":
        print("\nUTM tracking configured:")
        print(f"  Sources: {', '.join(TRACKING_SETUP['utm_system']['sources'])}")
        print(f"  Mediums: {', '.join(TRACKING_SETUP['utm_system']['mediums'])}")
        print(f"  Funnel: {' → '.join(TRACKING_SETUP['conversion_funnel'])}")

    elif cmd == "train-export":
        pairs = generate_training_data()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        out = DATA_DIR / "marketing_sft.jsonl"
        with open(out, "w") as f:
            for p in pairs:
                f.write(json.dumps(p) + "\n")
        print(f"Exported {len(pairs)} SFT pairs to {out}")

    else:
        print(__doc__)
