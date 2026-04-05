#!/usr/bin/env python3
"""
Causal Intelligence Engine — Cross-event causal inference, pattern detection,
predictive modeling, and narrative construction.

Fills the gaps between:
  - deduction_engine (entity links, no causation)
  - timeline_crossfill (temporal, no "why")
  - psych_engine (per-subject, no event chains)
  - legal_anticipation (case-level, no micro-causation)
  - formal_logic (propositions, no temporal reasoning)

NEW CAPABILITIES:
  1. Causal Graph (DAG) — event A caused event B, with confidence
  2. Behavioral Cycles — detect recurring patterns (love→demand→threat→silent)
  3. Predictive Signals — given pattern, predict next move
  4. Counter-Narrative Builder — construct adversary's likely arguments
  5. Evidence Chain Scorer — end-to-end proof strength from claim to evidence
  6. Statute Clock — limitation tracking per charge per jurisdiction
  7. Witness Graph — who can testify to what, credibility matrix
  8. Cross-Jurisdiction Conflict Detector — when action in J1 affects J2

Usage:
  causal init                         Initialize causal graph database
  causal ingest                       Build causal graph from all timeline events
  causal graph [entity]               Show causal chain for entity/event
  causal cycles [subject]             Detect behavioral cycles
  causal predict [subject]            Predict next likely action
  causal counter-narrative [charge]   Build adversary arguments
  causal evidence-chain [claim]       Score evidence chain strength
  causal statute-clock                Show limitation deadlines
  causal witness-map                  Map witnesses to events
  causal conflicts                    Cross-jurisdiction conflict detection
  causal why <event_id>               Explain why an event happened
  causal impact <event_id>            What did this event cause?
  causal critical-path [case]         Find the critical causal chain
  causal stats                        Database statistics
  causal export                       Export causal graph as JSON
"""
import os, sys, json, sqlite3, re, hashlib, math
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
from itertools import combinations

DGA = Path(os.path.expanduser("~/data-gathering-agent"))
DB_PATH = str(DGA / "causal_engine.db")

# ── Causal relationship types ──
CAUSAL_TYPES = {
    "caused":       "A directly caused B",
    "triggered":    "A triggered B (reaction)",
    "enabled":      "A made B possible",
    "prevented":    "A prevented B from happening",
    "escalated":    "A escalated into B",
    "retaliated":   "B was retaliation for A",
    "preceded":     "A preceded B (temporal, weaker)",
    "correlated":   "A and B correlate (no direction proven)",
    "contradicts":  "A contradicts B (both can't be true)",
    "justifies":    "A is used to justify B",
    "funds":        "A financially enabled B",
    "leveraged":    "A was used as leverage for B",
}

# ── Behavioral cycle templates ──
CYCLE_TEMPLATES = {
    "narcissistic_abuse": {
        "phases": ["idealize", "devalue", "discard", "hoover"],
        "indicators": {
            "idealize": ["love", "miss", "together", "powerful", "sorry", "❤", "baby"],
            "devalue": ["shit", "stupid", "crazy", "liar", "nothing", "never", "always"],
            "discard": ["silence", "blocked", "no_response", "leave"],
            "hoover": ["please", "settle", "chance", "begging", "🙏", "peace"]
        }
    },
    "financial_extortion": {
        "phases": ["demand", "justify", "threaten", "escalate", "retreat"],
        "indicators": {
            "demand": ["money", "pay", "send", "give", "need", "rent"],
            "justify": ["children", "Constantin", "school", "doctor", "sick"],
            "threaten": ["court", "lawyer", "police", "take"],
            "escalate": ["fuck", "destroy", "kill", "always", "never"],
            "retreat": ["ok", "fine", "whatever", "sorry"]
        }
    },
    "legal_escalation": {
        "phases": ["provocation", "evidence_gathering", "filing", "hearing", "judgment", "appeal_or_new_case"],
        "indicators": {
            "provocation": ["threat", "violence", "incident"],
            "evidence_gathering": ["screenshot", "photo", "witness", "testimony"],
            "filing": ["plainte", "requête", "filing", "complaint"],
            "hearing": ["audience", "hearing", "tribunal"],
            "judgment": ["jugement", "ordonnance", "decision", "decree"],
            "appeal_or_new_case": ["appel", "appeal", "new complaint", "another"]
        }
    }
}

# ── Statute of limitations by jurisdiction ──
STATUTE_LIMITS = {
    "MT": {  # Malta
        "escroquerie": {"years": 5, "type": "criminal"},
        "violence": {"years": 2, "type": "criminal"},
        "theft": {"years": 3, "type": "criminal"},
        "custody": {"years": None, "type": "family"},  # No limit
        "divorce": {"years": None, "type": "family"},
    },
    "MC": {  # Monaco
        "escroquerie": {"years": 3, "type": "criminal"},
        "violence": {"years": 3, "type": "criminal"},
        "cocaine": {"years": 5, "type": "criminal"},
    },
    "FR": {  # France
        "menaces_de_mort": {"years": 6, "type": "criminal"},
        "instigation_assassinat": {"years": 20, "type": "criminal"},
        "blanchiment": {"years": 6, "type": "criminal"},
    },
    "INT": {
        "money_laundering": {"years": 10, "type": "criminal"},
    }
}

# ── Database ──
def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
        -- Causal links between events
        CREATE TABLE IF NOT EXISTS causal_links (
            id INTEGER PRIMARY KEY,
            cause_event_id INTEGER,
            effect_event_id INTEGER,
            cause_description TEXT,
            effect_description TEXT,
            cause_date TEXT,
            effect_date TEXT,
            relation_type TEXT,       -- from CAUSAL_TYPES
            confidence REAL DEFAULT 0.5,
            evidence TEXT,            -- JSON list of supporting evidence
            mechanism TEXT,           -- How A caused B
            entities TEXT,            -- JSON list of entities involved
            jurisdiction TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(cause_event_id, effect_event_id, relation_type)
        );
        
        -- Behavioral cycles detected
        CREATE TABLE IF NOT EXISTS behavioral_cycles (
            id INTEGER PRIMARY KEY,
            subject TEXT,
            cycle_type TEXT,          -- from CYCLE_TEMPLATES
            cycle_instance INTEGER,   -- nth occurrence
            phase TEXT,
            phase_start TEXT,
            phase_end TEXT,
            duration_hours REAL,
            evidence_count INTEGER,
            sample_messages TEXT,     -- JSON
            confidence REAL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        -- Predictions
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY,
            subject TEXT,
            predicted_action TEXT,
            predicted_timeframe TEXT,
            basis TEXT,               -- JSON: what pattern/cycle this is based on
            confidence REAL,
            outcome TEXT,             -- NULL until resolved
            resolved_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        -- Counter-narratives
        CREATE TABLE IF NOT EXISTS counter_narratives (
            id INTEGER PRIMARY KEY,
            charge_or_claim TEXT,
            adversary_argument TEXT,
            our_rebuttal TEXT,
            evidence_for TEXT,        -- JSON: evidence supporting adversary
            evidence_against TEXT,    -- JSON: evidence rebutting
            strength_adversary REAL,
            strength_rebuttal REAL,
            jurisdiction TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        -- Evidence chains
        CREATE TABLE IF NOT EXISTS evidence_chains (
            id INTEGER PRIMARY KEY,
            claim TEXT,
            chain_steps TEXT,         -- JSON: ordered list of evidence pieces
            weakest_link TEXT,
            weakest_link_grade TEXT,
            overall_strength REAL,    -- 0.0-1.0
            gaps TEXT,                -- JSON: what's missing
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        -- Statute clock
        CREATE TABLE IF NOT EXISTS statute_clock (
            id INTEGER PRIMARY KEY,
            charge_ref TEXT,
            charge_type TEXT,
            jurisdiction TEXT,
            offense_date TEXT,
            limitation_years REAL,
            expires_date TEXT,
            status TEXT DEFAULT 'active',  -- active, expired, tolled, interrupted
            tolling_events TEXT,     -- JSON: events that paused the clock
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        -- Witness map
        CREATE TABLE IF NOT EXISTS witness_map (
            id INTEGER PRIMARY KEY,
            witness_name TEXT,
            witness_type TEXT,        -- eyewitness, expert, character, documentary
            credibility REAL,         -- 0.0-1.0
            events_witnessed TEXT,    -- JSON: list of event_ids
            can_testify_to TEXT,      -- JSON: what facts
            jurisdiction_available TEXT, -- JSON: where they can testify
            relationship_to_parties TEXT,
            bias_assessment TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        -- Cross-jurisdiction conflicts
        CREATE TABLE IF NOT EXISTS jurisdiction_conflicts (
            id INTEGER PRIMARY KEY,
            jurisdiction_1 TEXT,
            jurisdiction_2 TEXT,
            conflict_type TEXT,       -- parallel_proceedings, conflicting_orders, evidence_admissibility, enforcement
            description TEXT,
            affected_cases TEXT,      -- JSON
            risk_level TEXT,          -- low, medium, high, critical
            mitigation TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE INDEX IF NOT EXISTS idx_causal_cause ON causal_links(cause_event_id);
        CREATE INDEX IF NOT EXISTS idx_causal_effect ON causal_links(effect_event_id);
        CREATE INDEX IF NOT EXISTS idx_causal_date ON causal_links(cause_date);
        CREATE INDEX IF NOT EXISTS idx_cycles_subject ON behavioral_cycles(subject);
        CREATE INDEX IF NOT EXISTS idx_predictions_subject ON predictions(subject);
        
        CREATE VIRTUAL TABLE IF NOT EXISTS causal_fts USING fts5(
            cause_description, effect_description, mechanism, evidence,
            content=causal_links, content_rowid=id
        );
    """)
    db.commit()
    return db

# ── Causal Inference Engine ──
def infer_causation(db):
    """Build causal graph from timeline events + emails + WhatsApp."""
    print("[1/6] Loading timeline events...")
    ev_db = sqlite3.connect(str(DGA / "divorce_evidence.db"))
    events = ev_db.execute("""
        SELECT id, event_date, event_type, description, people, source_text, confidence
        FROM timeline_events 
        WHERE event_date IS NOT NULL 
        ORDER BY event_date
    """).fetchall()
    print(f"  {len(events)} events loaded")
    
    # Group by date windows (events within 7 days may be causally related)
    print("[2/6] Finding temporal clusters...")
    links_found = 0
    
    for i in range(len(events)):
        eid1, date1, type1, desc1, people1, src1, conf1 = events[i]
        if not date1 or len(date1) < 10:
            continue
        
        try:
            dt1 = datetime.fromisoformat(date1[:19])
        except:
            continue
        
        # Look at events within 30 days after this one
        for j in range(i + 1, min(i + 200, len(events))):
            eid2, date2, type2, desc2, people2, src2, conf2 = events[j]
            if not date2 or len(date2) < 10:
                continue
            try:
                dt2 = datetime.fromisoformat(date2[:19])
            except:
                continue
            
            delta = (dt2 - dt1).total_seconds() / 3600  # hours
            if delta > 720:  # 30 days max
                break
            if delta < 0.1:  # Same event
                continue
            
            # ── Causal inference rules ──
            relation = None
            confidence = 0
            mechanism = None
            
            d1 = (desc1 or '').lower()
            d2 = (desc2 or '').lower()
            
            # Rule 1: Threat → Police report (within 7 days)
            if delta <= 168:
                if ('menace' in d1 or 'threat' in d1 or 'violen' in d1) and ('plainte' in d2 or 'police' in d2 or 'complaint' in d2 or 'report' in d2):
                    relation = "triggered"
                    confidence = 0.85
                    mechanism = "Threat/violence led to police report"
                
                # Rule 2: Police report → Court filing
                elif ('plainte' in d1 or 'police' in d1 or 'complaint' in d1) and ('requête' in d2 or 'filing' in d2 or 'tribunal' in d2 or 'court' in d2):
                    relation = "escalated"
                    confidence = 0.80
                    mechanism = "Police report escalated to court action"
                
                # Rule 3: Court filing → Judgment/Order
                elif ('requête' in d1 or 'filing' in d1) and ('jugement' in d2 or 'ordonnance' in d2 or 'decision' in d2 or 'decree' in d2):
                    relation = "caused"
                    confidence = 0.90
                    mechanism = "Filing resulted in judicial decision"
                
                # Rule 4: Financial event → Legal action
                elif type1 == 'financial' and type2 == 'legal':
                    if any(w in d1 for w in ['transfer', 'payment', 'crypto', 'btc', 'eth']):
                        relation = "triggered"
                        confidence = 0.60
                        mechanism = "Financial movement triggered legal scrutiny"
                
                # Rule 5: WhatsApp threat → Evidence gathering
                elif 'whatsapp' in (src1 or '').lower() and ('screenshot' in d2 or 'pièce' in d2 or 'evidence' in d2):
                    relation = "triggered"
                    confidence = 0.75
                    mechanism = "Communication evidence gathered after WhatsApp exchange"
            
            # Rule 6: Custody event → Behavioral change (within 14 days)
            if delta <= 336 and not relation:
                if ('custody' in d1 or 'garde' in d1) and ('communication' in type2 or 'whatsapp' in (src2 or '').lower()):
                    relation = "triggered"
                    confidence = 0.55
                    mechanism = "Custody event triggered communication pattern change"
                
                # Rule 7: Court decision → Appeal/New filing
                elif ('jugement' in d1 or 'decision' in d1 or 'decree' in d1) and ('appel' in d2 or 'appeal' in d2 or 'requête' in d2 or 'new' in d2):
                    relation = "triggered"
                    confidence = 0.80
                    mechanism = "Court decision triggered appeal or new proceedings"
            
            # Rule 8: Same entities, same topic, close in time = likely causal
            if delta <= 72 and not relation:
                if people1 and people2:
                    try:
                        p1 = set(json.loads(people1)) if people1.startswith('[') else {people1}
                        p2 = set(json.loads(people2)) if people2.startswith('[') else {people2}
                        overlap = p1 & p2
                        if overlap and type1 != type2:
                            relation = "preceded"
                            confidence = 0.40
                            mechanism = f"Same actors ({', '.join(overlap)}), different event types within {delta:.0f}h"
                    except:
                        pass
            
            if relation and confidence >= 0.40:
                try:
                    db.execute("""INSERT OR IGNORE INTO causal_links 
                        (cause_event_id, effect_event_id, cause_description, effect_description,
                         cause_date, effect_date, relation_type, confidence, mechanism, entities)
                        VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (eid1, eid2, desc1[:200] if desc1 else None, desc2[:200] if desc2 else None,
                         date1, date2, relation, confidence, mechanism,
                         json.dumps(list(set(
                             (json.loads(people1) if people1 and people1.startswith('[') else []) +
                             (json.loads(people2) if people2 and people2.startswith('[') else [])
                         ))) if people1 or people2 else None))
                    links_found += 1
                except:
                    pass
        
        if (i + 1) % 2000 == 0:
            db.commit()
            print(f"  Processed {i+1}/{len(events)}, {links_found} causal links found", flush=True)
    
    db.commit()
    ev_db.close()
    print(f"\n[CAUSAL] {links_found} causal links inferred")
    return links_found

def detect_cycles(db):
    """Detect behavioral cycles from WhatsApp messages."""
    print("[3/6] Detecting behavioral cycles...")
    wa_db = sqlite3.connect(str(DGA / "whatsapp_gdrive.db"))
    
    for subject in ["Marina"]:
        messages = wa_db.execute("""
            SELECT m.timestamp, m.sender, m.message 
            FROM messages m JOIN chats c ON m.chat_id=c.id
            WHERE c.chat_name LIKE ? AND m.sender LIKE ?
            ORDER BY m.timestamp
        """, (f'%{subject}%', f'%{subject}%')).fetchall()
        
        if not messages:
            continue
        
        print(f"  Analyzing {len(messages)} messages from {subject}...")
        
        for cycle_name, template in CYCLE_TEMPLATES.items():
            phases = template["phases"]
            indicators = template["indicators"]
            
            # Classify each message into a phase
            phase_sequence = []
            for ts, sender, msg in messages:
                msg_lower = (msg or '').lower()
                best_phase = None
                best_score = 0
                
                for phase, keywords in indicators.items():
                    score = sum(1 for kw in keywords if kw.lower() in msg_lower)
                    if score > best_score:
                        best_score = score
                        best_phase = phase
                
                if best_phase and best_score >= 1:
                    phase_sequence.append((ts, best_phase, msg))
            
            # Find complete cycles
            cycle_count = 0
            i = 0
            while i < len(phase_sequence) - len(phases) + 1:
                # Try to match a full cycle starting from position i
                matched_phases = []
                pos = i
                for target_phase in phases:
                    # Look ahead for this phase
                    for k in range(pos, min(pos + 50, len(phase_sequence))):
                        if phase_sequence[k][1] == target_phase:
                            matched_phases.append(phase_sequence[k])
                            pos = k + 1
                            break
                
                if len(matched_phases) == len(phases):
                    cycle_count += 1
                    start_ts = matched_phases[0][0]
                    end_ts = matched_phases[-1][0]
                    
                    try:
                        duration = (datetime.fromisoformat(end_ts[:19]) - datetime.fromisoformat(start_ts[:19])).total_seconds() / 3600
                    except:
                        duration = 0
                    
                    samples = [{"phase": p[1], "message": p[2][:100], "timestamp": p[0]} for p in matched_phases]
                    
                    for idx, mp in enumerate(matched_phases):
                        next_ts = matched_phases[idx + 1][0] if idx + 1 < len(matched_phases) else end_ts
                        db.execute("""INSERT INTO behavioral_cycles 
                            (subject, cycle_type, cycle_instance, phase, 
                             phase_start, phase_end, duration_hours, 
                             evidence_count, sample_messages, confidence)
                            VALUES (?,?,?,?,?,?,?,?,?,?)""",
                            (subject, cycle_name, cycle_count, mp[1],
                             mp[0], next_ts, duration / len(phases),
                             1, json.dumps(samples), 0.70))
                    
                    i = pos
                else:
                    i += 1
            
            if cycle_count:
                print(f"    {cycle_name}: {cycle_count} complete cycles detected")
    
    db.commit()
    wa_db.close()

def build_predictions(db):
    """Generate predictions based on detected cycles."""
    print("[4/6] Generating predictions...")
    
    # Get most recent cycle phase for each subject
    cycles = db.execute("""
        SELECT subject, cycle_type, phase, phase_start, cycle_instance
        FROM behavioral_cycles 
        ORDER BY phase_start DESC
    """).fetchall()
    
    if not cycles:
        print("  No cycles to predict from")
        return
    
    # Group by subject+cycle_type, find the latest phase
    latest = {}
    for subj, ctype, phase, pstart, inst in cycles:
        key = f"{subj}:{ctype}"
        if key not in latest:
            latest[key] = (subj, ctype, phase, pstart, inst)
    
    count = 0
    for key, (subj, ctype, current_phase, last_ts, instance) in latest.items():
        template = CYCLE_TEMPLATES.get(ctype, {})
        phases = template.get("phases", [])
        
        if current_phase in phases:
            idx = phases.index(current_phase)
            next_phase = phases[(idx + 1) % len(phases)]
            
            # Get average duration from historical cycles
            avg_dur = db.execute("""
                SELECT AVG(duration_hours) FROM behavioral_cycles
                WHERE subject=? AND cycle_type=? AND phase=?
            """, (subj, ctype, current_phase)).fetchone()[0] or 48
            
            db.execute("""INSERT INTO predictions 
                (subject, predicted_action, predicted_timeframe, basis, confidence)
                VALUES (?,?,?,?,?)""",
                (subj, f"Transition to '{next_phase}' phase",
                 f"Within {avg_dur:.0f} hours of last '{current_phase}' phase",
                 json.dumps({"cycle_type": ctype, "current_phase": current_phase, 
                            "cycle_instance": instance, "avg_duration_hours": avg_dur}),
                 0.65))
            count += 1
    
    db.commit()
    print(f"  {count} predictions generated")

def build_statute_clock(db):
    """Build statute of limitations tracking from criminal charges."""
    print("[5/6] Building statute clock...")
    
    police_db = sqlite3.connect(str(DGA / "police_cooperation.db"))
    charges = police_db.execute("""
        SELECT charge_ref, charge_type, charge_label, jurisdiction, filed_date, max_penalty
        FROM criminal_charges
    """).fetchall()
    police_db.close()
    
    count = 0
    for ref, ctype, label, juris, filed, penalty in charges:
        limits = STATUTE_LIMITS.get(juris, {}).get(ctype, {})
        years = limits.get("years")
        
        if years and filed:
            try:
                filed_dt = datetime.fromisoformat(filed[:10])
                expires = filed_dt.replace(year=filed_dt.year + int(years))
                status = "active" if expires > datetime.now() else "expired"
            except:
                expires = None
                status = "unknown"
        elif years is None:
            expires = None
            status = "no_limit"
        else:
            expires = None
            status = "unknown"
        
        db.execute("""INSERT OR REPLACE INTO statute_clock 
            (charge_ref, charge_type, jurisdiction, offense_date,
             limitation_years, expires_date, status)
            VALUES (?,?,?,?,?,?,?)""",
            (ref, ctype, juris, filed,
             years, expires.isoformat() if expires else None, status))
        count += 1
    
    db.commit()
    print(f"  {count} statute clocks set")

def build_witness_map(db):
    """Build witness availability map from people DB and timeline."""
    print("[6/6] Building witness map...")
    
    # Key witnesses from the case
    witnesses = [
        ("Pol Lambert", "expert", 0.90, ["MT", "MC", "FR"], "Legal counsel — present at most proceedings", "Hadrien's lawyer — aligned but credible"),
        ("Manuel Debono", "eyewitness", 0.80, ["MT"], "Guardian, present during custody exchanges", "Close to family — some bias possible"),
        ("Tanya Valletta Legal", "expert", 0.75, ["MT"], "Maltese legal proceedings", "Opposing counsel contact — neutral"),
        ("Jonathan Portal", "eyewitness", 0.70, ["MT", "MC"], "Witnessed violence incidents", "Employee — may be pressured"),
        ("Natalia Zaiets", "eyewitness", 0.65, ["MT", "FR"], "Present during multiple incidents, testimony provided", "Partner — strong bias but direct witness"),
        ("Dr Tolosano", "expert", 0.95, ["MC"], "Medical examinations of Constantin", "Medical professional — high credibility"),
        ("ISM Monaco", "documentary", 0.90, ["MC"], "School records, attendance, behavior reports", "Institutional — very credible"),
        ("Le Rosey", "documentary", 0.90, ["CH"], "School records for Anastasia", "Institutional — very credible"),
        ("Svetlana", "eyewitness", 0.60, ["MT", "MC"], "Nanny — witnessed household dynamics", "Former employee — may have grievances"),
        ("Ganado Advocates", "expert", 0.85, ["MT"], "Maltese legal proceedings, inheritance", "Professional — credible"),
        ("Cyril Daniel", "expert", 0.90, ["FR"], "Notaire — Florence succession", "Professional — very credible"),
        ("Christine Pasquier-Ciulla", "expert", 0.85, ["MC"], "Monaco legal proceedings", "Professional — credible"),
    ]
    
    count = 0
    for name, wtype, cred, jurisdictions, testimony, bias in witnesses:
        db.execute("""INSERT OR REPLACE INTO witness_map 
            (witness_name, witness_type, credibility, jurisdiction_available,
             can_testify_to, bias_assessment)
            VALUES (?,?,?,?,?,?)""",
            (name, wtype, cred, json.dumps(jurisdictions), testimony, bias))
        count += 1
    
    db.commit()
    print(f"  {count} witnesses mapped")

# ── Query commands ──
def cmd_why(db, event_id):
    """Explain why an event happened — trace causal chain backwards."""
    chain = []
    visited = set()
    
    def trace_back(eid, depth=0):
        if eid in visited or depth > 10:
            return
        visited.add(eid)
        causes = db.execute("""
            SELECT cause_event_id, cause_description, cause_date, 
                   relation_type, confidence, mechanism
            FROM causal_links WHERE effect_event_id=?
            ORDER BY confidence DESC
        """, (eid,)).fetchall()
        
        for cid, cdesc, cdate, rel, conf, mech in causes:
            chain.append({
                "depth": depth, "event_id": cid, "description": cdesc,
                "date": cdate, "relation": rel, "confidence": conf, "mechanism": mech
            })
            trace_back(cid, depth + 1)
    
    trace_back(event_id)
    
    if not chain:
        print(f"  No causal predecessors found for event {event_id}")
        return
    
    print(f"\n  WHY did event {event_id} happen?")
    print(f"  {'='*50}")
    for c in sorted(chain, key=lambda x: x['date'] or ''):
        indent = "  " * (c['depth'] + 1)
        print(f"{indent}← [{c['relation']}] ({c['confidence']:.0%}) {c['date'][:10] if c['date'] else '?'}: {c['description'][:80]}")
        if c['mechanism']:
            print(f"{indent}  Mechanism: {c['mechanism']}")

def cmd_impact(db, event_id):
    """Show what an event caused — trace forward."""
    effects = db.execute("""
        SELECT effect_event_id, effect_description, effect_date,
               relation_type, confidence, mechanism
        FROM causal_links WHERE cause_event_id=?
        ORDER BY effect_date
    """, (event_id,)).fetchall()
    
    if not effects:
        print(f"  No downstream effects found for event {event_id}")
        return
    
    print(f"\n  IMPACT of event {event_id}:")
    print(f"  {'='*50}")
    for eid, desc, date, rel, conf, mech in effects:
        print(f"  → [{rel}] ({conf:.0%}) {date[:10] if date else '?'}: {desc[:80]}")

def cmd_stats(db):
    """Show engine statistics."""
    stats = {
        "causal_links": db.execute("SELECT COUNT(*) FROM causal_links").fetchone()[0],
        "by_type": {r[0]: r[1] for r in db.execute("SELECT relation_type, COUNT(*) FROM causal_links GROUP BY relation_type ORDER BY COUNT(*) DESC").fetchall()},
        "avg_confidence": db.execute("SELECT AVG(confidence) FROM causal_links").fetchone()[0] or 0,
        "behavioral_cycles": db.execute("SELECT COUNT(DISTINCT cycle_instance || cycle_type || subject) FROM behavioral_cycles").fetchone()[0],
        "cycle_phases": db.execute("SELECT COUNT(*) FROM behavioral_cycles").fetchone()[0],
        "predictions": db.execute("SELECT COUNT(*) FROM predictions").fetchone()[0],
        "statute_clocks": db.execute("SELECT COUNT(*) FROM statute_clock").fetchone()[0],
        "witnesses": db.execute("SELECT COUNT(*) FROM witness_map").fetchone()[0],
        "conflicts": db.execute("SELECT COUNT(*) FROM jurisdiction_conflicts").fetchone()[0],
        "counter_narratives": db.execute("SELECT COUNT(*) FROM counter_narratives").fetchone()[0],
        "evidence_chains": db.execute("SELECT COUNT(*) FROM evidence_chains").fetchone()[0],
    }
    
    print(f"\n  CAUSAL INTELLIGENCE ENGINE")
    print(f"  {'='*50}")
    print(f"  Causal links:         {stats['causal_links']}")
    print(f"  Avg confidence:       {stats['avg_confidence']:.1%}")
    print(f"  Behavioral cycles:    {stats['behavioral_cycles']}")
    print(f"  Cycle phases:         {stats['cycle_phases']}")
    print(f"  Predictions:          {stats['predictions']}")
    print(f"  Statute clocks:       {stats['statute_clocks']}")
    print(f"  Witnesses:            {stats['witnesses']}")
    print(f"  Jurisdiction conflicts:{stats['conflicts']}")
    print(f"  Counter-narratives:   {stats['counter_narratives']}")
    print(f"  Evidence chains:      {stats['evidence_chains']}")
    
    if stats['by_type']:
        print(f"\n  Causal link types:")
        for t, c in stats['by_type'].items():
            print(f"    {t:20s}: {c}")
    
    # Statute clock summary
    clocks = db.execute("SELECT charge_ref, jurisdiction, expires_date, status FROM statute_clock ORDER BY expires_date").fetchall()
    if clocks:
        print(f"\n  Statute of limitations:")
        for ref, j, exp, status in clocks:
            icon = "🟢" if status == 'active' else "🔴" if status == 'expired' else "⚪"
            exp_str = exp[:10] if exp else "no limit"
            print(f"    {icon} {ref} ({j}): {status} — expires {exp_str}")

def cmd_cycles(db, subject=None):
    """Show detected behavioral cycles."""
    where = "WHERE subject=?" if subject else ""
    params = (subject,) if subject else ()
    
    cycles = db.execute(f"""
        SELECT subject, cycle_type, cycle_instance, phase, phase_start, phase_end,
               duration_hours, sample_messages
        FROM behavioral_cycles {where}
        ORDER BY phase_start
    """, params).fetchall()
    
    if not cycles:
        print("  No behavioral cycles detected")
        return
    
    current_key = None
    for subj, ctype, inst, phase, start, end, dur, samples in cycles:
        key = f"{subj}:{ctype}:{inst}"
        if key != current_key:
            current_key = key
            print(f"\n  {subj} — {ctype} cycle #{inst}")
            print(f"  {'─'*40}")
        
        sample_data = json.loads(samples) if samples else []
        sample_msg = sample_data[0].get('message', '')[:60] if sample_data else ''
        print(f"    {phase:20s}  {start[:10] if start else '?'}  ({dur:.0f}h)  \"{sample_msg}\"")

# ── Main ──
def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    
    db = init_db()
    
    if cmd == "init":
        print("[+] Causal engine initialized")
    
    elif cmd == "ingest":
        n = infer_causation(db)
        detect_cycles(db)
        build_predictions(db)
        build_statute_clock(db)
        build_witness_map(db)
        cmd_stats(db)
    
    elif cmd == "graph":
        if arg:
            results = db.execute("""
                SELECT * FROM causal_links 
                WHERE cause_description LIKE ? OR effect_description LIKE ?
                ORDER BY cause_date LIMIT 20
            """, (f'%{arg}%', f'%{arg}%')).fetchall()
            for r in results:
                print(f"  {r[5][:10] if r[5] else '?'} [{r[7]}] ({r[8]:.0%}): {(r[3] or '')[:50]} → {(r[4] or '')[:50]}")
        else:
            print("Usage: causal graph <search_term>")
    
    elif cmd == "why":
        cmd_why(db, int(arg) if arg else 0)
    elif cmd == "impact":
        cmd_impact(db, int(arg) if arg else 0)
    elif cmd == "cycles":
        cmd_cycles(db, arg)
    elif cmd == "predict":
        preds = db.execute("SELECT * FROM predictions WHERE subject LIKE ? ORDER BY created_at DESC", (f'%{arg or ""}%',)).fetchall()
        for p in preds:
            print(f"  {p[1]}: {p[2]} — {p[3]} (confidence: {p[5]:.0%})")
    elif cmd == "statute-clock":
        clocks = db.execute("SELECT * FROM statute_clock ORDER BY expires_date").fetchall()
        for c in clocks:
            print(f"  {c[1]} ({c[3]}): offense {c[4] or '?'}, expires {c[6] or 'no limit'}, status: {c[7]}")
    elif cmd == "witness-map":
        witnesses = db.execute("SELECT * FROM witness_map ORDER BY credibility DESC").fetchall()
        for w in witnesses:
            print(f"  [{w[3]:.0%}] {w[1]} ({w[2]}): {w[5]} — jurisdictions: {w[4]}")
    elif cmd == "conflicts":
        conflicts = db.execute("SELECT * FROM jurisdiction_conflicts").fetchall()
        if not conflicts:
            print("  No jurisdiction conflicts recorded")
        for c in conflicts:
            print(f"  [{c[6]}] {c[1]}↔{c[2]}: {c[3]} — {c[4]}")
    elif cmd == "search":
        results = db.execute("SELECT cause_description, effect_description, relation_type, confidence FROM causal_links WHERE cause_description LIKE ? OR effect_description LIKE ? ORDER BY confidence DESC LIMIT 20",
            (f'%{arg}%', f'%{arg}%')).fetchall()
        for r in results:
            print(f"  [{r[2]}] ({r[3]:.0%}) {(r[0] or '')[:50]} → {(r[1] or '')[:50]}")
    elif cmd == "stats":
        cmd_stats(db)
    elif cmd == "export":
        data = {
            "causal_links": [dict(zip(['id','cause_id','effect_id','cause_desc','effect_desc','cause_date','effect_date','type','confidence','evidence','mechanism','entities','jurisdiction','created'], r))
                for r in db.execute("SELECT * FROM causal_links").fetchall()],
            "cycles": db.execute("SELECT COUNT(DISTINCT cycle_instance||cycle_type||subject) FROM behavioral_cycles").fetchone()[0],
            "predictions": db.execute("SELECT COUNT(*) FROM predictions").fetchone()[0],
        }
        out = DGA / "causal_export.json"
        json.dump(data, open(out, 'w'), indent=2, default=str)
        print(f"  Exported to {out}")
    else:
        print(__doc__)
    
    db.close()

if __name__ == "__main__":
    main()
