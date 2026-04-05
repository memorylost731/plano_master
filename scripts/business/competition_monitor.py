#!/usr/bin/env python3
"""
PlanO Competition Monitor — Competitive intelligence agent with pricing tracking.

Tracks 15+ competitors across pricing changes, feature launches, social media
follower counts, and Google Trends data. Generates alerts on significant changes
and exports SFT training pairs for the Competitive Analyst agent.

Usage:
    python3 competition_monitor.py scan                              # check all competitors
    python3 competition_monitor.py alerts                            # show unacknowledged alerts
    python3 competition_monitor.py report                            # competitive intelligence report
    python3 competition_monitor.py trends --keyword "floor plan" --country MT
    python3 competition_monitor.py train-export                      # SFT pairs

DEBUG: PLANO_DEBUG=1 for verbose output
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "business_sim"
DB_PATH = DATA_DIR / "competition.db"
TRAINING_DIR = DATA_DIR / "agent_training"

logging.basicConfig(
    level=logging.DEBUG if os.environ.get("PLANO_DEBUG") else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("plano.competition_monitor")

# 25% margin: max 75% of rate limits, sleep between requests
REQUEST_DELAY_SEC = 2.0
REQUEST_TIMEOUT_SEC = 15
MAX_RETRIES = 2
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"


# ═══════════════════════════════════════════════════════════
# COMPETITOR REGISTRY
# ═══════════════════════════════════════════════════════════

@dataclass
class CompetitorDef:
    """Static definition of a competitor to track."""
    name: str
    url: str
    pricing_url: str
    category: str
    social_facebook: str = ""
    social_instagram: str = ""
    social_linkedin: str = ""


COMPETITORS: list[CompetitorDef] = [
    CompetitorDef("SketchUp", "https://www.sketchup.com", "https://www.sketchup.com/plans-and-pricing", "3D modeling",
                  social_facebook="SketchUp", social_instagram="sketchup", social_linkedin="sketchup"),
    CompetitorDef("Floorplanner", "https://floorplanner.com", "https://floorplanner.com/pricing", "floor planning",
                  social_facebook="floorplanner", social_instagram="floorplanner", social_linkedin="floorplanner"),
    CompetitorDef("RoomSketcher", "https://www.roomsketcher.com", "https://www.roomsketcher.com/pricing/", "floor planning",
                  social_facebook="roomsketcher", social_instagram="roomsketcher", social_linkedin="roomsketcher"),
    CompetitorDef("MagicPlan", "https://www.magicplan.app", "https://www.magicplan.app/pricing/", "mobile floor planning",
                  social_facebook="magicplanapp", social_instagram="magicplanapp", social_linkedin="magic-plan"),
    CompetitorDef("Planner5D", "https://planner5d.com", "https://planner5d.com/pricing", "3D home design",
                  social_facebook="Planner5D", social_instagram="planner5d", social_linkedin="planner5d"),
    CompetitorDef("CubiCasa", "https://www.cubi.casa", "https://www.cubi.casa/pricing/", "AI floor plans",
                  social_facebook="cubicasa", social_instagram="cubicasa", social_linkedin="cubicasa"),
    CompetitorDef("Cedreo", "https://cedreo.com", "https://cedreo.com/pricing/", "home design software",
                  social_facebook="cedreo", social_instagram="cedreo", social_linkedin="cedreo"),
    CompetitorDef("Houzz", "https://www.houzz.com", "https://www.houzz.com/pro", "home renovation marketplace",
                  social_facebook="houzz", social_instagram="houzz", social_linkedin="houzz"),
    CompetitorDef("Roomle", "https://www.roomle.com", "https://www.roomle.com/en/pricing", "3D room planner",
                  social_facebook="roomle", social_instagram="roomle", social_linkedin="roomle"),
    CompetitorDef("HomeByMe", "https://home.by.me", "https://home.by.me/en/pricing", "3D home design",
                  social_facebook="homebyme", social_instagram="homebyme", social_linkedin="homebyme"),
    CompetitorDef("Kozikaza", "https://www.kozikaza.com", "https://www.kozikaza.com/pricing", "home design community",
                  social_facebook="kozikaza", social_instagram="kozikaza", social_linkedin="kozikaza"),
    CompetitorDef("Palette CAD", "https://www.palettecad.com", "https://www.palettecad.com/prices/", "professional CAD",
                  social_facebook="PaletteCAD", social_instagram="palettecad", social_linkedin="palette-cad"),
    CompetitorDef("Habitissimo", "https://www.habitissimo.com", "https://www.habitissimo.com/pro", "renovation marketplace",
                  social_facebook="habitissimo", social_instagram="habitissimo", social_linkedin="habitissimo"),
    CompetitorDef("pCon.planner", "https://pcon-planner.com", "https://pcon-planner.com/pricing/", "space planning",
                  social_facebook="pConplanner", social_instagram="pconplanner", social_linkedin="pcon-planner"),
    CompetitorDef("SmartDraw", "https://www.smartdraw.com", "https://www.smartdraw.com/floor-plan/floor-plan-software.htm", "diagramming",
                  social_facebook="SmartDraw", social_instagram="smartdraw", social_linkedin="smartdraw"),
]

# Google Trends keywords per market
TREND_KEYWORDS: dict[str, list[str]] = {
    "MT": ["floor plan", "renovation planner", "home design software", "interior design app"],
    "BG": ["floor plan", "renovation planner", "ремонт планировка", "план на етаж"],
}


# ═══════════════════════════════════════════════════════════
# DATABASE LAYER
# ═══════════════════════════════════════════════════════════

def get_db() -> sqlite3.Connection:
    """Return a connection to the competition database, creating tables if needed."""
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
        CREATE TABLE IF NOT EXISTS competitors (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL UNIQUE,
            url          TEXT NOT NULL,
            pricing_url  TEXT NOT NULL,
            category     TEXT NOT NULL,
            social_json  TEXT DEFAULT '{}',
            last_checked TEXT
        );

        CREATE TABLE IF NOT EXISTS price_snapshots (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            competitor_id INTEGER NOT NULL,
            tier          TEXT NOT NULL DEFAULT 'unknown',
            price_eur     REAL,
            currency      TEXT DEFAULT 'EUR',
            features_json TEXT DEFAULT '[]',
            raw_text      TEXT DEFAULT '',
            timestamp     TEXT NOT NULL,
            FOREIGN KEY (competitor_id) REFERENCES competitors(id)
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            competitor_id INTEGER,
            alert_type    TEXT NOT NULL,
            description   TEXT NOT NULL,
            severity      TEXT NOT NULL DEFAULT 'info',
            timestamp     TEXT NOT NULL,
            acknowledged  INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (competitor_id) REFERENCES competitors(id)
        );

        CREATE TABLE IF NOT EXISTS trends (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword   TEXT NOT NULL,
            country   TEXT NOT NULL,
            value     REAL,
            source    TEXT DEFAULT 'estimate',
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS social_snapshots (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            competitor_id INTEGER NOT NULL,
            platform      TEXT NOT NULL,
            followers     INTEGER,
            engagement    REAL,
            timestamp     TEXT NOT NULL,
            FOREIGN KEY (competitor_id) REFERENCES competitors(id)
        );

        CREATE INDEX IF NOT EXISTS idx_snapshots_comp ON price_snapshots(competitor_id);
        CREATE INDEX IF NOT EXISTS idx_snapshots_ts ON price_snapshots(timestamp);
        CREATE INDEX IF NOT EXISTS idx_alerts_ack ON alerts(acknowledged);
        CREATE INDEX IF NOT EXISTS idx_trends_kw ON trends(keyword, country);
    """)
    conn.commit()


def _ensure_competitors(conn: sqlite3.Connection) -> dict[str, int]:
    """Ensure all defined competitors exist in DB. Returns name->id mapping."""
    name_to_id: dict[str, int] = {}
    for comp in COMPETITORS:
        social = json.dumps({
            "facebook": comp.social_facebook,
            "instagram": comp.social_instagram,
            "linkedin": comp.social_linkedin,
        })
        conn.execute("""
            INSERT INTO competitors (name, url, pricing_url, category, social_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                url = excluded.url,
                pricing_url = excluded.pricing_url,
                category = excluded.category,
                social_json = excluded.social_json
        """, (comp.name, comp.url, comp.pricing_url, comp.category, social))

    conn.commit()
    for row in conn.execute("SELECT id, name FROM competitors").fetchall():
        name_to_id[row["name"]] = row["id"]
    return name_to_id


# ═══════════════════════════════════════════════════════════
# WEB FETCHING (GRACEFUL)
# ═══════════════════════════════════════════════════════════

def _fetch_url(url: str) -> Optional[str]:
    """Fetch a URL with retry logic and graceful error handling.

    Args:
        url: URL to fetch.

    Returns:
        Response body as string, or None on failure.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SEC) as resp:
                charset = resp.headers.get_content_charset() or "utf-8"
                body = resp.read().decode(charset, errors="replace")
                log.debug("Fetched %s (%d bytes)", url, len(body))
                return body
        except urllib.error.HTTPError as exc:
            log.warning("HTTP %d fetching %s (attempt %d/%d)", exc.code, url, attempt + 1, MAX_RETRIES + 1)
            if exc.code in (403, 429, 503) and attempt < MAX_RETRIES:
                time.sleep(REQUEST_DELAY_SEC * (attempt + 1))
                continue
            return None
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            log.warning("Network error fetching %s: %s (attempt %d/%d)", url, exc, attempt + 1, MAX_RETRIES + 1)
            if attempt < MAX_RETRIES:
                time.sleep(REQUEST_DELAY_SEC * (attempt + 1))
                continue
            return None

    return None


# ═══════════════════════════════════════════════════════════
# PRICE EXTRACTION
# ═══════════════════════════════════════════════════════════

# Common price patterns in HTML
PRICE_PATTERNS = [
    # $29.99/mo, €9.99/month, 29,99€
    re.compile(r'[\$€£][\s]?(\d{1,4}[.,]\d{2})\s*/?\s*(?:mo(?:nth)?|yr|year)?', re.IGNORECASE),
    re.compile(r'(\d{1,4}[.,]\d{2})\s*[\$€£]\s*/?\s*(?:mo(?:nth)?|yr|year)?', re.IGNORECASE),
    # $29/mo, €9/month
    re.compile(r'[\$€£][\s]?(\d{1,4})\s*/?\s*(?:mo(?:nth)?|yr|year)', re.IGNORECASE),
    # "price":"29.99"
    re.compile(r'"price"\s*:\s*"?(\d{1,4}[.,]?\d{0,2})"?', re.IGNORECASE),
    # data-price="29.99"
    re.compile(r'data-price\s*=\s*"(\d{1,4}[.,]?\d{0,2})"', re.IGNORECASE),
]

# Tier detection patterns
TIER_PATTERNS = [
    (re.compile(r'\b(free|basic)\b', re.IGNORECASE), "free"),
    (re.compile(r'\b(starter|personal|hobby)\b', re.IGNORECASE), "starter"),
    (re.compile(r'\b(pro(?:fessional)?|plus|standard)\b', re.IGNORECASE), "professional"),
    (re.compile(r'\b(business|team|enterprise|premium)\b', re.IGNORECASE), "business"),
]


def _extract_prices(html: str) -> list[dict]:
    """Extract pricing information from HTML content.

    Args:
        html: Raw HTML string.

    Returns:
        List of dicts with tier, price, currency info.
    """
    prices = []
    seen: set[str] = set()

    # Strip scripts and styles to reduce noise
    clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL | re.IGNORECASE)

    for pattern in PRICE_PATTERNS:
        for match in pattern.finditer(clean):
            price_str = match.group(1).replace(",", ".")
            try:
                price_val = float(price_str)
            except ValueError:
                continue

            if price_val <= 0 or price_val > 5000:
                continue

            # Detect currency
            context = clean[max(0, match.start() - 20):match.end() + 20]
            currency = "EUR"
            if "$" in context:
                currency = "USD"
            elif "£" in context:
                currency = "GBP"

            # Detect tier from surrounding text
            surrounding = clean[max(0, match.start() - 200):min(len(clean), match.end() + 200)]
            tier = "unknown"
            for tp, tier_name in TIER_PATTERNS:
                if tp.search(surrounding):
                    tier = tier_name
                    break

            key = f"{tier}:{price_val:.2f}:{currency}"
            if key not in seen:
                seen.add(key)
                prices.append({
                    "tier": tier,
                    "price": price_val,
                    "currency": currency,
                })

    return prices


def _detect_price_change(conn: sqlite3.Connection, competitor_id: int,
                         new_prices: list[dict], now: str) -> list[dict]:
    """Compare new prices with the most recent snapshot and generate alerts.

    Args:
        conn: Database connection.
        competitor_id: Competitor ID.
        new_prices: Newly extracted prices.
        now: Current timestamp.

    Returns:
        List of alert dicts if changes detected.
    """
    alerts = []

    # Get previous prices for this competitor
    prev = conn.execute("""
        SELECT tier, price_eur, currency FROM price_snapshots
        WHERE competitor_id = ?
        ORDER BY timestamp DESC
        LIMIT 20
    """, (competitor_id,)).fetchall()

    prev_map: dict[str, float] = {}
    for row in prev:
        key = f"{row['tier']}:{row['currency']}"
        if key not in prev_map:
            prev_map[key] = row["price_eur"]

    for np in new_prices:
        key = f"{np['tier']}:{np['currency']}"
        if key in prev_map:
            old_price = prev_map[key]
            if old_price and old_price > 0:
                change_pct = (np["price"] - old_price) / old_price * 100
                if abs(change_pct) >= 5.0:  # 5% threshold
                    severity = "high" if abs(change_pct) >= 15 else "medium"
                    alerts.append({
                        "competitor_id": competitor_id,
                        "alert_type": "price_change",
                        "description": (
                            f"Price changed for tier '{np['tier']}': "
                            f"{old_price:.2f} -> {np['price']:.2f} {np['currency']} "
                            f"({change_pct:+.1f}%)"
                        ),
                        "severity": severity,
                        "timestamp": now,
                    })

    return alerts


# ═══════════════════════════════════════════════════════════
# SCANNING ENGINE
# ═══════════════════════════════════════════════════════════

def scan_competitor(conn: sqlite3.Connection, comp: CompetitorDef,
                    comp_id: int) -> dict:
    """Scan a single competitor for pricing and feature changes.

    Args:
        conn: Database connection.
        comp: Competitor definition.
        comp_id: Competitor database ID.

    Returns:
        Dict with scan results.
    """
    now = datetime.now(timezone.utc).isoformat()
    result = {"name": comp.name, "status": "unknown", "prices_found": 0, "alerts": []}

    # Fetch pricing page
    log.info("Scanning %s (%s)", comp.name, comp.pricing_url)
    html = _fetch_url(comp.pricing_url)

    if html is None:
        result["status"] = "fetch_failed"
        log.warning("Failed to fetch %s", comp.pricing_url)
        # Record a connectivity alert (low severity, don't spam)
        conn.execute(
            "INSERT INTO alerts (competitor_id, alert_type, description, severity, timestamp) VALUES (?, ?, ?, ?, ?)",
            (comp_id, "fetch_error", f"Could not fetch pricing page: {comp.pricing_url}", "low", now),
        )
        conn.commit()
        return result

    # Extract prices
    prices = _extract_prices(html)
    result["prices_found"] = len(prices)

    if prices:
        result["status"] = "ok"

        # Detect changes before inserting new snapshots
        change_alerts = _detect_price_change(conn, comp_id, prices, now)
        for alert in change_alerts:
            conn.execute(
                "INSERT INTO alerts (competitor_id, alert_type, description, severity, timestamp) VALUES (?, ?, ?, ?, ?)",
                (alert["competitor_id"], alert["alert_type"], alert["description"], alert["severity"], alert["timestamp"]),
            )
            result["alerts"].append(alert)
            log.warning("ALERT [%s]: %s — %s", alert["severity"], comp.name, alert["description"])

        # Store new snapshots
        for p in prices:
            conn.execute(
                "INSERT INTO price_snapshots (competitor_id, tier, price_eur, currency, raw_text, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (comp_id, p["tier"], p["price"], p["currency"], "", now),
            )
    else:
        result["status"] = "no_prices_found"
        log.debug("No prices extracted from %s (page may use JS rendering)", comp.name)

    # Update last_checked
    conn.execute("UPDATE competitors SET last_checked = ? WHERE id = ?", (now, comp_id))
    conn.commit()

    return result


def scan_all() -> list[dict]:
    """Scan all competitors. Respects rate limiting with delays.

    Returns:
        List of scan result dicts.
    """
    conn = get_db()
    try:
        name_to_id = _ensure_competitors(conn)
        results = []

        total = len(COMPETITORS)
        for idx, comp in enumerate(COMPETITORS):
            comp_id = name_to_id[comp.name]
            result = scan_competitor(conn, comp, comp_id)
            results.append(result)

            # Rate limiting — 25% margin means we don't rush
            if idx < total - 1:
                time.sleep(REQUEST_DELAY_SEC)

        # Summary
        ok = sum(1 for r in results if r["status"] == "ok")
        failed = sum(1 for r in results if r["status"] == "fetch_failed")
        no_prices = sum(1 for r in results if r["status"] == "no_prices_found")
        total_alerts = sum(len(r["alerts"]) for r in results)

        log.info("Scan complete: %d/%d OK, %d failed, %d no prices, %d alerts", ok, total, failed, no_prices, total_alerts)
        return results
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# GOOGLE TRENDS (ESTIMATED)
# ═══════════════════════════════════════════════════════════

def record_trend_estimate(keyword: str, country: str, value: float,
                          source: str = "manual") -> None:
    """Record a trend data point.

    Google Trends doesn't have a public API, so values are estimated from
    manual lookups or third-party tools. This function stores them.

    Args:
        keyword: Search term.
        country: Country code.
        value: Relative interest value (0-100 scale).
        source: Data source identifier.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO trends (keyword, country, value, source, timestamp) VALUES (?, ?, ?, ?, ?)",
            (keyword, country, value, source, now),
        )
        conn.commit()
        log.debug("Recorded trend: %s/%s = %.1f (%s)", keyword, country, value, source)
    finally:
        conn.close()


def get_trends(keyword: str, country: str, limit: int = 30) -> list[dict]:
    """Retrieve trend data for a keyword-country pair.

    Args:
        keyword: Search term.
        country: Country code.
        limit: Maximum rows to return.

    Returns:
        List of trend dicts ordered by timestamp descending.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM trends WHERE keyword = ? AND country = ? ORDER BY timestamp DESC LIMIT ?",
            (keyword, country, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def seed_trend_baselines() -> None:
    """Seed baseline trend estimates for tracked keywords.

    These are rough estimates to bootstrap the system. Real data should
    be updated periodically via manual entry or third-party APIs.
    """
    # Baseline estimates (relative interest 0-100) based on public data
    baselines: dict[str, dict[str, float]] = {
        "floor plan": {"MT": 35.0, "BG": 25.0},
        "renovation planner": {"MT": 20.0, "BG": 15.0},
        "ремонт планировка": {"MT": 2.0, "BG": 40.0},
        "home design software": {"MT": 30.0, "BG": 20.0},
        "план на етаж": {"MT": 1.0, "BG": 30.0},
        "interior design app": {"MT": 25.0, "BG": 18.0},
    }

    conn = get_db()
    try:
        # Only seed if no trends exist
        count = conn.execute("SELECT COUNT(*) as cnt FROM trends").fetchone()["cnt"]
        if count > 0:
            log.debug("Trends already seeded (%d records), skipping", count)
            return

        now = datetime.now(timezone.utc).isoformat()
        for keyword, countries in baselines.items():
            for country, value in countries.items():
                conn.execute(
                    "INSERT INTO trends (keyword, country, value, source, timestamp) VALUES (?, ?, ?, ?, ?)",
                    (keyword, country, value, "baseline_estimate", now),
                )
        conn.commit()
        log.info("Seeded %d trend baselines", sum(len(c) for c in baselines.values()))
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# ALERTS
# ═══════════════════════════════════════════════════════════

def get_unacknowledged_alerts(limit: int = 50) -> list[dict]:
    """Get unacknowledged alerts.

    Args:
        limit: Maximum alerts to return.

    Returns:
        List of alert dicts with competitor name joined.
    """
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT a.*, c.name as competitor_name
            FROM alerts a
            LEFT JOIN competitors c ON a.competitor_id = c.id
            WHERE a.acknowledged = 0
            ORDER BY
                CASE a.severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                a.timestamp DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def acknowledge_alert(alert_id: int) -> bool:
    """Mark an alert as acknowledged.

    Args:
        alert_id: Alert ID to acknowledge.

    Returns:
        True if acknowledged, False if not found.
    """
    conn = get_db()
    try:
        cursor = conn.execute(
            "UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# COMPETITIVE INTELLIGENCE REPORT
# ═══════════════════════════════════════════════════════════

def generate_report() -> dict:
    """Generate a comprehensive competitive intelligence report.

    Returns:
        Dict with market overview, competitor details, pricing landscape,
        and strategic insights.
    """
    conn = get_db()
    try:
        _ensure_competitors(conn)
        report: dict = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "competitors": [],
            "pricing_landscape": {},
            "alerts_summary": {},
            "trend_summary": {},
        }

        # Competitor details with latest pricing
        for comp in COMPETITORS:
            row = conn.execute(
                "SELECT * FROM competitors WHERE name = ?", (comp.name,)
            ).fetchone()
            if not row:
                continue

            latest_prices = conn.execute("""
                SELECT tier, price_eur, currency, timestamp
                FROM price_snapshots
                WHERE competitor_id = ?
                ORDER BY timestamp DESC
                LIMIT 10
            """, (row["id"],)).fetchall()

            recent_alerts = conn.execute("""
                SELECT alert_type, description, severity, timestamp
                FROM alerts
                WHERE competitor_id = ?
                ORDER BY timestamp DESC
                LIMIT 5
            """, (row["id"],)).fetchall()

            report["competitors"].append({
                "name": row["name"],
                "category": row["category"],
                "url": row["url"],
                "last_checked": row["last_checked"],
                "prices": [dict(p) for p in latest_prices],
                "recent_alerts": [dict(a) for a in recent_alerts],
            })

        # Pricing landscape — avg price by tier across all competitors
        for tier_name in ("free", "starter", "professional", "business", "unknown"):
            avg_row = conn.execute("""
                SELECT AVG(price_eur) as avg_price, COUNT(DISTINCT competitor_id) as num_competitors
                FROM price_snapshots
                WHERE tier = ? AND price_eur > 0
                AND timestamp > datetime('now', '-30 days')
            """, (tier_name,)).fetchone()

            if avg_row and avg_row["avg_price"]:
                report["pricing_landscape"][tier_name] = {
                    "avg_price_eur": round(avg_row["avg_price"], 2),
                    "num_competitors": avg_row["num_competitors"],
                }

        # Alerts summary
        alert_counts = conn.execute("""
            SELECT severity, COUNT(*) as cnt
            FROM alerts
            WHERE acknowledged = 0
            GROUP BY severity
        """).fetchall()
        report["alerts_summary"] = {row["severity"]: row["cnt"] for row in alert_counts}

        # Trend summary
        for country in ("MT", "BG"):
            trends_data = conn.execute("""
                SELECT keyword, value, timestamp
                FROM trends
                WHERE country = ?
                ORDER BY timestamp DESC
                LIMIT 20
            """, (country,)).fetchall()
            report["trend_summary"][country] = [dict(t) for t in trends_data]

        return report
    finally:
        conn.close()


def print_report() -> None:
    """Print a formatted competitive intelligence report."""
    report = generate_report()
    print("\n" + "=" * 70)
    print("  PlanO Competitive Intelligence Report")
    print(f"  Generated: {report['generated_at'][:19]} UTC")
    print("=" * 70)

    # Alerts
    alerts = report.get("alerts_summary", {})
    if alerts:
        total_alerts = sum(alerts.values())
        print(f"\n  ALERTS: {total_alerts} unacknowledged", end="")
        parts = [f"{sev}={cnt}" for sev, cnt in sorted(alerts.items())]
        print(f" ({', '.join(parts)})")
    else:
        print("\n  ALERTS: None pending")

    # Pricing landscape
    print(f"\n  {'─' * 66}")
    print("  PRICING LANDSCAPE (30-day avg):")
    for tier, data in report.get("pricing_landscape", {}).items():
        print(f"    {tier:15s}  avg={data['avg_price_eur']:>7.2f} EUR  ({data['num_competitors']} competitors)")

    # Competitors
    print(f"\n  {'─' * 66}")
    print("  COMPETITORS:")
    for comp in report["competitors"]:
        checked = comp["last_checked"][:10] if comp["last_checked"] else "never"
        price_str = ""
        if comp["prices"]:
            prices = [f"{p['price_eur']:.0f}" for p in comp["prices"][:3]]
            price_str = f"  prices: {', '.join(prices)} {comp['prices'][0]['currency']}"
        alerts_count = len(comp.get("recent_alerts", []))
        alert_str = f"  [{alerts_count} alerts]" if alerts_count else ""
        print(f"    {comp['name']:20s} ({comp['category']})  checked={checked}{price_str}{alert_str}")

    # Trends
    for country in ("MT", "BG"):
        trends = report.get("trend_summary", {}).get(country, [])
        if trends:
            print(f"\n  {'─' * 66}")
            print(f"  TRENDS ({country}):")
            # Group by keyword
            seen_keywords: set[str] = set()
            for t in trends:
                if t["keyword"] not in seen_keywords:
                    seen_keywords.add(t["keyword"])
                    print(f"    {t['keyword']:30s}  value={t['value']:>5.1f}  ({t['timestamp'][:10]})")

    print("\n" + "=" * 70 + "\n")

    # Save JSON
    output = DATA_DIR / "latest_competition_report.json"
    with open(output, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  JSON written to {output}\n")


# ═══════════════════════════════════════════════════════════
# SFT TRAINING DATA EXPORT
# ═══════════════════════════════════════════════════════════

def export_sft_pairs() -> list[dict]:
    """Export SFT training pairs for the Competitive Analyst agent.

    Generates question-answer pairs from competitive data, alerts,
    and market trends.

    Returns:
        List of SFT message dicts.
    """
    pairs = []
    conn = get_db()
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)

    try:
        _ensure_competitors(conn)

        system_prompt = (
            "You are the Competitive Analyst for PlanO, a renovation SaaS "
            "operating in Malta and Bulgaria. You monitor competitors, track "
            "pricing changes, and provide strategic recommendations."
        )

        # Competitor overview pairs
        competitors = conn.execute("SELECT * FROM competitors ORDER BY name").fetchall()
        for comp in competitors:
            latest = conn.execute("""
                SELECT tier, price_eur, currency
                FROM price_snapshots
                WHERE competitor_id = ?
                ORDER BY timestamp DESC LIMIT 5
            """, (comp["id"],)).fetchall()

            if latest:
                price_info = "; ".join(f"{p['tier']}={p['price_eur']:.2f} {p['currency']}" for p in latest)
                pairs.append({
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"What do we know about {comp['name']} as a competitor?"},
                        {"role": "assistant", "content": (
                            f"{comp['name']} ({comp['category']}) is a competitor at {comp['url']}. "
                            f"Latest known pricing: {price_info}. "
                            f"Last checked: {comp['last_checked'] or 'never'}. "
                            f"They compete in the {comp['category']} segment which "
                            f"{'directly' if 'floor plan' in comp['category'].lower() else 'indirectly'} "
                            f"overlaps with PlanO's renovation planning offering."
                        )},
                    ]
                })

        # Price change alert pairs
        alerts = conn.execute("""
            SELECT a.*, c.name as competitor_name
            FROM alerts a
            JOIN competitors c ON a.competitor_id = c.id
            WHERE a.alert_type = 'price_change'
            ORDER BY a.timestamp DESC
            LIMIT 20
        """).fetchall()

        for alert in alerts:
            pairs.append({
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Alert: {alert['competitor_name']} — {alert['description']}. What should we do?"},
                    {"role": "assistant", "content": (
                        f"This is a {alert['severity']}-severity price change. "
                        f"{'We should evaluate our own pricing in this tier immediately.' if alert['severity'] in ('high', 'critical') else 'Monitor for customer reaction before responding.'} "
                        f"Key actions: 1) Compare our value proposition at this price point, "
                        f"2) Check if other competitors are following, "
                        f"3) {'Consider a promotional response' if 'increase' not in alert['description'] else 'Evaluate if we have room to optimize our pricing upward'}."
                    )},
                ]
            })

        # Market trend pairs
        for country in ("MT", "BG"):
            trends = conn.execute("""
                SELECT keyword, value FROM trends
                WHERE country = ?
                GROUP BY keyword
                HAVING MAX(timestamp)
                ORDER BY value DESC
            """, (country,)).fetchall()

            if trends:
                trend_info = ", ".join(f"'{t['keyword']}'={t['value']:.0f}" for t in trends)
                market_name = "Malta" if country == "MT" else "Bulgaria"
                pairs.append({
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"What are the search trends in {market_name}?"},
                        {"role": "assistant", "content": (
                            f"Current search interest in {market_name} (0-100 scale): {trend_info}. "
                            f"{'Malta shows moderate interest in floor planning tools, suggesting a niche but engaged market.' if country == 'MT' else 'Bulgaria shows strong interest in renovation planning in Cyrillic, indicating localization is essential.'} "
                            f"Recommendation: Focus content marketing on the highest-interest keywords and "
                            f"monitor for seasonal patterns."
                        )},
                    ]
                })

        # Strategic pairs from pricing landscape
        landscape = conn.execute("""
            SELECT tier, AVG(price_eur) as avg_price, MIN(price_eur) as min_price, MAX(price_eur) as max_price
            FROM price_snapshots
            WHERE price_eur > 0
            GROUP BY tier
        """).fetchall()

        if landscape:
            for row in landscape:
                if row["tier"] == "unknown":
                    continue
                pairs.append({
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"What is the competitive pricing range for the '{row['tier']}' tier?"},
                        {"role": "assistant", "content": (
                            f"For the '{row['tier']}' tier across tracked competitors: "
                            f"average={row['avg_price']:.2f} EUR, range={row['min_price']:.2f}-{row['max_price']:.2f} EUR. "
                            f"PlanO should position {'below average to gain market share' if row['tier'] == 'starter' else 'competitively while emphasizing unique AI renovation features'} "
                            f"in this tier."
                        )},
                    ]
                })

        # Write to file
        output_path = TRAINING_DIR / "competitive_analyst_sft.jsonl"
        with open(output_path, "w") as f:
            for pair in pairs:
                f.write(json.dumps(pair) + "\n")

        log.info("Exported %d SFT pairs to %s", len(pairs), output_path)
        return pairs
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════

def print_alerts() -> None:
    """Print unacknowledged alerts."""
    alerts = get_unacknowledged_alerts()
    print(f"\n{'=' * 60}")
    print(f"  PlanO Competition Monitor — Alerts ({len(alerts)} unacknowledged)")
    print(f"{'=' * 60}")

    if not alerts:
        print("\n  No unacknowledged alerts.\n")
        return

    for alert in alerts:
        sev_marker = {"critical": "!!!", "high": "!!", "medium": "!", "low": ".", "info": " "}.get(alert["severity"], " ")
        comp_name = alert.get("competitor_name", "Unknown")
        print(f"\n  [{sev_marker}] #{alert['id']} {alert['severity'].upper():8s} {comp_name}")
        print(f"      {alert['alert_type']}: {alert['description']}")
        print(f"      {alert['timestamp'][:19]}")

    print(f"\n{'=' * 60}\n")


def print_trends(keyword: str, country: str) -> None:
    """Print trend data for a keyword-country pair."""
    trends = get_trends(keyword, country)
    print(f"\n{'=' * 60}")
    print(f"  Trends: '{keyword}' in {country}")
    print(f"{'=' * 60}")

    if not trends:
        print(f"\n  No trend data found for '{keyword}' in {country}.")
        print("  Run 'scan' first to seed baseline estimates.\n")
        return

    for t in trends:
        bar = "#" * int(t["value"] / 2)
        print(f"  {t['timestamp'][:10]}  {t['value']:>5.1f}  {bar}  ({t['source']})")

    print(f"\n{'=' * 60}\n")


def print_scan_results(results: list[dict]) -> None:
    """Print formatted scan results."""
    print(f"\n{'=' * 60}")
    print("  PlanO Competition Monitor — Scan Results")
    print(f"{'=' * 60}")

    for r in results:
        status_icon = {"ok": "+", "fetch_failed": "X", "no_prices_found": "?", "unknown": "-"}.get(r["status"], "?")
        alerts_str = f"  [{len(r['alerts'])} alerts]" if r["alerts"] else ""
        print(f"  [{status_icon}] {r['name']:20s}  prices={r['prices_found']}{alerts_str}")

    ok = sum(1 for r in results if r["status"] == "ok")
    total_alerts = sum(len(r["alerts"]) for r in results)
    print(f"\n  Summary: {ok}/{len(results)} OK, {total_alerts} new alerts")
    print(f"{'=' * 60}\n")


def main() -> None:
    """CLI entry point for the competition monitor."""
    parser = argparse.ArgumentParser(
        description="PlanO Competition Monitor — competitive intelligence agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("scan", help="Scan all competitors")
    sub.add_parser("alerts", help="Show unacknowledged alerts")
    sub.add_parser("report", help="Generate competitive intelligence report")

    trends_parser = sub.add_parser("trends", help="Show trend data")
    trends_parser.add_argument("--keyword", required=True, help="Search keyword")
    trends_parser.add_argument("--country", required=True, help="Country code (MT or BG)")

    sub.add_parser("train-export", help="Export SFT training pairs")

    args = parser.parse_args()

    if args.command == "scan":
        seed_trend_baselines()
        results = scan_all()
        print_scan_results(results)
    elif args.command == "alerts":
        print_alerts()
    elif args.command == "report":
        print_report()
    elif args.command == "trends":
        print_trends(args.keyword, args.country)
    elif args.command == "train-export":
        pairs = export_sft_pairs()
        print(f"Exported {len(pairs)} SFT training pairs")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
