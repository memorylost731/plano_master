#!/usr/bin/env python3
"""
PlanO KPI Metrics Dashboard -- comprehensive SaaS metrics tracking.

Tracks all business metrics in SQLite, computes derived metrics,
generates weekly/monthly reports, alerts on anomalies (>2 sigma),
and exports SFT training pairs for agent integration.

Usage:
    metrics_dashboard.py record --metric mrr --value 450 [--country MT] [--segment pro]
    metrics_dashboard.py dashboard                -- print full KPI dashboard
    metrics_dashboard.py report --period monthly  -- generate report
    metrics_dashboard.py alerts                   -- show anomalies
    metrics_dashboard.py targets                  -- show progress vs targets
    metrics_dashboard.py funnel                   -- show conversion funnel
    metrics_dashboard.py train-export             -- SFT pairs for agents

DEBUG: PLANO_DEBUG=1 for verbose output
"""

import argparse
import json
import logging
import math
import os
import sqlite3
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# ── Config ──

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "business_sim"
DB_PATH = DATA_DIR / "metrics.db"
TRAINING_DIR = DATA_DIR / "agent_training"

ANOMALY_SIGMA_THRESHOLD = 2.0
ROLLING_WINDOW_DAYS = 30
MARGIN_FACTOR = 0.75  # 25% reserve margin on API calls

logging.basicConfig(
    level=logging.DEBUG if os.environ.get("PLANO_DEBUG") else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("plano.metrics")


# ── Metric Definitions ──

METRIC_REGISTRY: dict[str, dict] = {
    "mrr":                  {"unit": "EUR", "direction": "up",   "description": "Monthly Recurring Revenue"},
    "arr":                  {"unit": "EUR", "direction": "up",   "description": "Annual Recurring Revenue (MRR x 12)", "derived": True},
    "arpu":                 {"unit": "EUR", "direction": "up",   "description": "Average Revenue Per User (MRR / paid_users)", "derived": True},
    "paid_users":           {"unit": "count", "direction": "up", "description": "Total paying subscribers"},
    "free_users":           {"unit": "count", "direction": "up", "description": "Freemium users"},
    "churn_rate":           {"unit": "pct",  "direction": "down","description": "Monthly churn rate (cohort-based)"},
    "nrr":                  {"unit": "pct",  "direction": "up",  "description": "Net Revenue Retention", "derived": True},
    "ltv":                  {"unit": "EUR", "direction": "up",   "description": "Lifetime Value (ARPU / monthly_churn)", "derived": True},
    "cac":                  {"unit": "EUR", "direction": "down", "description": "Customer Acquisition Cost"},
    "ltv_cac_ratio":        {"unit": "ratio","direction": "up",  "description": "LTV:CAC ratio", "derived": True},
    "payback_months":       {"unit": "months","direction": "down","description": "CAC Payback Period", "derived": True},
    "rule_of_40":           {"unit": "pct",  "direction": "up",  "description": "Revenue growth % + profit margin %", "derived": True},
    "quick_ratio":          {"unit": "ratio","direction": "up",  "description": "(New+Expansion) / (Churn+Contraction)", "derived": True},
    "burn_rate":            {"unit": "EUR", "direction": "down", "description": "Monthly cash burn"},
    "runway_months":        {"unit": "months","direction": "up", "description": "Cash / monthly burn", "derived": True},
    "cash_balance":         {"unit": "EUR", "direction": "up",   "description": "Current cash balance"},
    "dau":                  {"unit": "count","direction": "up",  "description": "Daily Active Users"},
    "wau":                  {"unit": "count","direction": "up",  "description": "Weekly Active Users"},
    "mau":                  {"unit": "count","direction": "up",  "description": "Monthly Active Users"},
    "dau_mau_ratio":        {"unit": "ratio","direction": "up",  "description": "Stickiness (DAU/MAU)", "derived": True},
    "plans_per_user":       {"unit": "count","direction": "up",  "description": "Avg renovation plans created per user"},
    "rasta_accuracy":       {"unit": "pct",  "direction": "up",  "description": "Floor plan recognition accuracy"},
    "agent_autonomy":       {"unit": "level","direction": "up",  "description": "AI agent autonomy level (0-4)"},
    "tickets_total":        {"unit": "count","direction": "down","description": "Support tickets opened"},
    "tickets_ai_resolved":  {"unit": "count","direction": "up",  "description": "Tickets resolved by AI"},
    "tickets_human":        {"unit": "count","direction": "down","description": "Tickets escalated to human"},
    "nps_score":            {"unit": "score","direction": "up",  "description": "Net Promoter Score (-100 to 100)"},
    "visitors":             {"unit": "count","direction": "up",  "description": "Unique website visitors"},
    "signups":              {"unit": "count","direction": "up",  "description": "New signups"},
    "active_users":         {"unit": "count","direction": "up",  "description": "Users active in period"},
    "retained_users":       {"unit": "count","direction": "up",  "description": "Retained paid users"},
    "new_mrr":              {"unit": "EUR", "direction": "up",   "description": "MRR from new customers"},
    "expansion_mrr":        {"unit": "EUR", "direction": "up",   "description": "MRR from upgrades"},
    "contraction_mrr":      {"unit": "EUR", "direction": "down", "description": "MRR from downgrades"},
    "churned_mrr":          {"unit": "EUR", "direction": "down", "description": "MRR lost to churn"},
    "acquisition_spend":    {"unit": "EUR", "direction": "down", "description": "Total acquisition spend"},
    "new_customers":        {"unit": "count","direction": "up",  "description": "New paying customers"},
    "revenue_growth_pct":   {"unit": "pct",  "direction": "up",  "description": "MoM revenue growth %"},
    "profit_margin_pct":    {"unit": "pct",  "direction": "up",  "description": "Profit margin %"},
    "start_mrr":            {"unit": "EUR", "direction": "up",   "description": "MRR at start of period"},
}


# ── Database ──

def get_db() -> sqlite3.Connection:
    """Open (and initialize if needed) the metrics database."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _init_tables(conn)
    return conn


def _init_tables(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS metrics_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            country TEXT DEFAULT 'ALL',
            segment TEXT DEFAULT 'all',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_metrics_date_name
            ON metrics_daily(date, metric_name);
        CREATE INDEX IF NOT EXISTS idx_metrics_name_date
            ON metrics_daily(metric_name, date);

        CREATE TABLE IF NOT EXISTS metrics_targets (
            metric_name TEXT PRIMARY KEY,
            target_value REAL NOT NULL,
            target_date TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_name TEXT NOT NULL,
            expected REAL,
            actual REAL NOT NULL,
            deviation_sigma REAL NOT NULL,
            severity TEXT NOT NULL,
            timestamp TEXT DEFAULT (datetime('now')),
            acknowledged INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS cohorts (
            cohort_month TEXT NOT NULL,
            users_start INTEGER NOT NULL,
            month_offset INTEGER NOT NULL,
            users_remaining INTEGER NOT NULL,
            revenue REAL DEFAULT 0,
            PRIMARY KEY (cohort_month, month_offset)
        );
    """)
    conn.commit()


# ── Recording ──

def record_metric(
    metric_name: str,
    value: float,
    date: Optional[str] = None,
    country: str = "ALL",
    segment: str = "all",
) -> None:
    """Record a single metric value. Parameterized SQL only."""
    if metric_name not in METRIC_REGISTRY:
        log.warning("Unknown metric '%s' -- recording anyway", metric_name)

    date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO metrics_daily (date, metric_name, metric_value, country, segment) "
            "VALUES (?, ?, ?, ?, ?)",
            (date, metric_name, value, country, segment),
        )
        conn.commit()
        log.info("Recorded %s = %.2f (%s, %s, %s)", metric_name, value, date, country, segment)
        _check_anomaly(conn, metric_name, value, date)
    finally:
        conn.close()


def _check_anomaly(
    conn: sqlite3.Connection,
    metric_name: str,
    value: float,
    date: str,
) -> None:
    """Check if a recorded value is anomalous (> 2 sigma from rolling mean)."""
    rows = conn.execute(
        "SELECT metric_value FROM metrics_daily "
        "WHERE metric_name = ? AND date < ? "
        "ORDER BY date DESC LIMIT ?",
        (metric_name, date, ROLLING_WINDOW_DAYS),
    ).fetchall()

    if len(rows) < 7:
        return  # not enough data for anomaly detection

    values = [r["metric_value"] for r in rows]
    mean = statistics.mean(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 0.0

    if stdev == 0:
        return

    deviation = abs(value - mean) / stdev
    if deviation > ANOMALY_SIGMA_THRESHOLD:
        severity = "critical" if deviation > 3.0 else "warning"
        conn.execute(
            "INSERT INTO alerts (metric_name, expected, actual, deviation_sigma, severity) "
            "VALUES (?, ?, ?, ?, ?)",
            (metric_name, mean, value, deviation, severity),
        )
        conn.commit()
        log.warning(
            "ANOMALY: %s = %.2f (expected ~%.2f, %.1f sigma, %s)",
            metric_name, value, mean, deviation, severity,
        )


# ── Derived Metrics ──

def compute_derived(date: Optional[str] = None) -> dict[str, float]:
    """Compute all derived metrics from raw data for a given date."""
    date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_db()
    try:
        return _compute_derived_inner(conn, date)
    finally:
        conn.close()


def _latest_value(conn: sqlite3.Connection, metric: str, date: str) -> Optional[float]:
    """Get the most recent value for a metric on or before date."""
    row = conn.execute(
        "SELECT metric_value FROM metrics_daily "
        "WHERE metric_name = ? AND date <= ? "
        "ORDER BY date DESC LIMIT 1",
        (metric, date),
    ).fetchone()
    return row["metric_value"] if row else None


def _compute_derived_inner(conn: sqlite3.Connection, date: str) -> dict[str, float]:
    """Core derived metric computation."""
    derived: dict[str, float] = {}

    mrr = _latest_value(conn, "mrr", date)
    paid = _latest_value(conn, "paid_users", date)
    churn = _latest_value(conn, "churn_rate", date)
    dau = _latest_value(conn, "dau", date)
    mau = _latest_value(conn, "mau", date)
    cash = _latest_value(conn, "cash_balance", date)
    burn = _latest_value(conn, "burn_rate", date)
    new_mrr = _latest_value(conn, "new_mrr", date)
    expansion = _latest_value(conn, "expansion_mrr", date)
    contraction = _latest_value(conn, "contraction_mrr", date)
    churned_mrr = _latest_value(conn, "churned_mrr", date)
    start_mrr = _latest_value(conn, "start_mrr", date)
    acq_spend = _latest_value(conn, "acquisition_spend", date)
    new_cust = _latest_value(conn, "new_customers", date)
    rev_growth = _latest_value(conn, "revenue_growth_pct", date)
    profit_margin = _latest_value(conn, "profit_margin_pct", date)

    if mrr is not None:
        derived["arr"] = mrr * 12

    if mrr is not None and paid and paid > 0:
        derived["arpu"] = mrr / paid

    if "arpu" in derived and churn and churn > 0:
        derived["ltv"] = derived["arpu"] / churn

    if acq_spend is not None and new_cust and new_cust > 0:
        derived["cac"] = acq_spend / new_cust

    if "ltv" in derived and "cac" in derived and derived["cac"] > 0:
        derived["ltv_cac_ratio"] = derived["ltv"] / derived["cac"]

    if "cac" in derived and "arpu" in derived and derived["arpu"] > 0:
        derived["payback_months"] = derived["cac"] / derived["arpu"]

    if start_mrr and start_mrr > 0:
        exp = expansion or 0
        con = contraction or 0
        chm = churned_mrr or 0
        derived["nrr"] = (start_mrr + exp - con - chm) / start_mrr

    if (new_mrr is not None or expansion is not None) and (churned_mrr is not None or contraction is not None):
        numerator = (new_mrr or 0) + (expansion or 0)
        denominator = (churned_mrr or 0) + (contraction or 0)
        if denominator > 0:
            derived["quick_ratio"] = numerator / denominator

    if rev_growth is not None and profit_margin is not None:
        derived["rule_of_40"] = rev_growth + profit_margin

    if cash is not None and burn and burn > 0:
        derived["runway_months"] = cash / burn

    if dau is not None and mau and mau > 0:
        derived["dau_mau_ratio"] = dau / mau

    return derived


# ── Dashboard ──

def print_dashboard() -> None:
    """Print a full KPI dashboard to stdout."""
    conn = get_db()
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        derived = _compute_derived_inner(conn, today)

        print("=" * 78)
        print("  PlanO SaaS Metrics Dashboard")
        print(f"  Date: {today}")
        print("=" * 78)

        sections = [
            ("Revenue", ["mrr", "arr", "arpu", "new_mrr", "expansion_mrr", "churned_mrr", "contraction_mrr"]),
            ("Growth", ["paid_users", "free_users", "new_customers", "revenue_growth_pct", "rule_of_40"]),
            ("Retention", ["churn_rate", "nrr", "quick_ratio", "ltv", "retained_users"]),
            ("Acquisition", ["cac", "ltv_cac_ratio", "payback_months", "acquisition_spend"]),
            ("Engagement", ["dau", "wau", "mau", "dau_mau_ratio", "plans_per_user"]),
            ("AI & Product", ["rasta_accuracy", "agent_autonomy", "tickets_total", "tickets_ai_resolved", "tickets_human"]),
            ("Financial", ["cash_balance", "burn_rate", "runway_months", "profit_margin_pct"]),
            ("Satisfaction", ["nps_score"]),
        ]

        for section_name, metrics in sections:
            print(f"\n  --- {section_name} ---")
            for m in metrics:
                val = derived.get(m)
                if val is None:
                    val = _latest_value(conn, m, today)
                meta = METRIC_REGISTRY.get(m, {})
                unit = meta.get("unit", "")
                desc = meta.get("description", m)
                if val is not None:
                    formatted = _format_value(val, unit)
                    print(f"    {desc:<45} {formatted:>12}")
                else:
                    print(f"    {desc:<45} {'--':>12}")

        # Conversion funnel
        _print_funnel_inline(conn, today)

        # Active alerts
        alerts = conn.execute(
            "SELECT * FROM alerts WHERE acknowledged = 0 ORDER BY timestamp DESC LIMIT 5"
        ).fetchall()
        if alerts:
            print(f"\n  --- Active Alerts ({len(alerts)}) ---")
            for a in alerts:
                print(f"    [{a['severity'].upper()}] {a['metric_name']}: "
                      f"actual={a['actual']:.2f} expected={a['expected']:.2f} "
                      f"({a['deviation_sigma']:.1f} sigma)")
        else:
            print("\n  No active alerts.")

        print("\n" + "=" * 78)
    finally:
        conn.close()


def _format_value(value: float, unit: str) -> str:
    """Format a metric value with its unit."""
    if unit == "EUR":
        return f"EUR {value:,.2f}"
    elif unit == "pct":
        return f"{value * 100:.1f}%"
    elif unit == "ratio":
        return f"{value:.2f}x"
    elif unit == "count":
        return f"{int(value):,}"
    elif unit == "months":
        return f"{value:.1f} mo"
    elif unit == "level":
        return f"L{value:.1f}"
    elif unit == "score":
        return f"{value:+.0f}"
    return f"{value:.2f}"


def _print_funnel_inline(conn: sqlite3.Connection, date: str) -> None:
    """Print conversion funnel inline within dashboard."""
    funnel_metrics = ["visitors", "signups", "active_users", "paid_users", "retained_users"]
    funnel_labels = ["Visitors", "Signups", "Active", "Paid", "Retained"]
    values = []
    for m in funnel_metrics:
        v = _latest_value(conn, m, date)
        values.append(v)

    print(f"\n  --- Conversion Funnel ---")
    for i, (label, val) in enumerate(zip(funnel_labels, values)):
        if val is None:
            val_str = "--"
            rate_str = ""
        else:
            val_str = f"{int(val):,}"
            if i > 0 and values[i - 1] and values[i - 1] > 0:
                rate = val / values[i - 1] * 100
                rate_str = f"  ({rate:.1f}%)"
            else:
                rate_str = ""
        arrow = " --> " if i < len(funnel_labels) - 1 else ""
        print(f"    {label}: {val_str}{rate_str}{arrow}")


# ── Reports ──

def generate_report(period: str = "monthly") -> str:
    """Generate a weekly or monthly report as a markdown string."""
    conn = get_db()
    try:
        today = datetime.now(timezone.utc)
        if period == "weekly":
            start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            title = f"Weekly Report ({start} to {today.strftime('%Y-%m-%d')})"
        else:
            start = today.replace(day=1).strftime("%Y-%m-%d")
            title = f"Monthly Report ({today.strftime('%Y-%m')})"

        today_str = today.strftime("%Y-%m-%d")
        derived = _compute_derived_inner(conn, today_str)

        lines = [f"# PlanO {title}", ""]

        # Key metrics table
        lines.append("## Key Metrics")
        lines.append("")
        lines.append("| Metric | Value | Target | Status |")
        lines.append("|--------|-------|--------|--------|")

        key_metrics = ["mrr", "arr", "paid_users", "churn_rate", "nrr", "ltv_cac_ratio", "nps_score"]
        for m in key_metrics:
            val = derived.get(m, _latest_value(conn, m, today_str))
            target_row = conn.execute(
                "SELECT target_value FROM metrics_targets WHERE metric_name = ?", (m,)
            ).fetchone()
            target = target_row["target_value"] if target_row else None
            unit = METRIC_REGISTRY.get(m, {}).get("unit", "")
            val_str = _format_value(val, unit) if val is not None else "--"
            tgt_str = _format_value(target, unit) if target is not None else "--"
            if val is not None and target is not None:
                direction = METRIC_REGISTRY.get(m, {}).get("direction", "up")
                on_track = (val >= target) if direction == "up" else (val <= target)
                status = "ON TRACK" if on_track else "BEHIND"
            else:
                status = "--"
            lines.append(f"| {m} | {val_str} | {tgt_str} | {status} |")

        # Alerts summary
        alerts = conn.execute(
            "SELECT metric_name, severity, actual, expected, deviation_sigma "
            "FROM alerts WHERE timestamp >= ? ORDER BY deviation_sigma DESC",
            (start,),
        ).fetchall()
        lines.append("")
        lines.append(f"## Alerts ({len(alerts)} in period)")
        if alerts:
            for a in alerts:
                lines.append(f"- **[{a['severity'].upper()}]** {a['metric_name']}: "
                             f"{a['actual']:.2f} (expected {a['expected']:.2f}, {a['deviation_sigma']:.1f}sigma)")
        else:
            lines.append("No anomalies detected.")

        # Cohort summary
        cohorts = conn.execute(
            "SELECT cohort_month, users_start, month_offset, users_remaining "
            "FROM cohorts ORDER BY cohort_month DESC, month_offset ASC LIMIT 20"
        ).fetchall()
        if cohorts:
            lines.append("")
            lines.append("## Cohort Retention")
            for c in cohorts:
                retention = c["users_remaining"] / c["users_start"] * 100 if c["users_start"] > 0 else 0
                lines.append(f"- {c['cohort_month']} +{c['month_offset']}mo: "
                             f"{c['users_remaining']}/{c['users_start']} ({retention:.0f}%)")

        report = "\n".join(lines)
        return report
    finally:
        conn.close()


# ── Alerts ──

def show_alerts() -> None:
    """Display all unacknowledged alerts."""
    conn = get_db()
    try:
        alerts = conn.execute(
            "SELECT * FROM alerts WHERE acknowledged = 0 ORDER BY timestamp DESC"
        ).fetchall()
        if not alerts:
            print("No active alerts.")
            return

        print(f"{'ID':>4}  {'Severity':<10} {'Metric':<25} {'Actual':>10} {'Expected':>10} {'Sigma':>6}  {'Time'}")
        print("-" * 90)
        for a in alerts:
            print(f"{a['id']:>4}  {a['severity']:<10} {a['metric_name']:<25} "
                  f"{a['actual']:>10.2f} {a['expected']:>10.2f} {a['deviation_sigma']:>6.1f}  {a['timestamp']}")
    finally:
        conn.close()


# ── Targets ──

def show_targets() -> None:
    """Display progress vs targets."""
    conn = get_db()
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        derived = _compute_derived_inner(conn, today)
        targets = conn.execute("SELECT * FROM metrics_targets ORDER BY metric_name").fetchall()

        if not targets:
            print("No targets set. Use SQL to insert into metrics_targets.")
            _seed_default_targets(conn)
            targets = conn.execute("SELECT * FROM metrics_targets ORDER BY metric_name").fetchall()

        print(f"{'Metric':<25} {'Current':>12} {'Target':>12} {'Due':>12} {'Progress':>10} {'Status':<10}")
        print("-" * 85)
        for t in targets:
            val = derived.get(t["metric_name"], _latest_value(conn, t["metric_name"], today))
            unit = METRIC_REGISTRY.get(t["metric_name"], {}).get("unit", "")
            val_str = _format_value(val, unit) if val is not None else "--"
            tgt_str = _format_value(t["target_value"], unit)
            if val is not None and t["target_value"] > 0:
                progress = val / t["target_value"] * 100
                progress_str = f"{progress:.0f}%"
                direction = METRIC_REGISTRY.get(t["metric_name"], {}).get("direction", "up")
                status = "ON TRACK" if (progress >= 80 if direction == "up" else progress <= 120) else "BEHIND"
            else:
                progress_str = "--"
                status = "--"
            print(f"{t['metric_name']:<25} {val_str:>12} {tgt_str:>12} {t['target_date']:>12} {progress_str:>10} {status:<10}")
    finally:
        conn.close()


def _seed_default_targets(conn: sqlite3.Connection) -> None:
    """Insert default targets for PlanO milestones."""
    defaults = [
        ("mrr", 5000, "2026-12-31"),
        ("arr", 60000, "2026-12-31"),
        ("paid_users", 500, "2026-12-31"),
        ("churn_rate", 0.04, "2026-12-31"),
        ("nrr", 1.1, "2026-12-31"),
        ("ltv_cac_ratio", 3.0, "2026-12-31"),
        ("nps_score", 50, "2026-12-31"),
        ("rasta_accuracy", 0.95, "2026-12-31"),
        ("agent_autonomy", 3.0, "2026-12-31"),
        ("dau_mau_ratio", 0.3, "2026-12-31"),
    ]
    for metric, target, due in defaults:
        conn.execute(
            "INSERT OR IGNORE INTO metrics_targets (metric_name, target_value, target_date) "
            "VALUES (?, ?, ?)",
            (metric, target, due),
        )
    conn.commit()
    log.info("Seeded %d default targets", len(defaults))


# ── Funnel ──

def show_funnel() -> None:
    """Display the full conversion funnel."""
    conn = get_db()
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        _print_funnel_inline(conn, today)
    finally:
        conn.close()


# ── SFT Training Export ──

def generate_sft_pairs() -> list[dict]:
    """Generate SFT training pairs from metrics for agent training."""
    conn = get_db()
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        derived = _compute_derived_inner(conn, today)
        pairs: list[dict] = []

        # Metric explanation pairs
        for metric_name, meta in METRIC_REGISTRY.items():
            val = derived.get(metric_name, _latest_value(conn, metric_name, today))
            if val is None:
                continue
            unit = meta.get("unit", "")
            pairs.append({
                "messages": [
                    {"role": "system", "content": "You are a SaaS metrics analyst for PlanO, a renovation platform."},
                    {"role": "user", "content": f"What is our current {meta['description']}?"},
                    {"role": "assistant", "content": (
                        f"The current {meta['description']} ({metric_name}) is {_format_value(val, unit)}. "
                        f"{'This is trending in the right direction.' if meta.get('direction') == 'up' else 'We want to minimize this metric.'}"
                    )},
                ]
            })

        # Alert response pairs
        alerts = conn.execute(
            "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 10"
        ).fetchall()
        for a in alerts:
            pairs.append({
                "messages": [
                    {"role": "system", "content": "You are a SaaS metrics analyst for PlanO. Explain anomalies and recommend actions."},
                    {"role": "user", "content": (
                        f"Alert: {a['metric_name']} is {a['actual']:.2f} but expected ~{a['expected']:.2f} "
                        f"({a['deviation_sigma']:.1f} sigma deviation). What should we do?"
                    )},
                    {"role": "assistant", "content": _alert_response(a)},
                ]
            })

        return pairs
    finally:
        conn.close()


def _alert_response(alert: sqlite3.Row) -> str:
    """Generate a contextual response to a metric anomaly."""
    metric = alert["metric_name"]
    direction = "increase" if alert["actual"] > alert["expected"] else "decrease"
    severity = alert["severity"]

    if "churn" in metric:
        return (f"This {severity} alert shows an unexpected {direction} in churn. "
                "Immediate actions: 1) Check for recent product changes that may have degraded UX. "
                "2) Review support tickets for recurring issues. "
                "3) Run a cohort analysis to identify which segments are churning.")
    elif "mrr" in metric:
        return (f"MRR shows a significant {direction}. "
                "Check: 1) Is this driven by a single large customer? "
                "2) Review new subscription vs churn numbers. "
                "3) Check if pricing changes took effect this period.")
    else:
        return (f"The {metric} metric shows a {severity}-level deviation ({direction}). "
                f"Actual: {alert['actual']:.2f}, Expected: {alert['expected']:.2f}. "
                "Investigate the root cause and correlate with recent product or market changes.")


def export_training_pairs() -> Path:
    """Export SFT pairs to JSONL file."""
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    pairs = generate_sft_pairs()
    out_path = TRAINING_DIR / "metrics_sft.jsonl"
    with open(out_path, "w") as f:
        for pair in pairs:
            f.write(json.dumps(pair) + "\n")
    log.info("Exported %d SFT pairs to %s", len(pairs), out_path)
    return out_path


# ── Seed Demo Data ──

def seed_demo_data() -> None:
    """Seed the database with realistic demo data for testing."""
    conn = get_db()
    try:
        existing = conn.execute("SELECT COUNT(*) as c FROM metrics_daily").fetchone()["c"]
        if existing > 0:
            log.info("Database already has %d records, skipping seed", existing)
            return

        log.info("Seeding demo data for dashboard testing...")
        base = datetime(2026, 4, 1, tzinfo=timezone.utc)
        rng_seed = 42
        import random
        rng = random.Random(rng_seed)

        mrr = 0.0
        paid = 0
        free = 0
        cash = 5000.0

        for day_offset in range(5):
            date = (base + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            # Simulate growth
            new_visitors = rng.randint(50, 200)
            new_signups = int(new_visitors * rng.uniform(0.02, 0.05))
            new_paid = max(0, int(new_signups * rng.uniform(0.03, 0.08)))
            churned = max(0, int(paid * rng.uniform(0.001, 0.005)))

            paid = paid + new_paid - churned
            free = free + new_signups - new_paid
            mrr = paid * rng.uniform(9, 13)
            burn = rng.uniform(200, 400)
            cash = cash + mrr - burn

            records = [
                ("visitors", new_visitors), ("signups", new_signups),
                ("active_users", int(paid * 0.6 + free * 0.2)),
                ("paid_users", paid), ("free_users", free),
                ("retained_users", paid - churned),
                ("mrr", mrr), ("start_mrr", mrr * 0.95),
                ("new_mrr", new_paid * 10), ("expansion_mrr", rng.uniform(0, 20)),
                ("contraction_mrr", rng.uniform(0, 5)), ("churned_mrr", churned * 10),
                ("churn_rate", churned / max(paid, 1)),
                ("new_customers", new_paid),
                ("acquisition_spend", rng.uniform(50, 150)),
                ("dau", int(paid * 0.3 + free * 0.05)),
                ("wau", int(paid * 0.5 + free * 0.1)),
                ("mau", int(paid * 0.8 + free * 0.2)),
                ("plans_per_user", rng.uniform(1.5, 3.0)),
                ("rasta_accuracy", rng.uniform(0.91, 0.94)),
                ("agent_autonomy", 1.5),
                ("tickets_total", rng.randint(2, 10)),
                ("tickets_ai_resolved", rng.randint(1, 5)),
                ("tickets_human", rng.randint(0, 3)),
                ("nps_score", rng.randint(30, 60)),
                ("cash_balance", cash), ("burn_rate", burn),
                ("revenue_growth_pct", rng.uniform(0.05, 0.20)),
                ("profit_margin_pct", rng.uniform(-0.3, 0.1)),
            ]
            for metric, value in records:
                conn.execute(
                    "INSERT INTO metrics_daily (date, metric_name, metric_value, country, segment) "
                    "VALUES (?, ?, ?, 'ALL', 'all')",
                    (date, metric, float(value)),
                )

        conn.commit()
        log.info("Seeded %d days of demo data", 5)
    finally:
        conn.close()


# ── CLI ──

def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="PlanO SaaS Metrics Dashboard")
    sub = parser.add_subparsers(dest="command")

    # record
    rec = sub.add_parser("record", help="Record a metric value")
    rec.add_argument("--metric", required=True, help="Metric name")
    rec.add_argument("--value", required=True, type=float, help="Metric value")
    rec.add_argument("--date", default=None, help="Date (YYYY-MM-DD)")
    rec.add_argument("--country", default="ALL", help="Country code")
    rec.add_argument("--segment", default="all", help="User segment")

    # dashboard
    sub.add_parser("dashboard", help="Print full KPI dashboard")

    # report
    rep = sub.add_parser("report", help="Generate report")
    rep.add_argument("--period", default="monthly", choices=["weekly", "monthly"])

    # alerts
    sub.add_parser("alerts", help="Show anomalies")

    # targets
    sub.add_parser("targets", help="Show progress vs targets")

    # funnel
    sub.add_parser("funnel", help="Show conversion funnel")

    # train-export
    sub.add_parser("train-export", help="Export SFT training pairs")

    args = parser.parse_args()

    if args.command == "record":
        record_metric(args.metric, args.value, args.date, args.country, args.segment)
    elif args.command == "dashboard":
        seed_demo_data()
        print_dashboard()
    elif args.command == "report":
        report = generate_report(args.period)
        print(report)
    elif args.command == "alerts":
        show_alerts()
    elif args.command == "targets":
        show_targets()
    elif args.command == "funnel":
        seed_demo_data()
        show_funnel()
    elif args.command == "train-export":
        path = export_training_pairs()
        print(f"Exported to {path}")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
