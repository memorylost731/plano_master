#!/usr/bin/env python3
"""Deduction Engine — Bell-LaPadula + C4ISR + OODA Loop intel architecture.

Architecture:
  ┌─────────────────────────────────────────────────────────────────┐
  │  C4ISR FRAMEWORK (Command, Control, Communications,            │
  │         Computers, Intelligence, Surveillance, Reconnaissance)  │
  │                                                                 │
  │  SENSORS (10 DBs)  →  FUSION  →  ANALYSIS  →  DECISION        │
  │  lake, ocr, wa,       cross-     deduction     OODA loop       │
  │  crypto, finance,     search     engine         actionable     │
  │  doc, psych, legal,   entity     Bell-LaPadula  outputs        │
  │  police, legal_ant    linking    access control                 │
  └─────────────────────────────────────────────────────────────────┘

Bell-LaPadula Model (BLP):
  - Simple Security (no read-up): subject at level L cannot read objects at level > L
  - Star Property (no write-down): subject at level L cannot write to objects at level < L
  - Strong Star: subject can only read/write at their exact level
  Applied: deductions respect classification ceiling — combined intel inherits
           highest classification of any contributing source (HIGH WATER MARK).

OODA Loop (Observe-Orient-Decide-Act):
  OBSERVE:  Sensor sweep across all 10 databases (86K+ records)
  ORIENT:   Entity linking, corroboration, contradiction detection
  DECIDE:   Confidence calculus, grade upgrading, gap prioritization
  ACT:      Actionable intelligence products, timeline fills, financial chains

Deduction Rules:
  CORROBORATION:  2+ independent D-grade sources confirming same fact → upgrade to C
  TRIANGULATION:  3+ independent sources across databases → upgrade one tier
  TEMPORAL CHAIN: Events A→B→C with known A,C can deduce B timing
  FINANCIAL FLOW: Payment chains with known endpoints → reconstruct intermediaries
  IDENTITY LINK:  Phone/email/wallet appearing in 2+ contexts → link entities
  CONTRADICTION:  Conflicting data across compartments → flag for review

Confidence Calculus:
  Single source:  conf = grade_conf[grade]
  Corroboration:  conf = 1 - prod(1 - conf_i for i in sources)
  With decay:     conf *= 0.95^(months_old)

Usage:
  deduction audit                     Full compartment audit with gap analysis
  deduction corroborate <query>       Find corroborative chains for a claim
  deduction reconstruct               Reconstruct intel from low-grade fragments
  deduction contradictions             Surface cross-compartment contradictions
  deduction gaps                      Identify intelligence gaps
  deduction upgrade                   Auto-upgrade grades where corroboration exists
  deduction links                     Find hidden entity links across databases
  deduction timeline-fill             Fill timeline gaps from lesser sources
  deduction financial-chain <entity>  Trace financial flows across databases
  deduction ooda <topic>              Run full OODA cycle on a topic
  deduction blp-check                 Bell-LaPadula compliance audit
  deduction fusion                    C4ISR sensor fusion report
  deduction stats                     Deduction engine statistics
"""

import argparse
import json
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Set

# ══════════════════════════════════════════════════════════════
# DATABASE PATHS
# ══════════════════════════════════════════════════════════════

BASE = Path.home() / "data-gathering-agent"
DB_PATHS = {
    "lake":     BASE / "memory_lake" / "lake.db",
    "ocr":      BASE / "ocr_results.db",
    "doc":      BASE / "integrations" / "doc_index.db",
    "psych":    BASE / "psych_engine.db",
    "whatsapp": BASE / "whatsapp_gdrive.db",
    "crypto":   Path.home() / "forensic" / "Crypto-forensic" / "db" / "crypto_forensic.db",
    "finance":  Path.home() / "forensic" / "personal-finance" / "db" / "finance_lake.db",
    "legal":    BASE / "legal_engine.db",
    "legal_ant": BASE / "legal_anticipation.db",
    "police":   BASE / "police_cooperation.db",
}

DEDUCTION_DB = BASE / "deduction_engine.db"

# ══════════════════════════════════════════════════════════════
# CONFIDENCE MAPPING
# ══════════════════════════════════════════════════════════════

GRADE_CONFIDENCE = {
    "S": 0.97,  # Supreme — apostilled, court-sealed
    "A": 0.90,  # Authoritative — certified, official
    "B": 0.77,  # Business — contracts, invoices
    "C": 0.60,  # Casual — emails, screenshots
    "D": 0.40,  # Dubious — chat, social media
    "E": 0.20,  # Ephemeral — hearsay, corrupted
}

# Corroboration upgrade thresholds
UPGRADE_RULES = {
    # (current_grade, required_independent_sources, min_combined_conf) → new_grade
    ("E", 3, 0.49): "D",
    ("E", 2, 0.36): "D",
    ("D", 3, 0.65): "C",
    ("D", 2, 0.55): "C",
    ("C", 3, 0.80): "B",
    ("C", 2, 0.72): "B",
    ("B", 2, 0.90): "A",
}

# ══════════════════════════════════════════════════════════════
# KEY ENTITIES (for cross-reference linking)
# ══════════════════════════════════════════════════════════════

KEY_ENTITIES = {
    "persons": {
        "hadrien": ["hadrien", "majoie", "hadrien majoie"],
        "marina": ["marina", "gavryusheva", "marina gavryusheva", "marina majoie"],
        "giaccardi": ["giaccardi", "maître giaccardi", "thomas giaccardi"],
        "giotto": ["giotto", "de filippi", "giotto de filippi"],
        "bisazza": ["bisazza", "bisazza ganado"],
        "khalifa": ["khalifa", "dan khalifa", "dgfla"],
        "merkt": ["merkt", "romain jordan", "ronald asmar"],
        "zimeray": ["zimeray", "françois zimeray"],
        "ifw": ["ifw", "ifw global", "ken gamble", "ilana katz"],
        "gamble": ["ken gamble", "gamble"],
    },
    "institutions": {
        "kraken": ["kraken"],
        "julius_baer": ["julius baer", "julius bär", "sequestre"],
        "bnp": ["bnp", "bnp paribas"],
        "banque_frick": ["banque frick", "frick"],
        "n26": ["n26"],
        "emirates_nbd": ["emirates nbd", "nbd"],
        "simply_vc": ["simply vc", "simply staking", "simply holding"],
        "smartcow": ["smartcow", "smart cow"],
        "magest": ["magest", "magest capital"],
        "99avocats": ["99 avocats", "99avocats"],
    },
    "financial": {
        "pension": ["pension", "alimentaire", "€32,500", "€32500", "€85,000", "€85000"],
        "btc": ["bitcoin", "btc", "ledger", "seed", "wallet"],
        "atom": ["atom", "cosmos", "staking", "validator"],
        "redotpay": ["redotpay"],
    },
    "legal": {
        "hague": ["hague", "enlèvement", "abduction", "convention de la haye"],
        "escroquerie": ["escroquerie", "fraud", "swindling"],
        "donation": ["donation", "révocation", "revocation"],
        "custody": ["garde", "custody", "résidence", "residence"],
        "non_rep": ["non-représentation", "non représentation", "non-representation"],
    },
}

# ══════════════════════════════════════════════════════════════
# DATABASE HELPERS
# ══════════════════════════════════════════════════════════════

def get_db(path: Path) -> Optional[sqlite3.Connection]:
    """Open database if it exists."""
    if not path.exists():
        return None
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_deduction_db():
    """Initialize the deduction tracking database."""
    conn = sqlite3.connect(str(DEDUCTION_DB))
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS deductions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deduction_type TEXT NOT NULL,
            conclusion TEXT NOT NULL,
            confidence REAL NOT NULL,
            sources TEXT NOT NULL,
            reasoning TEXT NOT NULL,
            entity_links TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            reviewed_at TEXT,
            upgraded_grade TEXT
        );
        CREATE TABLE IF NOT EXISTS corroborations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim TEXT NOT NULL,
            source_db TEXT NOT NULL,
            source_id TEXT NOT NULL,
            source_grade TEXT,
            source_confidence REAL,
            content_excerpt TEXT,
            matched_entities TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS contradictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_a TEXT NOT NULL,
            source_a TEXT NOT NULL,
            claim_b TEXT NOT NULL,
            source_b TEXT NOT NULL,
            severity TEXT DEFAULT 'medium',
            resolution TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS entity_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_key TEXT NOT NULL,
            source_db TEXT NOT NULL,
            source_table TEXT NOT NULL,
            source_id TEXT NOT NULL,
            context TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(entity_key, source_db, source_table, source_id)
        );
        CREATE TABLE IF NOT EXISTS gaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gap_type TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT DEFAULT 'medium',
            potential_sources TEXT,
            status TEXT DEFAULT 'open',
            created_at TEXT DEFAULT (datetime('now')),
            resolved_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_ded_type ON deductions(deduction_type);
        CREATE INDEX IF NOT EXISTS idx_ded_status ON deductions(status);
        CREATE INDEX IF NOT EXISTS idx_link_entity ON entity_links(entity_key);
        CREATE INDEX IF NOT EXISTS idx_link_db ON entity_links(source_db);
        CREATE INDEX IF NOT EXISTS idx_gap_status ON gaps(status);
    """)
    conn.commit()
    return conn

# ══════════════════════════════════════════════════════════════
# CROSS-DATABASE SEARCH
# ══════════════════════════════════════════════════════════════

def search_lake(query: str, limit: int = 50) -> List[dict]:
    """Search memory lake FTS."""
    conn = get_db(DB_PATHS["lake"])
    if not conn:
        return []
    results = []
    try:
        # Sanitize for FTS5
        safe_q = re.sub(r'[^\w\s]', ' ', query).strip()
        if not safe_q:
            return []
        rows = conn.execute("""
            SELECT m.id, m.memory_type, m.content, m.doc_grade, m.tags, m.created_at,
                   m.source, m.cls_level, m.cls_label
            FROM memories m
            JOIN memory_fts f ON f.rowid = m.id
            WHERE memory_fts MATCH ?
            ORDER BY rank LIMIT ?
        """, (safe_q, limit)).fetchall()
        for r in rows:
            results.append(dict(r))
    except Exception:
        pass
    conn.close()
    return results

def search_ocr(query: str, limit: int = 50) -> List[dict]:
    """Search OCR results FTS."""
    conn = get_db(DB_PATHS["ocr"])
    if not conn:
        return []
    results = []
    try:
        safe_q = re.sub(r'[^\w\s]', ' ', query).strip()
        rows = conn.execute("""
            SELECT o.id, o.file_path, o.ocr_text, o.doc_grade, o.confidence, o.filename
            FROM ocr_results o
            JOIN ocr_fts f ON f.rowid = o.id
            WHERE ocr_fts MATCH ?
            ORDER BY rank LIMIT ?
        """, (safe_q, limit)).fetchall()
        for r in rows:
            results.append(dict(r))
    except Exception:
        pass
    conn.close()
    return results

def search_whatsapp(query: str, limit: int = 50) -> List[dict]:
    """Search WhatsApp messages."""
    conn = get_db(DB_PATHS["whatsapp"])
    if not conn:
        return []
    results = []
    try:
        safe_q = re.sub(r'[^\w\s]', ' ', query).strip()
        rows = conn.execute("""
            SELECT m.id, m.sender, m.message, m.timestamp, m.cls_level, m.cls_label,
                   c.chat_name
            FROM messages m
            JOIN messages_fts f ON f.rowid = m.id
            JOIN chats c ON c.id = m.chat_id
            WHERE messages_fts MATCH ?
            ORDER BY rank LIMIT ?
        """, (safe_q, limit)).fetchall()
        for r in rows:
            results.append(dict(r))
    except Exception:
        pass
    conn.close()
    return results

def search_crypto(query: str, limit: int = 50) -> List[dict]:
    """Search crypto forensic DB."""
    conn = get_db(DB_PATHS["crypto"])
    if not conn:
        return []
    results = []
    try:
        # Check if FTS exists
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if "case_fts" in tables:
            safe_q = re.sub(r'[^\w\s]', ' ', query).strip()
            rows = conn.execute("""
                SELECT * FROM case_timeline
                WHERE id IN (SELECT rowid FROM case_fts WHERE case_fts MATCH ?)
                LIMIT ?
            """, (safe_q, limit)).fetchall()
            for r in rows:
                results.append(dict(r))
    except Exception:
        pass
    conn.close()
    return results

def search_finance(query: str, limit: int = 50) -> List[dict]:
    """Search finance lake."""
    conn = get_db(DB_PATHS["finance"])
    if not conn:
        return []
    results = []
    try:
        safe_q = re.sub(r'[^\w\s]', ' ', query).strip()
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if "finance_fts" in tables:
            rows = conn.execute("""
                SELECT rowid, * FROM finance_fts WHERE finance_fts MATCH ? LIMIT ?
            """, (safe_q, limit)).fetchall()
            for r in rows:
                results.append(dict(r))
    except Exception:
        pass
    conn.close()
    return results

def search_doc(query: str, limit: int = 50) -> List[dict]:
    """Search document index."""
    conn = get_db(DB_PATHS["doc"])
    if not conn:
        return []
    results = []
    try:
        safe_q = re.sub(r'[^\w\s]', ' ', query).strip()
        rows = conn.execute("""
            SELECT d.id, d.file_path, d.doc_grade, d.filename,
                   substr(d.content, 1, 300) as content_preview
            FROM documents d
            JOIN doc_fts f ON f.rowid = d.id
            WHERE doc_fts MATCH ?
            ORDER BY rank LIMIT ?
        """, (safe_q, limit)).fetchall()
        for r in rows:
            results.append(dict(r))
    except Exception:
        pass
    conn.close()
    return results

ALL_SEARCHERS = {
    "lake": search_lake,
    "ocr": search_ocr,
    "whatsapp": search_whatsapp,
    "crypto": search_crypto,
    "finance": search_finance,
    "doc": search_doc,
}

def cross_search(query: str, limit_per_db: int = 20) -> Dict[str, List[dict]]:
    """Search across all databases."""
    results = {}
    for name, searcher in ALL_SEARCHERS.items():
        hits = searcher(query, limit_per_db)
        if hits:
            results[name] = hits
    return results

# ══════════════════════════════════════════════════════════════
# ENTITY DETECTION
# ══════════════════════════════════════════════════════════════

def detect_entities(text: str) -> Dict[str, Set[str]]:
    """Detect known entities in text."""
    if not text:
        return {}
    text_lower = text.lower()
    found = defaultdict(set)
    for category, entities in KEY_ENTITIES.items():
        for key, aliases in entities.items():
            for alias in aliases:
                if alias.lower() in text_lower:
                    found[category].add(key)
                    break
    return dict(found)

# ══════════════════════════════════════════════════════════════
# CONFIDENCE CALCULUS
# ══════════════════════════════════════════════════════════════

def combined_confidence(confidences: List[float]) -> float:
    """Compute combined confidence from independent sources.
    P(true) = 1 - prod(1 - p_i) for independent corroboration."""
    if not confidences:
        return 0.0
    product = 1.0
    for c in confidences:
        product *= (1.0 - c)
    return round(1.0 - product, 4)

def time_decay(conf: float, months_old: float) -> float:
    """Apply temporal decay to confidence."""
    return conf * (0.95 ** months_old)

def grade_to_conf(grade: str) -> float:
    """Convert letter grade to confidence score."""
    return GRADE_CONFIDENCE.get(grade, 0.30)

def conf_to_grade(conf: float) -> str:
    """Convert confidence to nearest grade."""
    if conf >= 0.93:
        return "S"
    elif conf >= 0.85:
        return "A"
    elif conf >= 0.68:
        return "B"
    elif conf >= 0.50:
        return "C"
    elif conf >= 0.30:
        return "D"
    return "E"

# ══════════════════════════════════════════════════════════════
# DEDUCTION RULES
# ══════════════════════════════════════════════════════════════

def find_corroborations(claim_keywords: str) -> List[dict]:
    """Find all sources that corroborate a claim across databases."""
    all_hits = cross_search(claim_keywords, limit_per_db=30)
    corroborations = []
    for db_name, hits in all_hits.items():
        for hit in hits:
            # Extract content field (varies by DB)
            content = (hit.get("content") or hit.get("ocr_text") or
                      hit.get("message") or hit.get("content_preview") or "")
            grade = hit.get("doc_grade") or hit.get("cls_label") or ""
            # Map classification labels to grades
            if not grade or grade in ("OFFICIAL", "RESTRICTED", "CONFIDENTIAL", "SECRET"):
                if grade == "SECRET":
                    grade = "A"
                elif grade == "CONFIDENTIAL":
                    grade = "B"
                elif grade == "RESTRICTED":
                    grade = "C"
                elif grade == "OFFICIAL":
                    grade = "D"
                else:
                    grade = ""
            conf = grade_to_conf(grade) if grade else 0.30
            entities = detect_entities(content)
            corroborations.append({
                "db": db_name,
                "id": hit.get("id", "?"),
                "grade": grade,
                "confidence": conf,
                "content": content[:200] if content else "",
                "entities": entities,
                "timestamp": hit.get("created_at") or hit.get("timestamp") or "",
            })
    return corroborations

def deduce_entity_links(ddb: sqlite3.Connection) -> int:
    """Scan all databases and build entity cross-reference links."""
    link_count = 0

    # Lake entities
    conn = get_db(DB_PATHS["lake"])
    if conn:
        rows = conn.execute("SELECT id, content, memory_type FROM memories").fetchall()
        for r in rows:
            entities = detect_entities(r["content"] or "")
            for cat, keys in entities.items():
                for key in keys:
                    try:
                        ddb.execute("""
                            INSERT OR IGNORE INTO entity_links
                            (entity_type, entity_key, source_db, source_table, source_id, context)
                            VALUES (?, ?, 'lake', 'memories', ?, ?)
                        """, (cat, key, str(r["id"]), r["memory_type"]))
                        link_count += 1
                    except Exception:
                        pass
        conn.close()

    # WhatsApp entities
    conn = get_db(DB_PATHS["whatsapp"])
    if conn:
        rows = conn.execute("""
            SELECT m.id, m.message, m.sender, c.chat_name
            FROM messages m JOIN chats c ON c.id = m.chat_id
            WHERE length(m.message) > 20
            LIMIT 50000
        """).fetchall()
        for r in rows:
            entities = detect_entities((r["message"] or "") + " " + (r["chat_name"] or "" if "chat_name" in r.keys() else ""))
            for cat, keys in entities.items():
                for key in keys:
                    try:
                        ddb.execute("""
                            INSERT OR IGNORE INTO entity_links
                            (entity_type, entity_key, source_db, source_table, source_id, context)
                            VALUES (?, ?, 'whatsapp', 'messages', ?, ?)
                        """, (cat, key, str(r["id"]), r["chat_name"] or r["sender"]))
                        link_count += 1
                    except Exception:
                        pass
        conn.close()

    # OCR entities
    conn = get_db(DB_PATHS["ocr"])
    if conn:
        rows = conn.execute("""
            SELECT id, ocr_text, filename, doc_grade FROM ocr_results
            WHERE length(ocr_text) > 50
        """).fetchall()
        for r in rows:
            entities = detect_entities(r["ocr_text"] or "")
            for cat, keys in entities.items():
                for key in keys:
                    try:
                        ddb.execute("""
                            INSERT OR IGNORE INTO entity_links
                            (entity_type, entity_key, source_db, source_table, source_id, context)
                            VALUES (?, ?, 'ocr', 'ocr_results', ?, ?)
                        """, (cat, key, str(r["id"]), r["filename"]))
                        link_count += 1
                    except Exception:
                        pass
        conn.close()

    # Doc index entities
    conn = get_db(DB_PATHS["doc"])
    if conn:
        try:
            rows = conn.execute("""
                SELECT id, content, filename, doc_grade FROM documents
                WHERE length(content) > 50
            """).fetchall()
            for r in rows:
                entities = detect_entities((r["content"] or "")[:5000])
                for cat, keys in entities.items():
                    for key in keys:
                        try:
                            ddb.execute("""
                                INSERT OR IGNORE INTO entity_links
                                (entity_type, entity_key, source_db, source_table, source_id, context)
                                VALUES (?, ?, 'doc', 'documents', ?, ?)
                            """, (cat, key, str(r["id"]), r["filename"]))
                            link_count += 1
                        except Exception:
                            pass
        except Exception:
            pass
        conn.close()

    # Crypto entities (case_timeline, wallets, marina_crypto)
    conn = get_db(DB_PATHS["crypto"])
    if conn:
        for tbl, text_col in [("case_timeline", "event"), ("wallets", "notes"),
                               ("marina_crypto", "notes"), ("ifw_documents", "title")]:
            try:
                cols = [r[1] for r in conn.execute(f"PRAGMA table_info({tbl})").fetchall()]
                if text_col not in cols:
                    continue
                rows = conn.execute(f"SELECT id, {text_col} FROM {tbl} WHERE {text_col} IS NOT NULL").fetchall()
                for r in rows:
                    entities = detect_entities(r[1] or "")
                    for cat, keys in entities.items():
                        for key in keys:
                            try:
                                ddb.execute("""
                                    INSERT OR IGNORE INTO entity_links
                                    (entity_type, entity_key, source_db, source_table, source_id, context)
                                    VALUES (?, ?, 'crypto', ?, ?, ?)
                                """, (cat, key, tbl, str(r[0]), tbl))
                                link_count += 1
                            except Exception:
                                pass
            except Exception:
                pass
        conn.close()

    # Finance entities (transactions, invoices, obligations, providers)
    conn = get_db(DB_PATHS["finance"])
    if conn:
        for tbl, text_col in [("transactions", "description"), ("invoices", "description"),
                               ("obligations", "description"), ("providers", "name"),
                               ("recurring", "description")]:
            try:
                cols = [r[1] for r in conn.execute(f"PRAGMA table_info({tbl})").fetchall()]
                if text_col not in cols:
                    continue
                rows = conn.execute(f"SELECT id, {text_col} FROM {tbl} WHERE {text_col} IS NOT NULL").fetchall()
                for r in rows:
                    entities = detect_entities(r[1] or "")
                    for cat, keys in entities.items():
                        for key in keys:
                            try:
                                ddb.execute("""
                                    INSERT OR IGNORE INTO entity_links
                                    (entity_type, entity_key, source_db, source_table, source_id, context)
                                    VALUES (?, ?, 'finance', ?, ?, ?)
                                """, (cat, key, tbl, str(r[0]), tbl))
                                link_count += 1
                            except Exception:
                                pass
            except Exception:
                pass
        conn.close()

    # Psych entities (analyses, manipulations, emotions)
    conn = get_db(DB_PATHS["psych"])
    if conn:
        for tbl, text_col in [("analyses", "content"), ("manipulations", "description"),
                               ("emotions", "context"), ("subjects", "name")]:
            try:
                cols = [r[1] for r in conn.execute(f"PRAGMA table_info({tbl})").fetchall()]
                if text_col not in cols:
                    continue
                rows = conn.execute(f"SELECT id, {text_col} FROM {tbl} WHERE {text_col} IS NOT NULL").fetchall()
                for r in rows:
                    entities = detect_entities(r[1] or "")
                    for cat, keys in entities.items():
                        for key in keys:
                            try:
                                ddb.execute("""
                                    INSERT OR IGNORE INTO entity_links
                                    (entity_type, entity_key, source_db, source_table, source_id, context)
                                    VALUES (?, ?, 'psych', ?, ?, ?)
                                """, (cat, key, tbl, str(r[0]), tbl))
                                link_count += 1
                            except Exception:
                                pass
            except Exception:
                pass
        conn.close()

    ddb.commit()
    return link_count

# ══════════════════════════════════════════════════════════════
# GAP ANALYSIS
# ══════════════════════════════════════════════════════════════

def analyze_gaps(ddb: sqlite3.Connection) -> List[dict]:
    """Identify intelligence gaps across all compartments."""
    gaps = []

    # 1. Ungraded data
    for db_name, db_path in DB_PATHS.items():
        conn = get_db(db_path)
        if not conn:
            continue
        try:
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for tbl in tables:
                cols = [r[1] for r in conn.execute(f"PRAGMA table_info({tbl})").fetchall()]
                if "doc_grade" in cols:
                    total = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                    ungraded = conn.execute(
                        f"SELECT COUNT(*) FROM {tbl} WHERE doc_grade IS NULL OR doc_grade=''"
                    ).fetchone()[0]
                    if ungraded > 0 and total > 0:
                        pct = round(100 * ungraded / total, 1)
                        if pct > 30:
                            gaps.append({
                                "type": "ungraded_data",
                                "description": f"{db_name}.{tbl}: {ungraded}/{total} records ungraded ({pct}%)",
                                "priority": "high" if pct > 60 else "medium",
                                "potential_sources": f"Run: doc-grade scan --db {db_name}",
                            })
        except Exception:
            pass
        conn.close()

    # 2. Crypto transactions without notes
    conn = get_db(DB_PATHS["crypto"])
    if conn:
        try:
            total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            empty = conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE notes IS NULL OR notes=''"
            ).fetchone()[0]
            if empty > 0:
                gaps.append({
                    "type": "unlabeled_transactions",
                    "description": f"Crypto: {empty}/{total} transactions without notes/labels",
                    "priority": "high",
                    "potential_sources": "Cross-ref with WhatsApp timestamps, email receipts, exchange records",
                })
        except Exception:
            pass
        conn.close()

    # 3. Timeline gaps — periods with no events
    conn = get_db(DB_PATHS["lake"])
    if conn:
        try:
            events = conn.execute("""
                SELECT date(created_at) as d, COUNT(*) as cnt
                FROM memories WHERE memory_type='event'
                GROUP BY date(created_at) ORDER BY d
            """).fetchall()
            if events:
                prev = None
                for e in events:
                    d = e["d"]
                    if prev and d:
                        try:
                            d1 = datetime.strptime(prev, "%Y-%m-%d")
                            d2 = datetime.strptime(d, "%Y-%m-%d")
                            gap_days = (d2 - d1).days
                            if gap_days > 30:
                                gaps.append({
                                    "type": "timeline_gap",
                                    "description": f"No events recorded between {prev} and {d} ({gap_days} days)",
                                    "priority": "medium",
                                    "potential_sources": "Check WhatsApp, email, OCR for this period",
                                })
                        except ValueError:
                            pass
                    prev = d
        except Exception:
            pass
        conn.close()

    # 4. Known unknowns
    known_unknowns = [
        {
            "type": "missing_data",
            "description": "BTC holdings: seed phrase unrecovered — exact balance unknown",
            "priority": "critical",
            "potential_sources": "Seed reconstruction, Ledger Live export, exchange records, blockchain scan",
        },
        {
            "type": "missing_data",
            "description": "Malta legal codes: legislation.mt JS-rendered, not yet indexed",
            "priority": "medium",
            "potential_sources": "eCourts PDFs, headless browser, University of Malta law resources",
        },
        {
            "type": "missing_data",
            "description": "Liechtenstein legal codes: gesetze.li blocked",
            "priority": "low",
            "potential_sources": "gesetze.li PDF endpoint, manual download",
        },
        {
            "type": "missing_data",
            "description": "WhatsApp bridge expired — no live message capture",
            "priority": "high",
            "potential_sources": "Re-link WhatsApp bridge (QR scan required)",
        },
    ]
    gaps.extend(known_unknowns)

    # Store gaps
    for g in gaps:
        try:
            ddb.execute("""
                INSERT INTO gaps (gap_type, description, priority, potential_sources)
                VALUES (?, ?, ?, ?)
            """, (g["type"], g["description"], g["priority"], g.get("potential_sources", "")))
        except Exception:
            pass
    ddb.commit()

    return gaps

# ══════════════════════════════════════════════════════════════
# RECONSTRUCT INTEL FROM LOW-GRADE DATA
# ══════════════════════════════════════════════════════════════

def reconstruct_intel(ddb: sqlite3.Connection) -> List[dict]:
    """Attempt to reconstruct higher-confidence intel from corroborating low-grade sources."""
    deductions = []

    # Key claims to investigate
    claims = [
        ("Marina crypto wallets", "marina wallet ledger crypto atom"),
        ("Pension payment flow", "pension alimentaire payment bank transfer"),
        ("Kraken accounts", "kraken exchange account crypto"),
        ("Donation revocation", "donation revocation révocation"),
        ("Child abduction case", "abduction hague enlèvement enfant"),
        ("Escroquerie proceedings", "escroquerie fraud criminal"),
        ("Simply VC exit", "simply vc exit sale giotto"),
        ("Malta conviction", "conviction malta magistrates"),
        ("IFW investigation", "ifw global investigation forensic"),
        ("Monaco residence", "monaco residence domicile address"),
        ("BTC holdings", "bitcoin btc holdings wallet seed"),
        ("99 Avocats fees", "99 avocats outstanding fees invoice"),
        ("Julius Baer sequestre", "julius baer sequestre account frozen"),
    ]

    for claim_name, keywords in claims:
        corrs = find_corroborations(keywords)
        if len(corrs) < 2:
            continue

        # Count independent databases
        dbs_seen = set(c["db"] for c in corrs)
        grades = [c["grade"] for c in corrs if c["grade"]]
        confs = [c["confidence"] for c in corrs]

        combined = combined_confidence(confs[:10])  # Cap at 10 sources
        current_best_grade = min(grades) if grades else "E"
        new_grade = conf_to_grade(combined)

        # Only report if we can upgrade
        if grade_to_conf(new_grade) > grade_to_conf(current_best_grade):
            sources_desc = ", ".join(f"{c['db']}#{c['id']}({c['grade'] or '?'})" for c in corrs[:5])
            deduction = {
                "type": "corroboration",
                "claim": claim_name,
                "sources_count": len(corrs),
                "databases": list(dbs_seen),
                "current_best_grade": current_best_grade,
                "combined_confidence": combined,
                "proposed_grade": new_grade,
                "sources": sources_desc,
                "reasoning": (
                    f"{len(corrs)} sources across {len(dbs_seen)} databases "
                    f"corroborate '{claim_name}'. Combined confidence: {combined:.2%}. "
                    f"Upgrade from {current_best_grade} → {new_grade} recommended."
                ),
            }
            deductions.append(deduction)

            # Store in DB
            try:
                ddb.execute("""
                    INSERT INTO deductions (deduction_type, conclusion, confidence, sources, reasoning, upgraded_grade)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, ("corroboration", claim_name, combined, sources_desc,
                      deduction["reasoning"], new_grade))
            except Exception:
                pass

    ddb.commit()
    return deductions

# ══════════════════════════════════════════════════════════════
# CONTRADICTION DETECTION
# ══════════════════════════════════════════════════════════════

def find_contradictions(ddb: sqlite3.Connection) -> List[dict]:
    """Detect conflicting information across compartments."""
    contradictions = []

    # Check for amount contradictions in pension data
    pension_hits = cross_search("pension alimentaire", limit_per_db=20)
    amounts_found = set()
    for db_name, hits in pension_hits.items():
        for hit in hits:
            content = (hit.get("content") or hit.get("ocr_text") or
                      hit.get("message") or "")
            # Extract EUR amounts
            for m in re.finditer(r'€\s?([\d,]+(?:\.\d+)?)', content):
                amt = m.group(1).replace(",", "")
                try:
                    val = float(amt)
                    if val > 10000:
                        amounts_found.add((val, db_name, str(hit.get("id", "?")), content[:100]))
                except ValueError:
                    pass

    if len(amounts_found) > 1:
        amts = sorted(amounts_found)
        for i in range(len(amts)):
            for j in range(i + 1, len(amts)):
                if amts[i][0] != amts[j][0]:
                    contradictions.append({
                        "claim_a": f"Pension = €{amts[i][0]:,.0f} (from {amts[i][1]}#{amts[i][2]})",
                        "claim_b": f"Pension = €{amts[j][0]:,.0f} (from {amts[j][1]}#{amts[j][2]})",
                        "severity": "low" if abs(amts[i][0] - amts[j][0]) < 1000 else "medium",
                        "note": "Pension amount changed over time (€85K→€32.5K in Jan 2024)"
                    })

    # Check BTC holdings contradictions
    btc_hits = cross_search("bitcoin btc holdings", limit_per_db=15)
    btc_amounts = set()
    for db_name, hits in btc_hits.items():
        for hit in hits:
            content = (hit.get("content") or hit.get("ocr_text") or hit.get("message") or "")
            for m in re.finditer(r'(\d+\.?\d*)\s*BTC', content):
                try:
                    val = float(m.group(1))
                    if val > 0.1:
                        btc_amounts.add((val, db_name, str(hit.get("id", "?"))))
                except ValueError:
                    pass

    if len(btc_amounts) > 1:
        for a in btc_amounts:
            for b in btc_amounts:
                if a[0] != b[0] and a[1] != b[1]:
                    contradictions.append({
                        "claim_a": f"BTC = {a[0]} (from {a[1]}#{a[2]})",
                        "claim_b": f"BTC = {b[0]} (from {b[1]}#{b[2]})",
                        "severity": "high",
                        "note": "BTC holdings unverified — seed phrase pending reconstruction"
                    })

    # Store contradictions
    for c in contradictions:
        try:
            ddb.execute("""
                INSERT INTO contradictions (claim_a, source_a, claim_b, source_b, severity, resolution)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (c["claim_a"], "", c["claim_b"], "", c["severity"], c.get("note", "")))
        except Exception:
            pass
    ddb.commit()

    return contradictions

# ══════════════════════════════════════════════════════════════
# FINANCIAL CHAIN TRACING
# ══════════════════════════════════════════════════════════════

def trace_financial_chain(entity: str, ddb: sqlite3.Connection) -> List[dict]:
    """Trace financial flows for an entity across all databases."""
    chain = []

    # Finance lake
    conn = get_db(DB_PATHS["finance"])
    if conn:
        try:
            rows = conn.execute("""
                SELECT * FROM transactions
                WHERE description LIKE ? OR counterparty LIKE ? OR notes LIKE ?
                ORDER BY date
            """, (f"%{entity}%", f"%{entity}%", f"%{entity}%")).fetchall()
            for r in rows:
                chain.append({
                    "source": "finance",
                    "date": r["date"] if "date" in r.keys() else "",
                    "amount": r["amount"] if "amount" in r.keys() else 0,
                    "description": r["description"] if "description" in r.keys() else "",
                    "type": "transaction",
                })
        except Exception:
            pass
        conn.close()

    # Crypto
    conn = get_db(DB_PATHS["crypto"])
    if conn:
        try:
            rows = conn.execute("""
                SELECT * FROM transactions
                WHERE notes LIKE ? OR from_address LIKE ? OR to_address LIKE ?
                ORDER BY timestamp
            """, (f"%{entity}%", f"%{entity}%", f"%{entity}%")).fetchall()
            for r in rows:
                chain.append({
                    "source": "crypto",
                    "date": r["timestamp"] if "timestamp" in r.keys() else "",
                    "amount": f"{r['amount']} {r['asset']}" if "amount" in r.keys() else "",
                    "description": r["notes"] if "notes" in r.keys() else "",
                    "type": "crypto_tx",
                })
        except Exception:
            pass
        conn.close()

    # OCR (invoices, receipts)
    ocr_hits = search_ocr(entity, limit=20)
    for hit in ocr_hits:
        text = hit.get("ocr_text", "")
        # Extract amounts from OCR text
        amounts = re.findall(r'(?:€|EUR|CHF|USD)\s?([\d,]+(?:\.\d{2})?)', text[:500])
        if amounts:
            chain.append({
                "source": "ocr",
                "date": "",
                "amount": ", ".join(amounts[:3]),
                "description": f"OCR document: {hit.get('filename', '?')}",
                "type": "document",
                "grade": hit.get("doc_grade", "?"),
            })

    # Sort by date where available
    chain.sort(key=lambda x: x.get("date", "9999"))

    return chain

# ══════════════════════════════════════════════════════════════
# CLI COMMANDS
# ══════════════════════════════════════════════════════════════

def cmd_audit(args):
    """Full compartment audit with gap analysis."""
    ddb = init_deduction_db()
    print("=" * 70)
    print("  DEDUCTION ENGINE — COMPARTMENTALIZATION AUDIT")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # 1. Database inventory
    print("\n  DATABASE INVENTORY")
    print("  " + "-" * 60)
    total_records = 0
    for name, path in DB_PATHS.items():
        if not path.exists():
            print(f"    {name:15s}  MISSING")
            continue
        size_mb = path.stat().st_size / (1024 * 1024)
        conn = get_db(path)
        if conn:
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '%fts%' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()]
            record_count = 0
            for tbl in tables:
                try:
                    cnt = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                    record_count += cnt
                except Exception:
                    pass
            total_records += record_count
            print(f"    {name:15s}  {size_mb:7.1f} MB  {record_count:>8,} records  ({len(tables)} tables)")
            conn.close()

    print(f"\n    TOTAL: {total_records:,} records across {len(DB_PATHS)} databases")

    # 2. Entity link scan
    print("\n  ENTITY CROSS-REFERENCE SCAN")
    print("  " + "-" * 60)
    print("    Scanning all databases for entity links... ", end="", flush=True)
    link_count = deduce_entity_links(ddb)
    print(f"{link_count:,} links found")

    # Entity summary
    rows = ddb.execute("""
        SELECT entity_key, entity_type, COUNT(DISTINCT source_db) as dbs,
               COUNT(*) as total, GROUP_CONCAT(DISTINCT source_db) as sources
        FROM entity_links GROUP BY entity_key
        ORDER BY dbs DESC, total DESC LIMIT 25
    """).fetchall()
    if rows:
        print(f"\n    {'Entity':<20s} {'Type':<12s} {'DBs':>4s} {'Refs':>6s}  Sources")
        print("    " + "-" * 68)
        for r in rows:
            print(f"    {r['entity_key']:<20s} {r['entity_type']:<12s} {r['dbs']:>4d} {r['total']:>6d}  {r['sources']}")

    # 3. Corroboration analysis
    print("\n  INTEL RECONSTRUCTION (corroboration analysis)")
    print("  " + "-" * 60)
    deductions = reconstruct_intel(ddb)
    if deductions:
        for d in deductions:
            arrow = f"{d['current_best_grade']} → {d['proposed_grade']}"
            print(f"    [{arrow}] {d['claim']}")
            print(f"           {d['sources_count']} sources across {len(d['databases'])} DBs "
                  f"| combined conf: {d['combined_confidence']:.1%}")
    else:
        print("    No grade upgrades possible from current corroborations.")

    # 4. Contradiction detection
    print("\n  CONTRADICTION DETECTION")
    print("  " + "-" * 60)
    contradictions = find_contradictions(ddb)
    if contradictions:
        for c in contradictions:
            sev = {"high": "\033[31m", "medium": "\033[33m", "low": "\033[36m"}.get(c["severity"], "")
            rst = "\033[0m"
            print(f"    {sev}[{c['severity'].upper()}]{rst} {c['claim_a']}")
            print(f"           vs {c['claim_b']}")
            if c.get("note"):
                print(f"           Note: {c['note']}")
    else:
        print("    No contradictions detected.")

    # 5. Gap analysis
    print("\n  INTELLIGENCE GAPS")
    print("  " + "-" * 60)
    gaps = analyze_gaps(ddb)
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    gaps.sort(key=lambda g: priority_order.get(g.get("priority", "medium"), 2))
    for g in gaps:
        prio = g.get("priority", "medium")
        color = {"critical": "\033[31;1m", "high": "\033[31m", "medium": "\033[33m", "low": "\033[36m"}.get(prio, "")
        rst = "\033[0m"
        print(f"    {color}[{prio.upper():>8s}]{rst} {g['description']}")
        if g.get("potential_sources"):
            print(f"              → {g['potential_sources']}")

    # 6. Summary
    total_links = ddb.execute("SELECT COUNT(*) FROM entity_links").fetchone()[0]
    total_deds = ddb.execute("SELECT COUNT(*) FROM deductions").fetchone()[0]
    total_gaps = ddb.execute("SELECT COUNT(*) FROM gaps WHERE status='open'").fetchone()[0]
    total_contras = ddb.execute("SELECT COUNT(*) FROM contradictions").fetchone()[0]

    print("\n  SUMMARY")
    print("  " + "-" * 60)
    print(f"    Entity links:     {total_links:>8,}")
    print(f"    Deductions:       {total_deds:>8,}")
    print(f"    Contradictions:   {total_contras:>8,}")
    print(f"    Open gaps:        {total_gaps:>8,}")

    ddb.close()

def cmd_corroborate(args):
    """Find corroborative chains for a specific claim."""
    if not args.query:
        print("Usage: deduction corroborate <query>")
        return
    query = " ".join(args.query)
    print(f"\n  CORROBORATION SEARCH: \"{query}\"")
    print("  " + "=" * 60)

    corrs = find_corroborations(query)
    if not corrs:
        print("  No corroborating sources found.")
        return

    # Group by database
    by_db = defaultdict(list)
    for c in corrs:
        by_db[c["db"]].append(c)

    all_confs = [c["confidence"] for c in corrs]
    combined = combined_confidence(all_confs[:15])

    for db_name, hits in sorted(by_db.items()):
        print(f"\n  [{db_name.upper()}] ({len(hits)} hits)")
        for h in hits[:5]:
            grade_str = f"[{h['grade']}]" if h['grade'] else "[?]"
            entities_str = ""
            if h["entities"]:
                ents = []
                for cat, keys in h["entities"].items():
                    ents.extend(keys)
                entities_str = f" → {', '.join(ents[:5])}"
            print(f"    {grade_str} #{h['id']} (conf: {h['confidence']:.0%}){entities_str}")
            if h["content"]:
                print(f"         {h['content'][:120]}...")

    print(f"\n  COMBINED CONFIDENCE: {combined:.1%} ({conf_to_grade(combined)}-equivalent)")
    print(f"  Sources: {len(corrs)} across {len(by_db)} databases")

def cmd_reconstruct(args):
    """Reconstruct intel from low-grade fragments."""
    ddb = init_deduction_db()
    print("\n  INTEL RECONSTRUCTION")
    print("  " + "=" * 60)
    deductions = reconstruct_intel(ddb)
    if deductions:
        for i, d in enumerate(deductions, 1):
            print(f"\n  {i}. {d['claim']}")
            print(f"     Current best: {d['current_best_grade']} → Proposed: {d['proposed_grade']}")
            print(f"     Combined confidence: {d['combined_confidence']:.1%}")
            print(f"     Sources: {d['sources_count']} across {', '.join(d['databases'])}")
            print(f"     Evidence: {d['sources'][:120]}")
    else:
        print("  No upgrades possible. All current grades match or exceed corroborative evidence.")
    ddb.close()

def cmd_contradictions(args):
    """Surface cross-compartment contradictions."""
    ddb = init_deduction_db()
    contradictions = find_contradictions(ddb)
    print(f"\n  CONTRADICTIONS DETECTED: {len(contradictions)}")
    print("  " + "=" * 60)
    for c in contradictions:
        print(f"\n  [{c['severity'].upper()}]")
        print(f"    A: {c['claim_a']}")
        print(f"    B: {c['claim_b']}")
        if c.get("note"):
            print(f"    Resolution: {c['note']}")
    ddb.close()

def cmd_gaps(args):
    """Identify intelligence gaps."""
    ddb = init_deduction_db()
    gaps = analyze_gaps(ddb)
    print(f"\n  INTELLIGENCE GAPS: {len(gaps)}")
    print("  " + "=" * 60)
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    gaps.sort(key=lambda g: priority_order.get(g.get("priority", "medium"), 2))
    for g in gaps:
        prio = g.get("priority", "medium")
        print(f"\n  [{prio.upper()}] ({g['type']})")
        print(f"    {g['description']}")
        if g.get("potential_sources"):
            print(f"    → {g['potential_sources']}")
    ddb.close()

def cmd_links(args):
    """Find hidden entity links across databases."""
    ddb = init_deduction_db()
    print("  Scanning for entity cross-references...", flush=True)
    link_count = deduce_entity_links(ddb)
    print(f"  {link_count:,} links processed\n")

    # Show entity network
    rows = ddb.execute("""
        SELECT entity_key, entity_type,
               COUNT(DISTINCT source_db) as dbs,
               COUNT(*) as total,
               GROUP_CONCAT(DISTINCT source_db) as sources
        FROM entity_links GROUP BY entity_key
        ORDER BY dbs DESC, total DESC
    """).fetchall()

    print(f"  ENTITY NETWORK ({len(rows)} entities)")
    print("  " + "=" * 60)
    print(f"  {'Entity':<20s} {'Type':<12s} {'DBs':>4s} {'Refs':>6s}  Sources")
    print("  " + "-" * 68)
    for r in rows:
        print(f"  {r['entity_key']:<20s} {r['entity_type']:<12s} {r['dbs']:>4d} {r['total']:>6d}  {r['sources']}")

    # Show cross-compartment links (entities appearing in 3+ databases)
    cross = [r for r in rows if r["dbs"] >= 3]
    if cross:
        print(f"\n  CROSS-COMPARTMENT ENTITIES ({len(cross)} spanning 3+ databases)")
        print("  " + "-" * 60)
        for r in cross:
            print(f"  ★ {r['entity_key']} ({r['entity_type']}): {r['sources']}")
            # Show sample references
            samples = ddb.execute("""
                SELECT source_db, source_table, source_id, context
                FROM entity_links WHERE entity_key = ?
                ORDER BY source_db LIMIT 10
            """, (r["entity_key"],)).fetchall()
            for s in samples:
                ctx = s["context"][:60] if s["context"] else ""
                print(f"      {s['source_db']}.{s['source_table']}#{s['source_id']} — {ctx}")

    ddb.close()

def cmd_timeline_fill(args):
    """Fill timeline gaps from lesser-classified sources."""
    print("\n  TIMELINE GAP FILL")
    print("  " + "=" * 60)

    # Get existing timeline from lake
    conn = get_db(DB_PATHS["lake"])
    if not conn:
        print("  Error: Memory lake not available.")
        return

    events = conn.execute("""
        SELECT id, content, created_at, doc_grade, tags
        FROM memories WHERE memory_type = 'event'
        ORDER BY created_at
    """).fetchall()
    conn.close()

    if not events:
        print("  No events in timeline.")
        return

    # Find date gaps
    dates = []
    for e in events:
        try:
            d = datetime.strptime(e["created_at"][:10], "%Y-%m-%d")
            dates.append(d)
        except (ValueError, TypeError):
            pass

    if len(dates) < 2:
        print("  Insufficient timeline data.")
        return

    dates.sort()
    gaps_found = []
    for i in range(len(dates) - 1):
        gap = (dates[i + 1] - dates[i]).days
        if gap > 14:
            gaps_found.append((dates[i], dates[i + 1], gap))

    print(f"  Timeline spans: {dates[0].date()} → {dates[-1].date()}")
    print(f"  Events: {len(events)} | Gaps > 14 days: {len(gaps_found)}")

    # For each gap, search WhatsApp and OCR for data in that period
    filled = 0
    for start, end, gap_days in gaps_found[:10]:
        print(f"\n  GAP: {start.date()} → {end.date()} ({gap_days} days)")

        # Check WhatsApp for messages in this period
        wa_conn = get_db(DB_PATHS["whatsapp"])
        if wa_conn:
            try:
                wa_count = wa_conn.execute("""
                    SELECT COUNT(*) FROM messages
                    WHERE timestamp BETWEEN ? AND ?
                """, (start.isoformat(), end.isoformat())).fetchone()[0]
                if wa_count > 0:
                    print(f"    ✓ WhatsApp: {wa_count} messages found in this period")
                    # Get sample messages with entity references
                    samples = wa_conn.execute("""
                        SELECT m.message, m.sender, m.timestamp, c.chat_name as name
                        FROM messages m JOIN chats c ON c.id = m.chat_id
                        WHERE m.timestamp BETWEEN ? AND ?
                        AND length(m.message) > 50
                        ORDER BY m.timestamp LIMIT 5
                    """, (start.isoformat(), end.isoformat())).fetchall()
                    for s in samples:
                        entities = detect_entities(s["message"])
                        if entities:
                            ents = []
                            for cat, keys in entities.items():
                                ents.extend(keys)
                            print(f"      [{s['timestamp'][:10]}] {s['name']}: ...{ents}...")
                            filled += 1
            except Exception:
                pass
            wa_conn.close()

        # Check OCR for documents from this period
        ocr_conn = get_db(DB_PATHS["ocr"])
        if ocr_conn:
            try:
                ocr_count = ocr_conn.execute("""
                    SELECT COUNT(*) FROM ocr_results
                    WHERE created_at BETWEEN ? AND ?
                """, (start.isoformat(), end.isoformat())).fetchone()[0]
                if ocr_count > 0:
                    print(f"    ✓ OCR: {ocr_count} documents from this period")
                    filled += 1
            except Exception:
                pass
            ocr_conn.close()

    print(f"\n  Potential timeline fills: {filled}")

def cmd_financial_chain(args):
    """Trace financial flows for an entity."""
    if not args.query:
        print("Usage: deduction financial-chain <entity>")
        return
    entity = " ".join(args.query)
    ddb = init_deduction_db()
    print(f"\n  FINANCIAL CHAIN TRACE: \"{entity}\"")
    print("  " + "=" * 60)
    chain = trace_financial_chain(entity, ddb)
    if chain:
        total_eur = 0
        for c in chain:
            date_str = c.get("date", "?")[:10] if c.get("date") else "?"
            amt = c.get("amount", "?")
            grade_str = f" [{c.get('grade', '')}]" if c.get("grade") else ""
            print(f"  [{date_str}] {c['source']:8s} {c['type']:12s} {amt}{grade_str}")
            if c.get("description"):
                print(f"            {c['description'][:80]}")
            # Sum EUR amounts
            if isinstance(amt, (int, float)):
                total_eur += amt
        print(f"\n  Total chain entries: {len(chain)}")
        if total_eur:
            print(f"  Sum of numeric amounts: €{total_eur:,.2f}")
    else:
        print(f"  No financial records found for '{entity}'.")
    ddb.close()

def cmd_upgrade(args):
    """Auto-upgrade grades where corroboration exists."""
    ddb = init_deduction_db()
    deductions = reconstruct_intel(ddb)
    if not deductions:
        print("  No upgrades available.")
        ddb.close()
        return

    print(f"\n  GRADE UPGRADE CANDIDATES: {len(deductions)}")
    print("  " + "=" * 60)
    for d in deductions:
        print(f"  {d['claim']}: {d['current_best_grade']} → {d['proposed_grade']} "
              f"(conf: {d['combined_confidence']:.1%}, {d['sources_count']} sources)")

    print("\n  Note: Run `doc-grade upgrade <id> <grade>` to apply specific upgrades.")
    ddb.close()

def cmd_stats(args):
    """Deduction engine statistics."""
    ddb = init_deduction_db()
    print("\n  DEDUCTION ENGINE STATISTICS")
    print("  " + "=" * 60)

    stats = {
        "Entity links": ddb.execute("SELECT COUNT(*) FROM entity_links").fetchone()[0],
        "Unique entities": ddb.execute("SELECT COUNT(DISTINCT entity_key) FROM entity_links").fetchone()[0],
        "Cross-DB entities": ddb.execute(
            "SELECT COUNT(*) FROM (SELECT entity_key FROM entity_links GROUP BY entity_key HAVING COUNT(DISTINCT source_db) >= 2)"
        ).fetchone()[0],
        "Deductions": ddb.execute("SELECT COUNT(*) FROM deductions").fetchone()[0],
        "Contradictions": ddb.execute("SELECT COUNT(*) FROM contradictions").fetchone()[0],
        "Open gaps": ddb.execute("SELECT COUNT(*) FROM gaps WHERE status='open'").fetchone()[0],
        "Corroborations": ddb.execute("SELECT COUNT(*) FROM corroborations").fetchone()[0],
    }

    for k, v in stats.items():
        print(f"    {k:<25s} {v:>8,}")

    # Per-entity type
    print("\n  Entity types:")
    rows = ddb.execute("""
        SELECT entity_type, COUNT(DISTINCT entity_key) as entities, COUNT(*) as refs
        FROM entity_links GROUP BY entity_type ORDER BY refs DESC
    """).fetchall()
    for r in rows:
        print(f"    {r['entity_type']:<15s} {r['entities']:>4d} entities, {r['refs']:>6d} refs")

    ddb.close()

# ══════════════════════════════════════════════════════════════
# BELL-LAPADULA MODEL
# ══════════════════════════════════════════════════════════════

# BLP Levels (maps to data_classification.py Level enum)
BLP_LEVELS = {
    "PUBLIC":       0,
    "UNCLASSIFIED": 1,
    "OFFICIAL":     2,
    "RESTRICTED":   3,
    "CONFIDENTIAL": 4,
    "SECRET":       5,
    "TOP SECRET":   6,
    "TS/SCI":       7,
    "EYES ONLY":    8,
    "BURN ON READ": 9,
}

def blp_high_water_mark(sources: List[dict]) -> int:
    """Bell-LaPadula HIGH WATER MARK: combined intel inherits highest
    classification of any contributing source."""
    max_level = 0
    for s in sources:
        cls = s.get("cls_level") or s.get("cls_label", "")
        if isinstance(cls, int):
            max_level = max(max_level, cls)
        elif isinstance(cls, str) and cls in BLP_LEVELS:
            max_level = max(max_level, BLP_LEVELS[cls])
    return max_level

def blp_can_read(subject_level: int, object_level: int) -> bool:
    """Simple Security Property: no read-up."""
    return subject_level >= object_level

def blp_can_write(subject_level: int, object_level: int) -> bool:
    """Star Property: no write-down."""
    return subject_level <= object_level

def cmd_blp_check(args):
    """Bell-LaPadula compliance audit across all compartments."""
    print("\n  BELL-LAPADULA COMPLIANCE AUDIT")
    print("  " + "=" * 70)

    violations = []
    level_dist = defaultdict(int)

    for db_name, db_path in DB_PATHS.items():
        conn = get_db(db_path)
        if not conn:
            continue
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '%fts%'"
        ).fetchall()]
        for tbl in tables:
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({tbl})").fetchall()]
            if "cls_level" in cols:
                try:
                    rows = conn.execute(f"""
                        SELECT cls_level, cls_label, COUNT(*) as cnt
                        FROM {tbl} WHERE cls_level IS NOT NULL
                        GROUP BY cls_level, cls_label ORDER BY cls_level
                    """).fetchall()
                    for r in rows:
                        lvl = r[0] or 0
                        lbl = r[1] or f"L{lvl}"
                        level_dist[f"{db_name}.{tbl} [{lbl}]"] += r[2]
                except Exception:
                    pass

            # Check for data at wrong classification
            if "doc_grade" in cols and "cls_level" in cols:
                try:
                    # Items with high doc_grade but low classification
                    mismatches = conn.execute(f"""
                        SELECT id, doc_grade, cls_level, cls_label
                        FROM {tbl}
                        WHERE doc_grade IN ('S', 'A') AND (cls_level IS NULL OR cls_level <= 2)
                        LIMIT 20
                    """).fetchall()
                    for m in mismatches:
                        violations.append({
                            "type": "UNDERCLASSIFIED",
                            "db": db_name, "table": tbl,
                            "id": m[0],
                            "detail": f"Grade {m[1]} (high-confidence evidence) at level {m[2] or 'NULL'} ({m[3] or 'NONE'})",
                        })
                except Exception:
                    pass
        conn.close()

    # Report
    print("\n  Classification Distribution:")
    for k, v in sorted(level_dist.items()):
        print(f"    {k:<50s} {v:>6d}")

    if violations:
        print(f"\n  BLP VIOLATIONS: {len(violations)}")
        print("  " + "-" * 60)
        for v in violations[:30]:
            print(f"    [{v['type']}] {v['db']}.{v['table']}#{v['id']}: {v['detail']}")
    else:
        print("\n  No BLP violations detected.")

    # Compartmentalization summary
    print("\n  COMPARTMENT BOUNDARIES:")
    print("  " + "-" * 60)
    compartments = {
        "LEGAL":    ["legal", "legal_ant", "police"],
        "FINANCIAL": ["finance", "crypto"],
        "COMMS":    ["whatsapp"],
        "INTEL":    ["lake", "ocr", "doc"],
        "PSYCH":    ["psych"],
    }
    for comp_name, dbs in compartments.items():
        total = 0
        max_lvl = 0
        for db_name in dbs:
            conn = get_db(DB_PATHS.get(db_name, Path("/dev/null")))
            if not conn:
                continue
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '%fts%' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()]
            for tbl in tables:
                try:
                    cnt = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                    total += cnt
                    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({tbl})").fetchall()]
                    if "cls_level" in cols:
                        mx = conn.execute(f"SELECT MAX(cls_level) FROM {tbl}").fetchone()[0]
                        if mx and mx > max_lvl:
                            max_lvl = mx
                except Exception:
                    pass
            conn.close()
        lvl_name = [k for k, v in BLP_LEVELS.items() if v == max_lvl]
        lvl_str = lvl_name[0] if lvl_name else f"L{max_lvl}"
        print(f"    {comp_name:<12s}  {total:>8,} records  ceiling: {lvl_str}  DBs: {', '.join(dbs)}")

# ══════════════════════════════════════════════════════════════
# OODA LOOP (Observe-Orient-Decide-Act)
# ══════════════════════════════════════════════════════════════

def cmd_ooda(args):
    """Run full OODA cycle on a specific topic."""
    if not args.query:
        print("Usage: deduction ooda <topic>")
        print("  Example: deduction ooda 'pension recovery'")
        return

    topic = " ".join(args.query)
    ddb = init_deduction_db()

    print("=" * 70)
    print(f"  OODA LOOP — {topic.upper()}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # ── OBSERVE ──────────────────────────────────────────────
    print("\n  ╔══════════════════════════════════════════════════╗")
    print("  ║  OBSERVE — Sensor Sweep                         ║")
    print("  ╚══════════════════════════════════════════════════╝")

    all_hits = cross_search(topic, limit_per_db=30)
    total_hits = sum(len(v) for v in all_hits.values())
    print(f"  Total sensor returns: {total_hits} across {len(all_hits)} databases")

    for db_name, hits in sorted(all_hits.items(), key=lambda x: -len(x[1])):
        print(f"    {db_name:<12s}  {len(hits):>4d} hits")

    # Collect all content for analysis
    all_content = []
    all_entities = defaultdict(int)
    source_levels = []
    for db_name, hits in all_hits.items():
        for h in hits:
            content = (h.get("content") or h.get("ocr_text") or
                      h.get("message") or h.get("content_preview") or "")
            all_content.append(content)
            entities = detect_entities(content)
            for cat, keys in entities.items():
                for k in keys:
                    all_entities[k] += 1
            # Track BLP levels
            cls = h.get("cls_level")
            if cls:
                source_levels.append({"cls_level": cls})

    # ── ORIENT ───────────────────────────────────────────────
    print("\n  ╔══════════════════════════════════════════════════╗")
    print("  ║  ORIENT — Situational Awareness                 ║")
    print("  ╚══════════════════════════════════════════════════╝")

    # Entity frequency analysis
    print("  Entity frequency in sensor returns:")
    for entity, count in sorted(all_entities.items(), key=lambda x: -x[1])[:15]:
        bar = "█" * min(count, 40)
        print(f"    {entity:<20s} {count:>4d}  {bar}")

    # High water mark
    hwm = blp_high_water_mark(source_levels) if source_levels else 0
    hwm_name = [k for k, v in BLP_LEVELS.items() if v == hwm]
    hwm_str = hwm_name[0] if hwm_name else f"L{hwm}"
    print(f"\n  Bell-LaPadula HIGH WATER MARK: {hwm_str} (level {hwm})")
    print(f"  → All deductions from this OODA cycle inherit ceiling: {hwm_str}")

    # Corroboration analysis
    corrs = find_corroborations(topic)
    confs = [c["confidence"] for c in corrs]
    combined = combined_confidence(confs[:15])
    grade_eq = conf_to_grade(combined)

    print(f"\n  Corroboration: {len(corrs)} sources → combined confidence {combined:.1%} ({grade_eq})")

    # Database diversity (higher = more reliable)
    db_diversity = len(set(c["db"] for c in corrs))
    diversity_score = min(1.0, db_diversity / 5)
    print(f"  Database diversity: {db_diversity}/5 ({diversity_score:.0%})")

    # Temporal spread
    timestamps = [c["timestamp"] for c in corrs if c["timestamp"]]
    if timestamps:
        ts_sorted = sorted(timestamps)
        print(f"  Temporal range: {ts_sorted[0][:10]} → {ts_sorted[-1][:10]}")

    # ── DECIDE ───────────────────────────────────────────────
    print("\n  ╔══════════════════════════════════════════════════╗")
    print("  ║  DECIDE — Intelligence Assessment               ║")
    print("  ╚══════════════════════════════════════════════════╝")

    # Confidence tier
    if combined >= 0.90:
        assessment = "HIGH CONFIDENCE — Multiple corroborating sources across databases"
        color = "\033[32m"
    elif combined >= 0.70:
        assessment = "MODERATE CONFIDENCE — Corroborated but limited database diversity"
        color = "\033[33m"
    elif combined >= 0.50:
        assessment = "LOW CONFIDENCE — Partially corroborated, gaps remain"
        color = "\033[33;1m"
    else:
        assessment = "UNCONFIRMED — Insufficient corroboration"
        color = "\033[31m"

    print(f"  {color}Assessment: {assessment}\033[0m")
    print(f"  Combined confidence: {combined:.1%}")
    print(f"  Equivalent grade: {grade_eq}")
    print(f"  Classification ceiling: {hwm_str}")

    # Identify what we know vs what we don't
    # Known facts (high-confidence items)
    known = [c for c in corrs if c["confidence"] >= 0.7]
    unknown_gaps = []

    # Check what related entities we DON'T have data on
    topic_entities = detect_entities(topic)
    for cat, keys in topic_entities.items():
        for key in keys:
            entity_refs = ddb.execute("""
                SELECT COUNT(DISTINCT source_db) FROM entity_links WHERE entity_key = ?
            """, (key,)).fetchone()[0]
            if entity_refs < 2:
                unknown_gaps.append(f"Entity '{key}' only in {entity_refs} database(s)")

    if unknown_gaps:
        print(f"\n  Knowledge gaps:")
        for g in unknown_gaps:
            print(f"    ⚠ {g}")

    # Decision matrix
    print(f"\n  Decision matrix:")
    print(f"    Sources:     {total_hits}")
    print(f"    Confidence:  {combined:.1%}")
    print(f"    Diversity:   {diversity_score:.0%}")
    print(f"    Known facts: {len(known)}")
    print(f"    Gaps:        {len(unknown_gaps)}")

    # ── ACT ──────────────────────────────────────────────────
    print("\n  ╔══════════════════════════════════════════════════╗")
    print("  ║  ACT — Recommended Actions                      ║")
    print("  ╚══════════════════════════════════════════════════╝")

    actions = []
    if len(unknown_gaps) > 0:
        actions.append("COLLECT: Fill intelligence gaps — " + "; ".join(unknown_gaps[:3]))
    if combined < 0.70:
        actions.append("VERIFY: Seek additional corroboration from independent sources")
    if db_diversity < 3:
        actions.append("DIVERSIFY: Cross-reference with additional databases "
                       f"(currently {db_diversity})")

    # Check for grade upgrades
    low_grade_sources = [c for c in corrs if c["grade"] in ("D", "E")]
    if low_grade_sources and combined >= 0.60:
        actions.append(f"UPGRADE: {len(low_grade_sources)} low-grade sources can be upgraded "
                       f"(combined conf {combined:.1%})")

    # Always recommend next OODA cycle
    actions.append("LOOP: Schedule next OODA cycle to track changes")

    for i, action in enumerate(actions, 1):
        phase = action.split(":")[0]
        detail = action[len(phase) + 1:].strip()
        print(f"  {i}. [{phase}] {detail}")

    # Store OODA result as deduction
    try:
        ddb.execute("""
            INSERT INTO deductions (deduction_type, conclusion, confidence, sources, reasoning)
            VALUES (?, ?, ?, ?, ?)
        """, ("ooda_cycle", f"OODA: {topic}",
              combined,
              json.dumps({"dbs": list(all_hits.keys()), "hits": total_hits, "entities": dict(list(all_entities.items())[:10])}),
              f"OODA cycle: {total_hits} sources, {combined:.1%} confidence, "
              f"{db_diversity} database diversity, ceiling {hwm_str}"))
        ddb.commit()
    except Exception:
        pass

    ddb.close()

# ══════════════════════════════════════════════════════════════
# C4ISR SENSOR FUSION
# ══════════════════════════════════════════════════════════════

def cmd_fusion(args):
    """C4ISR sensor fusion report — unified intelligence picture across all sensors."""
    print("=" * 70)
    print("  C4ISR SENSOR FUSION REPORT")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # Sensor inventory
    sensors = {}
    total_records = 0

    print("\n  SENSOR INVENTORY (Intelligence, Surveillance, Reconnaissance)")
    print("  " + "-" * 60)

    sensor_types = {
        "lake":      ("HUMINT/SIGINT",  "Memory lake — fused intelligence store"),
        "ocr":       ("IMINT",          "OCR data sea — document imagery intelligence"),
        "whatsapp":  ("SIGINT",         "WhatsApp SIGINT — communications intelligence"),
        "crypto":    ("FININT",         "Crypto forensics — financial intelligence"),
        "finance":   ("FININT",         "Finance lake — fiscal intelligence"),
        "doc":       ("DOCINT",         "Document index — document intelligence"),
        "psych":     ("PSYINT",         "Psych engine — psychological intelligence"),
        "legal":     ("LEGINT",         "Legal engine — legal intelligence"),
        "legal_ant": ("LEGINT",         "Legal anticipation — predictive legal intel"),
        "police":    ("LAWINT",         "Police cooperation — law enforcement intel"),
    }

    for db_name, (int_type, description) in sensor_types.items():
        path = DB_PATHS.get(db_name)
        if not path or not path.exists():
            continue
        conn = get_db(path)
        if not conn:
            continue
        count = 0
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '%fts%' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()]
        for tbl in tables:
            try:
                cnt = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                count += cnt
            except Exception:
                pass
        total_records += count
        sensors[db_name] = count
        status = "\033[32mONLINE\033[0m" if count > 0 else "\033[31mOFFLINE\033[0m"
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"    {int_type:<8s}  {db_name:<12s}  {count:>8,} records  {size_mb:>7.1f} MB  {status}")
        conn.close()

    print(f"\n    TOTAL SENSOR RECORDS: {total_records:,}")

    # Entity fusion — how many entities appear across how many sensors
    ddb = init_deduction_db()
    deduce_entity_links(ddb)

    print("\n  ENTITY FUSION MATRIX")
    print("  " + "-" * 60)

    rows = ddb.execute("""
        SELECT entity_key, entity_type,
               COUNT(DISTINCT source_db) as sensor_count,
               COUNT(*) as total_refs,
               GROUP_CONCAT(DISTINCT source_db) as sensors
        FROM entity_links
        GROUP BY entity_key
        HAVING sensor_count >= 2
        ORDER BY sensor_count DESC, total_refs DESC
    """).fetchall()

    print(f"  {'Entity':<20s} {'Type':<12s} {'Sensors':>7s} {'Refs':>6s}  Sensor Mix")
    print("  " + "-" * 68)
    for r in rows:
        print(f"  {r['entity_key']:<20s} {r['entity_type']:<12s} {r['sensor_count']:>7d} {r['total_refs']:>6d}  {r['sensors']}")

    # Intelligence gaps by sensor type
    print("\n  SENSOR COVERAGE GAPS")
    print("  " + "-" * 60)
    critical_entities = ["marina", "hadrien", "pension", "btc", "custody", "escroquerie", "hague"]
    for entity in critical_entities:
        present = ddb.execute("""
            SELECT GROUP_CONCAT(DISTINCT source_db) FROM entity_links WHERE entity_key = ?
        """, (entity,)).fetchone()
        present_dbs = set((present[0] or "").split(",")) if present and present[0] else set()
        all_dbs = set(DB_PATHS.keys())
        missing = all_dbs - present_dbs - {"legal", "legal_ant", "police"}  # Legal DBs are structural
        if missing:
            print(f"    {entity:<20s}  present: {', '.join(sorted(present_dbs)[:5])}")
            print(f"    {'':20s}  MISSING: {', '.join(sorted(missing))}")

    # Classification waterfall
    print("\n  CLASSIFICATION WATERFALL (Bell-LaPadula)")
    print("  " + "-" * 60)
    for db_name, db_path in DB_PATHS.items():
        conn = get_db(db_path)
        if not conn:
            continue
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '%fts%'"
        ).fetchall()]
        for tbl in tables:
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({tbl})").fetchall()]
            if "cls_level" in cols:
                try:
                    dist = conn.execute(f"""
                        SELECT cls_label, COUNT(*) as cnt FROM {tbl}
                        WHERE cls_label IS NOT NULL
                        GROUP BY cls_label ORDER BY cls_level DESC
                    """).fetchall()
                    if dist:
                        dist_str = " | ".join(f"{r[0]}:{r[1]}" for r in dist)
                        print(f"    {db_name}.{tbl}: {dist_str}")
                except Exception:
                    pass
        conn.close()

    ddb.close()

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

COMMANDS = {
    "audit": cmd_audit,
    "corroborate": cmd_corroborate,
    "reconstruct": cmd_reconstruct,
    "contradictions": cmd_contradictions,
    "gaps": cmd_gaps,
    "upgrade": cmd_upgrade,
    "links": cmd_links,
    "timeline-fill": cmd_timeline_fill,
    "financial-chain": cmd_financial_chain,
    "ooda": cmd_ooda,
    "blp-check": cmd_blp_check,
    "fusion": cmd_fusion,
    "stats": cmd_stats,
}

def main():
    parser = argparse.ArgumentParser(
        description="Deduction Engine — Cross-compartment intel reconstruction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("command", choices=list(COMMANDS.keys()),
                        help="Command to execute")
    parser.add_argument("query", nargs="*", help="Query/arguments")

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    COMMANDS[args.command](args)

if __name__ == "__main__":
    main()
