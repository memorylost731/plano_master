#!/usr/bin/env python3
"""
Adversary Strategy Predictor — Combines causal engine, psych profiles,
game theory, legal anticipation, behavioral cycles, and financial data
to predict Marina's next moves across all domains.

Usage:
  adversary predict                Full prediction report
  adversary next-move              Most likely next action
  adversary legal-forecast         Predicted legal moves
  adversary financial-forecast     Predicted financial moves
  adversary custody-forecast       Predicted custody/children moves
  adversary counter-strategy       Recommended counter-moves
  adversary red-team <scenario>    Role-play as Marina's legal team
  adversary war-game               Interactive adversarial simulation
  adversary briefing               Executive summary for lawyers
  adversary stats                  Engine statistics
"""
import os, sys, json, sqlite3, requests, re
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict

DGA = Path(os.path.expanduser("~/data-gathering-agent"))
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://100.71.235.99:11434")
MODEL = "huihui_ai/mistral-small-abliterated:24b-instruct-2501-q4_K_M"
DB_PATH = str(DGA / "adversary_predictor.db")

# ── Marina's known strategic patterns ──
MARINA_PLAYBOOK = {
    "legal_escalation": {
        "pattern": "When losing in one jurisdiction, opens front in another",
        "historical": [
            "MT custody → MC escroquerie (2020)",
            "MC violence → FR menaces de mort (2020)",
            "MT divorce proceedings → MC mainlevée (2021)",
            "MT annulment filed → anticipate new MC/FR filing"
        ],
        "probability": 0.80,
        "counter": "Pre-emptive filings, institutional coalition (police TF + CPM + victim support)"
    },
    "financial_extraction_cycle": {
        "pattern": "Demand → justify with children → threaten court → escalate → retreat → repeat",
        "cycle_avg_days": 34,
        "probability": 0.90,
        "counter": "Document every demand, route all payments through lawyer, maintain paper trail"
    },
    "parental_alienation": {
        "pattern": "Uses Constantin as emotional weapon, restricts access, makes medical claims",
        "triggers": ["New partner visible", "Pension discussion", "Court loss"],
        "probability": 0.75,
        "counter": "School records, medical records, third-party witnesses (Manuel Debono)"
    },
    "evidence_fabrication": {
        "pattern": "Screenshots edited/out of context, false police reports, coached witnesses",
        "historical": ["Violence claims contradicted by CCTV", "Coached Constantin testimony"],
        "probability": 0.60,
        "counter": "Forensic integrity seals, chain of custody, metadata analysis"
    },
    "jurisdiction_shopping": {
        "pattern": "Files in most favorable jurisdiction, sometimes simultaneously",
        "venues": {"MT": "custody/divorce", "MC": "criminal/financial", "FR": "threats/instigation"},
        "probability": 0.70,
        "counter": "Lis pendens, Brussels IIter regulation, forum non conveniens arguments"
    },
    "hoovering_before_court": {
        "pattern": "Love-bombs and offers settlement right before unfavorable hearing",
        "goal": "Extract concessions under time pressure, or create appearance of reasonableness for judge",
        "probability": 0.85,
        "counter": "Never negotiate under time pressure, all offers through lawyers, document the pattern"
    },
    "crypto_concealment": {
        "pattern": "Denies knowledge of crypto, claims Hadrien controls everything",
        "assets": "163 BTC + 875K ATOM + 7,243 ETH + 1,100 ETH distributed",
        "probability": 0.95,
        "counter": "Blockchain forensics, exchange KYC records, taint analysis, Ledger device forensics"
    },
    "victim_narrative_media": {
        "pattern": "Presents as abused wife to institutions, police, schools, social services",
        "targets": ["Police", "Social workers", "School staff", "Embassy"],
        "probability": 0.70,
        "counter": "Pre-brief institutions with evidence package, proactive relationship with school/police"
    }
}

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY,
            domain TEXT,              -- legal, financial, custody, social, crypto
            prediction TEXT,
            confidence REAL,
            timeframe TEXT,
            basis TEXT,               -- JSON: data sources and reasoning
            counter_strategy TEXT,
            priority TEXT,            -- critical, high, medium, low
            status TEXT DEFAULT 'active',
            outcome TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            resolved_at TEXT
        );
        
        CREATE TABLE IF NOT EXISTS red_team_sessions (
            id INTEGER PRIMARY KEY,
            scenario TEXT,
            marina_strategy TEXT,
            hadrien_counter TEXT,
            outcome_assessment TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS counter_strategies (
            id INTEGER PRIMARY KEY,
            threat TEXT,
            strategy TEXT,
            resources_needed TEXT,    -- JSON
            timeline TEXT,
            dependencies TEXT,       -- JSON
            status TEXT DEFAULT 'planned',
            priority TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS war_game_log (
            id INTEGER PRIMARY KEY,
            turn INTEGER,
            actor TEXT,
            action TEXT,
            response TEXT,
            outcome TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    db.commit()
    return db

def gather_intelligence():
    """Collect current state from all engines."""
    intel = {}
    
    # Causal engine — current cycles and predictions
    try:
        cdb = sqlite3.connect(str(DGA / "causal_engine.db"))
        intel["active_cycles"] = cdb.execute("""
            SELECT subject, cycle_type, phase, phase_start 
            FROM behavioral_cycles ORDER BY phase_start DESC LIMIT 10
        """).fetchall()
        intel["causal_predictions"] = cdb.execute(
            "SELECT subject, predicted_action, predicted_timeframe, confidence FROM predictions"
        ).fetchall()
        intel["statute_clocks"] = cdb.execute(
            "SELECT charge_ref, jurisdiction, expires_date, status FROM statute_clock"
        ).fetchall()
        cdb.close()
    except:
        intel["active_cycles"] = []
    
    # Legal anticipation — active cases
    try:
        ldb = sqlite3.connect(str(DGA / "legal_anticipation.db"))
        intel["active_cases"] = ldb.execute(
            "SELECT case_ref, jurisdiction, case_type, status FROM cases WHERE status NOT IN ('closed','dismissed')"
        ).fetchall()
        intel["upcoming_events"] = ldb.execute("""
            SELECT c.case_ref, e.event_date, e.event_type, e.description 
            FROM case_events e JOIN cases c ON e.case_id=c.id 
            WHERE e.event_date > date('now') ORDER BY e.event_date LIMIT 10
        """).fetchall()
        ldb.close()
    except:
        intel["active_cases"] = []
    
    # Psych engine — latest manipulation events
    try:
        pdb = sqlite3.connect(str(DGA / "psych_engine.db"))
        intel["recent_manipulations"] = pdb.execute("""
            SELECT technique, severity, description, detected_at 
            FROM manipulations 
            WHERE subject_id=(SELECT id FROM subjects WHERE name LIKE '%arina%' LIMIT 1)
            ORDER BY detected_at DESC LIMIT 10
        """).fetchall()
        intel["game_theory"] = pdb.execute("""
            SELECT analysis_type, substr(summary,1,200) FROM analyses 
            WHERE analysis_type='game_theory' ORDER BY created_at DESC LIMIT 5
        """).fetchall()
        pdb.close()
    except:
        intel["recent_manipulations"] = []
    
    # Financial strategy — current exposure
    try:
        fdb = sqlite3.connect(str(DGA / "financial_strategy.db"))
        intel["financial"] = fdb.execute(
            "SELECT * FROM strategy_log ORDER BY created_at DESC LIMIT 1"
        ).fetchall()
        fdb.close()
    except:
        intel["financial"] = []
    
    # WhatsApp — latest Marina messages
    try:
        wdb = sqlite3.connect(str(DGA / "whatsapp_gdrive.db"))
        intel["latest_messages"] = wdb.execute("""
            SELECT m.timestamp, m.message FROM messages m 
            JOIN chats c ON m.chat_id=c.id 
            WHERE c.chat_name LIKE '%arina%' AND m.sender LIKE '%arina%'
            ORDER BY m.timestamp DESC LIMIT 5
        """).fetchall()
        wdb.close()
    except:
        intel["latest_messages"] = []
    
    return intel

def generate_predictions(db):
    """Generate comprehensive adversary predictions."""
    print("  Gathering intelligence from all engines...")
    intel = gather_intelligence()
    
    predictions = []
    
    # ── 1. Legal predictions based on active cases ──
    active_cases = intel.get("active_cases", [])
    case_jurisdictions = set(c[1] for c in active_cases)
    
    # If she has active cases in MT and MC, predict FR escalation
    if 'MT' in case_jurisdictions and 'MC' in case_jurisdictions:
        predictions.append({
            "domain": "legal",
            "prediction": "New filing in France — jurisdiction shopping pattern. Likely targeting instigation d'assassinat charges or pension enforcement via French courts",
            "confidence": 0.70,
            "timeframe": "3-6 months",
            "basis": json.dumps({"pattern": "jurisdiction_shopping", "active_in": list(case_jurisdictions)}),
            "counter": "Pre-emptive French counsel engagement, prepare defense dossier for FR jurisdiction, monitor French court registries",
            "priority": "high"
        })
    
    # Annulment filed → predict custody escalation
    if any('ANNULMENT' in (c[0] or '') for c in active_cases):
        predictions.append({
            "domain": "custody",
            "prediction": "Custody battle escalation tied to annulment — if annulment succeeds, Marina will argue changed circumstances for full custody of Constantin",
            "confidence": 0.75,
            "timeframe": "6-12 months (follows annulment timeline)",
            "basis": json.dumps({"pattern": "parental_alienation", "trigger": "annulment_proceedings"}),
            "counter": "Strengthen school/institutional evidence of stable environment, Manuel Debono testimony, ISM/Le Rosey records showing children thrive with Hadrien",
            "priority": "critical"
        })
    
    # ── 2. Financial predictions based on cycles ──
    predictions.append({
        "domain": "financial",
        "prediction": "Next financial demand cycle — money request justified by Constantin's needs (school, medical, activities), escalating to court threats if refused",
        "confidence": 0.90,
        "timeframe": "Within 34 days (avg cycle length)",
        "basis": json.dumps({"pattern": "financial_extortion_cycle", "historical_cycles": 11, "avg_days": 34}),
        "counter": "Route all payments through Solwos, document every demand, respond only via lawyer, never in direct WhatsApp",
        "priority": "high"
    })
    
    # Pension reduction response
    predictions.append({
        "domain": "financial",
        "prediction": "Marina will fight pension reduction through: (1) emergency court filing claiming inability to pay rent, (2) emotional appeal using Constantin's welfare, (3) threats to withhold access to Constantin",
        "confidence": 0.85,
        "timeframe": "Immediate upon notification",
        "basis": json.dumps({"pattern": "financial_extraction_cycle", "game_theory": "pension_negotiation"}),
        "counter": "Present documented evidence of Marina's undisclosed crypto assets (€42M+), CRS exposure analysis, forensic blockchain trail",
        "priority": "critical"
    })
    
    # Crypto concealment
    predictions.append({
        "domain": "financial",
        "prediction": "Marina will attempt to liquidate or further obscure crypto holdings — likely through P2P exchanges, new wallets, or third-party nominees",
        "confidence": 0.65,
        "timeframe": "Ongoing — accelerates before any financial hearing",
        "basis": json.dumps({"pattern": "crypto_concealment", "assets": "163 BTC + 875K ATOM + 7,243 ETH + 1,100 ETH"}),
        "counter": "Blockchain monitoring alerts on known addresses, court order to freeze exchange accounts, taint analysis on outflows",
        "priority": "critical"
    })
    
    # ── 3. Custody predictions ──
    predictions.append({
        "domain": "custody",
        "prediction": "Marina will use probation period (Oct 2025-2028) as leverage — any perceived aggression from Hadrien becomes ammunition for custody modification",
        "confidence": 0.80,
        "timeframe": "Ongoing through 2028",
        "basis": json.dumps({"pattern": "parental_alienation", "constraint": "probation_2025_2028"}),
        "counter": "Absolute zero direct confrontation, all communication through lawyers, institutional channel only (police TF + CPM + victim support)",
        "priority": "critical"
    })
    
    predictions.append({
        "domain": "custody",
        "prediction": "Marina will attempt to relocate Constantin to Monaco or France — creating facts on the ground before next custody hearing",
        "confidence": 0.55,
        "timeframe": "Before next school year (Sep 2026)",
        "basis": json.dumps({"pattern": "jurisdiction_shopping", "goal": "establish_habitual_residence"}),
        "counter": "Hague Convention awareness, monitor school enrollment, maintain Malta habitual residence evidence, travel restrictions if available",
        "priority": "high"
    })
    
    # ── 4. Social/reputation predictions ──
    predictions.append({
        "domain": "social",
        "prediction": "Marina will approach institutions (school, social services, embassy) with victim narrative before next court date — pre-poisoning the well",
        "confidence": 0.70,
        "timeframe": "2-4 weeks before any hearing",
        "basis": json.dumps({"pattern": "victim_narrative_media", "targets": ["school", "social_services", "embassy"]}),
        "counter": "Pre-brief key institutions with evidence package, maintain proactive relationship with school, document all institutional contacts",
        "priority": "medium"
    })
    
    # ── 5. Hoovering prediction ──
    predictions.append({
        "domain": "legal",
        "prediction": "Settlement offer right before unfavorable hearing — love-bombing + 'for the children' rhetoric to extract concessions under time pressure",
        "confidence": 0.85,
        "timeframe": "1-2 weeks before next MT/MC hearing",
        "basis": json.dumps({"pattern": "hoovering_before_court", "historical_confidence": 0.85}),
        "counter": "Never negotiate under time pressure, all offers through lawyers with 72h minimum review period, document the hoovering pattern for judge",
        "priority": "high"
    })
    
    # ── 6. Evidence fabrication ──
    predictions.append({
        "domain": "legal",
        "prediction": "Fabricated or manipulated evidence submission — doctored screenshots, out-of-context messages, coached witness statements from new contacts",
        "confidence": 0.60,
        "timeframe": "Before any evidentiary hearing",
        "basis": json.dumps({"pattern": "evidence_fabrication", "counter_tool": "forensic_integrity"}),
        "counter": "Forensic metadata analysis on all submitted evidence, chain of custody challenges, EXIF/hash verification, request original files not screenshots",
        "priority": "high"
    })
    
    # Store predictions
    for p in predictions:
        db.execute("""INSERT INTO predictions 
            (domain, prediction, confidence, timeframe, basis, counter_strategy, priority)
            VALUES (?,?,?,?,?,?,?)""",
            (p["domain"], p["prediction"], p["confidence"], p["timeframe"],
             p["basis"], p["counter"], p["priority"]))
    
    db.commit()
    return predictions

def cmd_predict(db):
    """Full prediction report."""
    # Clear old predictions
    db.execute("DELETE FROM predictions")
    db.commit()
    
    predictions = generate_predictions(db)
    
    print(f"\n{'='*70}")
    print(f"  ADVERSARY STRATEGY FORECAST — Marina Gavryusheva")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Probation constraint: Oct 2025 → 2028 (ALL payoffs adjusted)")
    print(f"{'='*70}")
    
    # Sort by priority then confidence
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    predictions.sort(key=lambda p: (priority_order.get(p["priority"], 9), -p["confidence"]))
    
    for p in predictions:
        icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(p["priority"], "⚪")
        print(f"\n  {icon} [{p['priority'].upper()}] {p['domain'].upper()} — {p['confidence']:.0%} confidence")
        print(f"  ┌ Prediction: {p['prediction']}")
        print(f"  ├ Timeframe:  {p['timeframe']}")
        print(f"  └ Counter:    {p['counter']}")
    
    print(f"\n  {'─'*70}")
    print(f"  Total predictions: {len(predictions)}")
    print(f"  Critical: {sum(1 for p in predictions if p['priority']=='critical')}")
    print(f"  High:     {sum(1 for p in predictions if p['priority']=='high')}")

def cmd_counter_strategy(db):
    """Generate comprehensive counter-strategy."""
    intel = gather_intelligence()
    
    print(f"\n{'='*70}")
    print(f"  COUNTER-STRATEGY PLAYBOOK")
    print(f"{'='*70}")
    
    for name, play in MARINA_PLAYBOOK.items():
        print(f"\n  ■ {name.replace('_', ' ').title()}")
        print(f"    Pattern:     {play['pattern']}")
        print(f"    Probability: {play['probability']:.0%}")
        print(f"    Counter:     {play['counter']}")
        if 'historical' in play:
            print(f"    Historical:  {', '.join(play['historical'][:3])}")

def cmd_war_game(db):
    """Interactive adversarial war game — Hadrien vs Marina (AI-played)."""
    print(f"\n{'='*70}")
    print(f"  WAR GAME — Adversarial Simulation")
    print(f"  You play as Hadrien. Marina is played by AI.")
    print(f"  Type actions/moves. Type 'quit' to end.")
    print(f"  Type '/brief' for current situation assessment.")
    print(f"{'='*70}")
    
    intel = gather_intelligence()
    
    marina_system = """You are Marina Gavryusheva's LEGAL STRATEGIST (not Marina herself).
You think like her lawyer analyzing options. You are ruthless, strategic, and creative.

You know Marina's position:
- Divorcing Hadrien Majoie in Malta
- Has undisclosed crypto: 163 BTC + 875K ATOM + 7,243 ETH (she'll deny this)
- Currently receiving 32,500€/mo pension (wants to keep/increase)
- Has criminal charges: violence (MT), escroquerie (MC)
- Uses children (Constantin) as leverage
- Probation constraint on Hadrien (Oct 2025-2028) — she can exploit this
- Active cases in MT, MC, with potential FR front

When Hadrien makes a move, respond with Marina's STRATEGIC COUNTER-MOVE:
1. What Marina would do in response
2. Which jurisdiction she'd use
3. What leverage she'd apply
4. What the expected outcome would be

Be specific, tactical, and reference real legal mechanisms."""

    messages = [{"role": "system", "content": marina_system}]
    turn = 0
    
    # Seed with current situation
    case_summary = "\n".join(f"  - {c[0]} ({c[1]}): {c[3]}" for c in intel.get("active_cases", [])[:10])
    messages.append({"role": "user", "content": f"Current situation:\n{case_summary}\n\nGame begins. Waiting for Hadrien's first move."})
    
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/chat", json={
            "model": MODEL, "messages": messages, "stream": False,
            "options": {"temperature": 0.7, "num_predict": 200}
        }, timeout=60)
        opening = resp.json()["message"]["content"]
        print(f"\n  [Marina's Strategist]: {opening}\n")
        messages.append({"role": "assistant", "content": opening})
    except:
        print("  [AI connection issue — playing blind]")
    
    while True:
        try:
            move = input("\n  Hadrien's move > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        
        if not move:
            continue
        if move.lower() == 'quit':
            break
        if move == '/brief':
            cmd_predict(db)
            continue
        
        turn += 1
        messages.append({"role": "user", "content": f"Hadrien's move (turn {turn}): {move}\n\nWhat is Marina's strategic counter-move? Be specific about jurisdiction, legal mechanism, and timing."})
        
        try:
            resp = requests.post(f"{OLLAMA_URL}/api/chat", json={
                "model": MODEL, "messages": messages, "stream": False,
                "options": {"temperature": 0.75, "num_predict": 300}
            }, timeout=60)
            counter = resp.json()["message"]["content"]
            print(f"\n  [Marina's Counter (turn {turn})]:")
            for line in counter.split('\n'):
                if line.strip():
                    print(f"    {line.strip()}")
            
            messages.append({"role": "assistant", "content": counter})
            
            # Log
            db.execute("INSERT INTO war_game_log (turn, actor, action, response) VALUES (?,?,?,?)",
                (turn, "hadrien", move, counter))
            db.commit()
            
        except Exception as e:
            print(f"  [Error: {e}]")
    
    print(f"\n  War game ended. {turn} turns played.")

def cmd_red_team(db, scenario):
    """AI plays as Marina's legal team for a specific scenario."""
    scenarios = {
        "pension_reduction": "Hadrien is requesting pension reduction from 32,500€/mo to 5,000€/mo based on changed circumstances and undisclosed crypto assets",
        "crypto_disclosure": "Court has ordered Marina to disclose all crypto holdings. How does she respond?",
        "custody_modification": "Hadrien files for full custody of Constantin citing violence, alienation, and instability",
        "annulment_defense": "How does Marina defend against the annulment petition in Malta?",
        "cross_border_enforcement": "Maltese court order needs enforcement in Monaco. What can Marina do to obstruct?",
        "probation_exploitation": "How can Marina exploit Hadrien's probation period to gain advantage?",
        "settlement_negotiation": "Pre-trial settlement: what's Marina's opening position and bottom line?",
        "evidence_challenge": "How does Marina challenge the forensic evidence package (blockchain, WhatsApp, sealed documents)?",
    }
    
    if scenario not in scenarios:
        print("Available scenarios:")
        for k, v in scenarios.items():
            print(f"  {k}: {v}")
        return
    
    desc = scenarios[scenario]
    
    system = f"""You are a HIGHLY AGGRESSIVE family law attorney representing Marina Gavryusheva (née Majoie) in her divorce from Hadrien Majoie. You fight dirty but within legal bounds.

Scenario: {desc}

Your client Marina:
- Claims to be a victim of domestic abuse
- Has undisclosed crypto assets worth €42M+ (you know about this but will never admit it)
- Receives 32,500€/mo pension
- Has criminal charges against her (violence MT, escroquerie MC) which you'll minimize
- Her son Constantin is her primary leverage
- She has conviction in MT (2025) — you'll argue this was unjust

Strategy framework:
1. Deny everything that can't be proven beyond doubt
2. Attack Hadrien's credibility (his relationship with Natalia, his own legal issues)
3. Use children's welfare as ultimate argument
4. Exploit jurisdiction differences
5. Delay proceedings (time is money — literally, at 32,500€/mo)
6. Challenge evidence admissibility across jurisdictions

Provide a detailed strategic plan with specific legal arguments, motions to file, witnesses to call, and timeline."""

    print(f"\n{'='*70}")
    print(f"  RED TEAM: {scenario}")
    print(f"  {desc}")
    print(f"{'='*70}\n")
    
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/chat", json={
            "model": MODEL,
            "messages": [{"role": "system", "content": system}, 
                        {"role": "user", "content": f"Present your full strategic plan for this scenario. Be specific, aggressive, and tactical."}],
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 800}
        }, timeout=120)
        
        plan = resp.json()["message"]["content"]
        print(plan)
        
        db.execute("INSERT INTO red_team_sessions (scenario, marina_strategy) VALUES (?,?)",
            (scenario, plan))
        db.commit()
        
    except Exception as e:
        print(f"  Error: {e}")

def cmd_briefing(db):
    """Executive briefing for lawyers."""
    db2 = init_db()
    # Regenerate fresh predictions
    db2.execute("DELETE FROM predictions")
    db2.commit()
    predictions = generate_predictions(db2)
    
    intel = gather_intelligence()
    
    print(f"\n{'='*70}")
    print(f"  ADVERSARY INTELLIGENCE BRIEFING")
    print(f"  Subject: Marina Gavryusheva / Majoie")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"  Classification: CONFIDENTIAL — Attorney Work Product")
    print(f"{'='*70}")
    
    print(f"\n  1. CURRENT THREAT ASSESSMENT")
    print(f"  {'─'*50}")
    critical = [p for p in predictions if p["priority"] == "critical"]
    for p in critical:
        print(f"    🔴 {p['domain'].upper()}: {p['prediction'][:100]}")
    
    print(f"\n  2. ACTIVE FRONTS ({len(intel.get('active_cases', []))} cases)")
    print(f"  {'─'*50}")
    for c in intel.get("active_cases", []):
        print(f"    {c[1]}: {c[0]} ({c[2]}) — {c[3]}")
    
    print(f"\n  3. BEHAVIORAL CYCLE STATUS")
    print(f"  {'─'*50}")
    for pred in intel.get("causal_predictions", []):
        print(f"    {pred[0]}: {pred[1]} — {pred[2]} ({pred[3]:.0%})")
    
    print(f"\n  4. STATUTE CLOCKS")
    print(f"  {'─'*50}")
    for cl in intel.get("statute_clocks", []):
        icon = "🟢" if cl[3] == 'active' else "🔴"
        print(f"    {icon} {cl[0]} ({cl[1]}): {cl[3]} — expires {cl[2] or 'no limit'}")
    
    print(f"\n  5. RECOMMENDED IMMEDIATE ACTIONS")
    print(f"  {'─'*50}")
    print(f"    1. Freeze all direct communication — lawyer channel ONLY")
    print(f"    2. Pre-brief institutions before next hoovering cycle")
    print(f"    3. Monitor blockchain addresses for crypto movement")
    print(f"    4. Prepare counter-evidence package for next hearing")
    print(f"    5. Engage FR counsel pre-emptively if not already done")
    
    print(f"\n  6. PLAYBOOK PATTERNS (8 identified)")
    print(f"  {'─'*50}")
    for name, play in sorted(MARINA_PLAYBOOK.items(), key=lambda x: -x[1]['probability']):
        print(f"    [{play['probability']:.0%}] {name.replace('_', ' ').title()}")

def cmd_stats(db):
    stats = {
        "predictions": db.execute("SELECT COUNT(*) FROM predictions").fetchone()[0],
        "by_domain": {r[0]: r[1] for r in db.execute("SELECT domain, COUNT(*) FROM predictions GROUP BY domain").fetchall()},
        "red_team_sessions": db.execute("SELECT COUNT(*) FROM red_team_sessions").fetchone()[0],
        "war_game_turns": db.execute("SELECT COUNT(*) FROM war_game_log").fetchone()[0],
        "counter_strategies": db.execute("SELECT COUNT(*) FROM counter_strategies").fetchone()[0],
        "playbook_patterns": len(MARINA_PLAYBOOK),
    }
    print(f"\n  ADVERSARY PREDICTOR — Statistics")
    print(f"  {'='*40}")
    for k, v in stats.items():
        print(f"  {k:25s}: {v}")

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "predict"
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    
    db = init_db()
    
    if cmd == "predict":
        cmd_predict(db)
    elif cmd == "next-move":
        db.execute("DELETE FROM predictions")
        db.commit()
        preds = generate_predictions(db)
        preds.sort(key=lambda p: -p["confidence"])
        if preds:
            p = preds[0]
            print(f"\n  Most likely next move ({p['confidence']:.0%}):")
            print(f"  {p['prediction']}")
            print(f"\n  Counter: {p['counter']}")
    elif cmd in ("legal-forecast", "financial-forecast", "custody-forecast"):
        domain = cmd.split('-')[0]
        db.execute("DELETE FROM predictions")
        db.commit()
        preds = generate_predictions(db)
        domain_preds = [p for p in preds if p["domain"] == domain]
        for p in domain_preds:
            print(f"\n  [{p['priority'].upper()}] ({p['confidence']:.0%}) {p['prediction']}")
            print(f"  Counter: {p['counter']}")
    elif cmd == "counter-strategy":
        cmd_counter_strategy(db)
    elif cmd == "red-team":
        cmd_red_team(db, arg or "pension_reduction")
    elif cmd == "war-game":
        cmd_war_game(db)
    elif cmd == "briefing":
        cmd_briefing(db)
    elif cmd == "stats":
        cmd_stats(db)
    else:
        print(__doc__)
    
    db.close()

if __name__ == "__main__":
    main()
