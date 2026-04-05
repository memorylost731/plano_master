#!/usr/bin/env python3
"""
PlanO Business Simulator — Monte Carlo growth model with OSINT data pipeline.

Simulates company trajectory from launch to exit using real market data.
Outputs SFT training pairs for the 15 SaaS agents.

Usage:
    python3 simulator.py run [--months 36] [--simulations 1000]
    python3 simulator.py scenario --name aggressive|conservative|base
    python3 simulator.py osint --update          # refresh real-world data
    python3 simulator.py train-export            # generate agent training data
    python3 simulator.py dashboard               # print current projection

DEBUG: PLANO_DEBUG=1 for verbose output
"""

import json
import logging
import math
import os
import random
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "business_sim"
OSINT_DIR = DATA_DIR / "osint"
TRAINING_DIR = DATA_DIR / "agent_training"

logging.basicConfig(
    level=logging.DEBUG if os.environ.get("PLANO_DEBUG") else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("plano.simulator")


# ═══════════════════════════════════════════════════════════
# OSINT DATA PIPELINE — Real-world market intelligence
# ═══════════════════════════════════════════════════════════

@dataclass
class OSINTData:
    """Real-world data collected from public sources."""
    timestamp: str = ""

    # Malta market
    mt_population: int = 520_000
    mt_construction_permits_annual: int = 3_800  # Malta PA annual permits
    mt_renovation_market_eur: int = 300_000_000
    mt_avg_renovation_cost_eur: int = 25_000
    mt_contractors_registered: int = 2_200  # MBR estimate
    mt_internet_penetration: float = 0.87
    mt_smartphone_penetration: float = 0.82
    mt_avg_income_eur: int = 22_000

    # Bulgaria market
    bg_population: int = 6_500_000
    bg_construction_permits_annual: int = 28_000  # NSI Bulgaria
    bg_renovation_market_eur: int = 1_500_000_000
    bg_avg_renovation_cost_eur: int = 8_000
    bg_contractors_registered: int = 12_000  # KSB estimate
    bg_internet_penetration: float = 0.72
    bg_smartphone_penetration: float = 0.68
    bg_avg_income_eur: int = 9_500
    bg_eu_renovation_fund_eur: int = 500_000_000  # EU structural funds for BG renovation

    # SaaS benchmarks
    saas_avg_monthly_churn: float = 0.05  # 5% monthly churn (SMB SaaS)
    saas_organic_conversion_rate: float = 0.02  # 2% visitor → signup
    saas_free_to_paid_rate: float = 0.04  # 4% free → paid
    saas_viral_coefficient: float = 0.15  # each user brings 0.15 new users
    saas_arr_multiple_exit: float = 7.0  # median SaaS exit multiple 2025
    saas_arr_multiple_range: tuple = (5.0, 12.0)

    # Competitor intelligence
    competitors_mt: list = field(default_factory=lambda: [])
    competitors_bg: list = field(default_factory=lambda: [])

    # Economic indicators
    eur_bgn_rate: float = 1.9558  # fixed peg
    mt_inflation_rate: float = 0.028
    bg_inflation_rate: float = 0.035
    ecb_interest_rate: float = 0.035

    def to_dict(self) -> dict:
        return asdict(self)


def fetch_osint() -> OSINTData:
    """Fetch real-world data from public APIs and sources.

    Sources:
    - Eurostat API (population, income, construction)
    - World Bank API (economic indicators)
    - ECB API (interest rates, exchange rates)
    - Malta PA (building permits — cached, Cloudflare blocks)
    - NSI Bulgaria (construction stats)
    """
    data = OSINTData(timestamp=datetime.now(timezone.utc).isoformat())

    # Eurostat REST API — population
    try:
        url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/demo_pjan?geo=MT&geo=BG&time=2024&age=TOTAL&sex=T"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            values = result.get("value", {})
            # Parse Eurostat response
            if values:
                log.info("Eurostat population data retrieved")
    except Exception as e:
        log.warning("Eurostat API failed: %s — using defaults", e)

    # World Bank — GDP per capita
    try:
        for country, attr in [("MLT", "mt_avg_income_eur"), ("BGR", "bg_avg_income_eur")]:
            url = f"https://api.worldbank.org/v2/country/{country}/indicator/NY.GDP.PCAP.CD?date=2023&format=json"
            with urllib.request.urlopen(url, timeout=10) as resp:
                result = json.loads(resp.read())
                if len(result) > 1 and result[1]:
                    val = result[1][0].get("value")
                    if val:
                        setattr(data, attr, int(val))
                        log.info("%s GDP/capita: €%d", country, int(val))
    except Exception as e:
        log.warning("World Bank API failed: %s", e)

    # ECB exchange rate API
    try:
        url = "https://data-api.ecb.europa.eu/service/data/EXR/D.BGN.EUR.SP00.A?lastNObservations=1&format=jsondata"
        with urllib.request.urlopen(url, timeout=10) as resp:
            result = json.loads(resp.read())
            log.info("ECB rate data retrieved")
    except Exception as e:
        log.warning("ECB API failed: %s — BGN/EUR rate is fixed peg anyway", e)

    # Save OSINT snapshot
    OSINT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_file = OSINT_DIR / f"snapshot_{datetime.now().strftime('%Y%m%d')}.json"
    snapshot_file.write_text(json.dumps(data.to_dict(), indent=2))

    # Also save as latest
    (OSINT_DIR / "latest.json").write_text(json.dumps(data.to_dict(), indent=2))

    log.info("OSINT data saved to %s", snapshot_file)
    return data


def load_osint() -> OSINTData:
    """Load latest OSINT data or fetch if stale (>7 days)."""
    latest = OSINT_DIR / "latest.json"
    if latest.exists():
        raw = json.loads(latest.read_text())
        ts = raw.get("timestamp", "")
        if ts:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(ts)
            if age.days < 7:
                log.info("Using cached OSINT data (%.1f days old)", age.total_seconds() / 86400)
                d = OSINTData()
                for k, v in raw.items():
                    if hasattr(d, k) and k != "timestamp":
                        setattr(d, k, v)
                d.timestamp = ts
                return d
    log.info("OSINT data stale or missing — fetching fresh")
    return fetch_osint()


# ═══════════════════════════════════════════════════════════
# BUSINESS MODEL — Monthly state machine
# ═══════════════════════════════════════════════════════════

@dataclass
class MonthState:
    """State of the business at a given month."""
    month: int = 0
    date: str = ""

    # Users
    visitors_mt: int = 0
    visitors_bg: int = 0
    signups_mt: int = 0
    signups_bg: int = 0
    free_users: int = 0
    paid_users_mt: int = 0
    paid_users_bg: int = 0
    churned: int = 0

    # Revenue
    mrr_eur: float = 0
    arr_eur: float = 0
    total_revenue_eur: float = 0
    costs_eur: float = 0
    profit_eur: float = 0
    cumulative_profit_eur: float = 0

    # Metrics
    arpu_eur: float = 0
    churn_rate: float = 0
    cac_eur: float = 0
    ltv_eur: float = 0
    ltv_cac_ratio: float = 0

    # Growth
    organic_growth_rate: float = 0
    paid_growth_rate: float = 0
    viral_growth_rate: float = 0
    ad_spend_eur: float = 0

    # Valuation
    valuation_eur: float = 0
    ogi_equity_eur: float = 0
    hadrien_equity_eur: float = 0

    # Agents
    agent_content_pieces: int = 0
    agent_support_tickets_resolved: int = 0
    agent_autonomy_level: float = 0  # 0-4 scale

    # Rasta
    plans_processed: int = 0
    rasta_accuracy: float = 0.91


@dataclass
class ScenarioParams:
    """Tunable parameters for different growth scenarios."""
    name: str = "base"

    # Traffic
    initial_visitors_mt: int = 200
    initial_visitors_bg: int = 100
    visitor_growth_monthly: float = 0.15  # 15% MoM organic
    seo_ramp_months: int = 4  # months for SEO to fully kick in

    # Conversion
    visitor_to_signup: float = 0.03  # 3%
    signup_to_paid: float = 0.05  # 5%
    monthly_churn: float = 0.04  # 4%

    # Pricing
    arpu_mt: float = 12.0  # weighted avg across tiers
    arpu_bg: float = 6.0

    # Costs
    fixed_costs_monthly: float = 50.0  # server, BDO amortized, domain
    ad_spend_start: float = 150.0  # €/month
    ad_spend_max: float = 2000.0
    ad_cpc_mt: float = 0.80  # cost per click
    ad_cpc_bg: float = 0.20

    # Viral
    viral_coefficient: float = 0.12
    referral_bonus_months: int = 1

    # Agent autonomy ramp
    autonomy_month_1: float = 0.5  # L0.5
    autonomy_month_6: float = 2.0  # L2
    autonomy_month_12: float = 3.5  # L3.5

    # Exit
    target_valuation: float = 16_700_000  # €16.7M (Ogi's 60% = €10M)
    arr_multiple: float = 7.0


SCENARIOS = {
    "conservative": ScenarioParams(
        name="conservative",
        initial_visitors_mt=100, initial_visitors_bg=50,
        visitor_growth_monthly=0.10, visitor_to_signup=0.02,
        signup_to_paid=0.03, monthly_churn=0.06,
        ad_spend_start=50, arpu_mt=10, arpu_bg=5,
        arr_multiple=5.0,
    ),
    "base": ScenarioParams(name="base"),
    "aggressive": ScenarioParams(
        name="aggressive",
        initial_visitors_mt=500, initial_visitors_bg=300,
        visitor_growth_monthly=0.25, visitor_to_signup=0.05,
        signup_to_paid=0.08, monthly_churn=0.03,
        ad_spend_start=500, ad_spend_max=5000,
        arpu_mt=15, arpu_bg=8, arr_multiple=10.0,
    ),
}


def simulate_month(prev: MonthState, params: ScenarioParams, osint: OSINTData,
                   month: int, rng: random.Random) -> MonthState:
    """Simulate one month of business operation."""
    s = MonthState()
    s.month = month
    s.date = (datetime(2026, 5, 1) + timedelta(days=30 * month)).strftime("%Y-%m")

    # Agent autonomy ramp
    if month <= 6:
        s.agent_autonomy_level = params.autonomy_month_1 + (params.autonomy_month_6 - params.autonomy_month_1) * (month / 6)
    elif month <= 12:
        s.agent_autonomy_level = params.autonomy_month_6 + (params.autonomy_month_12 - params.autonomy_month_6) * ((month - 6) / 6)
    else:
        s.agent_autonomy_level = min(4.0, params.autonomy_month_12 + 0.05 * (month - 12))

    # SEO ramp factor (takes months to build organic traffic)
    seo_factor = min(1.0, month / params.seo_ramp_months)

    # Traffic (organic + paid + viral)
    organic_mt = int(params.initial_visitors_mt * (1 + params.visitor_growth_monthly) ** month * seo_factor)
    organic_bg = int(params.initial_visitors_bg * (1 + params.visitor_growth_monthly) ** month * seo_factor)

    # Ad spend scales with revenue (reinvest)
    if prev.mrr_eur > 0:
        s.ad_spend_eur = min(params.ad_spend_max, max(params.ad_spend_start, prev.mrr_eur * 0.3))
    else:
        s.ad_spend_eur = params.ad_spend_start

    paid_clicks_mt = int(s.ad_spend_eur * 0.6 / params.ad_cpc_mt) if params.ad_cpc_mt > 0 else 0
    paid_clicks_bg = int(s.ad_spend_eur * 0.4 / params.ad_cpc_bg) if params.ad_cpc_bg > 0 else 0

    # Viral (existing users bring new visitors)
    viral_visitors = int((prev.paid_users_mt + prev.paid_users_bg) * params.viral_coefficient * 10)

    s.visitors_mt = organic_mt + paid_clicks_mt + int(viral_visitors * 0.4)
    s.visitors_bg = organic_bg + paid_clicks_bg + int(viral_visitors * 0.6)

    # Signups
    noise = rng.gauss(1.0, 0.1)  # ±10% randomness
    s.signups_mt = max(0, int(s.visitors_mt * params.visitor_to_signup * noise))
    s.signups_bg = max(0, int(s.visitors_bg * params.visitor_to_signup * noise))

    # Conversions (free → paid)
    new_paid_mt = max(0, int(s.signups_mt * params.signup_to_paid * rng.gauss(1, 0.15)))
    new_paid_bg = max(0, int(s.signups_bg * params.signup_to_paid * rng.gauss(1, 0.15)))

    # Churn
    churn_noise = rng.gauss(1.0, 0.1)
    churn_mt = int(prev.paid_users_mt * params.monthly_churn * churn_noise)
    churn_bg = int(prev.paid_users_bg * params.monthly_churn * churn_noise)
    s.churned = churn_mt + churn_bg

    # Net users
    s.paid_users_mt = max(0, prev.paid_users_mt + new_paid_mt - churn_mt)
    s.paid_users_bg = max(0, prev.paid_users_bg + new_paid_bg - churn_bg)
    s.free_users = prev.free_users + s.signups_mt + s.signups_bg - new_paid_mt - new_paid_bg

    # Revenue
    s.mrr_eur = s.paid_users_mt * params.arpu_mt + s.paid_users_bg * params.arpu_bg
    s.arr_eur = s.mrr_eur * 12

    # Costs (scale with autonomy — less human cost at higher autonomy)
    human_cost_factor = max(0.1, 1.0 - s.agent_autonomy_level * 0.2)  # L4 = 20% of human cost
    s.costs_eur = params.fixed_costs_monthly + s.ad_spend_eur + (500 * human_cost_factor)  # €500 baseline human ops

    s.profit_eur = s.mrr_eur - s.costs_eur
    s.total_revenue_eur = prev.total_revenue_eur + s.mrr_eur
    s.cumulative_profit_eur = prev.cumulative_profit_eur + s.profit_eur

    # Metrics
    total_paid = s.paid_users_mt + s.paid_users_bg
    s.arpu_eur = s.mrr_eur / max(total_paid, 1)
    s.churn_rate = s.churned / max(prev.paid_users_mt + prev.paid_users_bg, 1)
    total_signups = s.signups_mt + s.signups_bg
    s.cac_eur = s.ad_spend_eur / max(new_paid_mt + new_paid_bg, 1)
    s.ltv_eur = s.arpu_eur / max(params.monthly_churn, 0.01)
    s.ltv_cac_ratio = s.ltv_eur / max(s.cac_eur, 1)

    # Valuation
    s.valuation_eur = s.arr_eur * params.arr_multiple
    s.ogi_equity_eur = s.valuation_eur * 0.60
    s.hadrien_equity_eur = s.valuation_eur * 0.40

    # Rasta usage
    s.plans_processed = prev.plans_processed + s.signups_mt + s.signups_bg
    s.rasta_accuracy = min(0.98, 0.91 + month * 0.003)  # improves with more data

    # Agent output
    s.agent_content_pieces = int(12 * s.agent_autonomy_level)  # scales with autonomy
    s.agent_support_tickets_resolved = int(total_paid * 0.1 * s.agent_autonomy_level)

    return s


def run_simulation(params: ScenarioParams, osint: OSINTData,
                   months: int = 36, seed: Optional[int] = None) -> list[MonthState]:
    """Run a single simulation trajectory."""
    rng = random.Random(seed)
    states = [MonthState()]  # month 0

    for m in range(1, months + 1):
        state = simulate_month(states[-1], params, osint, m, rng)
        states.append(state)

    return states


def run_monte_carlo(params: ScenarioParams, osint: OSINTData,
                    months: int = 36, simulations: int = 1000) -> dict:
    """Run Monte Carlo simulation — returns percentile distributions."""
    all_runs = []
    for i in range(simulations):
        trajectory = run_simulation(params, osint, months, seed=i)
        all_runs.append(trajectory)

    # Compute percentiles at each month
    results = {"scenario": params.name, "months": months, "simulations": simulations, "monthly": []}

    for m in range(months + 1):
        month_data = [run[m] for run in all_runs]

        mrrs = sorted([s.mrr_eur for s in month_data])
        users = sorted([s.paid_users_mt + s.paid_users_bg for s in month_data])
        vals = sorted([s.valuation_eur for s in month_data])
        ogi_eq = sorted([s.ogi_equity_eur for s in month_data])

        n = len(mrrs)
        results["monthly"].append({
            "month": m,
            "date": month_data[0].date,
            "mrr_p10": mrrs[int(n * 0.1)],
            "mrr_p50": mrrs[int(n * 0.5)],
            "mrr_p90": mrrs[int(n * 0.9)],
            "users_p10": users[int(n * 0.1)],
            "users_p50": users[int(n * 0.5)],
            "users_p90": users[int(n * 0.9)],
            "valuation_p50": vals[int(n * 0.5)],
            "ogi_equity_p50": ogi_eq[int(n * 0.5)],
            "autonomy": month_data[0].agent_autonomy_level,
            "rasta_accuracy": month_data[0].rasta_accuracy,
        })

    # Find when Ogi hits €10M
    for md in results["monthly"]:
        if md["ogi_equity_p50"] >= 10_000_000:
            results["ogi_10m_month"] = md["month"]
            results["ogi_10m_date"] = md["date"]
            break
    else:
        results["ogi_10m_month"] = None

    return results


# ═══════════════════════════════════════════════════════════
# AGENT TRAINING DATA EXPORT
# ═══════════════════════════════════════════════════════════

def generate_agent_training_data(sim_results: dict) -> list[dict]:
    """Generate SFT training pairs from simulation results for the 15 agents.

    Each pair: {"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}
    """
    pairs = []
    monthly = sim_results["monthly"]

    for m in monthly:
        if m["month"] == 0:
            continue

        # CEO Agent — strategic decisions
        pairs.append({
            "messages": [
                {"role": "system", "content": "You are the CEO Agent of PlanO, a renovation SaaS. You make strategic decisions based on business metrics."},
                {"role": "user", "content": f"Month {m['month']} ({m['date']}): MRR €{m['mrr_p50']:.0f}, {m['users_p50']} paid users, valuation €{m['valuation_p50']:,.0f}. Agent autonomy level: {m['autonomy']:.1f}/4. What are the top 3 priorities?"},
                {"role": "assistant", "content": _ceo_response(m, sim_results)},
            ]
        })

        # Marketing Strategist — campaign decisions
        if m["month"] % 3 == 0:  # quarterly
            pairs.append({
                "messages": [
                    {"role": "system", "content": "You are the Marketing Strategist for PlanO. You plan campaigns for Malta and Bulgaria markets."},
                    {"role": "user", "content": f"Q{(m['month']-1)//3+1} review: {m['users_p50']} users ({m['users_p10']}-{m['users_p90']} range). MRR €{m['mrr_p50']:.0f}. What marketing campaigns should we run next quarter?"},
                    {"role": "assistant", "content": _marketing_response(m)},
                ]
            })

        # Pricing Analyst — pricing optimization
        if m["month"] % 6 == 0:
            pairs.append({
                "messages": [
                    {"role": "system", "content": "You are the Pricing Analyst for PlanO. You optimize pricing for Malta (EUR) and Bulgaria (BGN)."},
                    {"role": "user", "content": f"6-month review: ARPU trend, churn data, competitor pricing. MRR €{m['mrr_p50']:.0f}. Should we adjust pricing?"},
                    {"role": "assistant", "content": _pricing_response(m)},
                ]
            })

        # Growth Hacker — experiments
        pairs.append({
            "messages": [
                {"role": "system", "content": "You are the Growth Hacker for PlanO. You design viral growth experiments."},
                {"role": "user", "content": f"Month {m['month']}: viral coefficient at baseline. {m['users_p50']} users. Suggest 2 growth experiments."},
                {"role": "assistant", "content": _growth_response(m)},
            ]
        })

    return pairs


def _ceo_response(m: dict, sim: dict) -> str:
    priorities = []
    if m["users_p50"] < 100:
        priorities.append("1. ACQUISITION: Below 100 users — focus all energy on customer acquisition. Double ad spend if CAC < LTV/3.")
    elif m["users_p50"] < 1000:
        priorities.append("1. RETENTION: Churn is the priority now. Ensure onboarding flow converts free→paid at >5%.")
    else:
        priorities.append("1. SCALE: Over 1000 users — optimize unit economics and prepare for geographic expansion.")

    if m["autonomy"] < 2.0:
        priorities.append(f"2. AUTOMATION: Agent autonomy at L{m['autonomy']:.1f}. Push to L2 — agents should publish content without human review.")
    else:
        priorities.append(f"2. EFFICIENCY: Agent autonomy at L{m['autonomy']:.1f}. Reduce remaining human touchpoints.")

    target_month = sim.get("ogi_10m_month")
    if target_month and m["month"] < target_month:
        remaining = target_month - m["month"]
        priorities.append(f"3. EXIT PREP: €10M target in ~{remaining} months. Current valuation €{m['valuation_p50']:,.0f}. {'On track.' if remaining < 24 else 'Need to accelerate growth.'}")
    elif m["valuation_p50"] >= 16_700_000:
        priorities.append("3. EXIT READY: Valuation exceeds €16.7M target. Begin data room preparation and SaaS fund outreach.")
    else:
        priorities.append(f"3. GROWTH: Valuation €{m['valuation_p50']:,.0f} vs €16.7M target. Focus on ARR growth.")

    return "\n".join(priorities)


def _marketing_response(m: dict) -> str:
    return f"""Next quarter marketing plan:

**Malta (MT):**
- SEO: Publish 12 articles targeting "renovation cost Malta", "bathroom renovation Sliema", "planning permission MT"
- Facebook Ads: €{min(500, m['mrr_p50'] * 0.2):.0f}/month targeting homeowners 30-55, interests: home renovation, interior design
- Referral: Launch contractor referral program — both parties get 1 month Pro free

**Bulgaria (BG):**
- SEO: 12 articles in Bulgarian — "ремонт апартамент цена", "панелно жилище ремонт София"
- Facebook/Instagram Ads: €{min(300, m['mrr_p50'] * 0.15):.0f}/month targeting 25-45, interests: ремонт, интериорен дизайн
- OLX.bg partnership: list PlanO in construction services category

**Cross-market:**
- Google Ads: €{min(200, m['mrr_p50'] * 0.1):.0f}/month on branded + competitor keywords
- Content: Before/after renovation showcases from real PlanO users"""


def _pricing_response(m: dict) -> str:
    return f"""Pricing analysis:

Current MRR: €{m['mrr_p50']:.0f} from {m['users_p50']} users.

**Recommendation:** {'HOLD current pricing' if m['users_p50'] < 500 else 'Consider 10-15% price increase on new signups'}.

Rationale:
- Malta ARPU healthy at €12 — aligned with MagicPlan ($10) and below RoomSketcher ($49)
- Bulgaria ARPU at €6 — appropriate for local purchasing power (avg income €9.5K)
- {'Too early to optimize pricing — focus on acquisition' if m['users_p50'] < 200 else 'Enough data to A/B test pricing tiers'}
- Annual discount (20%) conversion rate should be tracked — push annual for lower churn"""


def _growth_response(m: dict) -> str:
    return f"""Growth experiments for month {m['month']}:

**Experiment 1: Shareable project links**
- Hypothesis: Users who share their renovation plans bring 2-3 visitors each
- Implementation: "Share with contractor" button → generates public URL with "Made with PlanO" badge
- Success metric: viral coefficient > 0.2 (currently ~0.12)
- Effort: 2 days frontend

**Experiment 2: {'Free renovation cost calculator (lead magnet)' if m['users_p50'] < 200 else 'Contractor leaderboard + reviews'}**
- Hypothesis: {'Standalone cost calculator page converts 5% of visitors to PlanO signup' if m['users_p50'] < 200 else 'Contractors promote PlanO to win reviews'}
- Implementation: {'Landing page with room-by-room cost calculator → "Get full plan with PlanO" CTA' if m['users_p50'] < 200 else 'Public contractor profiles with PlanO project showcase'}
- Success metric: {'200+ calculator uses/month, 10+ signups' if m['users_p50'] < 200 else '50+ contractor profiles, 20% referral increase'}"""


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def print_dashboard(results: dict):
    """Print simulation dashboard."""
    print("=" * 80)
    print(f"  PlanO Business Simulator — {results['scenario'].upper()} scenario")
    print(f"  {results['simulations']} simulations, {results['months']} months")
    print("=" * 80)
    print()
    print(f"{'Month':>6} {'Date':>8} {'Users(p50)':>10} {'MRR(p50)':>10} {'Valuation':>14} {'Ogi Equity':>14} {'Auto':>5}")
    print("-" * 80)

    for m in results["monthly"]:
        if m["month"] % 3 == 0 or m["month"] <= 3:
            flag = ""
            if m["ogi_equity_p50"] >= 10_000_000:
                flag = " *** €10M TARGET ***"
            print(f"{m['month']:>6} {m['date']:>8} {m['users_p50']:>10,} {m['mrr_p50']:>9,.0f}€ {m['valuation_p50']:>13,.0f}€ {m['ogi_equity_p50']:>13,.0f}€ {m['autonomy']:>4.1f}{flag}")

    print()
    if results.get("ogi_10m_month"):
        print(f"  Ogi reaches €10M equity at month {results['ogi_10m_month']} ({results['ogi_10m_date']})")
    else:
        print(f"  Ogi does NOT reach €10M in {results['months']} months — need more growth or longer timeline")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "osint":
        fetch_osint()

    elif cmd == "run":
        months = 36
        sims = 1000
        for i, arg in enumerate(sys.argv[2:], 2):
            if arg == "--months" and i + 1 < len(sys.argv):
                months = int(sys.argv[i + 1])
            if arg == "--simulations" and i + 1 < len(sys.argv):
                sims = int(sys.argv[i + 1])

        osint = load_osint()
        params = SCENARIOS["base"]
        results = run_monte_carlo(params, osint, months, sims)
        print_dashboard(results)

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "latest_simulation.json").write_text(json.dumps(results, indent=2, default=str))

    elif cmd == "scenario":
        name = sys.argv[3] if len(sys.argv) > 3 else "base"
        osint = load_osint()
        params = SCENARIOS.get(name, SCENARIOS["base"])
        results = run_monte_carlo(params, osint, 36, 1000)
        print_dashboard(results)

    elif cmd == "train-export":
        osint = load_osint()
        params = SCENARIOS["base"]
        trajectory = run_simulation(params, osint, 36, seed=42)
        sim_results = run_monte_carlo(params, osint, 36, 100)
        pairs = generate_agent_training_data(sim_results)

        TRAINING_DIR.mkdir(parents=True, exist_ok=True)
        out = TRAINING_DIR / "business_sim_sft.jsonl"
        with open(out, "w") as f:
            for p in pairs:
                f.write(json.dumps(p) + "\n")
        log.info("Exported %d training pairs to %s", len(pairs), out)

    elif cmd == "dashboard":
        latest = DATA_DIR / "latest_simulation.json"
        if latest.exists():
            results = json.loads(latest.read_text())
            print_dashboard(results)
        else:
            print("No simulation data. Run: python3 simulator.py run")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
