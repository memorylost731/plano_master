#!/usr/bin/env python3
"""
PlanO Pricing Optimizer — Dynamic pricing agent with A/B testing and LTV maximization.

Monitors conversion rates per tier per country (MT, BG), runs A/B tests on
price variants, fits price elasticity curves via linear regression, and
generates weekly recommendations. All data persists in SQLite.

Usage:
    python3 pricing_optimizer.py status                                 # active tests + recommendations
    python3 pricing_optimizer.py recommend                              # fresh pricing recommendations
    python3 pricing_optimizer.py ab-test --country MT --tier starter --variant 11.99
    python3 pricing_optimizer.py train-export                           # SFT pairs for Pricing Analyst

DEBUG: PLANO_DEBUG=1 for verbose output
"""

import argparse
import hashlib
import json
import logging
import math
import os
import random
import sqlite3
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "business_sim"
DB_PATH = DATA_DIR / "pricing.db"
TRAINING_DIR = DATA_DIR / "agent_training"

logging.basicConfig(
    level=logging.DEBUG if os.environ.get("PLANO_DEBUG") else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("plano.pricing_optimizer")


# ═══════════════════════════════════════════════════════════
# PRICING CONFIGURATION
# ═══════════════════════════════════════════════════════════

# Base prices per tier per country (EUR)
BASE_PRICES: dict[str, dict[str, float]] = {
    "MT": {
        "free": 0.0,
        "starter": 9.99,
        "professional": 24.99,
        "business": 49.99,
    },
    "BG": {
        "free": 0.0,
        "starter": 4.99,
        "professional": 12.99,
        "business": 29.99,
    },
}

# Tiers eligible for A/B testing (exclude free)
TESTABLE_TIERS = ("starter", "professional", "business")
COUNTRIES = ("MT", "BG")

# A/B test traffic allocation — 10% of new visitors see variant
AB_TEST_TRAFFIC_FRACTION = 0.10

# Minimum sample size before drawing conclusions (per arm)
MIN_SAMPLE_SIZE = 30

# Maximum concurrent tests per country-tier pair
MAX_CONCURRENT_TESTS = 1

# LTV multiplier — average customer lifetime in months by tier
AVG_LIFETIME_MONTHS: dict[str, float] = {
    "starter": 8.0,
    "professional": 14.0,
    "business": 20.0,
}


# ═══════════════════════════════════════════════════════════
# DATABASE LAYER
# ═══════════════════════════════════════════════════════════

def get_db() -> sqlite3.Connection:
    """Return a connection to the pricing database, creating tables if needed."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _init_tables(conn)
    return conn


def _init_tables(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS price_tests (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            country     TEXT NOT NULL,
            tier        TEXT NOT NULL,
            base_price  REAL NOT NULL,
            variant_price REAL NOT NULL,
            start_date  TEXT NOT NULL,
            end_date    TEXT,
            status      TEXT NOT NULL DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS conversions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id     INTEGER,
            user_id_hash TEXT NOT NULL,
            arm         TEXT NOT NULL DEFAULT 'control',
            converted   INTEGER NOT NULL DEFAULT 0,
            revenue     REAL NOT NULL DEFAULT 0.0,
            ltv_estimate REAL NOT NULL DEFAULT 0.0,
            timestamp   TEXT NOT NULL,
            FOREIGN KEY (test_id) REFERENCES price_tests(id)
        );

        CREATE TABLE IF NOT EXISTS recommendations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            country     TEXT NOT NULL,
            tier        TEXT NOT NULL,
            recommended_price REAL NOT NULL,
            confidence  REAL NOT NULL,
            reasoning   TEXT NOT NULL,
            elasticity_coeff REAL,
            timestamp   TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_conversions_test ON conversions(test_id);
        CREATE INDEX IF NOT EXISTS idx_conversions_ts ON conversions(timestamp);
        CREATE INDEX IF NOT EXISTS idx_tests_status ON price_tests(status);
        CREATE INDEX IF NOT EXISTS idx_recs_ts ON recommendations(timestamp);
    """)
    conn.commit()


# ═══════════════════════════════════════════════════════════
# A/B TEST MANAGEMENT
# ═══════════════════════════════════════════════════════════

def start_ab_test(country: str, tier: str, variant_price: float) -> dict:
    """Start a new A/B test for a country-tier pair.

    Args:
        country: Country code (MT or BG).
        tier: Pricing tier name.
        variant_price: Price to test against the base.

    Returns:
        Dict with test details or error.
    """
    country = country.upper()
    if country not in COUNTRIES:
        return {"error": f"Invalid country: {country}. Must be one of {COUNTRIES}"}
    if tier not in TESTABLE_TIERS:
        return {"error": f"Invalid tier: {tier}. Must be one of {TESTABLE_TIERS}"}
    if variant_price <= 0:
        return {"error": "Variant price must be positive"}

    base_price = BASE_PRICES[country][tier]
    if abs(variant_price - base_price) / base_price > 0.40:
        return {"error": f"Variant deviates >40% from base ({base_price}). Too risky."}

    conn = get_db()
    try:
        # Check for active tests on this country-tier
        active = conn.execute(
            "SELECT COUNT(*) as cnt FROM price_tests WHERE country = ? AND tier = ? AND status = 'active'",
            (country, tier),
        ).fetchone()["cnt"]

        if active >= MAX_CONCURRENT_TESTS:
            return {"error": f"Already {active} active test(s) for {country}/{tier}. Finish or stop first."}

        now = datetime.now(timezone.utc).isoformat()
        cursor = conn.execute(
            "INSERT INTO price_tests (country, tier, base_price, variant_price, start_date, status) VALUES (?, ?, ?, ?, ?, 'active')",
            (country, tier, base_price, variant_price, now),
        )
        conn.commit()
        test_id = cursor.lastrowid
        log.info("Started A/B test #%d: %s/%s base=%.2f variant=%.2f", test_id, country, tier, base_price, variant_price)
        return {"test_id": test_id, "country": country, "tier": tier, "base_price": base_price, "variant_price": variant_price, "status": "active"}
    finally:
        conn.close()


def assign_visitor(user_id: str, country: str, tier: str) -> dict:
    """Assign a visitor to control or variant arm for active tests.

    Uses deterministic hashing so the same user always sees the same price.

    Args:
        user_id: Unique visitor identifier.
        country: Country code.
        tier: Pricing tier.

    Returns:
        Dict with assigned price and arm.
    """
    country = country.upper()
    conn = get_db()
    try:
        test = conn.execute(
            "SELECT * FROM price_tests WHERE country = ? AND tier = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
            (country, tier),
        ).fetchone()

        base_price = BASE_PRICES.get(country, {}).get(tier, 0.0)
        if not test:
            return {"price": base_price, "arm": "control", "test_id": None}

        # Deterministic assignment via hash
        hash_input = f"{user_id}:{test['id']}".encode()
        hash_val = int(hashlib.sha256(hash_input).hexdigest(), 16)
        fraction = (hash_val % 10000) / 10000.0

        if fraction < AB_TEST_TRAFFIC_FRACTION:
            arm = "variant"
            price = test["variant_price"]
        else:
            arm = "control"
            price = test["base_price"]

        return {"price": price, "arm": arm, "test_id": test["id"]}
    finally:
        conn.close()


def record_conversion(test_id: Optional[int], user_id: str, arm: str,
                      converted: bool, revenue: float, tier: str) -> None:
    """Record a conversion event for an A/B test.

    Args:
        test_id: The A/B test ID (None if no test active).
        user_id: Visitor identifier (will be hashed).
        arm: 'control' or 'variant'.
        converted: Whether the visitor converted.
        revenue: Immediate revenue (first payment).
        tier: Pricing tier for LTV estimation.
    """
    user_hash = hashlib.sha256(user_id.encode()).hexdigest()[:16]
    ltv = revenue * AVG_LIFETIME_MONTHS.get(tier, 8.0) if converted else 0.0
    now = datetime.now(timezone.utc).isoformat()

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO conversions (test_id, user_id_hash, arm, converted, revenue, ltv_estimate, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (test_id, user_hash, arm, int(converted), revenue, ltv, now),
        )
        conn.commit()
        log.debug("Recorded conversion: test=%s arm=%s converted=%s rev=%.2f ltv=%.2f", test_id, arm, converted, revenue, ltv)
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# PRICE ELASTICITY MODELING
# ═══════════════════════════════════════════════════════════

@dataclass
class ElasticityResult:
    """Result of price elasticity regression."""
    country: str
    tier: str
    slope: float          # change in conversion rate per EUR price change
    intercept: float      # conversion rate at price=0 (theoretical)
    r_squared: float      # goodness of fit
    optimal_price: float  # price that maximizes expected LTV
    sample_size: int


def compute_elasticity(country: str, tier: str) -> Optional[ElasticityResult]:
    """Compute price elasticity via simple linear regression on conversion data.

    Fits: conversion_rate = intercept + slope * price
    Then finds the price that maximizes: price * conversion_rate * avg_lifetime

    Args:
        country: Country code.
        tier: Pricing tier.

    Returns:
        ElasticityResult or None if insufficient data.
    """
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT pt.base_price as price, c.arm, c.converted, c.ltv_estimate
            FROM conversions c
            JOIN price_tests pt ON c.test_id = pt.id
            WHERE pt.country = ? AND pt.tier = ?
            UNION ALL
            SELECT pt.variant_price as price, c.arm, c.converted, c.ltv_estimate
            FROM conversions c
            JOIN price_tests pt ON c.test_id = pt.id
            WHERE pt.country = ? AND pt.tier = ? AND c.arm = 'variant'
        """, (country, tier, country, tier)).fetchall()

        if len(rows) < MIN_SAMPLE_SIZE:
            log.debug("Insufficient data for elasticity: %s/%s (%d rows)", country, tier, len(rows))
            return None

        # Group by price point, compute conversion rates
        price_groups: dict[float, list[int]] = {}
        for row in rows:
            price = row["price"]
            if price not in price_groups:
                price_groups[price] = []
            price_groups[price].append(row["converted"])

        if len(price_groups) < 2:
            log.debug("Need at least 2 price points for regression: %s/%s", country, tier)
            return None

        # Simple linear regression: conversion_rate = a + b * price
        points: list[tuple[float, float]] = []
        for price, conversions in price_groups.items():
            rate = sum(conversions) / len(conversions)
            points.append((price, rate))

        n = len(points)
        sum_x = sum(p[0] for p in points)
        sum_y = sum(p[1] for p in points)
        sum_xy = sum(p[0] * p[1] for p in points)
        sum_x2 = sum(p[0] ** 2 for p in points)

        denom = n * sum_x2 - sum_x ** 2
        if abs(denom) < 1e-10:
            return None

        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n

        # R-squared
        mean_y = sum_y / n
        ss_tot = sum((p[1] - mean_y) ** 2 for p in points)
        ss_res = sum((p[1] - (intercept + slope * p[0])) ** 2 for p in points)
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # Optimal price: maximize price * (intercept + slope * price) * lifetime
        # d/dp [p * (a + b*p)] = a + 2*b*p = 0  =>  p = -a / (2b)
        lifetime = AVG_LIFETIME_MONTHS.get(tier, 8.0)
        if slope < 0:
            optimal_price = -intercept / (2 * slope)
            optimal_price = max(1.0, min(optimal_price, BASE_PRICES[country][tier] * 1.5))
        else:
            # Positive slope (unlikely) — demand increases with price, use base
            optimal_price = BASE_PRICES[country][tier]

        return ElasticityResult(
            country=country,
            tier=tier,
            slope=round(slope, 6),
            intercept=round(intercept, 4),
            r_squared=round(r_squared, 4),
            optimal_price=round(optimal_price, 2),
            sample_size=len(rows),
        )
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# RECOMMENDATIONS ENGINE
# ═══════════════════════════════════════════════════════════

def generate_recommendations() -> list[dict]:
    """Generate pricing recommendations for all country-tier pairs.

    Uses elasticity modeling where data exists, falls back to heuristics.

    Returns:
        List of recommendation dicts.
    """
    recommendations = []
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()

    try:
        for country in COUNTRIES:
            for tier in TESTABLE_TIERS:
                base = BASE_PRICES[country][tier]
                elasticity = compute_elasticity(country, tier)

                if elasticity and elasticity.r_squared > 0.3:
                    rec_price = elasticity.optimal_price
                    confidence = min(0.95, elasticity.r_squared * 0.9 + 0.1)
                    reasoning = (
                        f"Elasticity model (R²={elasticity.r_squared:.2f}, slope={elasticity.slope:.4f}) "
                        f"suggests optimal price for LTV maximization. "
                        f"Based on {elasticity.sample_size} data points."
                    )
                    elast_coeff = elasticity.slope
                else:
                    # Heuristic fallback — recommend base price with low confidence
                    rec_price = base
                    confidence = 0.3
                    reasoning = "Insufficient A/B test data. Recommend maintaining base price until more data collected."
                    elast_coeff = None

                    # Check if any completed tests give directional signal
                    completed = conn.execute("""
                        SELECT pt.variant_price,
                               AVG(CASE WHEN c.arm = 'control' THEN c.converted ELSE NULL END) as ctrl_rate,
                               AVG(CASE WHEN c.arm = 'variant' THEN c.converted ELSE NULL END) as var_rate,
                               AVG(CASE WHEN c.arm = 'control' THEN c.ltv_estimate ELSE NULL END) as ctrl_ltv,
                               AVG(CASE WHEN c.arm = 'variant' THEN c.ltv_estimate ELSE NULL END) as var_ltv
                        FROM price_tests pt
                        LEFT JOIN conversions c ON c.test_id = pt.id
                        WHERE pt.country = ? AND pt.tier = ? AND pt.status = 'completed'
                        GROUP BY pt.id
                        ORDER BY pt.end_date DESC LIMIT 3
                    """, (country, tier)).fetchall()

                    if completed:
                        better_variant = sum(1 for r in completed if (r["var_ltv"] or 0) > (r["ctrl_ltv"] or 0))
                        if better_variant > len(completed) / 2:
                            rec_price = completed[0]["variant_price"] or base
                            confidence = 0.5
                            reasoning = f"Directional signal from {len(completed)} completed test(s) favors variant pricing."

                rec = {
                    "country": country,
                    "tier": tier,
                    "recommended_price": round(rec_price, 2),
                    "current_base": base,
                    "delta_pct": round((rec_price - base) / base * 100, 1) if base > 0 else 0.0,
                    "confidence": round(confidence, 2),
                    "reasoning": reasoning,
                    "elasticity_coeff": elast_coeff,
                }
                recommendations.append(rec)

                # Persist
                conn.execute(
                    "INSERT INTO recommendations (country, tier, recommended_price, confidence, reasoning, elasticity_coeff, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (country, tier, rec["recommended_price"], rec["confidence"], reasoning, elast_coeff, now),
                )

        conn.commit()
        log.info("Generated %d pricing recommendations", len(recommendations))
        return recommendations
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# SFT TRAINING DATA EXPORT
# ═══════════════════════════════════════════════════════════

def export_sft_pairs() -> list[dict]:
    """Export SFT training pairs for the Pricing Analyst agent.

    Generates question-answer pairs from historical tests, recommendations,
    and elasticity analyses.

    Returns:
        List of SFT message dicts.
    """
    pairs = []
    conn = get_db()
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)

    try:
        # Pairs from completed tests
        tests = conn.execute("""
            SELECT pt.*,
                   COUNT(c.id) as total_conversions,
                   AVG(CASE WHEN c.arm = 'control' THEN c.converted END) as ctrl_rate,
                   AVG(CASE WHEN c.arm = 'variant' THEN c.converted END) as var_rate,
                   AVG(CASE WHEN c.arm = 'control' THEN c.ltv_estimate END) as ctrl_ltv,
                   AVG(CASE WHEN c.arm = 'variant' THEN c.ltv_estimate END) as var_ltv
            FROM price_tests pt
            LEFT JOIN conversions c ON c.test_id = pt.id
            GROUP BY pt.id
            ORDER BY pt.start_date DESC
        """).fetchall()

        for test in tests:
            ctrl_rate = test["ctrl_rate"] or 0
            var_rate = test["var_rate"] or 0
            ctrl_ltv = test["ctrl_ltv"] or 0
            var_ltv = test["var_ltv"] or 0

            winner = "variant" if var_ltv > ctrl_ltv else "control"
            winner_price = test["variant_price"] if winner == "variant" else test["base_price"]

            pairs.append({
                "messages": [
                    {"role": "system", "content": "You are the Pricing Analyst for PlanO, a renovation SaaS operating in Malta and Bulgaria. You optimize pricing to maximize customer lifetime value."},
                    {"role": "user", "content": (
                        f"A/B test results for {test['country']}/{test['tier']}: "
                        f"Control ({test['base_price']:.2f} EUR) conversion={ctrl_rate:.1%}, avg LTV={ctrl_ltv:.2f} EUR. "
                        f"Variant ({test['variant_price']:.2f} EUR) conversion={var_rate:.1%}, avg LTV={var_ltv:.2f} EUR. "
                        f"Sample size: {test['total_conversions']}. What do you recommend?"
                    )},
                    {"role": "assistant", "content": (
                        f"Based on this A/B test, the {winner} arm at {winner_price:.2f} EUR performed better on LTV. "
                        f"{'The higher price reduced conversion but increased per-customer value.' if winner == 'variant' and test['variant_price'] > test['base_price'] else 'The price point balanced conversion volume with customer value.'} "
                        f"Recommendation: {'Adopt the variant price' if winner == 'variant' else 'Keep the current price'}. "
                        f"{'Note: sample size is below 100 — consider extending the test for higher confidence.' if test['total_conversions'] < 100 else 'Sample size is adequate for this conclusion.'}"
                    )},
                ]
            })

        # Pairs from recommendations
        recs = conn.execute(
            "SELECT * FROM recommendations ORDER BY timestamp DESC LIMIT 20"
        ).fetchall()

        for rec in recs:
            pairs.append({
                "messages": [
                    {"role": "system", "content": "You are the Pricing Analyst for PlanO. You provide data-driven pricing recommendations."},
                    {"role": "user", "content": f"What should we price the {rec['tier']} tier in {rec['country']}? Current price: base rate. Confidence needed for price change."},
                    {"role": "assistant", "content": (
                        f"Recommended price: {rec['recommended_price']:.2f} EUR (confidence: {rec['confidence']:.0%}). "
                        f"Reasoning: {rec['reasoning']}"
                    )},
                ]
            })

        # Elasticity knowledge pairs
        for country in COUNTRIES:
            for tier in TESTABLE_TIERS:
                elasticity = compute_elasticity(country, tier)
                if elasticity:
                    pairs.append({
                        "messages": [
                            {"role": "system", "content": "You are the Pricing Analyst for PlanO. You understand price elasticity modeling."},
                            {"role": "user", "content": f"What is the price elasticity for {country}/{tier}?"},
                            {"role": "assistant", "content": (
                                f"Price elasticity analysis for {country}/{tier}: "
                                f"slope={elasticity.slope:.4f} (each EUR increase {'decreases' if elasticity.slope < 0 else 'increases'} conversion by {abs(elasticity.slope):.2%}), "
                                f"R²={elasticity.r_squared:.2f}, optimal price={elasticity.optimal_price:.2f} EUR. "
                                f"Based on {elasticity.sample_size} observations."
                            )},
                        ]
                    })

        # Write to file
        output_path = TRAINING_DIR / "pricing_analyst_sft.jsonl"
        with open(output_path, "w") as f:
            for pair in pairs:
                f.write(json.dumps(pair) + "\n")

        log.info("Exported %d SFT pairs to %s", len(pairs), output_path)
        return pairs
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# STATUS & REPORTING
# ═══════════════════════════════════════════════════════════

def get_status() -> dict:
    """Get current status of all tests and latest recommendations.

    Returns:
        Dict with active_tests, completed_tests, latest_recommendations, and summary stats.
    """
    conn = get_db()
    try:
        active_tests = [dict(r) for r in conn.execute(
            "SELECT * FROM price_tests WHERE status = 'active' ORDER BY start_date DESC"
        ).fetchall()]

        completed_tests = [dict(r) for r in conn.execute(
            "SELECT * FROM price_tests WHERE status = 'completed' ORDER BY end_date DESC LIMIT 10"
        ).fetchall()]

        # Latest recommendation per country-tier
        latest_recs = [dict(r) for r in conn.execute("""
            SELECT r1.* FROM recommendations r1
            INNER JOIN (
                SELECT country, tier, MAX(timestamp) as max_ts
                FROM recommendations GROUP BY country, tier
            ) r2 ON r1.country = r2.country AND r1.tier = r2.tier AND r1.timestamp = r2.max_ts
            ORDER BY r1.country, r1.tier
        """).fetchall()]

        total_conversions = conn.execute("SELECT COUNT(*) as cnt FROM conversions").fetchone()["cnt"]
        total_tests = conn.execute("SELECT COUNT(*) as cnt FROM price_tests").fetchone()["cnt"]

        return {
            "active_tests": active_tests,
            "completed_tests": completed_tests,
            "latest_recommendations": latest_recs,
            "stats": {
                "total_tests": total_tests,
                "active_tests": len(active_tests),
                "completed_tests": len(completed_tests),
                "total_conversion_records": total_conversions,
            },
        }
    finally:
        conn.close()


def print_status() -> None:
    """Print formatted status to stdout."""
    status = get_status()
    print("\n" + "=" * 60)
    print("  PlanO Pricing Optimizer — Status")
    print("=" * 60)

    stats = status["stats"]
    print(f"\n  Total tests: {stats['total_tests']}  |  Active: {stats['active_tests']}  |  Completed: {stats['completed_tests']}")
    print(f"  Conversion records: {stats['total_conversion_records']}")

    if status["active_tests"]:
        print(f"\n  {'─' * 56}")
        print("  ACTIVE A/B TESTS:")
        for t in status["active_tests"]:
            print(f"    #{t['id']}  {t['country']}/{t['tier']}  base={t['base_price']:.2f}  variant={t['variant_price']:.2f}  since {t['start_date'][:10]}")
    else:
        print("\n  No active A/B tests.")

    if status["latest_recommendations"]:
        print(f"\n  {'─' * 56}")
        print("  LATEST RECOMMENDATIONS:")
        for r in status["latest_recommendations"]:
            delta = ""
            base = BASE_PRICES.get(r["country"], {}).get(r["tier"], 0)
            if base > 0:
                pct = (r["recommended_price"] - base) / base * 100
                delta = f" ({pct:+.1f}%)" if abs(pct) > 0.1 else " (no change)"
            print(f"    {r['country']}/{r['tier']}: {r['recommended_price']:.2f} EUR{delta}  confidence={r['confidence']:.0%}")
            print(f"      {r['reasoning'][:80]}...")
    else:
        print("\n  No recommendations yet. Run 'recommend' to generate.")

    print("\n" + "=" * 60 + "\n")


def print_recommendations() -> None:
    """Generate and print fresh pricing recommendations."""
    recs = generate_recommendations()
    print("\n" + "=" * 60)
    print("  PlanO Pricing Recommendations")
    print("=" * 60)
    for r in recs:
        symbol = "+" if r["delta_pct"] > 0 else "-" if r["delta_pct"] < 0 else "="
        print(f"\n  [{symbol}] {r['country']}/{r['tier']}")
        print(f"      Current: {r['current_base']:.2f} EUR  ->  Recommended: {r['recommended_price']:.2f} EUR ({r['delta_pct']:+.1f}%)")
        print(f"      Confidence: {r['confidence']:.0%}")
        print(f"      {r['reasoning']}")
    print("\n" + "=" * 60 + "\n")

    # Also dump as JSON
    output = DATA_DIR / "latest_pricing_recs.json"
    with open(output, "w") as f:
        json.dump(recs, f, indent=2)
    print(f"  JSON written to {output}\n")


# ═══════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════

def main() -> None:
    """CLI entry point for the pricing optimizer."""
    parser = argparse.ArgumentParser(
        description="PlanO Pricing Optimizer — dynamic pricing with A/B testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show active tests and recommendations")
    sub.add_parser("recommend", help="Generate fresh pricing recommendations")

    ab_parser = sub.add_parser("ab-test", help="Start a new A/B price test")
    ab_parser.add_argument("--country", required=True, help="Country code (MT or BG)")
    ab_parser.add_argument("--tier", required=True, help="Pricing tier")
    ab_parser.add_argument("--variant", required=True, type=float, help="Variant price (EUR)")

    sub.add_parser("train-export", help="Export SFT training pairs")

    args = parser.parse_args()

    if args.command == "status":
        print_status()
    elif args.command == "recommend":
        print_recommendations()
    elif args.command == "ab-test":
        result = start_ab_test(args.country, args.tier, args.variant)
        if "error" in result:
            print(f"ERROR: {result['error']}")
            sys.exit(1)
        print(f"Started A/B test #{result['test_id']}: {result['country']}/{result['tier']} base={result['base_price']:.2f} variant={result['variant_price']:.2f}")
    elif args.command == "train-export":
        pairs = export_sft_pairs()
        print(f"Exported {len(pairs)} SFT training pairs")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
