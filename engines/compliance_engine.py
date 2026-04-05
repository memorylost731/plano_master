#!/usr/bin/env python3
"""Compliance Tolerance Engine — Multi-Jurisdiction Institutional Margin Management.

Models the real gap between strict legal obligations and enforcement reality.
Prevents minor deviations from accumulating into actionable patterns.
Enforces a hard two-track strategy:

  FISCAL TRACK:     Prove innocence. Zero tolerance. Full transparency.
  NON-FISCAL TRACK: Right to silence (Art. 6 ECHR). Minimum disclosure.

A firewall between tracks prevents fiscal disclosures from leaking into
criminal/civil domains.

Core algorithms:
  - Cumulation scoring with exponential decay, institution aggressiveness
  - Tolerance margin (strict law vs enforcement reality)
  - Probation modifier (Oct 2025 – 2028): margins halved, weights doubled
  - Early warning: deadlines, CRS windows, cumulation thresholds
  - Audit simulation: "what if DGFiP audits tomorrow?"

Jurisdictions: MC, MT, FR, CH, LI, GB, AE, KN, RU, IT, SM, INTL

Usage:
  comply init                                    Initialize + seed
  comply obligations [--jurisdiction] [--domain] [--track] [--status]
  comply status [--obligation-ref REF]           Compliance matrix
  comply assess <ref> <status> [--deviation] [--notes]
  comply cumulation [--institution CODE]         Heat map
  comply institutions [--code CODE]              Institution profiles
  comply mitigate [--list|--add|--update|--complete]
  comply firewall [--check|--log|--approve|--block]
  comply audit [--simulate INST_CODE]            Audit trail + simulation
  comply dashboard                               Full overview
  comply alerts [--ack ID|--resolve ID]
  comply search <query>                          FTS5 search
  comply stats
  comply export [dir]
"""

import argparse
import hashlib
import json
import math
import os
import sqlite3
import sys
import textwrap
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
COMPLY_DB = SCRIPT_DIR / "compliance_engine.db"

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

# ── Alert Levels ───────────────────────────────────────────────────────────
ALERT_LEVELS = {
    "safe":     (f"{C.GREEN}●{C.RST}",     "SAFE"),
    "watch":    (f"{C.BLUE}●{C.RST}",      "WATCH"),
    "warning":  (f"{C.YELLOW}●{C.RST}",    "WARNING"),
    "danger":   (f"{C.RED}●{C.RST}",       "DANGER"),
    "critical": (f"{C.BG_RED}{C.WHITE}●{C.RST}", "CRITICAL"),
}

TRACK_BADGES = {
    "fiscal":     f"{C.CYAN}[FISCAL]{C.RST}",
    "non_fiscal": f"{C.MAGENTA}[NON-FISCAL]{C.RST}",
}

STATUS_BADGES = {
    "compliant":     f"{C.GREEN}✓ Compliant{C.RST}",
    "marginal":      f"{C.YELLOW}⚠ Marginal{C.RST}",
    "non_compliant": f"{C.RED}✗ Non-Compliant{C.RST}",
    "unknown":       f"{C.DIM}? Unknown{C.RST}",
}

# ── Probation Window ──────────────────────────────────────────────────────
PROBATION_START = date(2025, 10, 1)
PROBATION_END = date(2028, 10, 1)

def is_probation(d: Optional[date] = None) -> bool:
    d = d or date.today()
    return PROBATION_START <= d <= PROBATION_END

# ── Database ──────────────────────────────────────────────────────────────
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(COMPLY_DB))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS obligations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ref TEXT UNIQUE NOT NULL,
        jurisdiction TEXT NOT NULL,
        domain TEXT NOT NULL,
        track TEXT NOT NULL CHECK(track IN ('fiscal','non_fiscal')),
        title TEXT NOT NULL,
        description TEXT,
        legal_basis TEXT,
        tolerance_pct REAL NOT NULL DEFAULT 0.0,
        strict_threshold TEXT,
        enforced_threshold TEXT,
        deadline TEXT,
        recurrence TEXT,
        cls_level INTEGER DEFAULT 3,
        cls_label TEXT DEFAULT 'RESTRICTED',
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS compliance_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        obligation_ref TEXT NOT NULL REFERENCES obligations(ref),
        status TEXT NOT NULL CHECK(status IN ('compliant','marginal','non_compliant','unknown')),
        deviation_pct REAL DEFAULT 0.0,
        notes TEXT,
        assessed_at TEXT DEFAULT (datetime('now')),
        assessed_by TEXT DEFAULT 'system',
        cls_level INTEGER DEFAULT 4,
        cls_label TEXT DEFAULT 'CONFIDENTIAL'
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS institutions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        country TEXT NOT NULL,
        domain TEXT NOT NULL,
        aggressiveness REAL NOT NULL DEFAULT 1.0,
        threshold REAL NOT NULL DEFAULT 5.0,
        info_sharing TEXT,
        trigger_patterns TEXT,
        notes TEXT,
        cls_level INTEGER DEFAULT 3,
        cls_label TEXT DEFAULT 'RESTRICTED'
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS cumulation_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        institution_code TEXT NOT NULL REFERENCES institutions(code),
        obligation_ref TEXT REFERENCES obligations(ref),
        description TEXT NOT NULL,
        severity REAL NOT NULL DEFAULT 1.0,
        weight REAL NOT NULL DEFAULT 1.0,
        known_to_institution INTEGER NOT NULL DEFAULT 0,
        occurred_at TEXT NOT NULL,
        decay_rate REAL NOT NULL DEFAULT 0.05,
        notes TEXT,
        cls_level INTEGER DEFAULT 5,
        cls_label TEXT DEFAULT 'SECRET'
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS cumulation_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        institution_code TEXT UNIQUE NOT NULL REFERENCES institutions(code),
        score REAL NOT NULL DEFAULT 0.0,
        threshold REAL NOT NULL,
        headroom REAL NOT NULL,
        alert_level TEXT NOT NULL DEFAULT 'safe',
        computed_at TEXT DEFAULT (datetime('now')),
        cls_level INTEGER DEFAULT 4,
        cls_label TEXT DEFAULT 'CONFIDENTIAL'
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS firewall_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        direction TEXT NOT NULL,
        source_track TEXT NOT NULL,
        target_track TEXT NOT NULL,
        description TEXT NOT NULL,
        blocked INTEGER NOT NULL DEFAULT 1,
        approved_by TEXT,
        approved_at TEXT,
        logged_at TEXT DEFAULT (datetime('now')),
        cls_level INTEGER DEFAULT 5,
        cls_label TEXT DEFAULT 'SECRET'
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS mitigation_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        obligation_ref TEXT REFERENCES obligations(ref),
        institution_code TEXT REFERENCES institutions(code),
        title TEXT NOT NULL,
        description TEXT,
        priority TEXT NOT NULL DEFAULT 'medium' CHECK(priority IN ('critical','high','medium','low')),
        status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','in_progress','completed','blocked')),
        deadline TEXT,
        dependencies TEXT,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        completed_at TEXT,
        cls_level INTEGER DEFAULT 4,
        cls_label TEXT DEFAULT 'CONFIDENTIAL'
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        severity TEXT NOT NULL DEFAULT 'warning',
        title TEXT NOT NULL,
        description TEXT,
        obligation_ref TEXT,
        institution_code TEXT,
        acknowledged INTEGER NOT NULL DEFAULT 0,
        resolved INTEGER NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        resolved_at TEXT,
        cls_level INTEGER DEFAULT 4,
        cls_label TEXT DEFAULT 'CONFIDENTIAL'
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS information_flows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_institution TEXT NOT NULL,
        target_institution TEXT NOT NULL,
        mechanism TEXT NOT NULL,
        direction TEXT NOT NULL DEFAULT 'unidirectional',
        frequency TEXT,
        data_types TEXT,
        confirmed INTEGER NOT NULL DEFAULT 1,
        notes TEXT,
        cls_level INTEGER DEFAULT 3,
        cls_label TEXT DEFAULT 'RESTRICTED'
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS audit_trail (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        table_name TEXT NOT NULL,
        record_id INTEGER,
        details TEXT,
        prev_hash TEXT,
        entry_hash TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        cls_level INTEGER DEFAULT 3,
        cls_label TEXT DEFAULT 'RESTRICTED'
    )""")

    c.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS comply_fts USING fts5(
        ref, title, description, legal_basis, domain, jurisdiction,
        content='obligations', content_rowid='id',
        tokenize='porter unicode61'
    )""")

    c.execute("""CREATE TRIGGER IF NOT EXISTS obligations_ai AFTER INSERT ON obligations BEGIN
        INSERT INTO comply_fts(rowid, ref, title, description, legal_basis, domain, jurisdiction)
        VALUES (new.id, new.ref, new.title, new.description, new.legal_basis, new.domain, new.jurisdiction);
    END""")
    c.execute("""CREATE TRIGGER IF NOT EXISTS obligations_ad AFTER DELETE ON obligations BEGIN
        INSERT INTO comply_fts(comply_fts, rowid, ref, title, description, legal_basis, domain, jurisdiction)
        VALUES ('delete', old.id, old.ref, old.title, old.description, old.legal_basis, old.domain, old.jurisdiction);
    END""")
    c.execute("""CREATE TRIGGER IF NOT EXISTS obligations_au AFTER UPDATE ON obligations BEGIN
        INSERT INTO comply_fts(comply_fts, rowid, ref, title, description, legal_basis, domain, jurisdiction)
        VALUES ('delete', old.id, old.ref, old.title, old.description, old.legal_basis, old.domain, old.jurisdiction);
        INSERT INTO comply_fts(rowid, ref, title, description, legal_basis, domain, jurisdiction)
        VALUES (new.id, new.ref, new.title, new.description, new.legal_basis, new.domain, new.jurisdiction);
    END""")

    conn.commit()
    print(f"  {C.GREEN}✓{C.RST} Database initialized: {COMPLY_DB}")
    return conn


# ── Audit Trail (Hash Chain) ──────────────────────────────────────────────
def audit_log(conn: sqlite3.Connection, action: str, table: str, record_id: int = None, details: str = None):
    last = conn.execute("SELECT entry_hash FROM audit_trail ORDER BY id DESC LIMIT 1").fetchone()
    prev_hash = last["entry_hash"] if last else "GENESIS"
    payload = f"{prev_hash}|{action}|{table}|{record_id}|{details}|{datetime.now().isoformat()}"
    entry_hash = hashlib.sha256(payload.encode()).hexdigest()[:32]
    conn.execute(
        "INSERT INTO audit_trail (action, table_name, record_id, details, prev_hash, entry_hash) VALUES (?,?,?,?,?,?)",
        (action, table, record_id, details, prev_hash, entry_hash),
    )


# ── Seed Data ─────────────────────────────────────────────────────────────
SEED_OBLIGATIONS = [
    # ── FISCAL TRACK (0% tolerance) ────────────────────────────────────
    {"ref": "FR-FISC-001", "jurisdiction": "FR", "domain": "tax", "track": "fiscal",
     "title": "IRPP declaration (if FR resident)", "description": "Annual income tax return — declaration of worldwide income if French tax resident (Art. 4 B CGI).",
     "legal_basis": "Art. 4 B CGI, Art. 170 CGI", "tolerance_pct": 0.0,
     "deadline": "2026-05-31", "recurrence": "annual"},
    {"ref": "FR-FISC-002", "jurisdiction": "FR", "domain": "tax", "track": "fiscal",
     "title": "Foreign account declaration (Cerfa 3916)", "description": "Declaration of all foreign bank accounts, crypto platforms, trusts.",
     "legal_basis": "Art. 1649 A CGI", "tolerance_pct": 0.0,
     "deadline": "2026-05-31", "recurrence": "annual"},
    {"ref": "FR-FISC-003", "jurisdiction": "FR", "domain": "tax", "track": "fiscal",
     "title": "Crypto platform declaration (3916-bis)", "description": "Declaration of accounts on crypto exchanges (Kraken, Binance, etc.).",
     "legal_basis": "Art. 1649 bis C CGI", "tolerance_pct": 0.0,
     "deadline": "2026-05-31", "recurrence": "annual"},
    {"ref": "FR-FISC-004", "jurisdiction": "FR", "domain": "crs", "track": "fiscal",
     "title": "CRS address correction — Bank Frick & N26", "description": "CRITICAL: Bank Frick (LI) and N26 (DE) report French address via CRS→FR. Must change to Monaco address ASAP.",
     "legal_basis": "CRS (OECD), Dir. 2011/16/EU (DAC)", "tolerance_pct": 0.0,
     "strict_threshold": "Correct address immediately", "enforced_threshold": "Before next CRS exchange (Sep 2026)"},
    {"ref": "MT-FISC-001", "jurisdiction": "MT", "domain": "tax", "track": "fiscal",
     "title": "Malta tax return", "description": "Annual income tax return if Malta tax resident.",
     "legal_basis": "Income Tax Act Cap. 123", "tolerance_pct": 0.0,
     "deadline": "2026-06-30", "recurrence": "annual"},
    {"ref": "CH-FISC-001", "jurisdiction": "CH", "domain": "tax", "track": "fiscal",
     "title": "Julius Baer sequestre disclosure", "description": "Full disclosure of sequestrated assets. Already known via CH→FR CRS.",
     "legal_basis": "LBA Art. 9, CRS CH-FR", "tolerance_pct": 0.0},
    {"ref": "FR-FISC-005", "jurisdiction": "FR", "domain": "vat", "track": "fiscal",
     "title": "VAT registration & returns (if applicable)", "description": "French VAT obligations if conducting taxable activities in France. Late/incorrect returns trigger automatic penalties (10-80%).",
     "legal_basis": "Art. 256-293 CGI, Art. 1727-1729 CGI", "tolerance_pct": 0.0,
     "strict_threshold": "Monthly/quarterly returns + payment", "enforced_threshold": "Penalties from first missed return",
     "recurrence": "monthly"},
    {"ref": "MT-FISC-002", "jurisdiction": "MT", "domain": "vat", "track": "fiscal",
     "title": "Malta VAT compliance", "description": "VAT registration required if turnover exceeds threshold. Filing + payment deadlines strictly enforced.",
     "legal_basis": "VAT Act Cap. 406", "tolerance_pct": 0.0,
     "strict_threshold": "Quarterly returns", "enforced_threshold": "€20 daily penalty for late filing",
     "recurrence": "quarterly"},
    {"ref": "MC-FISC-001", "jurisdiction": "MC", "domain": "vat", "track": "fiscal",
     "title": "Monaco TVA/VAT obligations", "description": "Monaco applies French VAT system. Declaration required for any economic activity.",
     "legal_basis": "Convention fiscale FR-MC 1963, Art. 1 & 7", "tolerance_pct": 0.0,
     "recurrence": "quarterly"},
    {"ref": "IT-FISC-001", "jurisdiction": "IT", "domain": "tax", "track": "fiscal",
     "title": "Italy tax obligations (if applicable)", "description": "IRPEF/IVA if Italy source income or deemed resident. RW form for foreign assets.",
     "legal_basis": "TUIR Art. 2, DPR 917/1986", "tolerance_pct": 0.0,
     "recurrence": "annual"},
    {"ref": "FR-FISC-006", "jurisdiction": "FR", "domain": "vat", "track": "fiscal",
     "title": "VAT on crypto disposals (if taxable)", "description": "Capital gains on crypto may be subject to PFU (30%) or barème. Reporting mandatory if French tax resident.",
     "legal_basis": "Art. 150 VH bis CGI", "tolerance_pct": 0.0,
     "recurrence": "annual"},
    {"ref": "SM-FISC-001", "jurisdiction": "SM", "domain": "tax", "track": "fiscal",
     "title": "San Marino tax obligations (if applicable)", "description": "Limited applicability unless SM source income.",
     "legal_basis": "Legge tributaria SM", "tolerance_pct": 0.0},
    # ── NON-FISCAL TRACK (right to silence) ────────────────────────────
    {"ref": "MC-CRIM-001", "jurisdiction": "MC", "domain": "criminal", "track": "non_fiscal",
     "title": "Probation compliance (Monaco)", "description": "Strict probation conditions Oct 2025 – Oct 2028. Zero tolerance. Any breach = immediate incarceration.",
     "legal_basis": "Tribunal Correctionnel Monaco, Oct 2025", "tolerance_pct": 0.0,
     "strict_threshold": "Full compliance", "enforced_threshold": "Full compliance — no margin"},
    {"ref": "MT-CRIM-001", "jurisdiction": "MT", "domain": "criminal", "track": "non_fiscal",
     "title": "Malta DV proceedings", "description": "Domestic violence proceedings — right to silence applies in full.",
     "legal_basis": "Art. 6 ECHR, Criminal Code Cap. 9", "tolerance_pct": 100.0},
    {"ref": "MT-CIV-001", "jurisdiction": "MT", "domain": "civil", "track": "non_fiscal",
     "title": "Divorce proceedings (Malta)", "description": "Divorce proceedings — financial disclosure limited to what court orders.",
     "legal_basis": "Civil Code Cap. 16, Marriage Act Cap. 255", "tolerance_pct": 50.0},
    {"ref": "MT-CIV-002", "jurisdiction": "MT", "domain": "civil", "track": "non_fiscal",
     "title": "Custody — Constantin", "description": "Child custody proceedings. Best interest of the child standard.",
     "legal_basis": "Civil Code Cap. 16 Art. 131-149, Hague Convention", "tolerance_pct": 30.0},
    {"ref": "MT-CIV-003", "jurisdiction": "MT", "domain": "civil", "track": "non_fiscal",
     "title": "Pension maintenance (€32,500/mo)", "description": "Court-ordered pension. €32,500/month since Jan 2024 (was €85K/mo).",
     "legal_basis": "Court Order MT 2022", "tolerance_pct": 0.0,
     "recurrence": "monthly", "deadline": "2026-04-01"},
    {"ref": "FR-CRIM-001", "jurisdiction": "FR", "domain": "criminal", "track": "non_fiscal",
     "title": "France criminal investigation", "description": "Ongoing investigation. Full right to silence. Art. 6 ECHR, nemo tenetur.",
     "legal_basis": "Art. 6 ECHR, CPP Art. 113-1", "tolerance_pct": 100.0},
    {"ref": "FR-CIV-001", "jurisdiction": "FR", "domain": "civil", "track": "non_fiscal",
     "title": "Asset recovery / freezing orders", "description": "Civil asset recovery proceedings. Limited disclosure per court orders only.",
     "legal_basis": "CPC Art. 1-15", "tolerance_pct": 40.0},
    {"ref": "MC-CRIM-002", "jurisdiction": "MC", "domain": "criminal", "track": "non_fiscal",
     "title": "Escroquerie conviction (Monaco)", "description": "Conviction for escroquerie (fraud). Sentence completed/probation ongoing.",
     "legal_basis": "Code Pénal Monaco Art. 330-333", "tolerance_pct": 0.0},
    {"ref": "MC-CRIM-003", "jurisdiction": "MC", "domain": "criminal", "track": "non_fiscal",
     "title": "Cocaine possession (Monaco)", "description": "Prior conviction. Sentence served. Probation conditions apply.",
     "legal_basis": "Loi n° 890 substances stupéfiantes", "tolerance_pct": 0.0},
]

SEED_INSTITUTIONS = [
    {"code": "DGFIP", "name": "Direction Générale des Finances Publiques", "country": "FR",
     "domain": "fiscal", "aggressiveness": 1.8, "threshold": 4.0,
     "info_sharing": "CRS receiver (LI,CH,MT,DE,HK), shares with PNF/TRACFIN",
     "trigger_patterns": "CRS mismatch, undeclared accounts, address discrepancy, large movements",
     "notes": "Primary fiscal threat. Receives CRS from Bank Frick (LI), N26 (DE), Julius Baer (CH). French address on file = presumed FR tax residency."},
    {"code": "PNF", "name": "Parquet National Financier", "country": "FR",
     "domain": "criminal_fiscal", "aggressiveness": 2.0, "threshold": 3.0,
     "info_sharing": "Receives from DGFiP, TRACFIN",
     "trigger_patterns": "Tax fraud >€100K, laundering, complex structures",
     "notes": "RELENTLESS. Once triggered, full investigation powers. Can request EIO to Malta/Monaco."},
    {"code": "TRACFIN", "name": "TRACFIN", "country": "FR",
     "domain": "aml", "aggressiveness": 1.8, "threshold": 4.0,
     "info_sharing": "Egmont network (→FIAU_MT), receives from banks/DGFiP",
     "trigger_patterns": "Suspicious transactions, unusual patterns, crypto movements, STR from banks"},
    {"code": "MFSA", "name": "Malta Financial Services Authority", "country": "MT",
     "domain": "financial_regulation", "aggressiveness": 1.0, "threshold": 6.0,
     "info_sharing": "ESMA network, domestic (→CRA_MT, FIAU_MT)"},
    {"code": "FINMA", "name": "Swiss Financial Market Supervisory Authority", "country": "CH",
     "domain": "financial_regulation", "aggressiveness": 1.5, "threshold": 5.0,
     "info_sharing": "CRS sender (CH→FR confirmed), bilateral treaties"},
    {"code": "FMA_LI", "name": "Finanzmarktaufsicht Liechtenstein", "country": "LI",
     "domain": "financial_regulation", "aggressiveness": 1.0, "threshold": 6.0,
     "info_sharing": "CRS sender (LI→FR confirmed), EEA cooperation",
     "notes": "Bank Frick reports through FMA. CRS to France confirmed."},
    {"code": "HMRC", "name": "HM Revenue & Customs", "country": "GB",
     "domain": "fiscal", "aggressiveness": 1.5, "threshold": 4.5,
     "info_sharing": "CRS, FATCA, bilateral treaties",
     "notes": "Relevant if UK source income or UK residency claim."},
    {"code": "PARQUET_MC", "name": "Parquet Général de Monaco", "country": "MC",
     "domain": "criminal", "aggressiveness": 1.0, "threshold": 5.0,
     "info_sharing": "Bilateral FR-MC, can request EIO",
     "notes": "Probation supervisor. Direct interest in compliance."},
    {"code": "DVU_MT", "name": "Domestic Violence Unit — Pulizija ta' Malta", "country": "MT",
     "domain": "criminal", "aggressiveness": 0.5, "threshold": 7.0,
     "info_sharing": "Domestic (→Courts MT, →AG_MT), Europol National Unit",
     "notes": "Reactive. DV proceedings initiated. Operates under Pulizija ta' Malta Vice Squad."},
    {"code": "AG_MT", "name": "Avukat Ġenerali (Attorney General) — Malta", "country": "MT",
     "domain": "prosecution", "aggressiveness": 0.8, "threshold": 6.5,
     "info_sharing": "Receives from Pulizija ta' Malta, FIAU_MT, EIO requests",
     "notes": "Prosecutorial authority. Handles EIO execution from FR/MC. Europol liaison."},
    {"code": "COURTS_MT", "name": "Qrati ta' Malta (Courts of Justice)", "country": "MT",
     "domain": "judicial", "aggressiveness": 0.3, "threshold": 8.0,
     "info_sharing": "Receives from AG_MT, DVU_MT, parties",
     "notes": "Handles divorce, custody, DV. Standard processing."},
    {"code": "CRA_MT", "name": "Commissioner for Revenue (Malta)", "country": "MT",
     "domain": "fiscal", "aggressiveness": 1.0, "threshold": 6.0,
     "info_sharing": "CRS sender (MT→FR), domestic tax enforcement"},
    {"code": "FIAU_MT", "name": "Financial Intelligence Analysis Unit (Malta)", "country": "MT",
     "domain": "aml", "aggressiveness": 1.0, "threshold": 6.0,
     "info_sharing": "Egmont (←TRACFIN), domestic (→DVU_MT, →AG_MT)"},
    {"code": "AFC_CH", "name": "Administration Fédérale des Contributions", "country": "CH",
     "domain": "fiscal", "aggressiveness": 1.2, "threshold": 5.5,
     "info_sharing": "CRS sender (CH→FR), bilateral CH-FR treaty",
     "notes": "Julius Baer reports through AFC. Sequestre known."},
    {"code": "AGENZIA_IT", "name": "Agenzia delle Entrate", "country": "IT",
     "domain": "fiscal", "aggressiveness": 1.3, "threshold": 5.0,
     "info_sharing": "CRS, bilateral IT-FR, EU cooperation",
     "notes": "Relevant for San Marino connections and IT source income."},
    {"code": "SPJ_MC", "name": "Service de la Sûreté Publique (Monaco)", "country": "MC",
     "domain": "probation", "aggressiveness": 1.5, "threshold": 3.5,
     "info_sharing": "Domestic (→PARQUET_MC), bilateral FR-MC",
     "notes": "Probation enforcement. Direct monitoring Oct 2025-2028. ZERO tolerance."},
]

SEED_INFORMATION_FLOWS = [
    {"source": "FMA_LI", "target": "DGFIP", "mechanism": "CRS", "direction": "unidirectional",
     "frequency": "annual (Sep)", "data_types": "account balances, interest, dividends",
     "confirmed": 1, "notes": "Bank Frick → FMA → DGFiP. CONFIRMED. French address on file."},
    {"source": "AFC_CH", "target": "DGFIP", "mechanism": "CRS", "direction": "unidirectional",
     "frequency": "annual (Sep)", "data_types": "account balances, interest",
     "confirmed": 1, "notes": "Julius Baer → AFC → DGFiP. CONFIRMED. Sequestre known."},
    {"source": "CRA_MT", "target": "DGFIP", "mechanism": "CRS", "direction": "unidirectional",
     "frequency": "annual (Sep)", "data_types": "account balances",
     "confirmed": 1, "notes": "MT→FR CRS active since 2017."},
    {"source": "DGFIP", "target": "PNF", "mechanism": "internal_referral", "direction": "unidirectional",
     "frequency": "on trigger", "data_types": "tax fraud suspicion, CRS data",
     "confirmed": 1, "notes": "DGFiP refers cases >€100K to PNF."},
    {"source": "DGFIP", "target": "TRACFIN", "mechanism": "internal_referral", "direction": "unidirectional",
     "frequency": "on trigger", "data_types": "suspicious patterns",
     "confirmed": 1},
    {"source": "TRACFIN", "target": "FIAU_MT", "mechanism": "Egmont", "direction": "bidirectional",
     "frequency": "on request", "data_types": "FIU intelligence",
     "confirmed": 1, "notes": "Egmont network exchange."},
    {"source": "PARQUET_MC", "target": "DGFIP", "mechanism": "bilateral_FR_MC", "direction": "bidirectional",
     "frequency": "on request", "data_types": "judicial information",
     "confirmed": 1, "notes": "FR-MC bilateral treaty. Can exchange fiscal and criminal info."},
    {"source": "PNF", "target": "AG_MT", "mechanism": "EIO", "direction": "unidirectional",
     "frequency": "on request", "data_types": "evidence requests, freezing orders",
     "confirmed": 1, "notes": "European Investigation Order — FR requests MT cooperation via Avukat Ġenerali."},
    {"source": "SPJ_MC", "target": "PARQUET_MC", "mechanism": "internal", "direction": "unidirectional",
     "frequency": "on breach", "data_types": "probation violation reports",
     "confirmed": 1, "notes": "Probation service reports any breach directly to Parquet."},
    {"source": "AE_TAX", "target": "DGFIP", "mechanism": "CRS", "direction": "none",
     "frequency": "none", "data_types": "none",
     "confirmed": 0, "notes": "UAE has NO bilateral CRS with France. Emirates NBD = SAFE."},
]

SEED_CUMULATION_ENTRIES = [
    {"institution_code": "DGFIP", "obligation_ref": "FR-FISC-004",
     "description": "Bank Frick French address via CRS (LI→FR)",
     "severity": 8.0, "weight": 1.5, "known_to_institution": 1,
     "occurred_at": "2024-09-15", "notes": "DGFiP receives this annually. Creates presumption of FR tax residency."},
    {"institution_code": "DGFIP", "obligation_ref": "FR-FISC-004",
     "description": "N26 French address via CRS (DE→FR)",
     "severity": 8.0, "weight": 1.5, "known_to_institution": 1,
     "occurred_at": "2024-09-15", "notes": "Second independent CRS source confirming French address."},
    {"institution_code": "DGFIP", "obligation_ref": None,
     "description": "Undeclared Ledger BTC holdings",
     "severity": 7.0, "weight": 1.0, "known_to_institution": 0,
     "occurred_at": "2024-01-01", "notes": "NOT known to DGFiP. No CRS for hardware wallets. But discoverable in audit."},
    {"institution_code": "DGFIP", "obligation_ref": "FR-FISC-001",
     "description": "IRPP filing as implicit residence admission",
     "severity": 6.0, "weight": 1.0, "known_to_institution": 1,
     "occurred_at": "2023-05-15", "notes": "Filing IRPP = admitting FR tax residency for that year."},
    {"institution_code": "DGFIP", "obligation_ref": None,
     "description": "183-day presence ambiguity (FR/MC/MT)",
     "severity": 4.0, "weight": 0.8, "known_to_institution": 0,
     "occurred_at": "2024-06-30", "decay_rate": 0.03, "notes": "Difficult to prove. Partial knowledge only."},
    {"institution_code": "SPJ_MC", "obligation_ref": "MC-CRIM-001",
     "description": "Probation compliance baseline",
     "severity": 0.0, "weight": 1.0, "known_to_institution": 1,
     "occurred_at": "2025-10-01", "notes": "Clean baseline. Any future entry here is catastrophic."},
]

SEED_MITIGATIONS = [
    {"obligation_ref": "FR-FISC-004", "institution_code": "DGFIP",
     "title": "Change Bank Frick address from FR to MC",
     "description": "Contact Bank Frick, update registered address from French to Monaco. This stops CRS reporting to France via LI.",
     "priority": "critical", "status": "pending", "deadline": "2026-06-01"},
    {"obligation_ref": "FR-FISC-004", "institution_code": "DGFIP",
     "title": "Change N26 address from FR to MC",
     "description": "Update N26 registered address. May require closing FR account and opening MC/MT account.",
     "priority": "critical", "status": "pending", "deadline": "2026-06-01"},
    {"obligation_ref": "FR-FISC-002", "institution_code": "DGFIP",
     "title": "File Cerfa 3916 for all foreign accounts",
     "description": "Declare all foreign accounts: Bank Frick, Julius Baer, Emirates NBD, crypto platforms.",
     "priority": "high", "status": "pending", "deadline": "2026-05-31"},
    {"obligation_ref": "MT-CIV-003", "institution_code": "COURTS_MT",
     "title": "Maintain pension payments (€32,500/mo)",
     "description": "Ensure uninterrupted monthly pension payments. Non-payment triggers contempt of court.",
     "priority": "high", "status": "in_progress", "deadline": None},
    {"obligation_ref": "MC-CRIM-001", "institution_code": "SPJ_MC",
     "title": "Strict probation compliance",
     "description": "Zero tolerance for any probation breach Oct 2025-Oct 2028. Any violation = immediate incarceration.",
     "priority": "critical", "status": "in_progress", "deadline": "2028-10-01"},
    {"obligation_ref": "FR-FISC-005", "institution_code": "DGFIP",
     "title": "Verify VAT registration status (France)",
     "description": "Confirm whether any activity triggers FR VAT obligation. If yes, register and file. Penalties are automatic (10% late, up to 80% fraud).",
     "priority": "high", "status": "pending", "deadline": "2026-04-15"},
    {"obligation_ref": "MT-FISC-002", "institution_code": "CRA_MT",
     "title": "Verify Malta VAT status",
     "description": "Check if Malta activities require VAT registration. €20/day penalty for late filing.",
     "priority": "high", "status": "pending", "deadline": "2026-04-15"},
]


def seed_data(conn: sqlite3.Connection):
    c = conn.cursor()

    for ob in SEED_OBLIGATIONS:
        try:
            c.execute("""INSERT OR IGNORE INTO obligations
                (ref, jurisdiction, domain, track, title, description, legal_basis,
                 tolerance_pct, strict_threshold, enforced_threshold, deadline, recurrence)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (ob["ref"], ob["jurisdiction"], ob["domain"], ob["track"],
                 ob["title"], ob.get("description"), ob.get("legal_basis"),
                 ob.get("tolerance_pct", 0.0), ob.get("strict_threshold"),
                 ob.get("enforced_threshold"), ob.get("deadline"), ob.get("recurrence")))
        except sqlite3.IntegrityError:
            pass

    for inst in SEED_INSTITUTIONS:
        try:
            c.execute("""INSERT OR IGNORE INTO institutions
                (code, name, country, domain, aggressiveness, threshold, info_sharing, trigger_patterns, notes)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (inst["code"], inst["name"], inst["country"], inst["domain"],
                 inst["aggressiveness"], inst["threshold"],
                 inst.get("info_sharing"), inst.get("trigger_patterns"), inst.get("notes")))
        except sqlite3.IntegrityError:
            pass

    for flow in SEED_INFORMATION_FLOWS:
        existing = c.execute(
            "SELECT id FROM information_flows WHERE source_institution=? AND target_institution=? AND mechanism=?",
            (flow["source"], flow["target"], flow["mechanism"])).fetchone()
        if not existing:
            c.execute("""INSERT INTO information_flows
                (source_institution, target_institution, mechanism, direction, frequency, data_types, confirmed, notes)
                VALUES (?,?,?,?,?,?,?,?)""",
                (flow["source"], flow["target"], flow["mechanism"], flow["direction"],
                 flow.get("frequency"), flow.get("data_types"), flow.get("confirmed", 1), flow.get("notes")))

    for entry in SEED_CUMULATION_ENTRIES:
        existing = c.execute(
            "SELECT id FROM cumulation_entries WHERE institution_code=? AND description=?",
            (entry["institution_code"], entry["description"])).fetchone()
        if not existing:
            c.execute("""INSERT INTO cumulation_entries
                (institution_code, obligation_ref, description, severity, weight, known_to_institution, occurred_at, decay_rate, notes)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (entry["institution_code"], entry.get("obligation_ref"), entry["description"],
                 entry["severity"], entry.get("weight", 1.0), entry.get("known_to_institution", 0),
                 entry["occurred_at"], entry.get("decay_rate", 0.05), entry.get("notes")))

    for ob in SEED_OBLIGATIONS:
        existing = c.execute("SELECT id FROM compliance_status WHERE obligation_ref=?", (ob["ref"],)).fetchone()
        if not existing:
            status = "compliant" if ob.get("tolerance_pct", 0) == 0 and ob["track"] == "non_fiscal" and ob["ref"] in ("MT-CRIM-001", "FR-CRIM-001") else "unknown"
            c.execute("INSERT INTO compliance_status (obligation_ref, status, notes) VALUES (?,?,?)",
                      (ob["ref"], status, "Initial assessment — needs review"))

    for mit in SEED_MITIGATIONS:
        existing = c.execute("SELECT id FROM mitigation_actions WHERE title=?", (mit["title"],)).fetchone()
        if not existing:
            c.execute("""INSERT INTO mitigation_actions
                (obligation_ref, institution_code, title, description, priority, status, deadline)
                VALUES (?,?,?,?,?,?,?)""",
                (mit.get("obligation_ref"), mit.get("institution_code"), mit["title"],
                 mit.get("description"), mit["priority"], mit["status"], mit.get("deadline")))

    conn.commit()
    audit_log(conn, "SEED", "all", None, f"Seeded {len(SEED_OBLIGATIONS)} obligations, {len(SEED_INSTITUTIONS)} institutions, {len(SEED_INFORMATION_FLOWS)} flows, {len(SEED_CUMULATION_ENTRIES)} cumulation entries, {len(SEED_MITIGATIONS)} mitigations")
    conn.commit()
    print(f"  {C.GREEN}✓{C.RST} Seeded data: {len(SEED_OBLIGATIONS)} obligations, {len(SEED_INSTITUTIONS)} institutions")
    print(f"    {len(SEED_INFORMATION_FLOWS)} information flows, {len(SEED_CUMULATION_ENTRIES)} cumulation entries, {len(SEED_MITIGATIONS)} mitigations")


# ── Cumulation Scoring Algorithm ──────────────────────────────────────────
def compute_cumulation(conn: sqlite3.Connection, institution_code: Optional[str] = None) -> List[Dict]:
    """score = SUM(severity * weight * exp(-decay_rate * months) * known_multiplier * aggressiveness)"""
    c = conn.cursor()
    if institution_code:
        institutions = c.execute("SELECT * FROM institutions WHERE code=?", (institution_code,)).fetchall()
    else:
        institutions = c.execute("SELECT * FROM institutions").fetchall()

    results = []
    now = datetime.now()
    probation = is_probation()

    for inst in institutions:
        entries = c.execute("SELECT * FROM cumulation_entries WHERE institution_code=?", (inst["code"],)).fetchall()
        score = 0.0
        entry_details = []

        for e in entries:
            occurred = datetime.strptime(e["occurred_at"], "%Y-%m-%d")
            months = max(0, (now - occurred).days / 30.44)
            decay = math.exp(-e["decay_rate"] * months)
            known_mult = 2.0 if e["known_to_institution"] else 1.0
            weight = e["weight"] * (2.0 if probation else 1.0)
            entry_score = e["severity"] * weight * decay * known_mult * inst["aggressiveness"]
            score += entry_score
            entry_details.append({
                "description": e["description"],
                "raw_severity": e["severity"],
                "decay_factor": round(decay, 3),
                "known": bool(e["known_to_institution"]),
                "contribution": round(entry_score, 2),
            })

        threshold = inst["threshold"]
        headroom = threshold - score

        if headroom > threshold * 0.6:
            alert_level = "safe"
        elif headroom > threshold * 0.4:
            alert_level = "watch"
        elif headroom > threshold * 0.2:
            alert_level = "warning"
        elif headroom > 0:
            alert_level = "danger"
        else:
            alert_level = "critical"

        c.execute("DELETE FROM cumulation_scores WHERE institution_code=?", (inst["code"],))
        c.execute("""INSERT INTO cumulation_scores (institution_code, score, threshold, headroom, alert_level) VALUES (?,?,?,?,?)""",
            (inst["code"], round(score, 2), threshold, round(headroom, 2), alert_level))

        results.append({
            "code": inst["code"], "name": inst["name"], "country": inst["country"],
            "aggressiveness": inst["aggressiveness"],
            "score": round(score, 2), "threshold": threshold,
            "headroom": round(headroom, 2), "alert_level": alert_level,
            "entries": entry_details, "probation_active": probation,
        })

    conn.commit()
    return results


# ── Two-Track Firewall ────────────────────────────────────────────────────
FISCAL_KEYWORDS = {"crs", "tax", "fisc", "irpp", "vat", "tva", "cerfa", "3916", "cgi", "dgfip",
                    "impôt", "revenu", "déclaration", "fiscal", "taxable", "contribuable"}
CRIMINAL_KEYWORDS = {"pulizija", "sûreté", "gendarmerie", "judiciaire", "criminal", "pénal",
                      "crim", "arrest", "detention", "probation", "parquet",
                      "escroquerie", "cocaine", "violence", "assault", "threats", "dv"}

def _assert_firewall(source_track: str, text: str, conn: sqlite3.Connection) -> bool:
    target_track = "non_fiscal" if source_track == "fiscal" else "fiscal"
    text_lower = text.lower()
    cross_keywords = CRIMINAL_KEYWORDS if source_track == "fiscal" else FISCAL_KEYWORDS
    leaks = [kw for kw in cross_keywords if kw in text_lower]
    if leaks:
        conn.execute("""INSERT INTO firewall_log (direction, source_track, target_track, description, blocked) VALUES (?,?,?,?,1)""",
            (f"{source_track}→{target_track}", source_track, target_track,
             f"Cross-track leak detected: keywords [{', '.join(leaks)}] in {source_track} context"))
        conn.commit()
        return True
    return False


def firewall_check(conn: sqlite3.Connection) -> List[Dict]:
    c = conn.cursor()
    issues = []
    statuses = c.execute("""SELECT cs.*, o.track, o.ref FROM compliance_status cs JOIN obligations o ON o.ref = cs.obligation_ref WHERE cs.notes IS NOT NULL""").fetchall()
    for s in statuses:
        if s["notes"] and _assert_firewall(s["track"], s["notes"], conn):
            issues.append({"type": "compliance_status_leak", "obligation_ref": s["ref"], "track": s["track"], "notes_excerpt": s["notes"][:100]})
    mitigations = c.execute("""SELECT m.*, o.track FROM mitigation_actions m JOIN obligations o ON o.ref = m.obligation_ref WHERE m.description IS NOT NULL""").fetchall()
    for m in mitigations:
        if m["description"] and _assert_firewall(m["track"], m["description"], conn):
            issues.append({"type": "mitigation_leak", "title": m["title"], "track": m["track"]})
    return issues


# ── Early Warning System ──────────────────────────────────────────────────
def scan_alerts(conn: sqlite3.Connection) -> List[Dict]:
    c = conn.cursor()
    alerts = []
    today = date.today()

    obligations = c.execute("SELECT * FROM obligations WHERE deadline IS NOT NULL").fetchall()
    for ob in obligations:
        try:
            dl = date.fromisoformat(ob["deadline"])
        except (ValueError, TypeError):
            continue
        days_left = (dl - today).days
        if days_left < 0:
            alerts.append({"type": "deadline_overdue", "severity": "critical",
                           "title": f"OVERDUE: {ob['ref']} — {ob['title']}", "description": f"Deadline was {ob['deadline']} ({-days_left} days ago)", "obligation_ref": ob["ref"]})
        elif days_left <= 7:
            alerts.append({"type": "deadline_imminent", "severity": "danger",
                           "title": f"7 DAYS: {ob['ref']} — {ob['title']}", "description": f"Deadline: {ob['deadline']}", "obligation_ref": ob["ref"]})
        elif days_left <= 14:
            alerts.append({"type": "deadline_near", "severity": "warning",
                           "title": f"14 DAYS: {ob['ref']} — {ob['title']}", "description": f"Deadline: {ob['deadline']}", "obligation_ref": ob["ref"]})
        elif days_left <= 30:
            alerts.append({"type": "deadline_approaching", "severity": "watch",
                           "title": f"30 DAYS: {ob['ref']} — {ob['title']}", "description": f"Deadline: {ob['deadline']}", "obligation_ref": ob["ref"]})

    scores = compute_cumulation(conn)
    for s in scores:
        if s["alert_level"] in ("danger", "critical"):
            alerts.append({"type": "cumulation_threshold", "severity": s["alert_level"],
                           "title": f"Cumulation {s['alert_level'].upper()}: {s['code']}", "description": f"Score {s['score']}/{s['threshold']} (headroom: {s['headroom']})", "institution_code": s["code"]})

    if today.month >= 7 and today.month <= 9:
        alerts.append({"type": "crs_window", "severity": "warning",
                       "title": "CRS exchange window approaching", "description": f"Annual CRS data exchange typically occurs in September. Ensure all address corrections are completed."})

    if is_probation():
        alerts.append({"type": "probation_active", "severity": "danger",
                       "title": "PROBATION ACTIVE — All margins halved", "description": f"Probation period: {PROBATION_START} to {PROBATION_END}. Zero tolerance for any breach. All cumulation weights doubled."})

    mitigations = c.execute("SELECT * FROM mitigation_actions WHERE deadline IS NOT NULL AND status NOT IN ('completed')").fetchall()
    for m in mitigations:
        try:
            dl = date.fromisoformat(m["deadline"])
        except (ValueError, TypeError):
            continue
        days_left = (dl - today).days
        if days_left < 0:
            alerts.append({"type": "mitigation_overdue", "severity": "critical",
                           "title": f"OVERDUE mitigation: {m['title']}", "description": f"Was due {m['deadline']} ({-days_left} days ago). Priority: {m['priority']}", "obligation_ref": m.get("obligation_ref")})
        elif days_left <= 14:
            alerts.append({"type": "mitigation_due", "severity": "warning",
                           "title": f"Mitigation due soon: {m['title']}", "description": f"Due: {m['deadline']} ({days_left} days). Priority: {m['priority']}", "obligation_ref": m.get("obligation_ref")})

    for a in alerts:
        existing = c.execute("SELECT id FROM alerts WHERE title=? AND resolved=0", (a["title"],)).fetchone()
        if not existing:
            c.execute("""INSERT INTO alerts (type, severity, title, description, obligation_ref, institution_code) VALUES (?,?,?,?,?,?)""",
                (a["type"], a["severity"], a["title"], a.get("description"), a.get("obligation_ref"), a.get("institution_code")))

    conn.commit()
    return alerts


# ── Audit Simulation ──────────────────────────────────────────────────────
def simulate_audit(conn: sqlite3.Connection, institution_code: str) -> Dict:
    c = conn.cursor()
    inst = c.execute("SELECT * FROM institutions WHERE code=?", (institution_code,)).fetchone()
    if not inst:
        return {"error": f"Unknown institution: {institution_code}"}

    obligations = c.execute("""
        SELECT o.*, cs.status, cs.deviation_pct, cs.notes as status_notes
        FROM obligations o LEFT JOIN compliance_status cs ON cs.obligation_ref = o.ref
        WHERE o.jurisdiction = ? OR o.domain = ?
        ORDER BY o.track, o.tolerance_pct
    """, (inst["country"], inst["domain"])).fetchall()

    discoverable, hidden = [], []

    for ob in obligations:
        entries = c.execute("SELECT * FROM cumulation_entries WHERE institution_code=? AND obligation_ref=?",
            (institution_code, ob["ref"])).fetchall()
        item = {"ref": ob["ref"], "title": ob["title"], "track": ob["track"],
                "tolerance_pct": ob["tolerance_pct"], "status": ob["status"] or "unknown",
                "deviation_pct": ob["deviation_pct"] or 0}
        known_entries = [e for e in entries if e["known_to_institution"]]
        if known_entries or ob["status"] in ("non_compliant",):
            item["visibility"] = "HIGH"
            item["known_evidence"] = len(known_entries)
            discoverable.append(item)
        elif ob["status"] == "marginal":
            item["visibility"] = "MEDIUM"
            discoverable.append(item)
        else:
            item["visibility"] = "LOW"
            hidden.append(item)

    all_entries = c.execute("SELECT * FROM cumulation_entries WHERE institution_code=?", (institution_code,)).fetchall()
    known_count = sum(1 for e in all_entries if e["known_to_institution"])
    unknown_count = sum(1 for e in all_entries if not e["known_to_institution"])

    scores = compute_cumulation(conn, institution_code)
    score_data = scores[0] if scores else {}

    actions = c.execute("""SELECT * FROM mitigation_actions WHERE institution_code=? AND status NOT IN ('completed')
        ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END""",
        (institution_code,)).fetchall()

    return {
        "institution": dict(inst), "cumulation_score": score_data,
        "discoverable_items": discoverable, "hidden_items": hidden,
        "known_evidence": known_count, "unknown_evidence": unknown_count,
        "total_exposure": len(discoverable),
        "recommended_actions": [dict(a) for a in actions],
        "probation_active": is_probation(),
        "simulation_date": datetime.now().isoformat(),
    }


# ── CLI Commands ──────────────────────────────────────────────────────────

def cmd_init(args):
    conn = init_db()
    seed_data(conn)
    scores = compute_cumulation(conn)
    print(f"  {C.GREEN}✓{C.RST} Computed cumulation for {len(scores)} institutions")
    alerts = scan_alerts(conn)
    print(f"  {C.GREEN}✓{C.RST} Scanned {len(alerts)} alerts")
    conn.close()


def cmd_obligations(args):
    conn = get_db()
    query = "SELECT o.*, cs.status, cs.deviation_pct FROM obligations o LEFT JOIN compliance_status cs ON cs.obligation_ref = o.ref WHERE 1=1"
    params = []
    if args.jurisdiction:
        query += " AND o.jurisdiction=?"; params.append(args.jurisdiction.upper())
    if args.domain:
        query += " AND o.domain=?"; params.append(args.domain)
    if args.track:
        query += " AND o.track=?"; params.append(args.track)
    if args.status:
        query += " AND cs.status=?"; params.append(args.status)
    query += " ORDER BY o.track, o.jurisdiction, o.ref"
    rows = conn.execute(query, params).fetchall()

    if not rows:
        print(f"  {C.YELLOW}No obligations found{C.RST}"); return

    current_track = None
    for r in rows:
        if r["track"] != current_track:
            current_track = r["track"]
            print(f"\n  {TRACK_BADGES.get(current_track, current_track)}")
            print(f"  {'─'*70}")
        status_badge = STATUS_BADGES.get(r["status"] or "unknown", "?")
        tol = f" (tolerance: {r['tolerance_pct']:.0f}%)" if r["tolerance_pct"] > 0 else ""
        deadline = f" ⏰ {r['deadline']}" if r["deadline"] else ""
        print(f"    {C.BOLD}{r['ref']}{C.RST} [{r['jurisdiction']}] {r['title']}")
        print(f"      {status_badge}{tol}{deadline}")
        if r["legal_basis"]:
            print(f"      {C.DIM}{r['legal_basis']}{C.RST}")
    print(f"\n  Total: {len(rows)} obligations")
    conn.close()


def cmd_status(args):
    conn = get_db()
    if args.obligation_ref:
        rows = conn.execute("""SELECT o.*, cs.status, cs.deviation_pct, cs.notes as status_notes, cs.assessed_at
            FROM obligations o LEFT JOIN compliance_status cs ON cs.obligation_ref = o.ref WHERE o.ref=?""", (args.obligation_ref,)).fetchall()
    else:
        rows = conn.execute("""SELECT o.*, cs.status, cs.deviation_pct, cs.notes as status_notes, cs.assessed_at
            FROM obligations o LEFT JOIN compliance_status cs ON cs.obligation_ref = o.ref ORDER BY o.track, cs.status DESC, o.jurisdiction""").fetchall()

    if not rows:
        print(f"  {C.YELLOW}No obligations found{C.RST}"); return

    counts = {"compliant": 0, "marginal": 0, "non_compliant": 0, "unknown": 0}
    for r in rows:
        s = r["status"] or "unknown"
        counts[s] = counts.get(s, 0) + 1

    print(f"\n  {C.BOLD}Compliance Matrix{C.RST}")
    print(f"  {C.GREEN}✓ {counts['compliant']}{C.RST}  {C.YELLOW}⚠ {counts['marginal']}{C.RST}  {C.RED}✗ {counts['non_compliant']}{C.RST}  {C.DIM}? {counts['unknown']}{C.RST}")
    print(f"  {'═'*70}")

    for r in rows:
        status_badge = STATUS_BADGES.get(r["status"] or "unknown", "?")
        track_badge = TRACK_BADGES.get(r["track"], "")
        dev = f" (dev: {r['deviation_pct']:.0f}%)" if r["deviation_pct"] else ""
        print(f"  {status_badge} {C.BOLD}{r['ref']}{C.RST} {track_badge} {r['title']}{dev}")
        if r["status_notes"] and args.obligation_ref:
            print(f"    {C.DIM}Notes: {r['status_notes']}{C.RST}")
            print(f"    {C.DIM}Assessed: {r['assessed_at']}{C.RST}")
    conn.close()


def cmd_assess(args):
    conn = get_db()
    ob = conn.execute("SELECT * FROM obligations WHERE ref=?", (args.ref,)).fetchone()
    if not ob:
        print(f"  {C.RED}✗ Unknown obligation: {args.ref}{C.RST}"); return

    if args.notes and _assert_firewall(ob["track"], args.notes, conn):
        print(f"  {C.BG_RED}{C.WHITE}{C.BOLD} ██ FIREWALL BLOCK ██ {C.RST}")
        print(f"  Cross-track information detected in notes.")
        print(f"  Track: {ob['track']} — cannot reference {'criminal/civil' if ob['track'] == 'fiscal' else 'fiscal'} matters.")
        return

    deviation = args.deviation or 0.0
    effective_tolerance = ob["tolerance_pct"]
    if is_probation():
        effective_tolerance = effective_tolerance / 2.0

    if args.status == "marginal" and deviation > effective_tolerance:
        print(f"  {C.YELLOW}⚠ Deviation {deviation}% exceeds effective tolerance {effective_tolerance}%{C.RST}")
        if is_probation():
            print(f"  {C.RED}  (Probation halved tolerance from {ob['tolerance_pct']}% to {effective_tolerance}%){C.RST}")

    conn.execute("INSERT INTO compliance_status (obligation_ref, status, deviation_pct, notes) VALUES (?,?,?,?)",
        (args.ref, args.status, deviation, args.notes))
    audit_log(conn, "ASSESS", "compliance_status", None, f"ref={args.ref} status={args.status} deviation={deviation}")
    conn.commit()
    print(f"  {C.GREEN}✓{C.RST} {args.ref}: {STATUS_BADGES[args.status]}")
    conn.close()


def cmd_cumulation(args):
    conn = get_db()
    inst_code = args.institution if hasattr(args, 'institution') and args.institution else None
    results = compute_cumulation(conn, inst_code)

    if not results:
        print(f"  {C.YELLOW}No institutions found{C.RST}"); return

    probation_str = f" {C.RED}[PROBATION ACTIVE — weights doubled]{C.RST}" if is_probation() else ""
    print(f"\n  {C.BOLD}Cumulation Heat Map{C.RST}{probation_str}")
    print(f"  {'═'*70}")

    level_order = {"critical": 0, "danger": 1, "warning": 2, "watch": 3, "safe": 4}
    results.sort(key=lambda x: level_order.get(x["alert_level"], 5))

    for r in results:
        dot, label = ALERT_LEVELS[r["alert_level"]]
        bar_pct = min(100, int(r["score"] / r["threshold"] * 100)) if r["threshold"] > 0 else 0
        bar_filled = bar_pct // 5
        bar_empty = 20 - bar_filled

        if r["alert_level"] == "critical":
            bar_color = C.BG_RED + C.WHITE
        elif r["alert_level"] == "danger":
            bar_color = C.RED
        elif r["alert_level"] == "warning":
            bar_color = C.YELLOW
        else:
            bar_color = C.GREEN

        bar = f"{bar_color}{'█' * bar_filled}{C.RST}{C.DIM}{'░' * bar_empty}{C.RST}"
        print(f"  {dot} {C.BOLD}{r['code']:<12}{C.RST} [{bar}] {r['score']:5.1f}/{r['threshold']:.1f} (headroom: {r['headroom']:+.1f}) [{label}]")
        print(f"    {C.DIM}{r['name']} ({r['country']}) — aggr: {r['aggressiveness']}{C.RST}")

        if inst_code and r["entries"]:
            for e in r["entries"]:
                known_str = f" {C.RED}[KNOWN]{C.RST}" if e["known"] else ""
                print(f"      • {e['description']}: {C.BOLD}{e['contribution']:.1f}{C.RST} (sev={e['raw_severity']}, decay={e['decay_factor']}){known_str}")
    conn.close()


def cmd_institutions(args):
    conn = get_db()
    if args.code:
        rows = conn.execute("SELECT * FROM institutions WHERE code=?", (args.code,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM institutions ORDER BY aggressiveness DESC").fetchall()

    for r in rows:
        aggr = r["aggressiveness"]
        if aggr >= 1.8: aggr_badge = f"{C.RED}RELENTLESS ({aggr}){C.RST}"
        elif aggr >= 1.3: aggr_badge = f"{C.YELLOW}AGGRESSIVE ({aggr}){C.RST}"
        elif aggr >= 0.8: aggr_badge = f"{C.BLUE}STANDARD ({aggr}){C.RST}"
        else: aggr_badge = f"{C.GREEN}PASSIVE ({aggr}){C.RST}"

        print(f"\n  {C.BOLD}{r['code']}{C.RST} — {r['name']}")
        print(f"    Country: {r['country']}  Domain: {r['domain']}  Threshold: {r['threshold']}")
        print(f"    Aggressiveness: {aggr_badge}")
        if r["info_sharing"]: print(f"    Info sharing: {r['info_sharing']}")
        if r["trigger_patterns"]: print(f"    Triggers: {r['trigger_patterns']}")
        if r["notes"]: print(f"    {C.DIM}{r['notes']}{C.RST}")
    conn.close()


def cmd_mitigate(args):
    conn = get_db()
    if args.add:
        conn.execute("INSERT INTO mitigation_actions (obligation_ref, institution_code, title, priority, status) VALUES (?,?,?,?,?)",
            (args.obligation_ref, args.institution_code, args.add, args.priority or "medium", "pending"))
        conn.commit()
        print(f"  {C.GREEN}✓{C.RST} Added mitigation: {args.add}"); return

    if args.complete:
        conn.execute("UPDATE mitigation_actions SET status='completed', completed_at=datetime('now') WHERE id=?", (args.complete,))
        conn.commit()
        print(f"  {C.GREEN}✓{C.RST} Completed mitigation #{args.complete}"); return

    if args.update:
        parts = args.update.split(":", 1)
        if len(parts) == 2:
            conn.execute("UPDATE mitigation_actions SET status=? WHERE id=?", (parts[1], int(parts[0])))
            conn.commit()
            print(f"  {C.GREEN}✓{C.RST} Updated #{parts[0]} → {parts[1]}")
        return

    query = "SELECT m.*, o.track FROM mitigation_actions m LEFT JOIN obligations o ON o.ref = m.obligation_ref"
    if not args.all:
        query += " WHERE m.status NOT IN ('completed')"
    query += " ORDER BY CASE m.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END"
    rows = conn.execute(query).fetchall()

    priority_colors = {"critical": C.BG_RED + C.WHITE, "high": C.RED, "medium": C.YELLOW, "low": C.GREEN}
    status_icons = {"pending": "○", "in_progress": "◐", "completed": "●", "blocked": "✗"}

    print(f"\n  {C.BOLD}Mitigation Queue{C.RST}")
    print(f"  {'═'*70}")

    for r in rows:
        pc = priority_colors.get(r["priority"], "")
        si = status_icons.get(r["status"], "?")
        track = TRACK_BADGES.get(r["track"], "") if r["track"] else ""
        dl = f" ⏰ {r['deadline']}" if r["deadline"] else ""
        print(f"  {si} #{r['id']} {pc}[{r['priority'].upper()}]{C.RST} {track} {r['title']}{dl}")
        if r["description"]:
            print(f"    {C.DIM}{r['description'][:100]}{C.RST}")
    print(f"\n  Total: {len(rows)} actions")
    conn.close()


def cmd_firewall(args):
    conn = get_db()
    if args.check:
        issues = firewall_check(conn)
        if issues:
            print(f"\n  {C.BG_RED}{C.WHITE}{C.BOLD} ██ FIREWALL ISSUES ██ {C.RST}")
            for i in issues:
                print(f"  {C.RED}✗{C.RST} {i['type']}: {i.get('obligation_ref', i.get('title', ''))}")
                print(f"    Track: {i['track']}")
        else:
            print(f"  {C.GREEN}✓{C.RST} Firewall integrity: OK — no cross-track leaks detected")
        return

    if args.log:
        rows = conn.execute("SELECT * FROM firewall_log ORDER BY logged_at DESC LIMIT 20").fetchall()
        print(f"\n  {C.BOLD}Firewall Log (last 20){C.RST}")
        for r in rows:
            blocked = f"{C.RED}BLOCKED{C.RST}" if r["blocked"] else f"{C.GREEN}APPROVED{C.RST}"
            print(f"  [{r['logged_at']}] {blocked} {r['direction']}: {r['description'][:80]}")
        return

    fiscal_count = conn.execute("SELECT COUNT(*) as n FROM obligations WHERE track='fiscal'").fetchone()["n"]
    nonfiscal_count = conn.execute("SELECT COUNT(*) as n FROM obligations WHERE track='non_fiscal'").fetchone()["n"]
    blocked_count = conn.execute("SELECT COUNT(*) as n FROM firewall_log WHERE blocked=1").fetchone()["n"]

    print(f"\n  {C.BOLD}Two-Track Firewall Status{C.RST}")
    print(f"  {'═'*50}")
    print(f"  {TRACK_BADGES['fiscal']} {fiscal_count} obligations — prove innocence, 0% tolerance")
    print(f"  {TRACK_BADGES['non_fiscal']} {nonfiscal_count} obligations — right to silence (Art. 6 ECHR)")
    print(f"  {C.RED}Blocked cross-track flows: {blocked_count}{C.RST}")
    print(f"\n  {C.BOLD}Rule:{C.RST} Fiscal disclosures NEVER leak to non-fiscal without explicit approval")
    conn.close()


def cmd_audit(args):
    conn = get_db()
    if args.simulate:
        result = simulate_audit(conn, args.simulate)
        if "error" in result:
            print(f"  {C.RED}✗ {result['error']}{C.RST}"); return

        inst = result["institution"]
        print(f"\n  {C.BG_RED}{C.WHITE}{C.BOLD} ██ AUDIT SIMULATION: {args.simulate} ██ {C.RST}")
        print(f"  {C.BOLD}{inst['name']}{C.RST} ({inst['country']})")
        print(f"  Aggressiveness: {inst['aggressiveness']}  Threshold: {inst['threshold']}")
        if result["probation_active"]:
            print(f"  {C.RED}⚠ PROBATION ACTIVE — enhanced scrutiny{C.RST}")

        score = result.get("cumulation_score", {})
        if score:
            print(f"\n  Cumulation: {score.get('score', 0)}/{score.get('threshold', 0)} [{score.get('alert_level', '?').upper()}]")

        print(f"\n  {C.BOLD}Discoverable ({len(result['discoverable_items'])} items):{C.RST}")
        for d in result["discoverable_items"]:
            vis_color = C.RED if d["visibility"] == "HIGH" else C.YELLOW
            print(f"    {vis_color}[{d['visibility']}]{C.RST} {d['ref']}: {d['title']} ({d['status']})")

        if result["hidden_items"]:
            print(f"\n  {C.BOLD}Hidden ({len(result['hidden_items'])} items):{C.RST}")
            for h in result["hidden_items"]:
                print(f"    {C.DIM}[{h['visibility']}]{C.RST} {h['ref']}: {h['title']}")

        print(f"\n  Evidence: {result['known_evidence']} known, {result['unknown_evidence']} unknown")

        if result["recommended_actions"]:
            print(f"\n  {C.BOLD}Recommended immediate actions:{C.RST}")
            for a in result["recommended_actions"]:
                priority_colors = {"critical": C.BG_RED + C.WHITE, "high": C.RED, "medium": C.YELLOW, "low": C.GREEN}
                pc = priority_colors.get(a["priority"], "")
                print(f"    {pc}[{a['priority'].upper()}]{C.RST} {a['title']}")
        conn.close()
        return

    rows = conn.execute("SELECT * FROM audit_trail ORDER BY id DESC LIMIT 30").fetchall()
    print(f"\n  {C.BOLD}Audit Trail (last 30){C.RST}")
    print(f"  {'═'*70}")
    for r in rows:
        print(f"  [{r['created_at']}] {r['action']:10} {r['table_name']:20} #{r['record_id'] or '-':>5} {C.DIM}{r['entry_hash'][:12]}{C.RST}")
        if r["details"]:
            print(f"    {C.DIM}{r['details'][:80]}{C.RST}")

    chain = conn.execute("SELECT prev_hash, entry_hash FROM audit_trail ORDER BY id").fetchall()
    valid = True
    for i, entry in enumerate(chain):
        if i == 0:
            if entry["prev_hash"] != "GENESIS": valid = False; break
        else:
            if entry["prev_hash"] != chain[i-1]["entry_hash"]: valid = False; break

    if valid:
        print(f"\n  {C.GREEN}✓{C.RST} Chain integrity: VALID ({len(chain)} entries)")
    else:
        print(f"\n  {C.RED}✗{C.RST} Chain integrity: BROKEN — tamper detected!")
    conn.close()


def cmd_dashboard(args):
    conn = get_db()
    print(f"\n  {C.BOLD}{'═'*70}{C.RST}")
    print(f"  {C.BOLD}  COMPLIANCE TOLERANCE ENGINE — DASHBOARD{C.RST}")
    print(f"  {C.BOLD}{'═'*70}{C.RST}")
    print(f"  {C.DIM}Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}{C.RST}")

    if is_probation():
        days_left = (PROBATION_END - date.today()).days
        print(f"  {C.BG_RED}{C.WHITE}{C.BOLD} ⚠ PROBATION ACTIVE — {days_left} days remaining ⚠ {C.RST}")

    counts = conn.execute("SELECT cs.status, COUNT(*) as n FROM compliance_status cs GROUP BY cs.status").fetchall()
    count_map = {r["status"]: r["n"] for r in counts}
    total = sum(count_map.values())
    print(f"\n  {C.BOLD}▸ Compliance Summary{C.RST}")
    print(f"    {C.GREEN}✓ {count_map.get('compliant', 0)}{C.RST}  {C.YELLOW}⚠ {count_map.get('marginal', 0)}{C.RST}  {C.RED}✗ {count_map.get('non_compliant', 0)}{C.RST}  {C.DIM}? {count_map.get('unknown', 0)}{C.RST}  Total: {total}")

    track_counts = conn.execute("SELECT o.track, COUNT(*) as n FROM obligations o GROUP BY o.track").fetchall()
    for t in track_counts:
        print(f"    {TRACK_BADGES.get(t['track'], t['track'])}: {t['n']} obligations")

    print(f"\n  {C.BOLD}▸ Cumulation Heat Map (top threats){C.RST}")
    scores = compute_cumulation(conn)
    scores.sort(key=lambda x: x["headroom"])
    for s in scores[:5]:
        dot, label = ALERT_LEVELS[s["alert_level"]]
        print(f"    {dot} {s['code']:<12} {s['score']:5.1f}/{s['threshold']:.1f} (headroom: {s['headroom']:+.1f}) [{label}]")

    alerts_rows = conn.execute("SELECT * FROM alerts WHERE resolved=0 ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'danger' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END LIMIT 10").fetchall()
    if alerts_rows:
        print(f"\n  {C.BOLD}▸ Active Alerts ({len(alerts_rows)}){C.RST}")
        for a in alerts_rows:
            sev_colors = {"critical": C.BG_RED + C.WHITE, "danger": C.RED, "warning": C.YELLOW, "watch": C.BLUE}
            sc = sev_colors.get(a["severity"], "")
            print(f"    {sc}[{a['severity'].upper()}]{C.RST} {a['title']}")

    mits = conn.execute("SELECT * FROM mitigation_actions WHERE priority IN ('critical','high') AND status NOT IN ('completed') ORDER BY CASE priority WHEN 'critical' THEN 0 ELSE 1 END").fetchall()
    if mits:
        print(f"\n  {C.BOLD}▸ Critical Mitigations ({len(mits)}){C.RST}")
        for m in mits:
            si = {"pending": "○", "in_progress": "◐", "blocked": "✗"}.get(m["status"], "?")
            dl = f" ⏰ {m['deadline']}" if m["deadline"] else ""
            print(f"    {si} [{m['priority'].upper()}] {m['title']}{dl}")

    blocked = conn.execute("SELECT COUNT(*) as n FROM firewall_log WHERE blocked=1").fetchone()["n"]
    print(f"\n  {C.BOLD}▸ Firewall{C.RST}")
    print(f"    Cross-track blocks: {blocked}")
    issues = firewall_check(conn)
    if issues:
        print(f"    {C.RED}⚠ {len(issues)} active cross-track leak(s) detected!{C.RST}")
    else:
        print(f"    {C.GREEN}✓ No cross-track leaks{C.RST}")

    flows = conn.execute("SELECT COUNT(*) as n FROM information_flows WHERE confirmed=1").fetchone()["n"]
    safe_flows = conn.execute("SELECT COUNT(*) as n FROM information_flows WHERE confirmed=0").fetchone()["n"]
    print(f"\n  {C.BOLD}▸ Information Flows{C.RST}")
    print(f"    Confirmed channels: {flows}")
    print(f"    Safe (no exchange): {safe_flows}")
    print(f"\n  {C.BOLD}{'═'*70}{C.RST}")
    conn.close()


def cmd_alerts(args):
    conn = get_db()
    if args.ack:
        conn.execute("UPDATE alerts SET acknowledged=1 WHERE id=?", (args.ack,))
        conn.commit()
        print(f"  {C.GREEN}✓{C.RST} Acknowledged alert #{args.ack}"); return

    if args.resolve:
        conn.execute("UPDATE alerts SET resolved=1, resolved_at=datetime('now') WHERE id=?", (args.resolve,))
        conn.commit()
        print(f"  {C.GREEN}✓{C.RST} Resolved alert #{args.resolve}"); return

    scan_alerts(conn)
    rows = conn.execute("""SELECT * FROM alerts WHERE resolved=0
        ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'danger' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END""").fetchall()
    sev_colors = {"critical": C.BG_RED + C.WHITE, "danger": C.RED, "warning": C.YELLOW, "watch": C.BLUE, "safe": C.GREEN}

    print(f"\n  {C.BOLD}Active Alerts{C.RST} ({len(rows)})")
    print(f"  {'═'*70}")
    for r in rows:
        sc = sev_colors.get(r["severity"], "")
        ack = f" {C.DIM}[ACK]{C.RST}" if r["acknowledged"] else ""
        print(f"  #{r['id']:>3} {sc}[{r['severity'].upper():>8}]{C.RST} {r['title']}{ack}")
        if r["description"]:
            print(f"       {C.DIM}{r['description'][:80]}{C.RST}")
    conn.close()


def cmd_search(args):
    conn = get_db()
    query = " ".join(args.query)
    rows = conn.execute("""SELECT o.*, cs.status FROM comply_fts f
        JOIN obligations o ON o.id = f.rowid
        LEFT JOIN compliance_status cs ON cs.obligation_ref = o.ref
        WHERE comply_fts MATCH ? ORDER BY rank""", (query,)).fetchall()
    print(f"\n  {C.BOLD}Search: \"{query}\"{C.RST} — {len(rows)} results")
    for r in rows:
        status_badge = STATUS_BADGES.get(r["status"] or "unknown", "?")
        print(f"  {status_badge} {C.BOLD}{r['ref']}{C.RST} [{r['jurisdiction']}] {r['title']}")
        if r["description"]:
            print(f"    {C.DIM}{r['description'][:100]}{C.RST}")
    conn.close()


def cmd_stats(args):
    conn = get_db()
    print(f"\n  {C.BOLD}Compliance Engine Statistics{C.RST}")
    print(f"  {'═'*50}")
    tables = [("obligations", "Obligations"), ("compliance_status", "Status records"),
              ("institutions", "Institutions"), ("cumulation_entries", "Cumulation entries"),
              ("cumulation_scores", "Cached scores"), ("firewall_log", "Firewall log entries"),
              ("mitigation_actions", "Mitigation actions"), ("alerts", "Alerts"),
              ("information_flows", "Information flows"), ("audit_trail", "Audit trail entries")]
    total = 0
    for tbl, label in tables:
        n = conn.execute(f"SELECT COUNT(*) as n FROM {tbl}").fetchone()["n"]
        total += n
        print(f"    {label:<25} {n:>6}")
    print(f"    {'─'*35}")
    print(f"    {'Total':<25} {total:>6}")
    db_size = os.path.getsize(COMPLY_DB) if COMPLY_DB.exists() else 0
    print(f"\n    Database: {COMPLY_DB}")
    print(f"    Size: {db_size / 1024:.1f} KB")
    print(f"    Probation: {'ACTIVE' if is_probation() else 'inactive'}")
    conn.close()


def cmd_export(args):
    export_dir = Path(args.dir) if args.dir else SCRIPT_DIR / "compliance_export"
    export_dir.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    tables = ["obligations", "compliance_status", "institutions", "cumulation_entries",
              "cumulation_scores", "firewall_log", "mitigation_actions", "alerts",
              "information_flows", "audit_trail"]
    for tbl in tables:
        rows = conn.execute(f"SELECT * FROM {tbl}").fetchall()
        data = [dict(r) for r in rows]
        out_path = export_dir / f"{tbl}.json"
        with open(out_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        print(f"  {C.GREEN}✓{C.RST} {tbl}: {len(data)} records → {out_path.name}")

    for code in ["DGFIP", "PNF", "SPJ_MC"]:
        sim = simulate_audit(conn, code)
        out_path = export_dir / f"simulation_{code}.json"
        with open(out_path, "w") as f:
            json.dump(sim, f, indent=2, ensure_ascii=False, default=str)
        print(f"  {C.GREEN}✓{C.RST} Simulation {code} → {out_path.name}")
    conn.close()
    print(f"\n  Exported to: {export_dir}")


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Compliance Tolerance Engine", formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="Initialize database and seed data")

    p = sub.add_parser("obligations", help="List obligations")
    p.add_argument("--jurisdiction", "-j"); p.add_argument("--domain", "-d")
    p.add_argument("--track", "-t", choices=["fiscal", "non_fiscal"])
    p.add_argument("--status", "-s", choices=["compliant", "marginal", "non_compliant", "unknown"])

    p = sub.add_parser("status", help="Compliance matrix")
    p.add_argument("--obligation-ref", "-r")

    p = sub.add_parser("assess", help="Assess compliance status")
    p.add_argument("ref"); p.add_argument("status", choices=["compliant", "marginal", "non_compliant", "unknown"])
    p.add_argument("--deviation", type=float); p.add_argument("--notes", "-n")

    p = sub.add_parser("cumulation", help="Cumulation heat map")
    p.add_argument("--institution", "-i")

    p = sub.add_parser("institutions", help="Institution profiles")
    p.add_argument("--code", "-c")

    p = sub.add_parser("mitigate", help="Mitigation actions")
    p.add_argument("--list", "-l", action="store_true", default=True)
    p.add_argument("--add"); p.add_argument("--complete", type=int)
    p.add_argument("--update"); p.add_argument("--obligation-ref")
    p.add_argument("--institution-code"); p.add_argument("--priority", choices=["critical", "high", "medium", "low"])
    p.add_argument("--all", "-a", action="store_true")

    p = sub.add_parser("firewall", help="Two-track firewall")
    p.add_argument("--check", action="store_true"); p.add_argument("--log", action="store_true")

    p = sub.add_parser("audit", help="Audit trail and simulation")
    p.add_argument("--simulate", "-s")

    sub.add_parser("dashboard", help="Full compliance dashboard")

    p = sub.add_parser("alerts", help="Alert management")
    p.add_argument("--ack", type=int); p.add_argument("--resolve", type=int)

    p = sub.add_parser("search", help="FTS5 search")
    p.add_argument("query", nargs="+")

    sub.add_parser("stats", help="Statistics")

    p = sub.add_parser("export", help="Export compliance data")
    p.add_argument("dir", nargs="?")

    args = parser.parse_args()
    if not args.command:
        parser.print_help(); return

    COMMANDS = {
        "init": cmd_init, "obligations": cmd_obligations, "status": cmd_status,
        "assess": cmd_assess, "cumulation": cmd_cumulation, "institutions": cmd_institutions,
        "mitigate": cmd_mitigate, "firewall": cmd_firewall, "audit": cmd_audit,
        "dashboard": cmd_dashboard, "alerts": cmd_alerts, "search": cmd_search,
        "stats": cmd_stats, "export": cmd_export,
    }
    COMMANDS[args.command](args)


if __name__ == "__main__":
    main()
