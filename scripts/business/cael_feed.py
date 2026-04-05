#!/usr/bin/env python3
"""
PlanO -- Cael AI Intelligence Feed.

Aggregates all PlanO business intelligence and feeds it to Cael
(Mistral-Small-24B) via SFT training pairs and daily briefings.

Sources: simulator, metrics_dashboard, osm_sync, rasta_pipeline,
         pricing_optimizer, competition_monitor.

Usage:
    cael_feed.py briefing   -- print today's intelligence briefing
    cael_feed.py export     -- generate and push SFT pairs
    cael_feed.py status     -- show data freshness across all sources

DEBUG: PLANO_DEBUG=1 for verbose output
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Config ──

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "business_sim"
METRICS_DB = DATA_DIR / "metrics.db"
SIM_LATEST = DATA_DIR / "latest_simulation.json"
OSINT_LATEST = DATA_DIR / "osint" / "latest.json"
RASTA_METRICS = BASE_DIR / "data" / "rasta_metrics"
OSM_DATA = BASE_DIR / "data" / "osm"

TRAINING_LAKE = Path.home() / "data-gathering-agent" / "training_lake"
GPU_HOST = os.environ.get("PLANO_GPU_HOST", "gpu")
GPU_BUFFER = "/home/hadrienm/live_buffer"

MARGIN_FACTOR = 0.75  # 25% reserve on API calls

logging.basicConfig(
    level=logging.DEBUG if os.environ.get("PLANO_DEBUG") else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("plano.cael_feed")

# Import metrics dashboard for DB access (same package)
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from metrics_dashboard import get_db, _compute_derived_inner, _latest_value, _format_value, METRIC_REGISTRY
except ImportError:
    log.warning("metrics_dashboard not importable -- metrics section will be limited")
    get_db = None


# ── Data Sources ──

def _load_json_safe(path: Path) -> Optional[dict]:
    """Load a JSON file safely, returning None on failure."""
    try:
        if path.exists():
            return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Failed to load %s: %s", path, e)
    return None


def _get_source_freshness() -> dict[str, dict]:
    """Check freshness of all data sources."""
    sources = {}

    # Simulator
    if SIM_LATEST.exists():
        mtime = datetime.fromtimestamp(SIM_LATEST.stat().st_mtime, tz=timezone.utc)
        sim = _load_json_safe(SIM_LATEST)
        sources["simulator"] = {
            "path": str(SIM_LATEST),
            "last_updated": mtime.isoformat(),
            "age_hours": (datetime.now(timezone.utc) - mtime).total_seconds() / 3600,
            "status": "fresh" if (datetime.now(timezone.utc) - mtime).days < 7 else "stale",
            "details": f"{sim.get('scenario', '?')} scenario, {sim.get('months', '?')} months" if sim else "unreadable",
        }
    else:
        sources["simulator"] = {"status": "missing", "path": str(SIM_LATEST)}

    # Metrics DB
    if METRICS_DB.exists():
        mtime = datetime.fromtimestamp(METRICS_DB.stat().st_mtime, tz=timezone.utc)
        record_count = 0
        if get_db:
            try:
                conn = get_db()
                record_count = conn.execute("SELECT COUNT(*) as c FROM metrics_daily").fetchone()["c"]
                conn.close()
            except Exception:
                pass
        sources["metrics_dashboard"] = {
            "path": str(METRICS_DB),
            "last_updated": mtime.isoformat(),
            "age_hours": (datetime.now(timezone.utc) - mtime).total_seconds() / 3600,
            "status": "fresh" if (datetime.now(timezone.utc) - mtime).days < 1 else "stale",
            "details": f"{record_count} records",
        }
    else:
        sources["metrics_dashboard"] = {"status": "missing", "path": str(METRICS_DB)}

    # OSINT
    if OSINT_LATEST.exists():
        mtime = datetime.fromtimestamp(OSINT_LATEST.stat().st_mtime, tz=timezone.utc)
        sources["osint"] = {
            "path": str(OSINT_LATEST),
            "last_updated": mtime.isoformat(),
            "age_hours": (datetime.now(timezone.utc) - mtime).total_seconds() / 3600,
            "status": "fresh" if (datetime.now(timezone.utc) - mtime).days < 7 else "stale",
        }
    else:
        sources["osint"] = {"status": "missing", "path": str(OSINT_LATEST)}

    # Rasta metrics
    if RASTA_METRICS.exists():
        mtime = datetime.fromtimestamp(RASTA_METRICS.stat().st_mtime, tz=timezone.utc)
        sources["rasta_pipeline"] = {
            "path": str(RASTA_METRICS),
            "last_updated": mtime.isoformat(),
            "age_hours": (datetime.now(timezone.utc) - mtime).total_seconds() / 3600,
            "status": "fresh" if (datetime.now(timezone.utc) - mtime).days < 7 else "stale",
        }
    else:
        sources["rasta_pipeline"] = {"status": "missing", "path": str(RASTA_METRICS)}

    # OSM data
    if OSM_DATA.exists():
        mtime = datetime.fromtimestamp(OSM_DATA.stat().st_mtime, tz=timezone.utc)
        sources["osm_sync"] = {
            "path": str(OSM_DATA),
            "last_updated": mtime.isoformat(),
            "age_hours": (datetime.now(timezone.utc) - mtime).total_seconds() / 3600,
            "status": "fresh" if (datetime.now(timezone.utc) - mtime).days < 14 else "stale",
        }
    else:
        sources["osm_sync"] = {"status": "missing", "path": str(OSM_DATA)}

    # Pricing optimizer (may not exist yet)
    pricing_path = BASE_DIR / "scripts" / "business" / "pricing_optimizer.py"
    sources["pricing_optimizer"] = {
        "status": "available" if pricing_path.exists() else "not_implemented",
        "path": str(pricing_path),
    }

    # Competition monitor (may not exist yet)
    comp_path = BASE_DIR / "scripts" / "business" / "competition_monitor.py"
    sources["competition_monitor"] = {
        "status": "available" if comp_path.exists() else "not_implemented",
        "path": str(comp_path),
    }

    return sources


# ── Briefing Generation ──

def generate_daily_briefing() -> str:
    """Generate a comprehensive daily intelligence briefing in markdown."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"# PlanO Daily Intelligence Briefing",
        f"**Date:** {today}",
        f"**Generated for:** Cael (Mistral-Small-24B)",
        "",
    ]

    # 1. Metrics summary
    lines.append("## Business Metrics")
    if get_db and METRICS_DB.exists():
        try:
            conn = get_db()
            derived = _compute_derived_inner(conn, today)
            key_metrics = [
                "mrr", "arr", "arpu", "paid_users", "free_users",
                "churn_rate", "nrr", "ltv", "cac", "ltv_cac_ratio",
                "quick_ratio", "rule_of_40", "dau_mau_ratio",
                "rasta_accuracy", "agent_autonomy", "nps_score",
                "cash_balance", "burn_rate", "runway_months",
            ]
            for m in key_metrics:
                val = derived.get(m, _latest_value(conn, m, today))
                if val is not None:
                    meta = METRIC_REGISTRY.get(m, {})
                    unit = meta.get("unit", "")
                    lines.append(f"- **{meta.get('description', m)}**: {_format_value(val, unit)}")

            # Alerts
            alerts = conn.execute(
                "SELECT * FROM alerts WHERE acknowledged = 0 ORDER BY deviation_sigma DESC LIMIT 5"
            ).fetchall()
            if alerts:
                lines.append("")
                lines.append("### Active Alerts")
                for a in alerts:
                    lines.append(f"- [{a['severity'].upper()}] {a['metric_name']}: "
                                 f"{a['actual']:.2f} (expected {a['expected']:.2f}, "
                                 f"{a['deviation_sigma']:.1f} sigma)")
            conn.close()
        except Exception as e:
            lines.append(f"- Metrics unavailable: {e}")
    else:
        lines.append("- Metrics database not yet populated. Run `metrics_dashboard.py dashboard` first.")

    # 2. Simulation projections
    lines.append("")
    lines.append("## Growth Projections")
    sim = _load_json_safe(SIM_LATEST)
    if sim:
        monthly = sim.get("monthly", [])
        # Current month and +6, +12, +24
        for target_month in [3, 6, 12, 24]:
            if target_month < len(monthly):
                m = monthly[target_month]
                lines.append(
                    f"- **Month {m['month']} ({m.get('date', '?')})**: "
                    f"MRR EUR {m['mrr_p50']:,.0f} (p10: {m['mrr_p10']:,.0f}, p90: {m['mrr_p90']:,.0f}), "
                    f"{m['users_p50']:,} users, valuation EUR {m['valuation_p50']:,.0f}"
                )
        ogi_month = sim.get("ogi_10m_month")
        if ogi_month:
            lines.append(f"- **Exit target**: Ogi reaches EUR 10M equity at month {ogi_month}")
        else:
            lines.append(f"- **Exit target**: Not reached in {sim.get('months', '?')} month horizon")
    else:
        lines.append("- No simulation data available. Run `simulator.py run`.")

    # 3. OSINT / Market intelligence
    lines.append("")
    lines.append("## Market Intelligence")
    osint = _load_json_safe(OSINT_LATEST)
    if osint:
        lines.append(f"- Malta: {osint.get('mt_population', '?'):,} pop, "
                     f"{osint.get('mt_construction_permits_annual', '?'):,} permits/yr, "
                     f"EUR {osint.get('mt_renovation_market_eur', 0):,} renovation market")
        lines.append(f"- Bulgaria: {osint.get('bg_population', '?'):,} pop, "
                     f"{osint.get('bg_construction_permits_annual', '?'):,} permits/yr, "
                     f"EUR {osint.get('bg_renovation_market_eur', 0):,} renovation market")
        lines.append(f"- ECB rate: {osint.get('ecb_interest_rate', '?')}, "
                     f"MT inflation: {osint.get('mt_inflation_rate', '?')}, "
                     f"BG inflation: {osint.get('bg_inflation_rate', '?')}")
    else:
        lines.append("- OSINT data not available. Run `simulator.py osint`.")

    # 4. Source freshness
    lines.append("")
    lines.append("## Data Source Status")
    sources = _get_source_freshness()
    for name, info in sources.items():
        status = info.get("status", "unknown")
        age = info.get("age_hours")
        age_str = f" ({age:.0f}h ago)" if age is not None else ""
        details = info.get("details", "")
        detail_str = f" -- {details}" if details else ""
        icon = "OK" if status == "fresh" else status.upper()
        lines.append(f"- **{name}**: [{icon}]{age_str}{detail_str}")

    return "\n".join(lines)


# ── SFT Pair Generation ──

def generate_sft_pairs() -> list[dict]:
    """Generate SFT training pairs from all business intelligence sources.

    Format: Mistral-Small-24B chat format (messages array).
    """
    pairs: list[dict] = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    system_prompt = (
        "You are Cael, the AI business intelligence analyst for PlanO, "
        "a renovation SaaS platform operating in Malta and Bulgaria. "
        "You have deep knowledge of SaaS metrics, growth strategies, "
        "and the European renovation market."
    )

    # Briefing Q&A pairs
    briefing = generate_daily_briefing()
    pairs.append({
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate today's PlanO business intelligence briefing."},
            {"role": "assistant", "content": briefing},
        ]
    })

    # Metrics-specific pairs
    if get_db and METRICS_DB.exists():
        try:
            conn = get_db()
            derived = _compute_derived_inner(conn, today)

            metric_questions = [
                ("mrr", "What is our current MRR and how does it break down?"),
                ("churn_rate", "What is our churn rate and what can we do about it?"),
                ("ltv_cac_ratio", "Is our LTV:CAC ratio healthy?"),
                ("nrr", "What is our net revenue retention telling us?"),
                ("quick_ratio", "How is our SaaS quick ratio looking?"),
                ("rule_of_40", "Are we meeting the Rule of 40?"),
                ("rasta_accuracy", "How accurate is the Rasta floor plan engine?"),
                ("agent_autonomy", "What is the current AI agent autonomy level?"),
            ]

            for metric, question in metric_questions:
                val = derived.get(metric, _latest_value(conn, metric, today))
                if val is None:
                    continue
                meta = METRIC_REGISTRY.get(metric, {})
                unit = meta.get("unit", "")
                answer = _generate_metric_answer(metric, val, unit, meta, derived)
                pairs.append({
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": answer},
                    ]
                })
            conn.close()
        except Exception as e:
            log.warning("Could not generate metrics pairs: %s", e)

    # Simulation projection pairs
    sim = _load_json_safe(SIM_LATEST)
    if sim and sim.get("monthly"):
        monthly = sim["monthly"]
        for horizon in [6, 12, 24]:
            if horizon < len(monthly):
                m = monthly[horizon]
                pairs.append({
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"What do our {horizon}-month projections look like?"},
                        {"role": "assistant", "content": (
                            f"At month {horizon} ({m.get('date', '?')}), our median projection shows:\n"
                            f"- MRR: EUR {m['mrr_p50']:,.0f} (range: EUR {m['mrr_p10']:,.0f} to EUR {m['mrr_p90']:,.0f})\n"
                            f"- Paid users: {m['users_p50']:,} (range: {m['users_p10']:,} to {m['users_p90']:,})\n"
                            f"- Valuation: EUR {m['valuation_p50']:,.0f}\n"
                            f"- Agent autonomy: L{m.get('autonomy', 0):.1f}\n"
                            f"- Rasta accuracy: {m.get('rasta_accuracy', 0):.1%}\n\n"
                            f"{'These projections are based on the ' + sim.get('scenario', 'base') + ' scenario '}"
                            f"with {sim.get('simulations', '?')} Monte Carlo runs."
                        )},
                    ]
                })

    log.info("Generated %d SFT pairs", len(pairs))
    return pairs


def _generate_metric_answer(
    metric: str,
    value: float,
    unit: str,
    meta: dict,
    derived: dict,
) -> str:
    """Generate a contextual answer about a specific metric."""
    formatted = _format_value(value, unit)
    desc = meta.get("description", metric)

    base = f"Our current {desc} is {formatted}."

    if metric == "mrr":
        arr = derived.get("arr")
        arr_str = f" That translates to an ARR of EUR {arr:,.0f}." if arr else ""
        return base + arr_str
    elif metric == "churn_rate":
        ltv = derived.get("ltv")
        ltv_str = f" With this churn rate, customer LTV is EUR {ltv:,.0f}." if ltv else ""
        health = " This is within healthy SaaS range (<5%)." if value < 0.05 else " This is above the 5% target -- needs attention."
        return base + health + ltv_str
    elif metric == "ltv_cac_ratio":
        health = " A ratio above 3x is healthy." if value >= 3 else " Below 3x -- we should optimize acquisition costs or improve retention."
        return base + health
    elif metric == "nrr":
        health = " Above 100% means we are growing revenue from existing customers." if value > 1.0 else " Below 100% -- expansion revenue is not covering churn."
        return base + health
    elif metric == "quick_ratio":
        health = " Above 4x is best-in-class SaaS." if value >= 4 else (" Healthy range." if value >= 2 else " Below 2x -- growth is fragile.")
        return base + health
    elif metric == "rule_of_40":
        health = " Meeting the Rule of 40 benchmark." if value >= 40 else f" At {value:.0f}%, below the 40% benchmark."
        return base + health
    elif metric == "rasta_accuracy":
        return base + " Target is 95%+ for production quality."
    elif metric == "agent_autonomy":
        return base + " Scale: L0 (human does everything) to L4 (fully autonomous)."

    return base


# ── Push to Training Lake & GPU ──

def push_to_training_lake(pairs: list[dict]) -> Path:
    """Write SFT pairs to the training lake directory."""
    TRAINING_LAKE.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = TRAINING_LAKE / f"plano_business_{timestamp}.jsonl"

    with open(out_path, "w") as f:
        for pair in pairs:
            f.write(json.dumps(pair) + "\n")

    log.info("Wrote %d pairs to training lake: %s", len(pairs), out_path)
    return out_path


def push_to_gpu(lake_path: Path) -> bool:
    """Push training data to GPU server live buffer via scp."""
    try:
        result = subprocess.run(
            ["scp", str(lake_path), f"{GPU_HOST}:{GPU_BUFFER}/"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            log.info("Pushed %s to %s:%s", lake_path.name, GPU_HOST, GPU_BUFFER)
            return True
        else:
            log.warning("scp failed: %s", result.stderr.strip())
            return False
    except subprocess.TimeoutExpired:
        log.warning("scp to GPU timed out after 30s")
        return False
    except FileNotFoundError:
        log.warning("scp not found -- cannot push to GPU")
        return False


# ── CLI ──

def cmd_briefing() -> None:
    """Print today's intelligence briefing."""
    briefing = generate_daily_briefing()
    print(briefing)


def cmd_export() -> None:
    """Generate SFT pairs and push to training lake + GPU."""
    pairs = generate_sft_pairs()
    if not pairs:
        print("No data available to generate SFT pairs.")
        return

    lake_path = push_to_training_lake(pairs)
    print(f"Exported {len(pairs)} SFT pairs to {lake_path}")

    gpu_ok = push_to_gpu(lake_path)
    if gpu_ok:
        print(f"Pushed to GPU live buffer ({GPU_HOST}:{GPU_BUFFER})")
    else:
        print("GPU push failed -- pairs saved locally in training lake")


def cmd_status() -> None:
    """Show data freshness across all sources."""
    sources = _get_source_freshness()
    print("PlanO Data Source Status")
    print("=" * 70)
    print(f"{'Source':<25} {'Status':<15} {'Age':>8}  {'Details'}")
    print("-" * 70)
    for name, info in sources.items():
        status = info.get("status", "unknown")
        age = info.get("age_hours")
        age_str = f"{age:.0f}h" if age is not None else "--"
        details = info.get("details", "")
        print(f"{name:<25} {status:<15} {age_str:>8}  {details}")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="PlanO Cael AI Intelligence Feed")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("briefing", help="Print today's intelligence briefing")
    sub.add_parser("export", help="Generate and push SFT pairs")
    sub.add_parser("status", help="Show data freshness across all sources")

    args = parser.parse_args()

    if args.command == "briefing":
        cmd_briefing()
    elif args.command == "export":
        cmd_export()
    elif args.command == "status":
        cmd_status()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
