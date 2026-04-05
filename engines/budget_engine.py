#!/usr/bin/env python3
"""
Budget Engine — Multi-Level Hierarchical Budgeting
Reads from finance_lake.db, provides drill-down expense tracking and budgeting.

Levels:
  0: TOTAL (all spending)
  1: COMPARTMENT (PERSONAL, PROFESSIONAL, FAMILIAL, DIVORCE, OBLIGATIONS, ACCOUNTING)
  2: CATEGORY (food, transport, shopping, legal_fees_monaco, etc.)
  3: SUBCATEGORY (uber_eats, wolt, bolt, spires_tutors, etc.)
  4: MERCHANT (individual merchant names)

Usage:
  budget init                          Create tables, seed merchant map
  budget summary [YYYY-MM]             Monthly summary all levels
  budget daily [YYYY-MM-DD]            Daily breakdown
  budget weekly [YYYY-Www]             Weekly breakdown
  budget monthly [YYYY]                Monthly trend for year
  budget quarterly [YYYY]              Quarterly rollup
  budget yearly                        Year-over-year comparison
  budget compartment <name> [period]   Drill into compartment
  budget category <name> [period]      Drill into category
  budget merchant <pattern> [period]   Drill into merchant
  budget top [N] [period]              Top N expenses
  budget burn [months]                 Burn rate projection
  budget trend <category> [months]     Category trend over time
  budget compare <m1> <m2>             Compare two months
  budget set-target <comp> <cat> <amt> Set budget target
  budget targets                       Show all targets with status
  budget alerts                        Show budget alerts (over target)
  budget food [period]                 Quick shortcut for food spending
  budget transport [period]            Quick shortcut for transport
  budget education [period]            Quick shortcut for education/tutoring
  budget subscriptions [period]        Quick shortcut for subscriptions
  budget travel-spend [period]         Travel spending by destination
  budget stats                         Overall statistics
  budget export [file]                 Export full budget data as JSON
  budget projection [months]           12-month projection (current vs EUR 20K target)
  budget classify [start_date]         Investment vs expense classification
  budget runway                        Months of runway at current vs target burn
  budget cuts                          What to cut to reach EUR 20K/month target
"""

import sys
import os
import re
import json
import sqlite3
import math
from datetime import datetime, timedelta, date
from pathlib import Path
from collections import defaultdict

# ── Paths ──────────────────────────────────────────────────────────────────
DB_PATH = Path(os.path.expanduser("~/forensic/personal-finance/db/finance_lake.db"))

# ── ANSI Colors ────────────────────────────────────────────────────────────
class C:
    RST = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"

COMPARTMENT_COLORS = {
    "PERSONAL": C.CYAN,
    "PROFESSIONAL": C.BLUE,
    "FAMILIAL": C.GREEN,
    "DIVORCE": C.RED,
    "OBLIGATIONS": C.YELLOW,
    "ACCOUNTING": C.MAGENTA,
}

# ── Merchant Map (seed data) ──────────────────────────────────────────────
MERCHANT_SEEDS = [
    ("UBER *EATS", "uber_eats", "PERSONAL", "food", "GLOBAL", None),
    ("UBER *TRIP", "uber_rides", "PERSONAL", "transport", "GLOBAL", None),
    ("UBER *ONE", "uber_one", "PERSONAL", "subscriptions", "GLOBAL", None),
    ("BOLT.EU", "bolt_rides", "PERSONAL", "transport", "MALTA", None),
    ("Wolt", "wolt", "PERSONAL", "food", "MALTA", None),
    ("SPIRES ONLINE TUTORS", "spires_tutors", "FAMILIAL", "school_extras", "ONLINE", None),
    ("STUDY MIND", "study_mind", "FAMILIAL", "school_extras", "ONLINE", None),
    ("REVISION VILLAGE", "revision_village", "FAMILIAL", "school_extras", "ONLINE", None),
    ("STARLINK", "starlink", "PERSONAL", "telecom", "GLOBAL", None),
    ("Starlink", "starlink", "PERSONAL", "telecom", "GLOBAL", None),
    ("MONACO TELECOM", "monaco_telecom", "PERSONAL", "telecom", "MONACO", None),
    ("Monaco Telecom", "monaco_telecom", "PERSONAL", "telecom", "MONACO", None),
    ("ENGIE", "engie", "PERSONAL", "housing", "FRANCE", None),
    ("GOOGLE*PLAY", "google_play", "PERSONAL", "subscriptions", "ONLINE", None),
    ("GOOGLE*YOUTUBE", "youtube", "PERSONAL", "subscriptions", "ONLINE", None),
    ("KICKSTARTER", "kickstarter", "PERSONAL", "shopping", "ONLINE", None),
    ("INDIEGOGO", "indiegogo", "PERSONAL", "shopping", "ONLINE", None),
    ("PLIXI", "plixi", "PROFESSIONAL", "business_expense", "ONLINE", None),
    ("Plixi", "plixi", "PROFESSIONAL", "business_expense", "ONLINE", None),
    ("MEDETONE PHARMACY", "medetone", "PERSONAL", "health_personal", "MALTA", None),
    ("PAYPAL *ITUNESAPPST", "apple_itunes", "PERSONAL", "subscriptions", "ONLINE", None),
    ("Hotel at Booking.com", "booking_hotel", "PERSONAL", "travel", "GLOBAL", None),
    ("Palace Hotel Gstaad", "palace_gstaad", "PERSONAL", "travel", "SWITZERLAND", None),
    ("Berghotel Hahnenmoospa", "berghotel", "PERSONAL", "travel", "SWITZERLAND", None),
    ("SumUp *Taxi", "sumup_taxi", "PERSONAL", "transport", "SWITZERLAND", None),
    ("CAPT. A. CARUANA", "caruana_ws", "PERSONAL", "food", "MALTA", None),
    ("Cafe Giorgio", "cafe_giorgio", "PERSONAL", "food", "MALTA", None),
    ("BURGER KING VALLETTA", "bk_valletta", "PERSONAL", "food", "MALTA", None),
    ("MC DONALD", "mcdonalds", "PERSONAL", "food", "GLOBAL", None),
    ("WWW.FLEURETFLEURS.FR", "fleuretfleurs", "PERSONAL", "gifts", "FRANCE", None),
    ("CARHARTT", "carhartt", "PERSONAL", "shopping", "ONLINE", None),
    ("SP VOLLEBAK", "vollebak", "PERSONAL", "shopping", "ONLINE", None),
    ("SP CREED LEATHER", "creed", "PERSONAL", "shopping", "ONLINE", None),
    ("incogni.com", "incogni", "PERSONAL", "subscriptions", "ONLINE", None),
    ("CASELA WORLD", "casela", "PERSONAL", "entertainment", "MAURITIUS", None),
    ("ASS UNION FRAN", "assurance_union", "OBLIGATIONS", "insurance_home", "FRANCE", None),
    ("BRAZECO", "brazeco", "PERSONAL", "housing", "FRANCE", None),
    ("DHL", "dhl_shipping", "PERSONAL", "misc_personal", "GLOBAL", None),
    ("FEDERAL EXPRESS", "fedex_shipping", "PERSONAL", "misc_personal", "GLOBAL", None),
    ("Vodafone", "vodafone_roaming", "PERSONAL", "telecom", "GLOBAL", None),
    ("ASICS", "asics", "PERSONAL", "shopping", "SWITZERLAND", None),
    ("LA POSTE", "la_poste", "PROFESSIONAL", "business_expense", "FRANCE", None),
    ("AMAZON", "amazon", "PERSONAL", "shopping", "ONLINE", None),
    ("AMZN Mktp", "amazon", "PERSONAL", "shopping", "ONLINE", None),
    ("Trainline", "trainline", "PERSONAL", "transport", "EUROPE", None),
    ("SAMSUNG", "samsung", "PERSONAL", "subscriptions", "ONLINE", None),
    ("ALLDEBRID", "alldebrid", "PERSONAL", "subscriptions", "ONLINE", None),
    ("help.madmuscles", "madmuscles", "PERSONAL", "subscriptions", "ONLINE", None),
    ("SKIMS", "skims", "PERSONAL", "shopping", "ONLINE", None),
    ("STILETTO", "stiletto", "PERSONAL", "shopping", "ONLINE", None),
    ("VETEMENTACC", "vetements", "PERSONAL", "shopping", "ONLINE", None),
    ("GlobalE/Guizio", "guizio", "PERSONAL", "shopping", "ONLINE", None),
    ("PAYPAL *WILLEMSE", "willemse", "PERSONAL", "shopping", "ONLINE", None),
    ("PAYPAL *BLAINE", "blaine_box", "PERSONAL", "shopping", "ONLINE", None),
    ("PAYPAL *COMMENT FER", "comment_fer", "PERSONAL", "shopping", "ONLINE", None),
    ("PAYPAL *LONGEVITYST", "longevity_store", "PERSONAL", "health_personal", "ONLINE", None),
    ("PAYPAL *SANITINO", "sanitino", "PERSONAL", "housing", "ONLINE", None),
    ("PAYPAL *SOUNDMACHNE", "soundmachine", "PERSONAL", "entertainment", "ONLINE", None),
    ("PAYPAL *THE NEW GAR", "new_garden", "PERSONAL", "shopping", "ONLINE", None),
    ("Dick's Dumpstore", "dicks_dumpstore", "PERSONAL", "shopping", "ONLINE", None),
    ("EIKEN SHOP", "eiken_shop", "PERSONAL", "shopping", "ONLINE", None),
    ("FS *patterncouture", "pattern_couture", "PERSONAL", "shopping", "ONLINE", None),
    ("PYRENE BUSHCRAFT", "pyrene_bushcraft", "PERSONAL", "shopping", "ONLINE", None),
    ("SP NATURES FABRICS", "natures_fabrics", "PERSONAL", "shopping", "ONLINE", None),
    ("THE ATRIUM", "the_atrium", "PERSONAL", "shopping", "MALTA", None),
    ("SCP Spinosi", "spinosi", "DIVORCE", "legal_fees_france", "FRANCE", "Cassation lawyer"),
]


# ── Database ──────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_tables():
    """Create budget_targets and merchant_map tables, seed merchant map."""
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS budget_targets (
        id INTEGER PRIMARY KEY,
        compartment TEXT NOT NULL,
        category TEXT,
        subcategory TEXT,
        period TEXT DEFAULT 'monthly',
        target_amount REAL NOT NULL,
        currency TEXT DEFAULT 'EUR',
        alert_pct REAL DEFAULT 80.0,
        created_at TEXT DEFAULT (datetime('now')),
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS merchant_map (
        merchant_pattern TEXT PRIMARY KEY,
        subcategory TEXT NOT NULL,
        compartment TEXT,
        category TEXT,
        location_hint TEXT,
        notes TEXT
    );
    """)

    # Seed merchant map
    for pattern, subcat, comp, cat, loc, notes in MERCHANT_SEEDS:
        conn.execute("""
            INSERT OR IGNORE INTO merchant_map (merchant_pattern, subcategory, compartment, category, location_hint, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (pattern, subcat, comp, cat, loc, notes))

    conn.commit()
    # Count
    targets = conn.execute("SELECT count(*) FROM budget_targets").fetchone()[0]
    merchants = conn.execute("SELECT count(*) FROM merchant_map").fetchone()[0]
    conn.close()
    print(f"{C.GREEN}Budget engine initialized.{C.RST}")
    print(f"  budget_targets: {targets} rows")
    print(f"  merchant_map:   {merchants} patterns seeded")


# ── Merchant Resolution ───────────────────────────────────────────────────
def load_merchant_map(conn):
    """Load merchant_map into a list of (pattern, subcat, comp, cat, loc)."""
    try:
        rows = conn.execute("SELECT merchant_pattern, subcategory, compartment, category, location_hint FROM merchant_map").fetchall()
        return [(r[0], r[1], r[2], r[3], r[4]) for r in rows]
    except sqlite3.OperationalError:
        return []


def resolve_merchant(description, merchant_map):
    """Match a transaction description to a subcategory/location via merchant_map."""
    desc_upper = description.upper()
    for pattern, subcat, comp, cat, loc in merchant_map:
        if pattern.upper() in desc_upper:
            return {"subcategory": subcat, "compartment": comp, "category": cat, "location": loc}
    return None


def derive_subcategory(description):
    """Best-effort subcategory from description when no merchant_map match."""
    desc = description.strip()
    # Normalize common prefixes
    if desc.startswith("Pension alimentaire"):
        if "Sosso" in desc:
            return "pension_sosso"
        return "pension_marina"
    if "Monaco Telecom" in desc:
        return "monaco_telecom"
    if desc.startswith("PAS "):
        return "pas_acompte"
    # Use first significant word
    words = re.sub(r'[^a-zA-Z0-9 ]', '', desc).split()
    if words:
        return words[0].lower()
    return "unknown"


# ── Query Helpers ─────────────────────────────────────────────────────────
def get_transactions(conn, where="1=1", params=(), debits_only=True):
    """Fetch transactions with optional filtering. Returns list of dicts."""
    debit_clause = "AND amount < 0" if debits_only else ""
    sql = f"""
        SELECT id, date, amount, amount_eur, description, compartment, category,
               subcategory, counterparty, currency, source, account_id
        FROM transactions
        WHERE {where} {debit_clause}
        ORDER BY date DESC
    """
    rows = conn.execute(sql, params).fetchall()
    result = []
    for r in rows:
        amt = r["amount_eur"] if r["amount_eur"] else r["amount"]
        result.append({
            "id": r["id"],
            "date": r["date"],
            "amount": amt,
            "abs_amount": abs(amt),
            "description": r["description"],
            "compartment": r["compartment"],
            "category": r["category"] or "uncategorized",
            "subcategory": r["subcategory"] or "",
            "counterparty": r["counterparty"] or "",
            "currency": r["currency"],
            "source": r["source"] or "",
        })
    return result


def period_filter(period_str):
    """Parse period string to SQL WHERE clause and params.
    Accepts: YYYY-MM, YYYY-MM-DD, YYYY, YYYY-Qn, or None (current month)."""
    if not period_str:
        now = datetime.now()
        start = now.strftime("%Y-%m-01")
        # end of month
        if now.month == 12:
            end = f"{now.year + 1}-01-01"
        else:
            end = f"{now.year}-{now.month + 1:02d}-01"
        return "date >= ? AND date < ?", (start, end), now.strftime("%B %Y")

    p = period_str.strip()

    # YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}$', p):
        return "date = ?", (p,), p

    # YYYY-MM
    if re.match(r'^\d{4}-\d{2}$', p):
        y, m = int(p[:4]), int(p[5:7])
        start = f"{y}-{m:02d}-01"
        if m == 12:
            end = f"{y + 1}-01-01"
        else:
            end = f"{y}-{m + 1:02d}-01"
        dt = datetime(y, m, 1)
        label = dt.strftime("%B %Y")
        return "date >= ? AND date < ?", (start, end), label

    # YYYY-Qn
    qm = re.match(r'^(\d{4})-Q(\d)$', p, re.IGNORECASE)
    if qm:
        y, q = int(qm.group(1)), int(qm.group(2))
        sm = (q - 1) * 3 + 1
        start = f"{y}-{sm:02d}-01"
        em = sm + 3
        if em > 12:
            end = f"{y + 1}-{em - 12:02d}-01"
        else:
            end = f"{y}-{em:02d}-01"
        return "date >= ? AND date < ?", (start, end), f"Q{q} {y}"

    # YYYY-Www
    wm = re.match(r'^(\d{4})-W(\d{1,2})$', p, re.IGNORECASE)
    if wm:
        y, w = int(wm.group(1)), int(wm.group(2))
        start_dt = datetime.strptime(f"{y}-W{w:02d}-1", "%Y-W%W-%w")
        if start_dt.weekday() != 0:
            start_dt = datetime.strptime(f"{y}-W{w:02d}-1", "%G-W%V-%u")
        end_dt = start_dt + timedelta(days=7)
        return "date >= ? AND date < ?", (start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")), f"Week {w}, {y}"

    # YYYY
    if re.match(r'^\d{4}$', p):
        return "date >= ? AND date < ?", (f"{p}-01-01", f"{int(p) + 1}-01-01"), p

    return "1=1", (), p


def month_range(year, month):
    """Return (start_date, end_date) strings for a given year/month."""
    start = f"{year}-{month:02d}-01"
    if month == 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{month + 1:02d}-01"
    return start, end


# ── Formatting ────────────────────────────────────────────────────────────
def fmt_eur(amount, width=12):
    """Format amount as EUR string with color."""
    if amount is None:
        return " " * width
    sign = "-" if amount < 0 else "+"
    abs_val = abs(amount)
    if abs_val >= 1000:
        s = f"{sign}{abs_val:,.0f}EUR"
    else:
        s = f"{sign}{abs_val:,.2f}EUR"
    color = C.RED if amount < 0 else C.GREEN
    return f"{color}{s:>{width}}{C.RST}"


def bar(pct, width=20):
    """Render a percentage bar."""
    filled = int(round(pct / 100 * width))
    filled = max(0, min(filled, width))
    if pct >= 100:
        color = C.RED
    elif pct >= 80:
        color = C.YELLOW
    else:
        color = C.GREEN
    return f"{color}{'█' * filled}{C.DIM}{'░' * (width - filled)}{C.RST}"


def box_top(width=72):
    return f"{C.BOLD}╔{'═' * width}╗{C.RST}"


def box_bottom(width=72):
    return f"{C.BOLD}╚{'═' * width}╝{C.RST}"


def box_mid(width=72):
    return f"{C.BOLD}╠{'═' * width}╣{C.RST}"


def box_sep(widths):
    """Separator with column widths."""
    parts = []
    for i, w in enumerate(widths):
        parts.append("─" * w)
    return f"╠{'┼'.join(parts)}╣"


def box_row(cells, widths):
    """Row with cells aligned to widths."""
    parts = []
    for cell, w in zip(cells, widths):
        # Strip ANSI for length calculation
        visible = re.sub(r'\033\[[0-9;]*m', '', str(cell))
        pad = w - len(visible)
        if pad < 0:
            # Truncate visible part
            parts.append(str(cell)[:w])
        else:
            parts.append(str(cell) + " " * pad)
    return f"║{'│'.join(parts)}║"


def print_title(title, width=72):
    print(box_top(width))
    visible = re.sub(r'\033\[[0-9;]*m', '', title)
    pad = width - len(visible)
    print(f"║ {C.BOLD}{title}{C.RST}{' ' * max(0, pad - 1)}║")
    print(box_mid(width))


def print_table(headers, rows, widths=None, title=None):
    """Print a formatted table."""
    if not widths:
        widths = []
        for i, h in enumerate(headers):
            max_w = len(h)
            for row in rows[:50]:
                cell = str(row[i]) if i < len(row) else ""
                visible = re.sub(r'\033\[[0-9;]*m', '', cell)
                max_w = max(max_w, len(visible))
            widths.append(min(max_w + 2, 40))

    total_w = sum(widths) + len(widths) - 1
    if title:
        print_title(title, total_w)
    else:
        print(box_top(total_w))

    # Header
    hcells = [f"{C.BOLD}{h}{C.RST}" for h in headers]
    print(box_row(hcells, widths))
    print(box_sep(widths))

    for row in rows:
        cells = [str(row[i]) if i < len(row) else "" for i in range(len(headers))]
        print(box_row(cells, widths))

    print(box_bottom(total_w))


# ── Commands ──────────────────────────────────────────────────────────────

def cmd_stats(args):
    """Overall statistics."""
    conn = get_db()

    total_txn = conn.execute("SELECT count(*) FROM transactions").fetchone()[0]
    total_debit = conn.execute("SELECT count(*) FROM transactions WHERE amount < 0").fetchone()[0]
    total_credit = conn.execute("SELECT count(*) FROM transactions WHERE amount > 0").fetchone()[0]
    date_range = conn.execute("SELECT min(date), max(date) FROM transactions").fetchone()
    total_spent = conn.execute("SELECT sum(COALESCE(amount_eur, amount)) FROM transactions WHERE amount < 0").fetchone()[0] or 0

    # Exclude ACCOUNTING and large non-spending items for meaningful burn
    spending_sql = """
        SELECT sum(COALESCE(amount_eur, amount)) FROM transactions
        WHERE amount < 0 AND compartment != 'ACCOUNTING'
    """
    total_real_spent = conn.execute(spending_sql).fetchone()[0] or 0

    # Monthly averages (exclude ACCOUNTING)
    months_sql = """
        SELECT count(DISTINCT strftime('%Y-%m', date)) FROM transactions
        WHERE amount < 0 AND compartment != 'ACCOUNTING'
    """
    n_months = conn.execute(months_sql).fetchone()[0] or 1
    avg_monthly = total_real_spent / n_months

    # Current month
    now = datetime.now()
    cm_start = now.strftime("%Y-%m-01")
    if now.month == 12:
        cm_end = f"{now.year + 1}-01-01"
    else:
        cm_end = f"{now.year}-{now.month + 1:02d}-01"

    cm_spent = conn.execute("""
        SELECT sum(COALESCE(amount_eur, amount)) FROM transactions
        WHERE amount < 0 AND compartment != 'ACCOUNTING'
        AND date >= ? AND date < ?
    """, (cm_start, cm_end)).fetchone()[0] or 0

    # Days elapsed this month, project full month
    day_of_month = now.day
    import calendar
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    projected_month = (cm_spent / day_of_month) * days_in_month if day_of_month > 0 else 0

    # Compartment breakdown
    comp_rows = conn.execute("""
        SELECT compartment, count(*), sum(COALESCE(amount_eur, amount))
        FROM transactions WHERE amount < 0
        GROUP BY compartment ORDER BY sum(COALESCE(amount_eur, amount))
    """).fetchall()

    # Merchant map and targets
    try:
        n_merchants = conn.execute("SELECT count(*) FROM merchant_map").fetchone()[0]
    except sqlite3.OperationalError:
        n_merchants = 0
    try:
        n_targets = conn.execute("SELECT count(*) FROM budget_targets").fetchone()[0]
    except sqlite3.OperationalError:
        n_targets = 0

    conn.close()

    width = 72
    print_title(f"{C.CYAN}BUDGET ENGINE — Statistics{C.RST}", width)

    lines = [
        f"  Transactions:     {C.BOLD}{total_txn}{C.RST} total ({total_debit} debits, {total_credit} credits)",
        f"  Date range:       {C.BOLD}{date_range[0]}{C.RST} to {C.BOLD}{date_range[1]}{C.RST}",
        f"  Months of data:   {C.BOLD}{n_months}{C.RST}",
        f"  Total debits:     {fmt_eur(total_spent)}",
        f"  Real spending:    {fmt_eur(total_real_spent)} (excl. ACCOUNTING)",
        f"  Avg monthly:      {fmt_eur(avg_monthly)}",
        "",
        f"  {C.BOLD}Current Month ({now.strftime('%B %Y')}){C.RST}",
        f"  Spent so far:     {fmt_eur(cm_spent)} ({day_of_month}/{days_in_month} days)",
        f"  Projected:        {fmt_eur(projected_month)}",
        "",
        f"  Merchant patterns: {C.BOLD}{n_merchants}{C.RST}",
        f"  Budget targets:    {C.BOLD}{n_targets}{C.RST}",
    ]

    for line in lines:
        visible = re.sub(r'\033\[[0-9;]*m', '', line)
        pad = width - len(visible)
        print(f"║{line}{' ' * max(0, pad)}║")

    print(box_mid(width))

    # Compartment breakdown
    header = f"  {'COMPARTMENT':<18} {'COUNT':>6} {'TOTAL':>14} {'%':>7}  BAR"
    visible = re.sub(r'\033\[[0-9;]*m', '', header)
    print(f"║{header}{' ' * (width - len(visible))}║")

    total_abs = sum(abs(r[2]) for r in comp_rows if r[2]) or 1
    for r in comp_rows:
        comp = r[0] or "NULL"
        cnt = r[1]
        amt = r[2] or 0
        pct = abs(amt) / total_abs * 100
        color = COMPARTMENT_COLORS.get(comp, C.WHITE)
        line = f"  {color}{comp:<18}{C.RST} {cnt:>6} {fmt_eur(amt, 14)} {pct:>6.1f}%  {bar(pct, 15)}"
        visible = re.sub(r'\033\[[0-9;]*m', '', line)
        print(f"║{line}{' ' * max(0, width - len(visible))}║")

    print(box_bottom(width))


def cmd_summary(args):
    """Monthly summary with hierarchical breakdown."""
    period = args[0] if args else None
    conn = get_db()
    merchant_map = load_merchant_map(conn)

    where, params, label = period_filter(period)
    txns = get_transactions(conn, where, params)

    if not txns:
        print(f"{C.YELLOW}No transactions found for {label}.{C.RST}")
        conn.close()
        return

    # Aggregate by compartment > category > subcategory
    tree = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    comp_totals = defaultdict(float)
    cat_totals = defaultdict(float)
    grand_total = 0

    for t in txns:
        comp = t["compartment"]
        cat = t["category"]
        # Resolve subcategory
        sub = t["subcategory"]
        if not sub:
            resolved = resolve_merchant(t["description"], merchant_map)
            if resolved:
                sub = resolved["subcategory"]
            else:
                sub = derive_subcategory(t["description"])

        tree[comp][cat][sub] += t["amount"]
        comp_totals[comp] += t["amount"]
        cat_totals[f"{comp}/{cat}"] += t["amount"]
        grand_total += t["amount"]

    width = 72
    print_title(f"{C.CYAN}BUDGET SUMMARY — {label}{C.RST}", width)

    headers = ["COMPARTMENT", "Category", "Subcategory", "Amount", "% Total"]
    widths_t = [16, 18, 20, 13, 12]
    tw = sum(widths_t) + len(widths_t) - 1

    hcells = [f"{C.BOLD}{h}{C.RST}" for h in headers]
    # Reprint top with correct width
    print(f"\r", end="")
    # Just print header row and separator
    print(box_row(hcells, widths_t))
    print(box_sep(widths_t))

    abs_total = abs(grand_total) if grand_total != 0 else 1

    # Sort compartments by total spent
    sorted_comps = sorted(comp_totals.items(), key=lambda x: x[1])

    for comp, comp_amt in sorted_comps:
        color = COMPARTMENT_COLORS.get(comp, C.WHITE)
        # Compartment total row
        pct = abs(comp_amt) / abs_total * 100
        cells = [
            f"{color}{C.BOLD}{comp}{C.RST}",
            "",
            "",
            fmt_eur(comp_amt, 11),
            f"{pct:>5.1f}% {bar(pct, 6)}",
        ]
        print(box_row(cells, widths_t))

        # Sort categories within compartment
        sorted_cats = sorted(tree[comp].items(), key=lambda x: sum(x[1].values()))
        for cat, subs in sorted_cats:
            cat_amt = sum(subs.values())
            cat_pct = abs(cat_amt) / abs_total * 100
            cells = [
                "",
                f"  {cat}",
                "",
                fmt_eur(cat_amt, 11),
                f"{cat_pct:>5.1f}%",
            ]
            print(box_row(cells, widths_t))

            # Subcategories (only if >1 or interesting)
            if len(subs) > 1 or (len(subs) == 1 and list(subs.keys())[0] != cat):
                sorted_subs = sorted(subs.items(), key=lambda x: x[1])
                for sub, sub_amt in sorted_subs:
                    sub_pct = abs(sub_amt) / abs_total * 100
                    cells = [
                        "",
                        "",
                        f"    {sub[:18]}",
                        fmt_eur(sub_amt, 11),
                        f"{sub_pct:>5.1f}%",
                    ]
                    print(box_row(cells, widths_t))

        # Separator between compartments
        print(box_sep(widths_t))

    # Grand total
    cells = [
        f"{C.BOLD}TOTAL{C.RST}",
        "",
        f"{len(txns)} txns",
        fmt_eur(grand_total, 11),
        "100.0%",
    ]
    print(box_row(cells, widths_t))
    print(box_bottom(sum(widths_t) + len(widths_t) - 1))

    conn.close()


def cmd_daily(args):
    """Daily breakdown."""
    period = args[0] if args else None
    conn = get_db()

    if period and re.match(r'^\d{4}-\d{2}-\d{2}$', period):
        where, params, label = period_filter(period)
    elif period and re.match(r'^\d{4}-\d{2}$', period):
        where, params, label = period_filter(period)
    else:
        where, params, label = period_filter(period)

    txns = get_transactions(conn, where, params)
    conn.close()

    if not txns:
        print(f"{C.YELLOW}No transactions for {label}.{C.RST}")
        return

    # Group by date
    daily = defaultdict(list)
    for t in txns:
        daily[t["date"]].append(t)

    rows = []
    for d in sorted(daily.keys()):
        day_txns = daily[d]
        total = sum(t["amount"] for t in day_txns)
        cats = defaultdict(float)
        for t in day_txns:
            cats[t["category"]] += t["amount"]
        top_cats = sorted(cats.items(), key=lambda x: x[1])[:3]
        cat_str = ", ".join(f"{c}: {fmt_eur(a, 8)}" for c, a in top_cats)
        rows.append((d, f"{len(day_txns):>3}", fmt_eur(total, 11), cat_str))

    print_table(
        ["Date", "#Txn", "Total", "Top Categories"],
        rows,
        widths=[12, 5, 13, 45],
        title=f"{C.CYAN}DAILY BREAKDOWN — {label}{C.RST}"
    )

    # Summary
    total = sum(t["amount"] for t in txns)
    avg = total / len(daily) if daily else 0
    print(f"\n  Total: {fmt_eur(total)}  |  Daily avg: {fmt_eur(avg)}  |  {len(daily)} days, {len(txns)} txns")


def cmd_weekly(args):
    """Weekly breakdown."""
    period = args[0] if args else None
    conn = get_db()

    # Default to current month for weekly view
    if period and re.match(r'^\d{4}-W\d{1,2}$', period, re.IGNORECASE):
        where, params, label = period_filter(period)
    elif period:
        where, params, label = period_filter(period)
    else:
        now = datetime.now()
        where, params, label = period_filter(now.strftime("%Y-%m"))

    txns = get_transactions(conn, where, params)
    conn.close()

    if not txns:
        print(f"{C.YELLOW}No transactions for {label}.{C.RST}")
        return

    # Group by ISO week
    weekly = defaultdict(list)
    for t in txns:
        dt = datetime.strptime(t["date"], "%Y-%m-%d")
        week_key = dt.strftime("%Y-W%V")
        weekly[week_key].append(t)

    rows = []
    for wk in sorted(weekly.keys()):
        wk_txns = weekly[wk]
        total = sum(t["amount"] for t in wk_txns)
        dates = sorted(set(t["date"] for t in wk_txns))
        date_range = f"{dates[0]} to {dates[-1]}" if len(dates) > 1 else dates[0]
        rows.append((wk, f"{len(wk_txns):>3}", fmt_eur(total, 11), date_range))

    print_table(
        ["Week", "#Txn", "Total", "Date Range"],
        rows,
        widths=[10, 5, 13, 30],
        title=f"{C.CYAN}WEEKLY BREAKDOWN — {label}{C.RST}"
    )


def cmd_monthly(args):
    """Monthly trend for a year."""
    year = int(args[0]) if args else datetime.now().year
    conn = get_db()

    rows_data = []
    for m in range(1, 13):
        start, end = month_range(year, m)
        r = conn.execute("""
            SELECT count(*), sum(COALESCE(amount_eur, amount))
            FROM transactions WHERE amount < 0 AND compartment != 'ACCOUNTING'
            AND date >= ? AND date < ?
        """, (start, end)).fetchone()
        cnt = r[0] or 0
        amt = r[1] or 0
        if cnt > 0:
            month_name = datetime(year, m, 1).strftime("%b %Y")
            rows_data.append((month_name, f"{cnt:>4}", fmt_eur(amt, 12), bar(min(abs(amt) / 50000 * 100, 100), 25)))

    if not rows_data:
        print(f"{C.YELLOW}No spending data for {year}.{C.RST}")
        conn.close()
        return

    print_table(
        ["Month", "#Txn", "Spent", "Scale (50K ref)"],
        rows_data,
        widths=[12, 6, 14, 27],
        title=f"{C.CYAN}MONTHLY TREND — {year}{C.RST}"
    )

    # Totals
    total_sql = conn.execute("""
        SELECT sum(COALESCE(amount_eur, amount))
        FROM transactions WHERE amount < 0 AND compartment != 'ACCOUNTING'
        AND date >= ? AND date < ?
    """, (f"{year}-01-01", f"{year + 1}-01-01")).fetchone()
    total = total_sql[0] or 0
    n_months = len(rows_data)
    avg = total / n_months if n_months else 0
    print(f"\n  Year total: {fmt_eur(total)}  |  Monthly avg: {fmt_eur(avg)}  |  Annualized: {fmt_eur(avg * 12)}")
    conn.close()


def cmd_quarterly(args):
    """Quarterly rollup."""
    year = int(args[0]) if args else datetime.now().year
    conn = get_db()

    rows_data = []
    for q in range(1, 5):
        sm = (q - 1) * 3 + 1
        start = f"{year}-{sm:02d}-01"
        em = sm + 3
        if em > 12:
            end = f"{year + 1}-{em - 12:02d}-01"
        else:
            end = f"{year}-{em:02d}-01"

        r = conn.execute("""
            SELECT count(*), sum(COALESCE(amount_eur, amount))
            FROM transactions WHERE amount < 0 AND compartment != 'ACCOUNTING'
            AND date >= ? AND date < ?
        """, (start, end)).fetchone()

        cnt = r[0] or 0
        amt = r[1] or 0
        if cnt > 0:
            rows_data.append((f"Q{q} {year}", f"{cnt:>4}", fmt_eur(amt, 13), bar(min(abs(amt) / 150000 * 100, 100), 20)))

    print_table(
        ["Quarter", "#Txn", "Spent", "Scale (150K ref)"],
        rows_data,
        widths=[10, 6, 15, 22],
        title=f"{C.CYAN}QUARTERLY ROLLUP — {year}{C.RST}"
    )
    conn.close()


def cmd_yearly(args):
    """Year-over-year comparison."""
    conn = get_db()
    years = conn.execute("""
        SELECT DISTINCT strftime('%Y', date) as yr FROM transactions
        WHERE amount < 0 AND compartment != 'ACCOUNTING'
        ORDER BY yr
    """).fetchall()

    rows_data = []
    prev_amt = None
    for yr_row in years:
        yr = yr_row[0]
        start = f"{yr}-01-01"
        end = f"{int(yr) + 1}-01-01"
        r = conn.execute("""
            SELECT count(*), sum(COALESCE(amount_eur, amount))
            FROM transactions WHERE amount < 0 AND compartment != 'ACCOUNTING'
            AND date >= ? AND date < ?
        """, (start, end)).fetchone()

        cnt = r[0] or 0
        amt = r[1] or 0
        if prev_amt and prev_amt != 0:
            yoy = ((abs(amt) - abs(prev_amt)) / abs(prev_amt)) * 100
            yoy_str = f"{'+' if yoy >= 0 else ''}{yoy:.1f}%"
            yoy_color = C.RED if yoy > 0 else C.GREEN
            yoy_display = f"{yoy_color}{yoy_str}{C.RST}"
        else:
            yoy_display = "  —"

        rows_data.append((yr, f"{cnt:>4}", fmt_eur(amt, 14), yoy_display))
        prev_amt = amt

    print_table(
        ["Year", "#Txn", "Total Spent", "YoY Change"],
        rows_data,
        widths=[8, 6, 16, 14],
        title=f"{C.CYAN}YEAR-OVER-YEAR COMPARISON{C.RST}"
    )
    conn.close()


def cmd_compartment(args):
    """Drill into a specific compartment."""
    if not args:
        print(f"{C.RED}Usage: budget compartment <COMPARTMENT_NAME> [period]{C.RST}")
        return

    comp = args[0].upper()
    period = args[1] if len(args) > 1 else None

    conn = get_db()
    where, params, label = period_filter(period)
    full_where = f"{where} AND compartment = ?"
    full_params = params + (comp,)

    txns = get_transactions(conn, full_where, full_params)
    conn.close()

    if not txns:
        print(f"{C.YELLOW}No transactions for {comp} in {label}.{C.RST}")
        return

    # Group by category
    cats = defaultdict(lambda: {"total": 0, "count": 0, "txns": []})
    for t in txns:
        c = t["category"]
        cats[c]["total"] += t["amount"]
        cats[c]["count"] += 1
        cats[c]["txns"].append(t)

    total = sum(t["amount"] for t in txns)
    abs_total = abs(total) if total != 0 else 1

    color = COMPARTMENT_COLORS.get(comp, C.WHITE)
    rows_data = []
    for cat, data in sorted(cats.items(), key=lambda x: x[1]["total"]):
        pct = abs(data["total"]) / abs_total * 100
        rows_data.append((
            f"  {cat}",
            f"{data['count']:>4}",
            fmt_eur(data["total"], 12),
            f"{pct:>5.1f}%",
            bar(pct, 15),
        ))

    rows_data.append(("", "", "", "", ""))
    rows_data.append((
        f"{C.BOLD}  TOTAL{C.RST}",
        f"{len(txns):>4}",
        fmt_eur(total, 12),
        "100.0%",
        "",
    ))

    print_table(
        ["Category", "#Txn", "Amount", "%", ""],
        rows_data,
        widths=[22, 6, 14, 8, 17],
        title=f"{color}{comp}{C.RST} — {label}"
    )


def cmd_category(args):
    """Drill into a specific category."""
    if not args:
        print(f"{C.RED}Usage: budget category <category_name> [period]{C.RST}")
        return

    cat_name = args[0].lower()
    period = args[1] if len(args) > 1 else None

    conn = get_db()
    merchant_map = load_merchant_map(conn)
    where, params, label = period_filter(period)
    full_where = f"{where} AND lower(category) = ?"
    full_params = params + (cat_name,)

    txns = get_transactions(conn, full_where, full_params)
    conn.close()

    if not txns:
        print(f"{C.YELLOW}No transactions for category '{cat_name}' in {label}.{C.RST}")
        return

    # Group by subcategory/merchant
    subs = defaultdict(lambda: {"total": 0, "count": 0})
    for t in txns:
        sub = t["subcategory"]
        if not sub:
            resolved = resolve_merchant(t["description"], merchant_map)
            if resolved:
                sub = resolved["subcategory"]
            else:
                sub = derive_subcategory(t["description"])
        subs[sub]["total"] += t["amount"]
        subs[sub]["count"] += 1

    total = sum(t["amount"] for t in txns)
    abs_total = abs(total) if total != 0 else 1

    rows_data = []
    for sub, data in sorted(subs.items(), key=lambda x: x[1]["total"]):
        pct = abs(data["total"]) / abs_total * 100
        rows_data.append((
            f"  {sub[:24]}",
            f"{data['count']:>4}",
            fmt_eur(data["total"], 12),
            f"{pct:>5.1f}%",
            bar(pct, 12),
        ))

    rows_data.append(("", "", "", "", ""))
    rows_data.append((f"{C.BOLD}  TOTAL{C.RST}", f"{len(txns):>4}", fmt_eur(total, 12), "100.0%", ""))

    print_table(
        ["Subcategory", "#Txn", "Amount", "%", ""],
        rows_data,
        widths=[26, 6, 14, 8, 14],
        title=f"{C.CYAN}Category: {cat_name}{C.RST} — {label}"
    )


def cmd_merchant(args):
    """Drill into transactions matching a merchant pattern."""
    if not args:
        print(f"{C.RED}Usage: budget merchant <pattern> [period]{C.RST}")
        return

    pattern = args[0]
    period = args[1] if len(args) > 1 else None

    conn = get_db()
    where, params, label = period_filter(period)
    full_where = f"{where} AND description LIKE ?"
    full_params = params + (f"%{pattern}%",)

    txns = get_transactions(conn, full_where, full_params)
    conn.close()

    if not txns:
        print(f"{C.YELLOW}No transactions matching '{pattern}' in {label}.{C.RST}")
        return

    rows_data = []
    for t in txns[:50]:
        rows_data.append((
            t["date"],
            t["description"][:30],
            fmt_eur(t["amount"], 11),
            t["category"],
        ))

    total = sum(t["amount"] for t in txns)
    rows_data.append(("", "", "", ""))
    rows_data.append((f"{C.BOLD}TOTAL{C.RST}", f"{len(txns)} txns", fmt_eur(total, 11), ""))

    print_table(
        ["Date", "Description", "Amount", "Category"],
        rows_data,
        widths=[12, 32, 13, 16],
        title=f"{C.CYAN}Merchant: {pattern}{C.RST} — {label}"
    )


def cmd_top(args):
    """Top N expenses."""
    n = int(args[0]) if args and args[0].isdigit() else 20
    period = args[1] if len(args) > 1 else None
    if args and not args[0].isdigit():
        period = args[0]

    conn = get_db()
    where, params, label = period_filter(period)
    # Exclude ACCOUNTING for meaningful top
    full_where = f"{where} AND compartment != 'ACCOUNTING'"
    txns = get_transactions(conn, full_where, params)
    conn.close()

    # Sort by absolute amount
    txns.sort(key=lambda t: t["amount"])
    top = txns[:n]

    rows_data = []
    for i, t in enumerate(top, 1):
        color = COMPARTMENT_COLORS.get(t["compartment"], C.WHITE)
        rows_data.append((
            f"{i:>3}",
            t["date"],
            t["description"][:28],
            fmt_eur(t["amount"], 12),
            f"{color}{t['compartment'][:8]}{C.RST}",
            t["category"][:14],
        ))

    print_table(
        ["#", "Date", "Description", "Amount", "Comp", "Category"],
        rows_data,
        widths=[5, 12, 30, 14, 10, 16],
        title=f"{C.CYAN}TOP {n} EXPENSES{C.RST} — {label}"
    )


def cmd_burn(args):
    """Burn rate projection."""
    months_back = int(args[0]) if args and args[0].isdigit() else 6
    conn = get_db()
    now = datetime.now()

    # Get monthly totals for last N months (excl ACCOUNTING)
    monthly_totals = []
    for i in range(months_back, 0, -1):
        dt = now - timedelta(days=i * 30)
        y, m = dt.year, dt.month
        start, end = month_range(y, m)
        r = conn.execute("""
            SELECT sum(COALESCE(amount_eur, amount))
            FROM transactions WHERE amount < 0 AND compartment != 'ACCOUNTING'
            AND date >= ? AND date < ?
        """, (start, end)).fetchone()
        amt = r[0] or 0
        if amt != 0:
            monthly_totals.append((datetime(y, m, 1).strftime("%b %Y"), amt))

    # Current month partial
    cm_start = now.strftime("%Y-%m-01")
    if now.month == 12:
        cm_end = f"{now.year + 1}-01-01"
    else:
        cm_end = f"{now.year}-{now.month + 1:02d}-01"
    cm_r = conn.execute("""
        SELECT sum(COALESCE(amount_eur, amount))
        FROM transactions WHERE amount < 0 AND compartment != 'ACCOUNTING'
        AND date >= ? AND date < ?
    """, (cm_start, cm_end)).fetchone()
    cm_spent = cm_r[0] or 0

    import calendar
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    projected = (cm_spent / now.day) * days_in_month if now.day > 0 else 0

    conn.close()

    rows_data = []
    for label, amt in monthly_totals:
        rows_data.append((label, fmt_eur(amt, 13), bar(min(abs(amt) / 100000 * 100, 100), 20)))

    rows_data.append(("", "", ""))
    rows_data.append((
        f"{C.YELLOW}{now.strftime('%b %Y')} (proj){C.RST}",
        fmt_eur(projected, 13),
        bar(min(abs(projected) / 100000 * 100, 100), 20),
    ))

    print_table(
        ["Month", "Spending", "Scale (100K)"],
        rows_data,
        widths=[18, 15, 22],
        title=f"{C.CYAN}BURN RATE — Last {months_back} Months{C.RST}"
    )

    if monthly_totals:
        amounts = [abs(a) for _, a in monthly_totals]
        avg_monthly = sum(amounts) / len(amounts)
        # Rolling averages
        r30 = amounts[-1] if amounts else 0
        r90 = sum(amounts[-3:]) / min(3, len(amounts)) if amounts else 0

        print(f"\n  {C.BOLD}Burn Rate Analysis:{C.RST}")
        print(f"  30-day avg:    {fmt_eur(-r30)}")
        print(f"  90-day avg:    {fmt_eur(-r90)}")
        print(f"  {months_back}-month avg: {fmt_eur(-avg_monthly)}")
        print(f"  Annualized:    {fmt_eur(-avg_monthly * 12)}")
        print(f"  Current month: {fmt_eur(cm_spent)} ({now.day}/{days_in_month} days) -> projected {fmt_eur(projected)}")


def cmd_trend(args):
    """Category trend over time."""
    if not args:
        print(f"{C.RED}Usage: budget trend <category> [months]{C.RST}")
        return

    cat_name = args[0].lower()
    months_back = int(args[1]) if len(args) > 1 and args[1].isdigit() else 12

    conn = get_db()
    now = datetime.now()

    rows_data = []
    amounts = []
    for i in range(months_back, 0, -1):
        dt = now - timedelta(days=i * 30)
        y, m = dt.year, dt.month
        start, end = month_range(y, m)
        r = conn.execute("""
            SELECT count(*), sum(COALESCE(amount_eur, amount))
            FROM transactions WHERE amount < 0 AND lower(category) = ?
            AND date >= ? AND date < ?
        """, (cat_name, start, end)).fetchone()

        cnt = r[0] or 0
        amt = r[1] or 0
        if cnt > 0:
            amounts.append(abs(amt))
            month_label = datetime(y, m, 1).strftime("%b %Y")
            rows_data.append((month_label, f"{cnt:>4}", fmt_eur(amt, 12)))

    if not rows_data:
        print(f"{C.YELLOW}No data for category '{cat_name}'.{C.RST}")
        conn.close()
        return

    print_table(
        ["Month", "#Txn", "Amount"],
        rows_data,
        widths=[12, 6, 14],
        title=f"{C.CYAN}TREND: {cat_name}{C.RST} — Last {months_back} months"
    )

    if amounts:
        avg = sum(amounts) / len(amounts)
        print(f"\n  Average: {fmt_eur(-avg)}  |  Min: {fmt_eur(-min(amounts))}  |  Max: {fmt_eur(-max(amounts))}")

    conn.close()


def cmd_compare(args):
    """Compare two months."""
    if len(args) < 2:
        print(f"{C.RED}Usage: budget compare <YYYY-MM> <YYYY-MM>{C.RST}")
        return

    conn = get_db()
    results = {}
    for period in args[:2]:
        where, params, label = period_filter(period)
        txns = get_transactions(conn, where, params)

        cats = defaultdict(float)
        for t in txns:
            if t["compartment"] != "ACCOUNTING":
                cats[t["category"]] += t["amount"]
        results[label] = {"cats": cats, "total": sum(t["amount"] for t in txns if t["compartment"] != "ACCOUNTING"), "count": len(txns)}

    conn.close()

    labels = list(results.keys())
    all_cats = sorted(set(list(results[labels[0]]["cats"].keys()) + list(results[labels[1]]["cats"].keys())))

    rows_data = []
    for cat in all_cats:
        a1 = results[labels[0]]["cats"].get(cat, 0)
        a2 = results[labels[1]]["cats"].get(cat, 0)
        diff = a2 - a1  # positive means more spending in month2 (more negative)
        if a1 != 0:
            pct_change = ((abs(a2) - abs(a1)) / abs(a1)) * 100
            chg_str = f"{'+' if pct_change >= 0 else ''}{pct_change:.0f}%"
            chg_color = C.RED if pct_change > 20 else (C.GREEN if pct_change < -20 else C.YELLOW)
            chg_display = f"{chg_color}{chg_str}{C.RST}"
        else:
            chg_display = f"{C.CYAN}new{C.RST}"

        rows_data.append((cat, fmt_eur(a1, 11), fmt_eur(a2, 11), chg_display))

    # Totals
    rows_data.append(("", "", "", ""))
    t1 = results[labels[0]]["total"]
    t2 = results[labels[1]]["total"]
    if t1 != 0:
        total_pct = ((abs(t2) - abs(t1)) / abs(t1)) * 100
        total_chg = f"{'+' if total_pct >= 0 else ''}{total_pct:.0f}%"
    else:
        total_chg = "—"
    rows_data.append((f"{C.BOLD}TOTAL{C.RST}", fmt_eur(t1, 11), fmt_eur(t2, 11), total_chg))

    print_table(
        ["Category", labels[0], labels[1], "Change"],
        rows_data,
        widths=[20, 13, 13, 10],
        title=f"{C.CYAN}COMPARE{C.RST} — {labels[0]} vs {labels[1]}"
    )


def cmd_set_target(args):
    """Set a budget target."""
    if len(args) < 3:
        print(f"{C.RED}Usage: budget set-target <compartment> <category> <amount> [period] [alert_pct]{C.RST}")
        print(f"  Example: budget set-target PERSONAL food 3000 monthly 80")
        return

    comp = args[0].upper()
    cat = args[1].lower() if args[1] != "*" else None
    amt = float(args[2])
    period = args[3] if len(args) > 3 else "monthly"
    alert_pct = float(args[4]) if len(args) > 4 else 80.0

    conn = get_db()
    # Upsert
    conn.execute("""
        INSERT INTO budget_targets (compartment, category, period, target_amount, alert_pct)
        VALUES (?, ?, ?, ?, ?)
    """, (comp, cat, period, amt, alert_pct))
    conn.commit()
    conn.close()

    print(f"{C.GREEN}Target set: {comp}/{cat or '*'} = {amt:,.0f} EUR/{period} (alert at {alert_pct}%){C.RST}")


def cmd_targets(args):
    """Show all budget targets with current status."""
    conn = get_db()
    try:
        targets = conn.execute("SELECT * FROM budget_targets ORDER BY compartment, category").fetchall()
    except sqlite3.OperationalError:
        print(f"{C.YELLOW}No budget_targets table. Run 'budget init' first.{C.RST}")
        conn.close()
        return

    if not targets:
        print(f"{C.YELLOW}No budget targets set. Use 'budget set-target' to add one.{C.RST}")
        conn.close()
        return

    now = datetime.now()
    rows_data = []

    for t in targets:
        comp = t["compartment"]
        cat = t["category"]
        target = t["target_amount"]
        period = t["period"]
        alert_pct = t["alert_pct"]

        # Get current spend for this period
        if period == "monthly":
            where, params, _ = period_filter(now.strftime("%Y-%m"))
        elif period == "yearly":
            where, params, _ = period_filter(str(now.year))
        elif period == "quarterly":
            q = (now.month - 1) // 3 + 1
            where, params, _ = period_filter(f"{now.year}-Q{q}")
        elif period == "weekly":
            where, params, _ = period_filter(now.strftime("%G-W%V"))
        else:
            where, params, _ = period_filter(None)

        cat_clause = "AND lower(category) = ?" if cat else ""
        cat_params = (cat.lower(),) if cat else ()

        r = conn.execute(f"""
            SELECT sum(COALESCE(amount_eur, amount))
            FROM transactions WHERE amount < 0
            AND compartment = ? {cat_clause}
            AND {where}
        """, (comp,) + cat_params + params).fetchone()

        spent = abs(r[0] or 0)
        pct = (spent / target * 100) if target > 0 else 0

        if pct >= 100:
            status = f"{C.BG_RED}{C.WHITE} OVER {C.RST}"
        elif pct >= alert_pct:
            status = f"{C.YELLOW} WARN {C.RST}"
        else:
            status = f"{C.GREEN}  OK  {C.RST}"

        color = COMPARTMENT_COLORS.get(comp, C.WHITE)
        rows_data.append((
            f"{color}{comp}{C.RST}",
            cat or "*",
            period,
            f"{target:>10,.0f}",
            fmt_eur(-spent, 11),
            f"{pct:>5.1f}%",
            bar(pct, 10),
            status,
        ))

    print_table(
        ["Compartment", "Category", "Period", "Target", "Spent", "%", "", "Status"],
        rows_data,
        widths=[14, 16, 9, 12, 13, 8, 12, 8],
        title=f"{C.CYAN}BUDGET TARGETS{C.RST} — {now.strftime('%B %Y')}"
    )
    conn.close()


def cmd_alerts(args):
    """Show budget alerts (targets exceeded or near limit)."""
    conn = get_db()
    try:
        targets = conn.execute("SELECT * FROM budget_targets ORDER BY compartment, category").fetchall()
    except sqlite3.OperationalError:
        print(f"{C.YELLOW}No budget_targets table. Run 'budget init' first.{C.RST}")
        conn.close()
        return

    now = datetime.now()
    alerts = []

    for t in targets:
        comp = t["compartment"]
        cat = t["category"]
        target = t["target_amount"]
        period = t["period"]
        alert_pct = t["alert_pct"]

        if period == "monthly":
            where, params, label = period_filter(now.strftime("%Y-%m"))
        elif period == "yearly":
            where, params, label = period_filter(str(now.year))
        else:
            where, params, label = period_filter(None)

        cat_clause = "AND lower(category) = ?" if cat else ""
        cat_params = (cat.lower(),) if cat else ()

        r = conn.execute(f"""
            SELECT sum(COALESCE(amount_eur, amount))
            FROM transactions WHERE amount < 0
            AND compartment = ? {cat_clause}
            AND {where}
        """, (comp,) + cat_params + params).fetchone()

        spent = abs(r[0] or 0)
        pct = (spent / target * 100) if target > 0 else 0

        if pct >= alert_pct:
            severity = "OVER BUDGET" if pct >= 100 else "WARNING"
            alerts.append((severity, comp, cat or "*", target, spent, pct, label))

    conn.close()

    if not alerts:
        print(f"{C.GREEN}No budget alerts. All targets within limits.{C.RST}")
        return

    rows_data = []
    for sev, comp, cat, target, spent, pct, label in alerts:
        sev_color = C.BG_RED if sev == "OVER BUDGET" else C.BG_YELLOW
        rows_data.append((
            f"{sev_color}{C.WHITE} {sev} {C.RST}",
            comp,
            cat,
            f"{target:>10,.0f}",
            fmt_eur(-spent, 11),
            f"{pct:>5.1f}%",
        ))

    print_table(
        ["Alert", "Compartment", "Category", "Target", "Spent", "%Used"],
        rows_data,
        widths=[14, 14, 16, 12, 13, 8],
        title=f"{C.RED}BUDGET ALERTS{C.RST}"
    )


def cmd_food(args):
    """Quick shortcut for food spending analysis."""
    period = args[0] if args else None
    conn = get_db()
    merchant_map = load_merchant_map(conn)
    where, params, label = period_filter(period)
    full_where = f"{where} AND lower(category) = 'food'"
    txns = get_transactions(conn, full_where, params)
    conn.close()

    if not txns:
        print(f"{C.YELLOW}No food transactions for {label}.{C.RST}")
        return

    # Group by subcategory
    subs = defaultdict(lambda: {"total": 0, "count": 0})
    delivery_total = 0
    for t in txns:
        sub = t["subcategory"]
        if not sub:
            resolved = resolve_merchant(t["description"], merchant_map)
            if resolved:
                sub = resolved["subcategory"]
            else:
                sub = derive_subcategory(t["description"])
        subs[sub]["total"] += t["amount"]
        subs[sub]["count"] += 1
        if sub in ("uber_eats", "wolt", "bolt_food"):
            delivery_total += t["amount"]

    total = sum(t["amount"] for t in txns)
    abs_total = abs(total) if total != 0 else 1

    rows_data = []
    for sub, data in sorted(subs.items(), key=lambda x: x[1]["total"]):
        pct = abs(data["total"]) / abs_total * 100
        rows_data.append((
            f"  {sub[:24]}",
            f"{data['count']:>4}",
            fmt_eur(data["total"], 12),
            f"{pct:>5.1f}%",
            bar(pct, 12),
        ))

    print_table(
        ["Source", "#Txn", "Amount", "%", ""],
        rows_data,
        widths=[26, 6, 14, 8, 14],
        title=f"{C.CYAN}FOOD SPENDING{C.RST} — {label}"
    )

    # Delivery dependency analysis
    delivery_pct = abs(delivery_total) / abs_total * 100 if abs_total > 0 else 0
    print(f"\n  Total food:       {fmt_eur(total)}")
    print(f"  Delivery apps:    {fmt_eur(delivery_total)} ({delivery_pct:.1f}% of food budget)")
    print(f"  Daily food avg:   {fmt_eur(total / max(1, len(set(t['date'] for t in txns))))}")

    # Anomaly detection
    daily_amounts = defaultdict(float)
    for t in txns:
        daily_amounts[t["date"]] += abs(t["amount"])
    if daily_amounts:
        avg_daily = sum(daily_amounts.values()) / len(daily_amounts)
        anomalies = [(d, a) for d, a in daily_amounts.items() if a > avg_daily * 2]
        if anomalies:
            print(f"\n  {C.YELLOW}Anomalies (>2x daily avg of {avg_daily:.0f} EUR):{C.RST}")
            for d, a in sorted(anomalies, key=lambda x: -x[1])[:5]:
                print(f"    {d}: {a:.0f} EUR")


def cmd_transport(args):
    """Quick shortcut for transport spending."""
    args_new = ["transport"] + list(args)
    cmd_category(args_new)


def cmd_education(args):
    """Quick shortcut for education/tutoring spending."""
    period = args[0] if args else None
    conn = get_db()
    where, params, label = period_filter(period)

    # Get school_fees + school_extras
    full_where = f"{where} AND (lower(category) IN ('school_fees', 'school_extras'))"
    txns = get_transactions(conn, full_where, params)
    conn.close()

    if not txns:
        print(f"{C.YELLOW}No education transactions for {label}.{C.RST}")
        return

    cats = defaultdict(lambda: {"total": 0, "count": 0})
    for t in txns:
        key = f"{t['category']}/{t['subcategory']}" if t['subcategory'] else t['category']
        cats[key]["total"] += t["amount"]
        cats[key]["count"] += 1

    total = sum(t["amount"] for t in txns)
    abs_total = abs(total) if total != 0 else 1

    rows_data = []
    for cat, data in sorted(cats.items(), key=lambda x: x[1]["total"]):
        pct = abs(data["total"]) / abs_total * 100
        rows_data.append((cat[:28], f"{data['count']:>4}", fmt_eur(data["total"], 12), f"{pct:>5.1f}%"))

    rows_data.append(("", "", "", ""))
    rows_data.append((f"{C.BOLD}TOTAL{C.RST}", f"{len(txns):>4}", fmt_eur(total, 12), "100.0%"))

    print_table(
        ["Education Item", "#Txn", "Amount", "%"],
        rows_data,
        widths=[30, 6, 14, 8],
        title=f"{C.CYAN}EDUCATION SPENDING{C.RST} — {label}"
    )


def cmd_subscriptions(args):
    """Quick shortcut for subscriptions."""
    args_new = ["subscriptions"] + list(args)
    cmd_category(args_new)


def cmd_travel_spend(args):
    """Travel spending by destination/location."""
    period = args[0] if args else None
    conn = get_db()
    merchant_map = load_merchant_map(conn)
    where, params, label = period_filter(period)
    full_where = f"{where} AND lower(category) = 'travel'"
    txns = get_transactions(conn, full_where, params)

    # Also grab transport that has location hints
    full_where2 = f"{where} AND lower(category) IN ('transport', 'food', 'entertainment', 'shopping') AND compartment = 'PERSONAL'"
    all_txns = get_transactions(conn, full_where2, params)
    conn.close()

    # Resolve locations
    location_spend = defaultdict(float)
    location_count = defaultdict(int)

    for t in txns:
        resolved = resolve_merchant(t["description"], merchant_map)
        loc = resolved["location"] if resolved else "UNKNOWN"
        location_spend[loc] += t["amount"]
        location_count[loc] += 1

    # Add location-tagged non-travel items
    for t in all_txns:
        resolved = resolve_merchant(t["description"], merchant_map)
        if resolved and resolved["location"] not in ("GLOBAL", "ONLINE", None):
            loc = resolved["location"]
            location_spend[loc] += t["amount"]
            location_count[loc] += 1

    if not location_spend:
        print(f"{C.YELLOW}No travel/location data for {label}.{C.RST}")
        return

    total = sum(location_spend.values())
    abs_total = abs(total) if total != 0 else 1

    rows_data = []
    for loc, amt in sorted(location_spend.items(), key=lambda x: x[1]):
        pct = abs(amt) / abs_total * 100
        rows_data.append((loc, f"{location_count[loc]:>4}", fmt_eur(amt, 12), f"{pct:>5.1f}%"))

    print_table(
        ["Location", "#Txn", "Amount", "%"],
        rows_data,
        widths=[16, 6, 14, 8],
        title=f"{C.CYAN}TRAVEL/LOCATION SPENDING{C.RST} — {label}"
    )


def cmd_export(args):
    """Export full budget data as JSON."""
    filepath = args[0] if args else None
    conn = get_db()
    merchant_map = load_merchant_map(conn)

    # Export all transactions with resolved subcategories
    txns = get_transactions(conn, "1=1", (), debits_only=False)

    export_data = {
        "exported_at": datetime.now().isoformat(),
        "total_transactions": len(txns),
        "transactions": [],
        "merchant_map": [],
        "budget_targets": [],
    }

    for t in txns:
        resolved = resolve_merchant(t["description"], merchant_map)
        entry = dict(t)
        if resolved:
            entry["resolved_subcategory"] = resolved["subcategory"]
            entry["resolved_location"] = resolved.get("location")
        export_data["transactions"].append(entry)

    # Merchant map
    try:
        mrows = conn.execute("SELECT * FROM merchant_map").fetchall()
        for m in mrows:
            export_data["merchant_map"].append(dict(m))
    except sqlite3.OperationalError:
        pass

    # Budget targets
    try:
        trows = conn.execute("SELECT * FROM budget_targets").fetchall()
        for t in trows:
            export_data["budget_targets"].append(dict(t))
    except sqlite3.OperationalError:
        pass

    conn.close()

    if filepath:
        with open(filepath, "w") as f:
            json.dump(export_data, f, indent=2, default=str)
        print(f"{C.GREEN}Exported to {filepath}{C.RST}")
    else:
        print(json.dumps(export_data, indent=2, default=str))


# ── Analytics ─────────────────────────────────────────────────────────────

def detect_anomalies(conn, period_where, period_params):
    """Detect spending anomalies (>2x category average)."""
    # Get historical averages by category
    hist = conn.execute("""
        SELECT category, avg(monthly_total) as avg_monthly
        FROM (
            SELECT category, strftime('%Y-%m', date) as ym, sum(COALESCE(amount_eur, amount)) as monthly_total
            FROM transactions
            WHERE amount < 0 AND compartment != 'ACCOUNTING'
            GROUP BY category, strftime('%Y-%m', date)
        )
        GROUP BY category
    """).fetchall()

    cat_avgs = {r[0]: r[1] for r in hist}

    # Get current period by category
    current = conn.execute(f"""
        SELECT category, sum(COALESCE(amount_eur, amount)) as total
        FROM transactions
        WHERE amount < 0 AND compartment != 'ACCOUNTING'
        AND {period_where}
        GROUP BY category
    """, period_params).fetchall()

    anomalies = []
    for r in current:
        cat = r[0]
        current_amt = abs(r[1])
        avg_amt = abs(cat_avgs.get(cat, 0))
        if avg_amt > 0 and current_amt > avg_amt * 2:
            ratio = current_amt / avg_amt
            anomalies.append((cat, current_amt, avg_amt, ratio))

    return anomalies


# ── Investment vs Expense Classification ──────────────────────────────────

INVESTMENT_CATEGORIES = {
    'crypto_purchase', 'crypto_sale', 'asset_purchase', 'equipment',
    'refurbishment', 'property_improvement', 'vehicle', 'business_tools',
    'staking_rewards',
}

INVESTMENT_PAYEE_PATTERNS = [
    r'(?i)BTC', r'(?i)bitcoin', r'(?i)ETH', r'(?i)crypto',
    r'(?i)PUR/BTC', r'(?i)PUR/ETH', r'(?i)RET/BTC', r'(?i)RET/ETH',
    r'(?i)Ledger', r'(?i)Vasta\s*Piscine', r'(?i)Foltronics',
    r'(?i)AkrylDek', r'(?i)Samsung', r'(?i)refurb',
    r'(?i)RAPTOR\s*TACTICA', r'(?i)Open\s*Forged',
]

EXPENSE_CATEGORIES = {
    'legal_fees_france', 'legal_fees_malta', 'legal_fees_monaco',
    'legal_fees_switzerland', 'legal_fees_other',
    'pension_alimentaire', 'food', 'travel', 'entertainment',
    'housing', 'telecom', 'subscriptions', 'misc_personal', 'misc',
    'transport', 'health_personal', 'shopping', 'gifts',
    'family_support', 'school_fees', 'school_extras',
    'standing_order', 'insurance_home', 'bank_fees',
    'tax', 'tax_income', 'tax_property', 'debt_service',
    'forensics', 'professional_services', 'business_expense',
    'wire_out', 'card_funding', 'transfer_internal',
}

# Classification rules to seed expense_classification table
CLASSIFICATION_SEEDS = [
    # (category, subcategory, payee_pattern, classification, rationale)
    ('crypto_purchase', None, '%BTC%', 'INVESTMENT', 'Bitcoin purchase — digital asset'),
    ('crypto_purchase', None, '%ETH%', 'INVESTMENT', 'Ethereum purchase — digital asset'),
    ('crypto_purchase', None, None, 'INVESTMENT', 'Cryptocurrency acquisition'),
    ('crypto_sale', None, None, 'INVESTMENT', 'Crypto disposal — capital event'),
    ('staking_rewards', None, None, 'INVESTMENT', 'Staking yield — passive income'),
    ('asset_purchase', None, None, 'INVESTMENT', 'Asset acquisition — retains value'),
    ('equipment', None, None, 'INVESTMENT', 'Equipment — depreciable asset'),
    ('refurbishment', None, None, 'INVESTMENT', 'Property improvement — adds value'),
    ('property_improvement', None, None, 'INVESTMENT', 'Property capital expenditure'),
    ('vehicle', None, None, 'INVESTMENT', 'Vehicle — depreciable asset'),
    ('business_tools', None, None, 'INVESTMENT', 'Business tools — productive asset'),
    (None, None, '%Vasta Piscine%', 'INVESTMENT', 'Pool construction — property improvement'),
    (None, None, '%Foltronics%', 'INVESTMENT', 'Tech/electronics investment'),
    (None, None, '%AkrylDek%', 'INVESTMENT', 'Property improvement materials'),
    (None, None, '%RAPTOR TACTICA%', 'INVESTMENT', 'Tactical equipment'),
    (None, None, '%Open Forged%', 'INVESTMENT', 'Software development — business asset'),
    (None, None, '%Ledger%', 'INVESTMENT', 'Crypto hardware wallet'),
    ('pension_alimentaire', None, None, 'EXPENSE', 'Court-ordered maintenance — consumption'),
    ('legal_fees_france', None, None, 'EXPENSE', 'Legal fees — service consumption'),
    ('legal_fees_malta', None, None, 'EXPENSE', 'Legal fees — service consumption'),
    ('legal_fees_monaco', None, None, 'EXPENSE', 'Legal fees — service consumption'),
    ('legal_fees_switzerland', None, None, 'EXPENSE', 'Legal fees — service consumption'),
    ('legal_fees_other', None, None, 'EXPENSE', 'Legal fees — service consumption'),
    ('food', None, None, 'EXPENSE', 'Food — consumption'),
    ('travel', None, None, 'EXPENSE', 'Travel — consumption'),
    ('entertainment', None, None, 'EXPENSE', 'Entertainment — consumption'),
    ('housing', None, None, 'EXPENSE', 'Housing — recurring cost'),
    ('telecom', None, None, 'EXPENSE', 'Telecoms — consumption'),
    ('subscriptions', None, None, 'EXPENSE', 'Subscriptions — consumption'),
    ('misc_personal', None, None, 'EXPENSE', 'Miscellaneous personal spending'),
    ('transport', None, None, 'EXPENSE', 'Transport — consumption'),
    ('health_personal', None, None, 'EXPENSE', 'Healthcare — consumption'),
    ('shopping', None, None, 'EXPENSE', 'Shopping — consumption (depreciates fast)'),
    ('gifts', None, None, 'EXPENSE', 'Gifts — no return value'),
    ('family_support', None, None, 'EXPENSE', 'Family support — consumption'),
    ('school_fees', None, None, 'EXPENSE', 'Education — consumption (non-tangible)'),
    ('school_extras', None, None, 'EXPENSE', 'Education extras — consumption'),
    ('standing_order', None, None, 'EXPENSE', 'Standing orders — recurring expense'),
    ('insurance_home', None, None, 'EXPENSE', 'Insurance — consumption'),
    ('bank_fees', None, None, 'EXPENSE', 'Bank fees — consumption'),
    ('tax', None, None, 'EXPENSE', 'Tax payments — mandatory expense'),
    ('tax_income', None, None, 'EXPENSE', 'Income tax — mandatory expense'),
    ('tax_property', None, None, 'EXPENSE', 'Property tax — mandatory expense'),
    ('debt_service', None, None, 'EXPENSE', 'Debt service — obligation'),
    ('forensics', None, None, 'EXPENSE', 'Forensics — service consumption'),
    ('professional_services', None, None, 'EXPENSE', 'Professional services — consumption'),
    ('business_expense', None, None, 'EXPENSE', 'Business expenses — operating cost'),
    ('wire_out', None, None, 'EXPENSE', 'Outbound wire — transfer/expense'),
    ('card_funding', None, None, 'EXPENSE', 'Card funding — transfer'),
    ('transfer_internal', None, None, 'EXPENSE', 'Internal transfer — reallocation'),
    ('misc', None, None, 'EXPENSE', 'Miscellaneous — consumption'),
]

# Available liquid balances for runway calculation
LIQUID_BALANCES = {
    'BNP': {'amount': 326_000, 'currency': 'EUR'},
    'Frick': {'amount': 139_000, 'currency': 'EUR'},
    'N26': {'amount': 32_000, 'currency': 'EUR'},
    'BTC (20.5 @ 85K)': {'amount': 20.5 * 85_000, 'currency': 'EUR'},
}
FROZEN_BALANCES = {
    'Julius Baer (sequestre)': {'amount': 2_000_000, 'currency': 'CHF', 'status': 'FROZEN'},
}

# Known recurring monthly obligations
MONTHLY_OBLIGATIONS = {
    'pension_alimentaire': 32_500,
    'monaco_telecom': 1_199,
    'starlink': 40,
    'google_workspace': 12,
}

# Quarterly obligations
QUARTERLY_OBLIGATIONS = {
    'le_rosey': 60_000 * 0.93,  # CHF to EUR approx
}


def classify_transaction(category, counterparty):
    """Classify a transaction as INVESTMENT or EXPENSE."""
    if category in INVESTMENT_CATEGORIES:
        return 'INVESTMENT'
    if counterparty:
        for pattern in INVESTMENT_PAYEE_PATTERNS:
            if re.search(pattern, counterparty):
                return 'INVESTMENT'
    return 'EXPENSE'


def init_projection_tables():
    """Create projections and expense_classification tables, seed rules."""
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS projections (
        id INTEGER PRIMARY KEY,
        month TEXT NOT NULL,
        scenario TEXT NOT NULL,
        compartment TEXT,
        category TEXT,
        classification TEXT,
        projected_amount REAL,
        actual_amount REAL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS expense_classification (
        id INTEGER PRIMARY KEY,
        category TEXT,
        subcategory TEXT,
        payee_pattern TEXT,
        classification TEXT NOT NULL,
        rationale TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Seed classification rules if empty
    existing = conn.execute("SELECT count(*) FROM expense_classification").fetchone()[0]
    if existing == 0:
        for cat, subcat, payee, cls, rationale in CLASSIFICATION_SEEDS:
            conn.execute("""
                INSERT INTO expense_classification (category, subcategory, payee_pattern, classification, rationale)
                VALUES (?, ?, ?, ?, ?)
            """, (cat, subcat, payee, cls, rationale))
        conn.commit()
        print(f"  {C.GREEN}Seeded {len(CLASSIFICATION_SEEDS)} classification rules{C.RST}")
    else:
        print(f"  {C.DIM}Classification rules already seeded ({existing} rules){C.RST}")

    conn.close()


def get_monthly_spending(conn, start_date='2024-01-01', end_date=None):
    """Get monthly spending breakdown by category, compartment, counterparty."""
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')

    rows = conn.execute("""
        SELECT strftime('%Y-%m', date) as month, category, compartment,
               counterparty, SUM(ABS(amount_eur)) as total, COUNT(*) as cnt
        FROM transactions
        WHERE amount_eur < 0
          AND date >= ? AND date <= ?
        GROUP BY month, category, compartment
        ORDER BY month, total DESC
    """, (start_date, end_date)).fetchall()
    return rows


def build_projections(conn, months_ahead=12):
    """Build 12-month forward projections under current and target scenarios."""
    now = datetime.now()

    # Get last 3 months of spending by category (excl ACCOUNTING transfers)
    three_months_ago = (now - timedelta(days=90)).strftime('%Y-%m-%d')
    today = now.strftime('%Y-%m-%d')

    cat_monthly = defaultdict(list)
    rows = conn.execute("""
        SELECT strftime('%Y-%m', date) as month, category, compartment,
               SUM(ABS(COALESCE(amount_eur, amount))) as total
        FROM transactions
        WHERE amount_eur < 0
          AND date >= ? AND date <= ?
          AND category NOT IN ('transfer_internal', 'card_funding', 'crypto_purchase', 'crypto_sale')
        GROUP BY month, category
        ORDER BY month
    """, (three_months_ago, today)).fetchall()

    for r in rows:
        cat_monthly[r[1]].append(r[3])

    # Compute 3-month average per category
    cat_avg = {}
    for cat, amounts in cat_monthly.items():
        cat_avg[cat] = sum(amounts) / max(len(amounts), 1)

    # Override with known recurring obligations
    cat_avg['pension_alimentaire'] = MONTHLY_OBLIGATIONS['pension_alimentaire']
    cat_avg['standing_order'] = MONTHLY_OBLIGATIONS['monaco_telecom'] + MONTHLY_OBLIGATIONS['starlink'] + MONTHLY_OBLIGATIONS['google_workspace']

    # Build monthly projections
    projections_current = []
    projections_target = []

    for i in range(1, months_ahead + 1):
        future = now + timedelta(days=i * 30)
        month_str = future.strftime('%Y-%m')

        month_total_current = 0
        month_items_current = []
        month_items_target = []

        for cat, avg in sorted(cat_avg.items(), key=lambda x: -x[1]):
            cls = classify_transaction(cat, None)
            if cls == 'INVESTMENT':
                continue  # Don't project investment purchases

            compartment = _cat_to_compartment(cat)
            month_items_current.append({
                'month': month_str, 'category': cat, 'compartment': compartment,
                'classification': cls, 'amount': avg, 'scenario': 'current',
            })
            month_total_current += avg

        # Quarterly items (Le Rosey — add in appropriate months)
        if future.month in (1, 4, 9):  # School fee quarters
            rosey_eur = QUARTERLY_OBLIGATIONS['le_rosey']
            month_items_current.append({
                'month': month_str, 'category': 'school_fees', 'compartment': 'FAMILIAL',
                'classification': 'EXPENSE', 'amount': rosey_eur, 'scenario': 'current',
            })
            month_total_current += rosey_eur

        projections_current.append((month_str, month_total_current, month_items_current))

        # Target 20K scenario — apply cuts
        target_total = 0
        target_budget = 20_000
        # Pension is non-negotiable court order
        pension = MONTHLY_OBLIGATIONS['pension_alimentaire']
        remaining_budget = target_budget  # This is the target EXCLUDING pension
        # In target scenario, pension stays but we count total including it
        for item in month_items_current:
            cat = item['category']
            amt = item['amount']
            if cat == 'pension_alimentaire':
                target_amt = amt  # Can't cut court order
            elif cat in ('standing_order', 'insurance_home'):
                target_amt = amt  # Fixed obligations
            elif cat in ('school_fees', 'school_extras'):
                target_amt = amt  # Education non-negotiable
            elif cat == 'tax_income':
                target_amt = amt  # Tax is mandatory
            elif cat == 'tax_property':
                target_amt = amt
            elif cat in ('housing',):
                target_amt = min(amt, 2000)  # Cap housing
            elif cat in ('food',):
                target_amt = min(amt, 800)  # Cap food
            elif cat in ('telecom',):
                target_amt = min(amt, 200)  # Minimize telecom
            elif cat in ('health_personal',):
                target_amt = min(amt, 500)  # Essential health only
            elif cat in ('transport',):
                target_amt = min(amt, 200)
            elif cat.startswith('legal_fees'):
                target_amt = amt * 0.3  # Reduce legal engagement
            elif cat == 'business_expense':
                target_amt = amt * 0.4  # Cut business costs
            elif cat == 'professional_services':
                target_amt = amt * 0.2
            elif cat == 'forensics':
                target_amt = 0  # Cut forensics
            elif cat in ('entertainment', 'shopping', 'gifts', 'travel', 'misc_personal', 'misc'):
                target_amt = 0  # Eliminate discretionary
            elif cat == 'family_support':
                target_amt = min(amt, 2000)
            elif cat == 'debt_service':
                target_amt = amt  # Can't cut debt
            else:
                target_amt = amt * 0.5  # 50% cut on unknown

            month_items_target.append({
                'month': month_str, 'category': cat, 'compartment': item['compartment'],
                'classification': 'EXPENSE', 'amount': target_amt, 'scenario': 'target_20k',
            })
            target_total += target_amt

        projections_target.append((month_str, target_total, month_items_target))

    return projections_current, projections_target


def _cat_to_compartment(category):
    """Map category to compartment."""
    if category.startswith('legal_fees') or category in ('pension_alimentaire', 'forensics'):
        return 'DIVORCE'
    if category in ('school_fees', 'school_extras'):
        return 'FAMILIAL'
    if category in ('business_expense', 'professional_services'):
        return 'PROFESSIONAL'
    if category in ('tax', 'tax_income', 'tax_property', 'standing_order',
                     'insurance_home', 'bank_fees', 'debt_service'):
        return 'OBLIGATIONS'
    if category in ('crypto_purchase', 'crypto_sale', 'transfer_internal',
                     'card_funding', 'wire_out'):
        return 'ACCOUNTING'
    return 'PERSONAL'


def cmd_projection(args):
    """Show 12-month projection (current trajectory vs EUR 20K target)."""
    conn = get_db()
    init_projection_tables()

    months = int(args[0]) if args and args[0].isdigit() else 12
    proj_current, proj_target = build_projections(conn, months)

    # Store projections
    conn.execute("DELETE FROM projections WHERE scenario IN ('current', 'target_20k')")
    for month_str, total, items in proj_current:
        for item in items:
            conn.execute("""
                INSERT INTO projections (month, scenario, compartment, category, classification, projected_amount)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (item['month'], 'current', item['compartment'], item['category'],
                  item['classification'], item['amount']))
    for month_str, total, items in proj_target:
        for item in items:
            conn.execute("""
                INSERT INTO projections (month, scenario, compartment, category, classification, projected_amount)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (item['month'], 'target_20k', item['compartment'], item['category'],
                  item['classification'], item['amount']))
    conn.commit()

    # Display
    print()
    total_w = 90
    print_title(f"{C.CYAN}12-MONTH EXPENSE PROJECTION — Current vs Target{C.RST}", total_w)

    headers = ["Month", "Current", "Target 20K", "Savings", "Curr Bar", "Tgt Bar"]
    widths = [10, 14, 14, 14, 20, 18]

    rows_data = []
    cum_current = 0
    cum_target = 0
    max_monthly = max(t for _, t, _ in proj_current) if proj_current else 100000

    for (m_c, t_c, _), (m_t, t_t, _) in zip(proj_current, proj_target):
        cum_current += t_c
        cum_target += t_t
        savings = t_c - t_t
        pct_c = min(t_c / max_monthly * 100, 100) if max_monthly > 0 else 0
        pct_t = min(t_t / max_monthly * 100, 100) if max_monthly > 0 else 0
        rows_data.append((
            m_c,
            fmt_eur(-t_c, 14),
            fmt_eur(-t_t, 14),
            f"{C.GREEN}+{savings:,.0f}{C.RST}" if savings > 0 else f"{C.RED}{savings:,.0f}{C.RST}",
            bar(pct_c, 18),
            bar(pct_t, 16),
        ))

    # Totals row
    rows_data.append(("", "", "", "", "", ""))
    total_savings = cum_current - cum_target
    rows_data.append((
        f"{C.BOLD}TOTAL{C.RST}",
        fmt_eur(-cum_current, 14),
        fmt_eur(-cum_target, 14),
        f"{C.GREEN}{C.BOLD}+{total_savings:,.0f}{C.RST}",
        "",
        "",
    ))
    rows_data.append((
        f"{C.BOLD}Monthly avg{C.RST}",
        fmt_eur(-cum_current / max(len(proj_current), 1), 14),
        fmt_eur(-cum_target / max(len(proj_target), 1), 14),
        f"{C.GREEN}+{total_savings / max(len(proj_current), 1):,.0f}{C.RST}",
        "",
        "",
    ))

    print_table(headers, rows_data, widths)

    # Compartment breakdown for current scenario
    print(f"\n  {C.BOLD}Projected Annual Spending by Compartment (Current):{C.RST}")
    comp_totals = defaultdict(float)
    for _, _, items in proj_current:
        for item in items:
            comp_totals[item['compartment']] += item['amount']

    for comp in ['DIVORCE', 'PERSONAL', 'FAMILIAL', 'PROFESSIONAL', 'OBLIGATIONS']:
        total = comp_totals.get(comp, 0)
        color = COMPARTMENT_COLORS.get(comp, C.WHITE)
        pct = total / cum_current * 100 if cum_current > 0 else 0
        print(f"  {color}{comp:<15}{C.RST} {fmt_eur(-total, 14)}  ({pct:5.1f}%)  {bar(pct, 25)}")

    conn.close()
    print()


def cmd_classify(args):
    """Show investment vs expense breakdown for all transactions."""
    conn = get_db()
    init_projection_tables()

    period = args[0] if args else '2024-01-01'
    if len(period) == 4:
        period = f"{period}-01-01"

    rows = conn.execute("""
        SELECT id, date, category, counterparty, compartment,
               ABS(COALESCE(amount_eur, amount)) as amt, description
        FROM transactions
        WHERE amount_eur < 0
          AND date >= ?
        ORDER BY date
    """, (period,)).fetchall()

    inv_total = 0
    exp_total = 0
    inv_by_cat = defaultdict(float)
    exp_by_cat = defaultdict(float)
    inv_by_month = defaultdict(float)
    exp_by_month = defaultdict(float)

    for r in rows:
        cls = classify_transaction(r['category'], r['counterparty'])
        amt = r['amt']
        month = r['date'][:7]
        if cls == 'INVESTMENT':
            inv_total += amt
            inv_by_cat[r['category']] += amt
            inv_by_month[month] += amt
        else:
            exp_total += amt
            exp_by_cat[r['category']] += amt
            exp_by_month[month] += amt

    grand = inv_total + exp_total

    # Summary
    print()
    print_title(f"{C.CYAN}INVESTMENT vs EXPENSE CLASSIFICATION{C.RST} (since {period[:7]})", 80)

    inv_pct = inv_total / grand * 100 if grand > 0 else 0
    exp_pct = exp_total / grand * 100 if grand > 0 else 0

    print(f"\n  {C.GREEN}{C.BOLD}INVESTMENTS{C.RST}  {fmt_eur(-inv_total, 16)}  ({inv_pct:5.1f}%)  {bar(inv_pct, 30)}")
    print(f"  {C.RED}{C.BOLD}EXPENSES   {C.RST}  {fmt_eur(-exp_total, 16)}  ({exp_pct:5.1f}%)  {bar(exp_pct, 30)}")
    print(f"  {C.BOLD}TOTAL      {C.RST}  {fmt_eur(-grand, 16)}")

    # Investment breakdown
    print(f"\n  {C.GREEN}{C.BOLD}Investment Breakdown:{C.RST}")
    for cat, amt in sorted(inv_by_cat.items(), key=lambda x: -x[1]):
        pct = amt / inv_total * 100 if inv_total > 0 else 0
        print(f"    {cat:<30} {fmt_eur(-amt, 14)}  ({pct:5.1f}%)")

    # Top expense categories
    print(f"\n  {C.RED}{C.BOLD}Top 15 Expense Categories:{C.RST}")
    for i, (cat, amt) in enumerate(sorted(exp_by_cat.items(), key=lambda x: -x[1])[:15]):
        pct = amt / exp_total * 100 if exp_total > 0 else 0
        print(f"    {i+1:2d}. {cat:<28} {fmt_eur(-amt, 14)}  ({pct:5.1f}%)  {bar(pct, 15)}")

    # Monthly trend
    print(f"\n  {C.BOLD}Monthly Investment vs Expense:{C.RST}")
    all_months = sorted(set(list(inv_by_month.keys()) + list(exp_by_month.keys())))
    for m in all_months[-12:]:
        inv_m = inv_by_month.get(m, 0)
        exp_m = exp_by_month.get(m, 0)
        total_m = inv_m + exp_m
        inv_p = inv_m / total_m * 100 if total_m > 0 else 0
        print(f"    {m}  INV {fmt_eur(-inv_m, 14)}  EXP {fmt_eur(-exp_m, 14)}  ratio {C.GREEN}{inv_p:5.1f}%{C.RST} inv")

    conn.close()
    print()


def cmd_runway(args):
    """Show months of runway at current vs target burn rate."""
    conn = get_db()

    # Calculate current burn rate (last 3 months average, excl ACCOUNTING)
    now = datetime.now()
    three_months_ago = (now - timedelta(days=90)).strftime('%Y-%m-%d')

    monthly_totals = []
    for i in range(3, 0, -1):
        dt = now - timedelta(days=i * 30)
        y, m = dt.year, dt.month
        start, end = month_range(y, m)
        r = conn.execute("""
            SELECT SUM(ABS(COALESCE(amount_eur, amount)))
            FROM transactions WHERE amount_eur < 0
            AND compartment != 'ACCOUNTING'
            AND category NOT IN ('transfer_internal', 'card_funding', 'crypto_purchase', 'crypto_sale')
            AND date >= ? AND date < ?
        """, (start, end)).fetchone()
        amt = r[0] or 0
        if amt > 0:
            monthly_totals.append(amt)

    current_burn = sum(monthly_totals) / max(len(monthly_totals), 1)
    target_burn = 20_000  # EUR 20K target (excl pension)
    pension = MONTHLY_OBLIGATIONS['pension_alimentaire']

    # Current burn already includes pension in the monthly totals
    current_total_burn = current_burn
    target_total_burn = target_burn + pension  # 20K discretionary + 32.5K pension

    # Liquid assets
    total_liquid = sum(b['amount'] for b in LIQUID_BALANCES.values())
    total_liquid_ex_btc = total_liquid - LIQUID_BALANCES['BTC (20.5 @ 85K)']['amount']

    runway_current = total_liquid / current_total_burn if current_total_burn > 0 else float('inf')
    runway_target = total_liquid / target_total_burn if target_total_burn > 0 else float('inf')
    runway_current_ex = total_liquid_ex_btc / current_total_burn if current_total_burn > 0 else float('inf')
    runway_target_ex = total_liquid_ex_btc / target_total_burn if target_total_burn > 0 else float('inf')

    # Display
    print()
    print_title(f"{C.CYAN}RUNWAY ANALYSIS — How Long Can You Last?{C.RST}", 80)

    # Balances
    print(f"\n  {C.BOLD}Liquid Assets:{C.RST}")
    for name, bal in LIQUID_BALANCES.items():
        print(f"    {name:<25}  {C.GREEN}{bal['amount']:>12,.0f} EUR{C.RST}")
    print(f"    {'─' * 40}")
    print(f"    {C.BOLD}{'Total Liquid':<25}  {C.GREEN}{C.BOLD}{total_liquid:>12,.0f} EUR{C.RST}")
    print(f"    {C.DIM}{'(excl BTC)':<25}  {total_liquid_ex_btc:>12,.0f} EUR{C.RST}")

    print(f"\n  {C.BOLD}Frozen (not counted):{C.RST}")
    for name, bal in FROZEN_BALANCES.items():
        print(f"    {C.DIM}{name:<25}  {bal['amount']:>12,.0f} {bal['currency']}  [{bal['status']}]{C.RST}")

    # Burn rates
    print(f"\n  {C.BOLD}Monthly Burn Rates:{C.RST}")
    print(f"    {C.RED}Current trajectory:  {current_total_burn:>10,.0f} EUR/month{C.RST}")
    print(f"    {C.GREEN}Target (20K+pension): {target_total_burn:>10,.0f} EUR/month{C.RST}")
    print(f"    {C.BOLD}Difference:           {current_total_burn - target_total_burn:>10,.0f} EUR/month{C.RST}")

    # Runway bars
    print(f"\n  {C.BOLD}Runway (months until zero):{C.RST}")
    max_runway = max(runway_current, runway_target, runway_current_ex, runway_target_ex, 1)

    scenarios = [
        ("Current (incl BTC)", runway_current, C.RED),
        ("Current (excl BTC)", runway_current_ex, C.RED),
        ("Target 20K (incl BTC)", runway_target, C.GREEN),
        ("Target 20K (excl BTC)", runway_target_ex, C.GREEN),
    ]
    for label, months, color in scenarios:
        years = months / 12
        pct = months / max_runway * 100
        filled = int(round(pct / 100 * 30))
        filled = max(0, min(filled, 30))
        bar_str = f"{color}{'█' * filled}{C.DIM}{'░' * (30 - filled)}{C.RST}"
        print(f"    {label:<25} {color}{months:>6.1f} months{C.RST} ({years:.1f}y)  {bar_str}")

    # Depletion dates
    print(f"\n  {C.BOLD}Estimated Depletion Dates:{C.RST}")
    for label, months, color in scenarios:
        depletion = now + timedelta(days=months * 30.44)
        print(f"    {label:<25} {color}{depletion.strftime('%B %Y')}{C.RST}")

    # Annual comparison
    print(f"\n  {C.BOLD}Annualized Comparison:{C.RST}")
    print(f"    Current: {C.RED}{current_total_burn * 12:>12,.0f} EUR/year{C.RST}")
    print(f"    Target:  {C.GREEN}{target_total_burn * 12:>12,.0f} EUR/year{C.RST}")
    print(f"    Saving:  {C.BOLD}{(current_total_burn - target_total_burn) * 12:>12,.0f} EUR/year{C.RST}")

    conn.close()
    print()


def cmd_cuts(args):
    """Show what to cut to reach EUR 20K target, ordered by impact."""
    conn = get_db()

    now = datetime.now()
    three_months_ago = (now - timedelta(days=90)).strftime('%Y-%m-%d')

    # Get average monthly spend per category (last 3 months)
    rows = conn.execute("""
        SELECT category, compartment,
               SUM(ABS(COALESCE(amount_eur, amount))) / 3.0 as monthly_avg,
               COUNT(*) as txn_count
        FROM transactions
        WHERE amount_eur < 0
          AND date >= ?
          AND compartment != 'ACCOUNTING'
          AND category NOT IN ('transfer_internal', 'card_funding', 'crypto_purchase', 'crypto_sale')
        GROUP BY category
        ORDER BY monthly_avg DESC
    """, (three_months_ago,)).fetchall()

    pension = MONTHLY_OBLIGATIONS['pension_alimentaire']
    target = 20_000  # Target excl pension
    total_target_with_pension = target + pension

    # Calculate current non-pension spend
    current_total = sum(r['monthly_avg'] for r in rows)
    current_excl_pension = current_total - pension
    excess = current_excl_pension - target

    print()
    print_title(f"{C.CYAN}EXPENSE REDUCTION PLAN — Target: EUR 20K/month (excl pension){C.RST}", 92)

    print(f"\n  {C.BOLD}Current monthly burn (excl ACCOUNTING):{C.RST} {C.RED}{current_total:>12,.0f} EUR{C.RST}")
    print(f"  {C.BOLD}Pension (non-negotiable):{C.RST}               {C.YELLOW}{pension:>12,.0f} EUR{C.RST}")
    print(f"  {C.BOLD}Current excl pension:{C.RST}                   {C.RED}{current_excl_pension:>12,.0f} EUR{C.RST}")
    print(f"  {C.BOLD}Target excl pension:{C.RST}                    {C.GREEN}{target:>12,.0f} EUR{C.RST}")
    print(f"  {C.BOLD}Need to cut:{C.RST}                            {C.RED}{C.BOLD}{excess:>12,.0f} EUR/month{C.RST}")

    # Classify each category as cuttable or not
    cuts = []
    non_negotiable = []
    for r in rows:
        cat = r['category']
        avg = r['monthly_avg']
        comp = r['compartment']

        if cat == 'pension_alimentaire':
            non_negotiable.append((cat, avg, 0, 'Court order — non-negotiable'))
            continue
        elif cat in ('tax', 'tax_income', 'tax_property'):
            non_negotiable.append((cat, avg, 0, 'Mandatory tax obligation'))
            continue
        elif cat == 'debt_service':
            non_negotiable.append((cat, avg, 0, 'Debt service — contractual'))
            continue

        # Determine potential savings
        if cat in ('entertainment', 'shopping', 'gifts', 'travel', 'misc_personal', 'misc'):
            target_amt = 0
            action = 'ELIMINATE — fully discretionary'
            priority = 1
        elif cat == 'family_support':
            target_amt = min(avg, 2000)
            action = f'CAP at EUR 2,000/mo (was {avg:,.0f})'
            priority = 2
        elif cat.startswith('legal_fees'):
            target_amt = avg * 0.3
            action = f'REDUCE 70% — consolidate/settle cases'
            priority = 3
        elif cat == 'business_expense':
            target_amt = avg * 0.4
            action = f'REDUCE 60% — cut non-essential'
            priority = 4
        elif cat == 'professional_services':
            target_amt = avg * 0.2
            action = f'REDUCE 80% — minimize consultants'
            priority = 4
        elif cat == 'forensics':
            target_amt = 0
            action = 'ELIMINATE — wind down operations'
            priority = 2
        elif cat == 'housing':
            target_amt = min(avg, 2000)
            action = f'CAP at EUR 2,000/mo'
            priority = 5
        elif cat == 'food':
            target_amt = min(avg, 800)
            action = f'CAP at EUR 800/mo — cook more'
            priority = 6
        elif cat == 'telecom':
            target_amt = min(avg, 200)
            action = f'REDUCE — drop Monaco Telecom if possible'
            priority = 5
        elif cat == 'health_personal':
            target_amt = min(avg, 500)
            action = f'CAP at EUR 500/mo — essential only'
            priority = 7
        elif cat == 'transport':
            target_amt = min(avg, 200)
            action = f'CAP at EUR 200/mo — less Uber'
            priority = 6
        elif cat in ('school_fees', 'school_extras'):
            target_amt = avg  # Non-negotiable
            non_negotiable.append((cat, avg, 0, 'Education — non-negotiable'))
            continue
        elif cat == 'standing_order':
            target_amt = avg  # Fixed
            non_negotiable.append((cat, avg, 0, 'Standing orders — contractual'))
            continue
        elif cat == 'insurance_home':
            target_amt = avg
            non_negotiable.append((cat, avg, 0, 'Insurance — contractual'))
            continue
        elif cat == 'wire_out':
            target_amt = avg * 0.3
            action = f'REDUCE 70% — minimize outbound wires'
            priority = 3
        elif cat == 'subscriptions':
            target_amt = 0
            action = 'ELIMINATE — cancel all subscriptions'
            priority = 1
        elif cat == 'bank_fees':
            target_amt = avg * 0.5
            action = 'REDUCE — close unnecessary accounts'
            priority = 8
        else:
            target_amt = avg * 0.5
            action = f'REDUCE 50% — review and cut'
            priority = 5

        saving = avg - target_amt
        if saving > 0:
            cuts.append((cat, avg, target_amt, saving, action, priority, comp))

    # Sort by saving (highest impact first)
    cuts.sort(key=lambda x: -x[3])

    # Display cuts table
    print(f"\n  {C.BOLD}{C.GREEN}Proposed Cuts (ordered by impact):{C.RST}")
    headers = ["#", "Category", "Current/mo", "Target/mo", "Saving/mo", "Action"]
    widths = [4, 25, 13, 13, 13, 32]

    rows_data = []
    cum_saving = 0
    for i, (cat, curr, tgt, saving, action, prio, comp) in enumerate(cuts, 1):
        cum_saving += saving
        color = COMPARTMENT_COLORS.get(comp, C.WHITE)
        check = f"{C.GREEN}*{C.RST}" if cum_saving >= excess else " "
        rows_data.append((
            f"{check}{i:2d}",
            f"{color}{cat}{C.RST}",
            fmt_eur(-curr, 12),
            fmt_eur(-tgt, 12),
            f"{C.GREEN}+{saving:>9,.0f}{C.RST}",
            action,
        ))
        if cum_saving >= excess and i > 1:
            # Mark where we hit the target
            pass

    cum_saving_total = sum(s for _, _, _, s, _, _, _ in cuts)
    rows_data.append(("", "", "", "", "", ""))
    rows_data.append((
        "",
        f"{C.BOLD}TOTAL SAVINGS{C.RST}",
        "",
        "",
        f"{C.GREEN}{C.BOLD}+{cum_saving_total:>9,.0f}{C.RST}",
        f"{'Target MET' if cum_saving_total >= excess else 'SHORTFALL: ' + str(int(excess - cum_saving_total))}",
    ))

    print_table(headers, rows_data, widths)

    # Non-negotiable items
    print(f"\n  {C.BOLD}{C.YELLOW}Non-Negotiable Items (cannot cut):{C.RST}")
    nn_total = 0
    for cat, amt, _, reason in sorted(non_negotiable, key=lambda x: -x[1]):
        nn_total += amt
        print(f"    {cat:<28} {fmt_eur(-amt, 12)}  {C.DIM}{reason}{C.RST}")
    print(f"    {'─' * 50}")
    print(f"    {C.BOLD}{'Total fixed':<28} {fmt_eur(-nn_total, 12)}{C.RST}")

    # Summary
    print(f"\n  {C.BOLD}Summary:{C.RST}")
    new_total = current_total - cum_saving_total
    print(f"    Current monthly:     {C.RED}{current_total:>10,.0f} EUR{C.RST}")
    print(f"    After all cuts:      {C.GREEN}{new_total:>10,.0f} EUR{C.RST}")
    print(f"    Target (incl pension):{C.CYAN}{total_target_with_pension:>10,.0f} EUR{C.RST}")
    gap = new_total - total_target_with_pension
    if gap > 0:
        print(f"    {C.RED}Still over target by:  {gap:>10,.0f} EUR/month{C.RST}")
    else:
        print(f"    {C.GREEN}Under target by:       {abs(gap):>10,.0f} EUR/month{C.RST}")

    conn.close()
    print()


# ── Main CLI ──────────────────────────────────────────────────────────────
COMMANDS = {
    "init": ("Create tables, seed merchant map", init_tables),
    "summary": ("Monthly summary all levels", cmd_summary),
    "daily": ("Daily breakdown", cmd_daily),
    "weekly": ("Weekly breakdown", cmd_weekly),
    "monthly": ("Monthly trend for year", cmd_monthly),
    "quarterly": ("Quarterly rollup", cmd_quarterly),
    "yearly": ("Year-over-year comparison", cmd_yearly),
    "compartment": ("Drill into compartment", cmd_compartment),
    "category": ("Drill into category", cmd_category),
    "merchant": ("Drill into merchant", cmd_merchant),
    "top": ("Top N expenses", cmd_top),
    "burn": ("Burn rate projection", cmd_burn),
    "trend": ("Category trend over time", cmd_trend),
    "compare": ("Compare two months", cmd_compare),
    "set-target": ("Set budget target", cmd_set_target),
    "targets": ("Show all targets with status", cmd_targets),
    "alerts": ("Show budget alerts", cmd_alerts),
    "food": ("Food spending analysis", cmd_food),
    "transport": ("Transport spending", cmd_transport),
    "education": ("Education/tutoring spending", cmd_education),
    "subscriptions": ("Subscriptions spending", cmd_subscriptions),
    "travel-spend": ("Travel spending by destination", cmd_travel_spend),
    "stats": ("Overall statistics", cmd_stats),
    "export": ("Export full budget data as JSON", cmd_export),
    "projection": ("12-month projection (current vs target)", cmd_projection),
    "classify": ("Investment vs expense breakdown", cmd_classify),
    "runway": ("Months of runway at current vs target burn", cmd_runway),
    "cuts": ("What to cut to reach EUR 20K target", cmd_cuts),
}


def show_help():
    print(f"\n{C.BOLD}{C.CYAN}Budget Engine — Multi-Level Hierarchical Budgeting{C.RST}")
    print(f"{C.DIM}Reads from finance_lake.db, provides drill-down expense tracking.{C.RST}\n")
    max_cmd = max(len(c) for c in COMMANDS)
    for cmd, (desc, _) in COMMANDS.items():
        print(f"  {C.BOLD}budget {cmd:<{max_cmd}}{C.RST}  {desc}")
    print()


def main():
    if len(sys.argv) < 2:
        show_help()
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd in ("help", "-h", "--help"):
        show_help()
        return

    if cmd == "init":
        init_tables()
        return

    if cmd == "set-target":
        cmd_set_target(args)
        return

    if cmd == "travel-spend":
        cmd_travel_spend(args)
        return

    if cmd in COMMANDS:
        _, func = COMMANDS[cmd]
        if func == init_tables:
            init_tables()
        else:
            func(args)
    else:
        print(f"{C.RED}Unknown command: {cmd}{C.RST}")
        show_help()


if __name__ == "__main__":
    main()
