#!/usr/bin/env python3
"""
Multi-Party Simulation Engine — Orchestrates avatar interactions for
scenario planning, legal rehearsal, and adversarial gaming.

Combines all 13 avatars + causal engine + adversary predictor into
a unified simulation framework.

Usage:
  simulate roster                          List all available avatars
  simulate scene <scenario>                Run a preset multi-party scene
  simulate courtroom <case>                Courtroom simulation
  simulate negotiation <topic>             Multi-party negotiation
  simulate family <event>                  Family dynamics simulation
  simulate freeform <participants>         Open simulation with chosen avatars
  simulate replay <session_id>             Replay a past simulation
  simulate stats                           Engine statistics
"""
import os, sys, json, sqlite3, requests, re, argparse
from pathlib import Path
from datetime import datetime

DGA = Path(os.path.expanduser("~/data-gathering-agent"))
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://100.71.235.99:11434")
MODEL = "huihui_ai/mistral-small-abliterated:24b-instruct-2501-q4_K_M"
DB_PATH = str(DGA / "simulation_engine.db")

AVATARS = {
    "hadrien":   {"file": "hadrien_avatar.py",   "name": "Hadrien Majoie",    "short": "Hadrien",   "role": "Protagonist — father, strategist"},
    "anastasia":  {"file": "anastasia_avatar.py",  "name": "Anastasia Majoie",  "short": "Anastasia",  "role": "Daughter — Le Rosey student"},
    "marina":     {"file": "marina_avatar.py",      "name": "Marina Gavryusheva", "short": "Marina",     "role": "Ex-wife — adversary"},
    "natalia":    {"file": "natalia_avatar.py",      "name": "Natalia Zaiets",     "short": "Natalia",    "role": "Partner — legal ops + domestic"},
    "pol":        {"file": "pol_lambert_avatar.py",  "name": "Pol Lambert",        "short": "Pol",        "role": "Primary lawyer — Solwos"},
    "manuel":     {"file": "manuel_debono_avatar.py","name": "Manuel Debono",      "short": "Manuel",     "role": "Guardian/advisor"},
    "bisazza":    {"file": "carlo_bisazza_avatar.py","name": "Carlo Bisazza",      "short": "Carlo",      "role": "MT lawyer — Bisazza Legal"},
    "blangero":   {"file": "nathalie_blangero_avatar.py","name": "Nathalie Blangero","short": "Nathalie", "role": "MC lawyer — Giaccardi & Brezzo"},
    "berthelot":  {"file": "thierry_berthelot_avatar.py","name": "Thierry Berthelot","short": "Thierry",  "role": "Expert witness — financial"},
    "oggi":       {"file": "oggi_avatar.py",         "name": "Oggi",               "short": "Oggi",       "role": "Business partner — PlanO"},
    "simon":      {"file": "simon_debono_avatar.py", "name": "Simon Debono",       "short": "Simon",      "role": "Family friend"},
    "matthew":    {"file": "matthew_xuereb_avatar.py","name": "Matthew Xuereb",    "short": "Matthew",    "role": "Associate"},
    "gregory":    {"file": "gregory_prenleloup_avatar.py","name": "Gregory Prenleloup","short": "Gregory","role": "Friend"},
    "isaac":      {"file": "isaac_avatar.py",        "name": "Isaac",              "short": "Isaac",      "role": "Friend"},
}

SCENES = {
    "custody_hearing": {
        "description": "Malta Family Court — custody of Constantin",
        "participants": ["pol", "bisazza", "marina", "manuel"],
        "context": "Hadrien's team (Pol + Carlo) vs Marina in Maltese custody hearing. Manuel testifies as witness. Judge asks questions.",
        "judge": True
    },
    "pension_negotiation": {
        "description": "Settlement negotiation — pension reduction from 32,500 to proposed 5,000",
        "participants": ["pol", "marina", "blangero"],
        "context": "Pre-trial settlement meeting. Pol represents Hadrien. Marina and her Monaco counsel negotiate.",
        "judge": False
    },
    "crypto_discovery": {
        "description": "Court-ordered crypto asset disclosure hearing",
        "participants": ["pol", "bisazza", "marina", "berthelot"],
        "context": "Thierry Berthelot presents financial analysis. Marina is cross-examined about 163 BTC + 875K ATOM + 7,243 ETH.",
        "judge": True
    },
    "family_dinner": {
        "description": "Family dinner — Hadrien, Anastasia, Natalia, Constantin",
        "participants": ["anastasia", "natalia"],
        "context": "Casual family dinner. Anastasia is visiting from Le Rosey. Natalia is hosting. Constantin is present but not speaking.",
        "judge": False
    },
    "annulment_hearing": {
        "description": "Malta annulment proceedings",
        "participants": ["bisazza", "marina"],
        "context": "Carlo Bisazza presents annulment petition. Marina defends. Judge presides.",
        "judge": True
    },
    "crisis_response": {
        "description": "Emergency — Marina withholds Constantin, threatens police",
        "participants": ["pol", "natalia", "manuel", "bisazza"],
        "context": "Marina has refused to return Constantin after weekend visit. Team coordinates response.",
        "judge": False
    },
    "legal_strategy": {
        "description": "Internal strategy meeting — all lawyers + Natalia",
        "participants": ["pol", "bisazza", "blangero", "natalia"],
        "context": "Planning session before next round of hearings. All jurisdictions reviewed. Natalia provides witness perspective.",
        "judge": False
    },
    "monaco_escroquerie": {
        "description": "Monaco criminal hearing — escroquerie charge against Marina",
        "participants": ["blangero", "marina", "berthelot"],
        "context": "Monaco court. Nathalie Blangero prosecutes. Berthelot provides financial evidence. Marina defends.",
        "judge": True
    },
}

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY, scene TEXT, participants TEXT,
            context TEXT, started_at TEXT, ended_at TEXT, turns INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS turns (
            id INTEGER PRIMARY KEY, session_id INTEGER REFERENCES sessions(id),
            turn_num INTEGER, actor TEXT, actor_role TEXT,
            statement TEXT, created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY, session_id INTEGER REFERENCES sessions(id),
            assessor TEXT, assessment TEXT, recommendations TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    db.commit()
    return db

def get_avatar_response(name, role, context, conversation_so_far, is_judge=False):
    """Get a response from a specific avatar in the simulation context."""
    if is_judge:
        system = f"""You are a {context.get('jurisdiction', 'Maltese')} Family Court judge presiding over this case. You are impartial, formal, and focused on the law and the children's best interests. You ask pointed questions, rule on objections, and maintain order. Address parties formally."""
    else:
        avatar = AVATARS.get(name, {})
        system = f"""You are {avatar.get('name', name)} in a simulation.
Role: {avatar.get('role', role)}

Context: {context.get('scenario', '')}

You are participating in: {context.get('scene_type', 'a meeting')}

IMPORTANT: Stay in character. Respond as this person would. Keep responses concise (2-4 sentences for courtroom, longer for strategy meetings). Reference real facts from the case when relevant."""

    messages = [{"role": "system", "content": system}]
    for turn in conversation_so_far[-10:]:  # Last 10 turns for context
        if turn["actor"] == name:
            messages.append({"role": "assistant", "content": turn["statement"]})
        else:
            messages.append({"role": "user", "content": f"[{turn['actor']}]: {turn['statement']}"})
    
    if not any(m["role"] == "user" for m in messages):
        messages.append({"role": "user", "content": f"[Scene begins] {context.get('scenario', 'Proceed.')}"})
    
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/chat", json={
            "model": MODEL, "messages": messages, "stream": False,
            "options": {"temperature": 0.75, "num_predict": 200}
        }, timeout=60)
        return resp.json()["message"]["content"]
    except Exception as e:
        return f"[{name} is silent — {e}]"

def run_scene(db, scene_name):
    if scene_name not in SCENES:
        print("Available scenes:")
        for k, v in SCENES.items():
            print(f"  {k}: {v['description']}")
        return
    
    scene = SCENES[scene_name]
    participants = scene["participants"]
    has_judge = scene.get("judge", False)
    
    print(f"\n{'='*60}")
    print(f"  SIMULATION: {scene['description']}")
    print(f"  Participants: {', '.join(AVATARS[p]['name'] for p in participants)}")
    if has_judge:
        print(f"  Judge: Presiding")
    print(f"  You play as: Hadrien Majoie")
    print(f"{'='*60}")
    print(f"  Commands: quit, /next (auto-advance), /assess (get assessment)")
    print()
    
    # Create session
    session_id = db.execute("INSERT INTO sessions (scene, participants, context, started_at) VALUES (?,?,?,?)",
        (scene_name, json.dumps(participants), scene["context"], datetime.now().isoformat())).lastrowid
    db.commit()
    
    conversation = []
    context = {"scenario": scene["context"], "scene_type": scene["description"]}
    turn_num = 0
    
    # Opening — judge or first participant sets the scene
    if has_judge:
        opening = get_avatar_response("judge", "Judge", context, conversation, is_judge=True)
        conversation.append({"actor": "Judge", "statement": opening})
        print(f"  Judge: {opening}\n")
        turn_num += 1
        db.execute("INSERT INTO turns (session_id, turn_num, actor, actor_role, statement) VALUES (?,?,?,?,?)",
            (session_id, turn_num, "Judge", "Judge", opening))
    
    while True:
        try:
            user_input = input(f"\n  Hadrien: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        
        if not user_input:
            continue
        if user_input == 'quit':
            break
        
        if user_input == '/assess':
            # Get AI assessment of the simulation so far
            assess_prompt = f"Analyze this legal simulation:\n\nScene: {scene['description']}\n\n"
            for t in conversation[-20:]:
                assess_prompt += f"{t['actor']}: {t['statement']}\n"
            assess_prompt += "\nProvide: 1) Who is winning 2) Key mistakes 3) Recommended next moves for Hadrien"
            
            resp = requests.post(f"{OLLAMA_URL}/api/chat", json={
                "model": MODEL,
                "messages": [{"role": "user", "content": assess_prompt}],
                "stream": False, "options": {"temperature": 0.5, "num_predict": 400}
            }, timeout=60)
            assessment = resp.json()["message"]["content"]
            print(f"\n  {'─'*50}")
            print(f"  ASSESSMENT:")
            print(f"  {assessment}")
            print(f"  {'─'*50}")
            db.execute("INSERT INTO assessments (session_id, assessor, assessment) VALUES (?,?,?)",
                (session_id, "AI", assessment))
            db.commit()
            continue
        
        if user_input == '/next':
            user_input = "[Hadrien listens and waits for the next party to speak]"
        
        # Record Hadrien's statement
        turn_num += 1
        conversation.append({"actor": "Hadrien", "statement": user_input})
        db.execute("INSERT INTO turns (session_id, turn_num, actor, actor_role, statement) VALUES (?,?,?,?,?)",
            (session_id, turn_num, "Hadrien", "Plaintiff", user_input))
        
        # Each participant responds in order
        for p in participants:
            avatar = AVATARS[p]
            response = get_avatar_response(p, avatar["role"], context, conversation)
            turn_num += 1
            conversation.append({"actor": avatar["short"], "statement": response})
            print(f"\n  {avatar['short']}: {response}")
            db.execute("INSERT INTO turns (session_id, turn_num, actor, actor_role, statement) VALUES (?,?,?,?,?)",
                (session_id, turn_num, avatar["short"], avatar["role"], response))
        
        # Judge responds if applicable
        if has_judge:
            judge_resp = get_avatar_response("judge", "Judge", context, conversation, is_judge=True)
            turn_num += 1
            conversation.append({"actor": "Judge", "statement": judge_resp})
            print(f"\n  Judge: {judge_resp}")
            db.execute("INSERT INTO turns (session_id, turn_num, actor, actor_role, statement) VALUES (?,?,?,?,?)",
                (session_id, turn_num, "Judge", "Judge", judge_resp))
        
        db.commit()
    
    # End session
    db.execute("UPDATE sessions SET ended_at=?, turns=? WHERE id=?",
        (datetime.now().isoformat(), turn_num, session_id))
    db.commit()
    print(f"\n  Session ended. {turn_num} turns. ID: {session_id}")

def cmd_roster(db):
    print(f"\n  {'='*60}")
    print(f"  AVATAR ROSTER — 13 Protagonists")
    print(f"  {'='*60}")
    # Include the 3 hand-built ones
    all_avatars = {**AVATARS}
    for key, av in sorted(all_avatars.items()):
        exists = os.path.exists(str(DGA / av["file"]))
        icon = "✓" if exists else "✗"
        print(f"  {icon} {av['short']:20s} {av['role']}")
    print(f"\n  Aliases: <name>-sim (e.g., pol-lambert-sim, manuel-debono-sim)")

def cmd_stats(db):
    sessions = db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    turns = db.execute("SELECT COUNT(*) FROM turns").fetchone()[0]
    assessments = db.execute("SELECT COUNT(*) FROM assessments").fetchone()[0]
    print(f"\n  SIMULATION ENGINE")
    print(f"  Sessions: {sessions}")
    print(f"  Total turns: {turns}")
    print(f"  Assessments: {assessments}")
    print(f"  Available scenes: {len(SCENES)}")
    print(f"  Available avatars: {len(AVATARS)}")

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "roster"
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    
    db = init_db()
    
    if cmd == "roster":
        cmd_roster(db)
    elif cmd == "scene":
        run_scene(db, arg or "")
    elif cmd in ("courtroom", "negotiation", "family"):
        # Map to scenes
        mapping = {
            "courtroom": "custody_hearing",
            "negotiation": "pension_negotiation",
            "family": "family_dinner"
        }
        run_scene(db, arg or mapping.get(cmd, ""))
    elif cmd == "freeform":
        if arg:
            parts = arg.split(",")
            scene = {"description": "Freeform simulation", "participants": [p.strip() for p in parts], "context": "Open conversation", "judge": False}
            SCENES["freeform"] = scene
            run_scene(db, "freeform")
        else:
            print("Usage: simulate freeform <avatar1,avatar2,...>")
    elif cmd == "stats":
        cmd_stats(db)
    else:
        print(__doc__)
    
    db.close()

if __name__ == "__main__":
    main()
