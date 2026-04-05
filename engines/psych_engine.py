#!/usr/bin/env python3
"""
Psychological Engine — Multirole behavioral analysis platform.

Roles:
  profile     Build/update psychological profile for a person
  negotiate   Analyze negotiation dynamics and tactics
  deception   Detect inconsistencies, lies, DARVO, gaslighting
  emotion     Track emotional states over time
  relations   Map power dynamics and relationship patterns
  predict     Predict behavioral responses to scenarios
  manipulate  Classify manipulation techniques in communications
  timeline    Show psychological event timeline for a person
  compare     Compare two people's communication styles
  game        Game theory analysis (Nash, prisoner's dilemma, chicken, etc.)
  payoff      Compute payoff matrix for a decision scenario
  briefing    Generate full psychological briefing (all roles)
  search      Search analysis results
  people      List profiled people
  stats       Show engine statistics
  ingest      Pull fresh data from all sources

Usage:
  psych profile <name>           Build/refresh profile
  psych negotiate <chat_name>    Analyze negotiation in a chat
  psych deception <name>         Run deception analysis
  psych emotion <name>           Emotional timeline
  psych relations [name]         Relationship map
  psych manipulate <name>        Classify manipulation patterns
  psych predict <name> <scenario> Predict reaction
  psych game <scenario_key>      Run game theory analysis
  psych payoff <scenario_key>    Show payoff matrix
  psych briefing <name>          Full multi-role briefing
  psych compare <name1> <name2>  Compare communication styles
  psych timeline <name>          Psychological event timeline
  psych psyops <name>            PSYOPS influence analysis
  psych bias                     Show detected cognitive biases (self-analysis)
  psych bias check <decision>    Run decision through bias filters
  psych bias mitigate <id>       Mark a bias as mitigated
  psych debias                   Debiased probability estimates (reference class)
  psych premortem <scenario>     Premortem analysis ("it's 2027, this failed, why?")
  psych reframe <amount>         Reframe EUR amount in runway/pension terms
  psych search <query>           Search analysis
  psych people                   List profiled people
  psych stats                    Engine statistics
  psych ingest                   Refresh data from sources
"""

import sys
import os
import re
import json
import sqlite3
import math
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from textwrap import dedent

# ── Paths ──────────────────────────────────────────────────────────────────
ENGINE_DIR = Path(__file__).parent
DB_PATH = ENGINE_DIR / "psych_engine.db"
WA_DB = ENGINE_DIR / "whatsapp_gdrive.db"
LAKE_DB = ENGINE_DIR / "memory_lake" / "lake.db"
CONTACTS_DB = ENGINE_DIR / "integrations" / "contacts.db"
DOC_DB = ENGINE_DIR / "integrations" / "doc_index.db"
FINANCE_DB = Path.home() / "forensic" / "personal-finance" / "db" / "finance_lake.db"
CRYPTO_DB = Path.home() / "forensic" / "Crypto-forensic" / "db" / "crypto_forensic.db"

# ── Manipulation taxonomy ──────────────────────────────────────────────────
MANIPULATION_PATTERNS = {
    "love_bombing": {
        "label": "Love Bombing",
        "markers": [
            r"\b(my love|darling|sweetheart|i love you|miss you so much|forever)\b",
            r"\b(perfect|amazing|incredible|soulmate|destiny)\b",
            r"\b(can't live without|need you|only you)\b",
        ],
        "desc": "Excessive affection to create dependency and obligation"
    },
    "darvo": {
        "label": "DARVO (Deny, Attack, Reverse Victim/Offender)",
        "markers": [
            r"\b(i('m| am) the victim|you('re| are) the (abuser|aggressor|one who))\b",
            r"\b(you did this to (me|us|yourself)|it's your fault|you started)\b",
            r"\b(i never|i didn't|that never happened|you('re| are) lying)\b",
            r"\b(look what you made me|because of you|you forced me)\b",
        ],
        "desc": "Deny abuse, attack accuser, reverse roles"
    },
    "gaslighting": {
        "label": "Gaslighting",
        "markers": [
            r"\b(you('re| are) (crazy|insane|paranoid|imagining|delusional))\b",
            r"\b(that (never|didn't) happen|you('re| are) making (it|things) up)\b",
            r"\b(no one will believe you|everyone (thinks|knows) you('re| are))\b",
            r"\b(you('re| are) too (sensitive|emotional|dramatic))\b",
        ],
        "desc": "Making target doubt their own reality"
    },
    "triangulation": {
        "label": "Triangulation",
        "markers": [
            r"\b(everyone (says|thinks|agrees)|other people|my (friends|lawyer|family) (say|think))\b",
            r"\b((she|he|they) (told|said|think) you|compared to)\b",
            r"\b(at least (she|he|they)|unlike you)\b",
        ],
        "desc": "Bringing third parties into conflict to manipulate"
    },
    "financial_abuse": {
        "label": "Financial Control/Abuse",
        "markers": [
            r"\b(block.*(account|money|card)|cut.*(off|money)|no money|can't afford)\b",
            r"\b(pension|alimony|pay.*nothing|legal right.*give.*money)\b",
            r"\b(your money|my money|i pay|you spend|ungrateful)\b",
        ],
        "desc": "Using money as control mechanism"
    },
    "parental_alienation": {
        "label": "Parental Alienation",
        "markers": [
            r"\b(Constantin.*(against|hate|doesn't want|refuses|afraid))\b",
            r"\b((your|his|her) (father|mother|dad|mom).*(bad|dangerous|crazy))\b",
            r"\b(custody|not your (day|turn|time)|can't see|won't let)\b",
            r"\b(child.*(weapon|pawn|hostage|leverage))\b",
        ],
        "desc": "Using child as weapon, turning child against other parent"
    },
    "threat_intimidation": {
        "label": "Threats & Intimidation",
        "markers": [
            r"\b(you('ll| will) (regret|pay|suffer|lose)|watch (out|yourself))\b",
            r"\b(i('ll| will) (destroy|ruin|expose|take everything))\b",
            r"\b(consequence|sanction|legal action|police|court)\b",
            r"\b(careful|warning|last chance|deadline|ultimatum)\b",
        ],
        "desc": "Using fear to control"
    },
    "silent_treatment": {
        "label": "Silent Treatment / Stonewalling",
        "markers": [],  # Detected by response gap analysis, not text patterns
        "desc": "Withholding communication as punishment"
    },
    "projection": {
        "label": "Projection",
        "markers": [
            r"\b(you('re| are) the one who|you always|you never)\b",
            r"\b(that's what you do|look at yourself|hypocrit)\b",
        ],
        "desc": "Attributing own behavior to the other person"
    },
    "guilt_tripping": {
        "label": "Guilt Tripping",
        "markers": [
            r"\b(after (all|everything) i('ve| have)|how could you)\b",
            r"\b(i sacrificed|gave up everything|do you even care)\b",
            r"\b(selfish|ungrateful|heartless|cold)\b",
        ],
        "desc": "Inducing guilt to control behavior"
    },
    "moving_goalposts": {
        "label": "Moving Goalposts",
        "markers": [
            r"\b(that's not (what|enough)|now you need to|one more thing)\b",
            r"\b(changed.*mind|new condition|additional|also need)\b",
        ],
        "desc": "Changing requirements to maintain control"
    },
    "hoovering": {
        "label": "Hoovering (Sucking Back In)",
        "markers": [
            r"\b(i('ve| have) changed|give me (another|one more) chance)\b",
            r"\b(remember when|we were so (happy|good)|for (Constantin|the (kid|child)))\b",
            r"\b(family|together again|fresh start|new beginning)\b",
        ],
        "desc": "Attempting to re-engage after separation"
    },
}

# ── Emotional lexicon (multilingual) ──────────────────────────────────────
EMOTION_LEXICON = {
    "anger": [
        r"\b(angry|furious|rage|hate|disgusting|sick of|fed up|unacceptable)\b",
        r"\b(en colère|furieux|furieuse|dégoûté|marre|inacceptable|honteux)\b",
        r"[!]{2,}",  # Multiple exclamation marks
        r"\b(idiot|stupid|fool|liar|menteur|menteuse)\b",
    ],
    "fear": [
        r"\b(afraid|scared|terrified|anxious|worried|panic|danger)\b",
        r"\b(peur|effrayé|terrorisé|inquiet|panique|dangereux)\b",
    ],
    "sadness": [
        r"\b(sad|depressed|cry|crying|tears|heartbroken|lonely|miss)\b",
        r"\b(triste|déprimé|pleurer|larmes|seul|manque)\b",
    ],
    "contempt": [
        r"\b(pathetic|worthless|beneath|disgusting|loser|joke)\b",
        r"\b(pathétique|minable|mépris|dégoûtant)\b",
        r"🙄|😒|😤",
    ],
    "joy": [
        r"\b(happy|wonderful|amazing|great|love|beautiful|excited)\b",
        r"\b(heureux|merveilleux|magnifique|formidable|amour|beau)\b",
        r"[😊❤️💕🥰😍🎉]+",
    ],
    "anxiety": [
        r"\b(stress|overwhelm|can't (sleep|breathe|think)|panic|nervous)\b",
        r"\b(stressé|submergé|ne (dors|respire) (pas|plus)|panique|nerveux)\b",
    ],
    "dominance": [
        r"\b(must|shall|will not|i (order|command|demand|decide))\b",
        r"\b(i('m| am) (certain|right|sure)|trust me|listen to me)\b",
        r"\b(obey|submit|comply|respect my)\b",
    ],
    "submission": [
        r"\b(sorry|please|i('ll| will) do|whatever you (say|want))\b",
        r"\b(you('re| are) right|my fault|i was wrong|forgive me)\b",
    ],
}

# ── Communication style markers ────────────────────────────────────────────
STYLE_MARKERS = {
    "interrogative": r"\?",
    "imperative": r"\b(do|don't|send|call|stop|give|tell|come|go|read|look|wait|answer)\b.*[.!]$",
    "conditional": r"\b(if|unless|would|could|should|might)\b",
    "absolute": r"\b(always|never|every|all|nothing|nobody|everyone|everything)\b",
    "legal_language": r"\b(custody|pension|alimony|court|lawyer|judge|tribunal|procedure|plainte|avocat|juge)\b",
    "emotional_appeal": r"\b(please|for (god|our|the love)|i beg|have mercy|heart)\b",
    "sarcasm": r"\b(oh really|sure|right|of course|brilliant|genius)\b.*[.!]$",
    "passive_aggressive": r"\b(fine|whatever|if you say so|do what you want|your (choice|problem))\b",
    "deflection": r"\b(anyway|moving on|that's not the point|regardless|let's talk about)\b",
    "ultimatum": r"\b(last (chance|time|warning)|final|or else|deadline|until)\b",
    "self_reference": r"\b(i|me|my|mine|myself)\b",
    "other_reference": r"\b(you|your|yours|yourself)\b",
}


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        -- People being analyzed
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            aliases TEXT DEFAULT '[]',  -- JSON list of known aliases
            role TEXT DEFAULT 'unknown', -- protagonist, antagonist, witness, child, legal, associate
            notes TEXT DEFAULT '',
            profile_json TEXT DEFAULT '{}',  -- latest profile snapshot
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        -- Individual analysis results
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER REFERENCES subjects(id),
            analysis_type TEXT NOT NULL,  -- profile, negotiate, deception, emotion, manipulate, predict, briefing
            scope TEXT DEFAULT '',  -- what data was analyzed (date range, chat, etc.)
            result_json TEXT NOT NULL,  -- structured analysis output
            summary TEXT NOT NULL,  -- human-readable summary
            confidence REAL DEFAULT 0.5,  -- 0-1 confidence score
            llm_used INTEGER DEFAULT 0,  -- whether Mistral was invoked
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Detected manipulation events
        CREATE TABLE IF NOT EXISTS manipulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER REFERENCES subjects(id),
            target_subject_id INTEGER REFERENCES subjects(id),
            technique TEXT NOT NULL,  -- key from MANIPULATION_PATTERNS
            source TEXT NOT NULL,  -- whatsapp, email, document, etc.
            source_ref TEXT,  -- message ID, doc path, etc.
            timestamp TEXT NOT NULL,
            message_excerpt TEXT,
            severity REAL DEFAULT 0.5,  -- 0-1
            context TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Emotional state tracking
        CREATE TABLE IF NOT EXISTS emotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER REFERENCES subjects(id),
            timestamp TEXT NOT NULL,
            emotion TEXT NOT NULL,  -- key from EMOTION_LEXICON
            intensity REAL DEFAULT 0.5,  -- 0-1
            source TEXT NOT NULL,
            source_ref TEXT,
            message_excerpt TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Relationship edges (power dynamics)
        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_a INTEGER REFERENCES subjects(id),
            subject_b INTEGER REFERENCES subjects(id),
            relationship_type TEXT,  -- spouse, parent-child, lawyer-client, etc.
            power_balance REAL DEFAULT 0.0,  -- -1 (A dominates) to +1 (B dominates)
            communication_freq REAL DEFAULT 0.0,  -- msgs per day
            avg_response_time REAL,  -- seconds
            conflict_level REAL DEFAULT 0.0,  -- 0-1
            data_json TEXT DEFAULT '{}',
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(subject_a, subject_b)
        );

        -- Communication statistics per person per period
        CREATE TABLE IF NOT EXISTS comm_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER REFERENCES subjects(id),
            period TEXT NOT NULL,  -- YYYY-MM or YYYY-WXX
            total_messages INTEGER DEFAULT 0,
            avg_length REAL DEFAULT 0,
            avg_response_time REAL,  -- seconds
            question_ratio REAL DEFAULT 0,
            imperative_ratio REAL DEFAULT 0,
            emotional_intensity REAL DEFAULT 0,
            self_reference_ratio REAL DEFAULT 0,
            dominant_emotion TEXT,
            manipulation_count INTEGER DEFAULT 0,
            style_json TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(subject_id, period)
        );

        -- Predictions and their outcomes (for calibration)
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER REFERENCES subjects(id),
            scenario TEXT NOT NULL,
            predicted_response TEXT NOT NULL,
            confidence REAL DEFAULT 0.5,
            reasoning TEXT,
            actual_outcome TEXT,  -- filled in later for calibration
            was_correct INTEGER,  -- 0/1, filled later
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- FTS for searching analyses
        CREATE VIRTUAL TABLE IF NOT EXISTS analyses_fts USING fts5(
            summary, content='analyses', content_rowid='id'
        );
        CREATE TRIGGER IF NOT EXISTS analyses_ai AFTER INSERT ON analyses BEGIN
            INSERT INTO analyses_fts(rowid, summary) VALUES (new.id, new.summary);
        END;
        CREATE TRIGGER IF NOT EXISTS analyses_ad AFTER DELETE ON analyses BEGIN
            INSERT INTO analyses_fts(analyses_fts, rowid, summary) VALUES ('delete', old.id, old.summary);
        END;

        -- Cognitive bias tracking (self-analysis)
        CREATE TABLE IF NOT EXISTS cognitive_biases (
            id INTEGER PRIMARY KEY,
            bias_name TEXT NOT NULL,
            category TEXT,  -- decision, financial, legal, emotional, social
            detected_in TEXT,  -- description of where the bias was detected
            severity TEXT,  -- low, medium, high, critical
            financial_impact REAL,  -- estimated EUR impact of this bias
            mitigation TEXT,  -- recommended countermeasure
            status TEXT DEFAULT 'active',  -- active, mitigated, acknowledged
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            mitigated_at TIMESTAMP
        );

        -- Bias intervention log
        CREATE TABLE IF NOT EXISTS bias_interventions (
            id INTEGER PRIMARY KEY,
            bias_id INTEGER REFERENCES cognitive_biases(id),
            intervention_type TEXT,  -- reframe, premortem, reference_class, devil_advocate, delay
            message TEXT NOT NULL,  -- the actual intervention message to show
            triggered_by TEXT,  -- what triggered this intervention
            shown_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            acknowledged INTEGER DEFAULT 0
        );

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_analyses_subject ON analyses(subject_id);
        CREATE INDEX IF NOT EXISTS idx_analyses_type ON analyses(analysis_type);
        CREATE INDEX IF NOT EXISTS idx_manip_subject ON manipulations(subject_id);
        CREATE INDEX IF NOT EXISTS idx_manip_tech ON manipulations(technique);
        CREATE INDEX IF NOT EXISTS idx_manip_ts ON manipulations(timestamp);
        CREATE INDEX IF NOT EXISTS idx_emo_subject ON emotions(subject_id);
        CREATE INDEX IF NOT EXISTS idx_emo_ts ON emotions(timestamp);
        CREATE INDEX IF NOT EXISTS idx_comm_subject ON comm_stats(subject_id);
        CREATE INDEX IF NOT EXISTS idx_bias_status ON cognitive_biases(status);
        CREATE INDEX IF NOT EXISTS idx_bias_severity ON cognitive_biases(severity);
        CREATE INDEX IF NOT EXISTS idx_intervention_bias ON bias_interventions(bias_id);
    """)
    conn.commit()
    return conn


# ── Data source connectors ─────────────────────────────────────────────────

def _connect_ro(path):
    """Connect to external DB read-only."""
    if not path.exists():
        return None
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_whatsapp_messages(person_name, limit=5000):
    """Get all WhatsApp messages for/from a person."""
    wa = _connect_ro(WA_DB)
    if not wa:
        return []
    rows = wa.execute("""
        SELECT m.timestamp, m.sender, m.message, c.chat_name, m.is_media
        FROM messages m JOIN chats c ON m.chat_id = c.id
        WHERE (m.sender LIKE ? OR c.chat_name LIKE ?)
        AND m.is_system = 0 AND m.message IS NOT NULL AND m.message != 'null'
        ORDER BY m.timestamp
        LIMIT ?
    """, (f'%{person_name}%', f'%{person_name}%', limit)).fetchall()
    wa.close()
    return [dict(r) for r in rows]


def get_whatsapp_chat(chat_name, limit=5000):
    """Get all messages from a specific chat."""
    wa = _connect_ro(WA_DB)
    if not wa:
        return []
    rows = wa.execute("""
        SELECT m.timestamp, m.sender, m.message, c.chat_name, m.is_media
        FROM messages m JOIN chats c ON m.chat_id = c.id
        WHERE c.chat_name LIKE ? AND m.is_system = 0
        AND m.message IS NOT NULL AND m.message != 'null'
        ORDER BY m.timestamp
        LIMIT ?
    """, (f'%{chat_name}%', limit)).fetchall()
    wa.close()
    return [dict(r) for r in rows]


# ── Core analysis functions ────────────────────────────────────────────────

def analyze_text(text):
    """Analyze a single message for emotions, manipulation, and style."""
    text_lower = text.lower() if text else ""
    result = {
        "emotions": {},
        "manipulations": [],
        "style": {},
        "word_count": len(text.split()) if text else 0,
    }

    # Emotion detection
    for emotion, patterns in EMOTION_LEXICON.items():
        score = 0
        for p in patterns:
            matches = re.findall(p, text_lower, re.IGNORECASE)
            score += len(matches)
        if score > 0:
            # Normalize: more matches = higher intensity, capped at 1.0
            result["emotions"][emotion] = min(1.0, score * 0.25)

    # Manipulation detection
    for tech_key, tech in MANIPULATION_PATTERNS.items():
        for p in tech.get("markers", []):
            if re.search(p, text_lower, re.IGNORECASE):
                result["manipulations"].append(tech_key)
                break

    # Style markers
    for marker, pattern in STYLE_MARKERS.items():
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        if matches:
            result["style"][marker] = len(matches)

    return result


def compute_response_times(messages, person_name):
    """Compute average response times for a person in conversation."""
    times = []
    prev_msg = None
    for msg in messages:
        if prev_msg and msg["sender"] != prev_msg["sender"]:
            try:
                t1 = datetime.fromisoformat(prev_msg["timestamp"])
                t2 = datetime.fromisoformat(msg["timestamp"])
                delta = (t2 - t1).total_seconds()
                if 0 < delta < 86400:  # Within 24 hours
                    if person_name.lower() in msg["sender"].lower():
                        times.append(delta)
            except (ValueError, TypeError):
                pass
        prev_msg = msg
    return times


def compute_silence_gaps(messages, person_name, threshold_hours=48):
    """Detect silent treatment periods (gaps > threshold)."""
    gaps = []
    last_msg_time = None
    for msg in messages:
        if person_name.lower() in msg["sender"].lower():
            try:
                t = datetime.fromisoformat(msg["timestamp"])
                if last_msg_time:
                    delta_hours = (t - last_msg_time).total_seconds() / 3600
                    if delta_hours > threshold_hours:
                        gaps.append({
                            "start": last_msg_time.isoformat(),
                            "end": t.isoformat(),
                            "hours": round(delta_hours, 1),
                        })
                last_msg_time = t
            except (ValueError, TypeError):
                pass
    return gaps


def message_frequency_by_period(messages, person_name, period="month"):
    """Count messages per period."""
    counts = Counter()
    for msg in messages:
        if not msg.get("timestamp"):
            continue
        ts = msg["timestamp"][:7] if period == "month" else msg["timestamp"][:10]
        if person_name.lower() in msg["sender"].lower():
            counts[ts] += 1
    return dict(sorted(counts.items()))


# ── Role: Profiler ─────────────────────────────────────────────────────────

def build_profile(conn, subject_name, use_llm=False):
    """Build comprehensive psychological profile from all available data."""
    messages = get_whatsapp_messages(subject_name)
    if not messages:
        print(f"  No messages found for '{subject_name}'")
        return None

    # Get or create subject
    sub = conn.execute("SELECT * FROM subjects WHERE name LIKE ?",
                       (f'%{subject_name}%',)).fetchone()
    if not sub:
        conn.execute("INSERT INTO subjects (name, role) VALUES (?, 'unknown')",
                     (subject_name,))
        conn.commit()
        sub = conn.execute("SELECT * FROM subjects WHERE name = ?",
                           (subject_name,)).fetchone()
    subject_id = sub["id"]

    # Analyze all messages from this person
    their_msgs = [m for m in messages if subject_name.lower() in m["sender"].lower()]
    others_msgs = [m for m in messages if subject_name.lower() not in m["sender"].lower()]

    total_emotions = Counter()
    total_manipulations = Counter()
    total_style = Counter()
    total_words = 0
    msg_lengths = []

    for msg in their_msgs:
        if not msg.get("message") or msg["message"] == "null":
            continue
        analysis = analyze_text(msg["message"])
        for emo, score in analysis["emotions"].items():
            total_emotions[emo] += score
        for manip in analysis["manipulations"]:
            total_manipulations[manip] += 1
        for style, count in analysis["style"].items():
            total_style[style] += count
        total_words += analysis["word_count"]
        msg_lengths.append(analysis["word_count"])

    n_msgs = len(their_msgs) or 1

    # Response time analysis
    resp_times = compute_response_times(messages, subject_name)
    avg_resp = sum(resp_times) / len(resp_times) if resp_times else None

    # Silence gaps (potential silent treatment)
    silence_gaps = compute_silence_gaps(messages, subject_name)

    # Message frequency
    freq = message_frequency_by_period(messages, subject_name)

    # Self vs other reference ratio
    self_refs = total_style.get("self_reference", 0)
    other_refs = total_style.get("other_reference", 0)
    narcissism_indicator = self_refs / (self_refs + other_refs) if (self_refs + other_refs) > 0 else 0.5

    # Compute dominant emotion
    dominant_emo = total_emotions.most_common(1)[0][0] if total_emotions else "neutral"

    # Build profile dict
    profile = {
        "message_count": len(their_msgs),
        "total_analyzed": n_msgs,
        "avg_msg_length": round(total_words / n_msgs, 1),
        "median_msg_length": sorted(msg_lengths)[len(msg_lengths)//2] if msg_lengths else 0,
        "date_range": {
            "first": their_msgs[0]["timestamp"][:10] if their_msgs else None,
            "last": their_msgs[-1]["timestamp"][:10] if their_msgs else None,
        },
        "emotions": {k: round(v / n_msgs, 3) for k, v in total_emotions.most_common(10)},
        "dominant_emotion": dominant_emo,
        "manipulation_techniques": {k: v for k, v in total_manipulations.most_common(10)},
        "total_manipulation_events": sum(total_manipulations.values()),
        "communication_style": {k: round(v / n_msgs, 3) for k, v in total_style.most_common(15)},
        "response_time": {
            "avg_seconds": round(avg_resp, 0) if avg_resp else None,
            "avg_minutes": round(avg_resp / 60, 1) if avg_resp else None,
            "samples": len(resp_times),
        },
        "silence_gaps": {
            "count": len(silence_gaps),
            "longest_hours": max(g["hours"] for g in silence_gaps) if silence_gaps else 0,
            "gaps": silence_gaps[:5],  # Top 5 longest
        },
        "narcissism_indicator": round(narcissism_indicator, 3),
        "self_reference_ratio": round(self_refs / n_msgs, 3) if n_msgs else 0,
        "question_ratio": round(total_style.get("interrogative", 0) / n_msgs, 3),
        "imperative_ratio": round(total_style.get("imperative", 0) / n_msgs, 3),
        "absolute_language_ratio": round(total_style.get("absolute", 0) / n_msgs, 3),
        "message_frequency": freq,
    }

    # LLM deep analysis
    llm_summary = ""
    if use_llm:
        try:
            from mistral_client import mistral_chat
            sample = "\n".join(
                f"[{m['timestamp'][:16]}] {m['sender']}: {m['message'][:200]}"
                for m in their_msgs[-100:]
                if m.get("message") and m["message"] != "null"
            )
            llm_summary = mistral_chat(
                f"Analyse psychologique de cette personne basée sur ses messages. "
                f"Identifie: traits de personnalité, mécanismes de défense, style d'attachement, "
                f"stratégies de manipulation, vulnérabilités, forces. "
                f"Sois clinique et précis.\n\n{sample[:6000]}",
                system="Tu es un psychologue forensique expert en analyse comportementale. "
                       "Réponds en anglais. Sois direct et clinique."
            )
            profile["llm_analysis"] = llm_summary
        except Exception as e:
            llm_summary = f"[LLM unavailable: {e}]"

    # Generate summary
    manip_top = ", ".join(
        f"{MANIPULATION_PATTERNS[k]['label']}({v})"
        for k, v in total_manipulations.most_common(5)
    ) or "None detected"

    summary = (
        f"PROFILE: {subject_name}\n"
        f"Messages: {len(their_msgs)} | Period: {profile['date_range']['first']} → {profile['date_range']['last']}\n"
        f"Avg length: {profile['avg_msg_length']} words | Response time: {profile['response_time']['avg_minutes']}min\n"
        f"Dominant emotion: {dominant_emo} | Narcissism indicator: {profile['narcissism_indicator']}\n"
        f"Manipulation events: {profile['total_manipulation_events']} — {manip_top}\n"
        f"Question ratio: {profile['question_ratio']} | Imperative ratio: {profile['imperative_ratio']}\n"
        f"Absolute language: {profile['absolute_language_ratio']} | Silence gaps: {profile['silence_gaps']['count']}\n"
    )
    if llm_summary:
        summary += f"\nLLM Analysis:\n{llm_summary[:500]}\n"

    # Save
    conn.execute("UPDATE subjects SET profile_json = ?, updated_at = datetime('now') WHERE id = ?",
                 (json.dumps(profile), subject_id))
    conn.execute("""
        INSERT INTO analyses (subject_id, analysis_type, scope, result_json, summary, confidence, llm_used)
        VALUES (?, 'profile', ?, ?, ?, ?, ?)
    """, (subject_id, f"{len(their_msgs)} messages",
          json.dumps(profile), summary, 0.7, 1 if use_llm else 0))
    conn.commit()

    return profile, summary


# ── Role: Manipulation Classifier ──────────────────────────────────────────

def classify_manipulations(conn, subject_name, target_name=None):
    """Scan all messages and classify manipulation techniques."""
    messages = get_whatsapp_messages(subject_name)
    if not messages:
        print(f"  No messages for '{subject_name}'")
        return

    sub = conn.execute("SELECT id FROM subjects WHERE name LIKE ?",
                       (f'%{subject_name}%',)).fetchone()
    if not sub:
        conn.execute("INSERT INTO subjects (name) VALUES (?)", (subject_name,))
        conn.commit()
        sub = conn.execute("SELECT id FROM subjects WHERE name = ?", (subject_name,)).fetchone()
    subject_id = sub["id"]

    target_id = None
    if target_name:
        t = conn.execute("SELECT id FROM subjects WHERE name LIKE ?",
                         (f'%{target_name}%',)).fetchone()
        if t:
            target_id = t["id"]

    their_msgs = [m for m in messages if subject_name.lower() in m["sender"].lower()]
    events = []

    for msg in their_msgs:
        if not msg.get("message") or msg["message"] == "null":
            continue
        analysis = analyze_text(msg["message"])
        for tech in analysis["manipulations"]:
            severity = 0.5
            # Boost severity for certain patterns
            if tech in ("darvo", "gaslighting", "parental_alienation"):
                severity = 0.8
            elif tech in ("threat_intimidation", "financial_abuse"):
                severity = 0.7

            events.append({
                "technique": tech,
                "timestamp": msg["timestamp"],
                "message": msg["message"][:300],
                "severity": severity,
            })

            try:
                conn.execute("""
                    INSERT OR IGNORE INTO manipulations
                    (subject_id, target_subject_id, technique, source, source_ref, timestamp, message_excerpt, severity)
                    VALUES (?, ?, ?, 'whatsapp', ?, ?, ?, ?)
                """, (subject_id, target_id, tech, msg.get("chat_name", ""),
                      msg["timestamp"], msg["message"][:300], severity))
            except Exception:
                pass

    # Detect silent treatment by gaps
    silence_gaps = compute_silence_gaps(messages, subject_name, threshold_hours=72)
    for gap in silence_gaps:
        events.append({
            "technique": "silent_treatment",
            "timestamp": gap["start"],
            "message": f"Silence gap: {gap['hours']} hours ({gap['start']} → {gap['end']})",
            "severity": min(1.0, gap["hours"] / 168),  # 1 week = max severity
        })
        try:
            conn.execute("""
                INSERT OR IGNORE INTO manipulations
                (subject_id, target_subject_id, technique, source, timestamp, message_excerpt, severity)
                VALUES (?, ?, 'silent_treatment', 'whatsapp', ?, ?, ?)
            """, (subject_id, target_id, gap["start"],
                  f"Silence: {gap['hours']}h", min(1.0, gap["hours"] / 168)))
        except Exception:
            pass

    conn.commit()

    # Summary
    tech_counts = Counter(e["technique"] for e in events)
    summary_lines = [f"MANIPULATION ANALYSIS: {subject_name}", f"Total events: {len(events)}", ""]
    for tech, count in tech_counts.most_common():
        label = MANIPULATION_PATTERNS.get(tech, {}).get("label", tech)
        desc = MANIPULATION_PATTERNS.get(tech, {}).get("desc", "")
        summary_lines.append(f"  {label}: {count} occurrences")
        summary_lines.append(f"    → {desc}")
        # Show worst examples
        worst = sorted([e for e in events if e["technique"] == tech],
                       key=lambda x: x["severity"], reverse=True)[:3]
        for w in worst:
            summary_lines.append(f"    [{w['timestamp'][:16]}] {w['message'][:100]}")
        summary_lines.append("")

    summary = "\n".join(summary_lines)

    conn.execute("""
        INSERT INTO analyses (subject_id, analysis_type, scope, result_json, summary, confidence)
        VALUES (?, 'manipulate', ?, ?, ?, 0.65)
    """, (subject_id, f"{len(their_msgs)} messages, {len(events)} events",
          json.dumps({"events": len(events), "by_technique": dict(tech_counts)}), summary))
    conn.commit()

    return events, summary


# ── Role: Emotion Timeline ─────────────────────────────────────────────────

def build_emotion_timeline(conn, subject_name):
    """Track emotional states over time."""
    messages = get_whatsapp_messages(subject_name)
    if not messages:
        print(f"  No messages for '{subject_name}'")
        return

    sub = conn.execute("SELECT id FROM subjects WHERE name LIKE ?",
                       (f'%{subject_name}%',)).fetchone()
    if not sub:
        conn.execute("INSERT INTO subjects (name) VALUES (?)", (subject_name,))
        conn.commit()
        sub = conn.execute("SELECT id FROM subjects WHERE name = ?", (subject_name,)).fetchone()
    subject_id = sub["id"]

    their_msgs = [m for m in messages if subject_name.lower() in m["sender"].lower()]
    monthly_emotions = defaultdict(lambda: Counter())
    all_entries = []

    for msg in their_msgs:
        if not msg.get("message") or msg["message"] == "null":
            continue
        analysis = analyze_text(msg["message"])
        month = msg["timestamp"][:7] if msg.get("timestamp") else "unknown"

        for emo, intensity in analysis["emotions"].items():
            monthly_emotions[month][emo] += intensity
            all_entries.append({
                "timestamp": msg["timestamp"],
                "emotion": emo,
                "intensity": intensity,
                "excerpt": msg["message"][:100],
            })
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO emotions
                    (subject_id, timestamp, emotion, intensity, source, source_ref, message_excerpt)
                    VALUES (?, ?, ?, ?, 'whatsapp', ?, ?)
                """, (subject_id, msg["timestamp"], emo, intensity,
                      msg.get("chat_name", ""), msg["message"][:200]))
            except Exception:
                pass

    conn.commit()

    # Build timeline display
    months = sorted(monthly_emotions.keys())
    summary_lines = [f"EMOTIONAL TIMELINE: {subject_name}", f"Period: {months[0] if months else '?'} → {months[-1] if months else '?'}", ""]

    for month in months:
        emotions = monthly_emotions[month]
        dominant = emotions.most_common(1)[0] if emotions else ("neutral", 0)
        total = sum(emotions.values())
        bar_len = min(40, int(total))
        emo_bar = "█" * bar_len

        summary_lines.append(f"  {month}  {dominant[0]:12s} ({total:5.1f})  {emo_bar}")
        # Sub-emotions
        for emo, score in emotions.most_common(3):
            pct = (score / total * 100) if total > 0 else 0
            summary_lines.append(f"           {emo:12s}  {pct:5.1f}%")

    summary = "\n".join(summary_lines)

    conn.execute("""
        INSERT INTO analyses (subject_id, analysis_type, scope, result_json, summary, confidence)
        VALUES (?, 'emotion', ?, ?, ?, 0.6)
    """, (subject_id, f"{len(their_msgs)} messages, {len(months)} months",
          json.dumps({"months": {m: dict(e) for m, e in monthly_emotions.items()}}), summary))
    conn.commit()

    return monthly_emotions, summary


# ── Role: Relationship Mapper ──────────────────────────────────────────────

def map_relationships(conn, focus_name=None):
    """Map communication patterns and power dynamics."""
    wa = _connect_ro(WA_DB)
    if not wa:
        print("  WhatsApp DB not available")
        return

    # Get all chat participants
    if focus_name:
        rows = wa.execute("""
            SELECT c.chat_name, m.sender, count(*) as cnt,
                   MIN(m.timestamp) as first, MAX(m.timestamp) as last,
                   AVG(length(m.message)) as avg_len
            FROM messages m JOIN chats c ON m.chat_id = c.id
            WHERE (c.chat_name LIKE ? OR m.sender LIKE ?)
            AND m.is_system = 0 AND m.message != 'null'
            GROUP BY c.chat_name, m.sender
            ORDER BY cnt DESC
        """, (f'%{focus_name}%', f'%{focus_name}%')).fetchall()
    else:
        rows = wa.execute("""
            SELECT c.chat_name, m.sender, count(*) as cnt,
                   MIN(m.timestamp) as first, MAX(m.timestamp) as last,
                   AVG(length(m.message)) as avg_len
            FROM messages m JOIN chats c ON m.chat_id = c.id
            WHERE m.is_system = 0 AND m.message != 'null'
            GROUP BY c.chat_name, m.sender
            HAVING cnt > 10
            ORDER BY cnt DESC LIMIT 100
        """).fetchall()
    wa.close()

    # Build relationship summary
    chat_dynamics = defaultdict(lambda: {"participants": {}, "total": 0})
    for r in rows:
        chat = r["chat_name"]
        sender = r["sender"]
        chat_dynamics[chat]["participants"][sender] = {
            "count": r["cnt"],
            "avg_len": round(r["avg_len"], 1) if r["avg_len"] else 0,
            "first": r["first"],
            "last": r["last"],
        }
        chat_dynamics[chat]["total"] += r["cnt"]

    summary_lines = [f"RELATIONSHIP MAP{' — ' + focus_name if focus_name else ''}", ""]

    for chat, data in sorted(chat_dynamics.items(), key=lambda x: x[1]["total"], reverse=True)[:20]:
        summary_lines.append(f"  [{chat[:35]:35s}]  {data['total']:>6,d} msgs")
        participants = data["participants"]
        total = data["total"] or 1

        for sender, info in sorted(participants.items(), key=lambda x: x[1]["count"], reverse=True):
            pct = info["count"] / total * 100
            dominance = "▓" if pct > 60 else "▒" if pct > 40 else "░"
            summary_lines.append(
                f"    {dominance} {sender[:25]:25s} {info['count']:>5,d} ({pct:4.1f}%)  "
                f"avg {info['avg_len']:>5.0f} chars  {info['first'][:10]}→{info['last'][:10]}"
            )
        summary_lines.append("")

    summary = "\n".join(summary_lines)
    print(summary)
    return chat_dynamics


# ── Role: Deception Detector ───────────────────────────────────────────────

def detect_deception(conn, subject_name, use_llm=False):
    """Detect inconsistencies, contradictions, and deceptive patterns."""
    messages = get_whatsapp_messages(subject_name)
    if not messages:
        print(f"  No messages for '{subject_name}'")
        return

    sub = conn.execute("SELECT id FROM subjects WHERE name LIKE ?",
                       (f'%{subject_name}%',)).fetchone()
    if not sub:
        conn.execute("INSERT INTO subjects (name) VALUES (?)", (subject_name,))
        conn.commit()
        sub = conn.execute("SELECT id FROM subjects WHERE name = ?", (subject_name,)).fetchone()
    subject_id = sub["id"]

    their_msgs = [m for m in messages if subject_name.lower() in m["sender"].lower()
                  and m.get("message") and m["message"] != "null"]

    findings = []

    # 1. Contradiction detection: statements that flip
    # Track claims about locations, events, feelings
    location_claims = []
    for msg in their_msgs:
        text = msg["message"].lower()
        # Location mentions
        loc_match = re.search(r'\b(i am|i\'m|we are|we\'re|currently|right now).{0,30}(in |at |near )([\w\s]+)', text)
        if loc_match:
            location_claims.append({
                "timestamp": msg["timestamp"],
                "location": loc_match.group(3).strip()[:30],
                "full": msg["message"][:100],
            })

    # Check for rapid location changes (potential lies)
    for i in range(1, len(location_claims)):
        prev = location_claims[i-1]
        curr = location_claims[i]
        if prev["location"] != curr["location"]:
            try:
                t1 = datetime.fromisoformat(prev["timestamp"])
                t2 = datetime.fromisoformat(curr["timestamp"])
                hours = (t2 - t1).total_seconds() / 3600
                if 0 < hours < 6:  # Location change within 6 hours
                    findings.append({
                        "type": "rapid_location_change",
                        "timestamp": curr["timestamp"],
                        "detail": f"'{prev['location']}' → '{curr['location']}' in {hours:.1f}h",
                        "severity": 0.6,
                        "evidence": [prev["full"], curr["full"]],
                    })
            except (ValueError, TypeError):
                pass

    # 2. Denial patterns: "I never" / "I didn't" followed by evidence of the contrary
    denial_msgs = [m for m in their_msgs
                   if re.search(r'\b(i never|i didn\'t|i don\'t|that (never|didn\'t) happen|not true)\b',
                                m["message"].lower())]
    for msg in denial_msgs:
        findings.append({
            "type": "denial_statement",
            "timestamp": msg["timestamp"],
            "detail": msg["message"][:200],
            "severity": 0.4,
            "evidence": [],
        })

    # 3. Deflection patterns
    deflection_msgs = [m for m in their_msgs
                       if re.search(r'\b(anyway|that\'s not the point|you\'re changing|don\'t change the subject|not about)\b',
                                    m["message"].lower())]
    for msg in deflection_msgs:
        findings.append({
            "type": "deflection",
            "timestamp": msg["timestamp"],
            "detail": msg["message"][:200],
            "severity": 0.3,
            "evidence": [],
        })

    # 4. Promise tracking: unfulfilled commitments
    promise_msgs = [m for m in their_msgs
                    if re.search(r'\b(i (will|promise|swear)|tomorrow|next week|soon|i\'ll send|i\'ll do)\b',
                                 m["message"].lower())]
    for msg in promise_msgs:
        findings.append({
            "type": "promise",
            "timestamp": msg["timestamp"],
            "detail": msg["message"][:200],
            "severity": 0.2,
            "evidence": [],
        })

    # 5. LLM deep deception analysis
    llm_analysis = ""
    if use_llm and their_msgs:
        try:
            from mistral_client import mistral_chat
            sample = "\n".join(
                f"[{m['timestamp'][:16]}] {m['message'][:200]}"
                for m in their_msgs[-80:]
            )
            llm_analysis = mistral_chat(
                f"Analyze these messages for signs of deception, manipulation, and inconsistencies. "
                f"Look for: contradictions, changed stories, DARVO patterns, gaslighting, "
                f"projection, blame-shifting. Be specific with timestamps.\n\n{sample[:6000]}",
                system="You are a forensic psychologist specializing in deception detection. "
                       "Be clinical, specific, and evidence-based."
            )
        except Exception as e:
            llm_analysis = f"[LLM error: {e}]"

    # Summary
    type_counts = Counter(f["type"] for f in findings)
    summary_lines = [
        f"DECEPTION ANALYSIS: {subject_name}",
        f"Total findings: {len(findings)}",
        "",
    ]
    for ftype, count in type_counts.most_common():
        summary_lines.append(f"  {ftype}: {count}")
        examples = [f for f in findings if f["type"] == ftype][:3]
        for ex in examples:
            summary_lines.append(f"    [{ex['timestamp'][:16]}] {ex['detail'][:100]}")
        summary_lines.append("")

    if llm_analysis:
        summary_lines.append(f"LLM Analysis:\n{llm_analysis[:800]}")

    summary = "\n".join(summary_lines)

    conn.execute("""
        INSERT INTO analyses (subject_id, analysis_type, scope, result_json, summary, confidence, llm_used)
        VALUES (?, 'deception', ?, ?, ?, 0.5, ?)
    """, (subject_id, f"{len(their_msgs)} messages, {len(findings)} findings",
          json.dumps({"findings": len(findings), "by_type": dict(type_counts)}),
          summary, 1 if use_llm else 0))
    conn.commit()

    return findings, summary


# ── Role: Negotiation Analyzer ─────────────────────────────────────────────

def analyze_negotiation(conn, chat_name, use_llm=False):
    """Analyze negotiation dynamics in a chat."""
    messages = get_whatsapp_chat(chat_name)
    if not messages:
        print(f"  No messages in chat '{chat_name}'")
        return

    # Identify participants
    participants = Counter(m["sender"] for m in messages if m.get("sender"))

    # Negotiation-specific patterns
    negotiation_markers = {
        "offer": r"\b(i (propose|offer|suggest)|how about|what if|let's|deal)\b",
        "counter_offer": r"\b(instead|rather|better if|i prefer|no but|alternatively)\b",
        "concession": r"\b(ok|fine|i (accept|agree)|you('re| are) right|fair enough|deal)\b",
        "rejection": r"\b(no|refuse|impossible|never|won't|can't accept|out of question)\b",
        "threat": r"\b(or else|otherwise|i('ll| will)|consequence|court|lawyer|police)\b",
        "deadline": r"\b(by (tomorrow|friday|monday|\d)|until|deadline|last chance|time limit)\b",
        "emotional_pressure": r"\b(for (Constantin|the child|our family)|please|i beg)\b",
        "anchoring": r"\b(\d+[.,]\d+|\d+ (euro|eur|€|usd|\$|chf)|percent|%)\b",
        "walkaway": r"\b(that's it|i'm done|forget it|goodbye|no more|final)\b",
    }

    # Analyze each message
    negotiation_events = []
    for msg in messages:
        if not msg.get("message") or msg["message"] == "null":
            continue
        text = msg["message"].lower()
        for ntype, pattern in negotiation_markers.items():
            if re.search(pattern, text, re.IGNORECASE):
                negotiation_events.append({
                    "type": ntype,
                    "sender": msg["sender"],
                    "timestamp": msg["timestamp"],
                    "message": msg["message"][:200],
                })

    # Power dynamics: who makes more offers vs rejections
    sender_tactics = defaultdict(lambda: Counter())
    for evt in negotiation_events:
        sender_tactics[evt["sender"]][evt["type"]] += 1

    summary_lines = [
        f"NEGOTIATION ANALYSIS: {chat_name}",
        f"Messages: {len(messages)} | Negotiation events: {len(negotiation_events)}",
        f"Participants: {', '.join(f'{k}({v})' for k, v in participants.most_common())}",
        "",
    ]

    for sender, tactics in sorted(sender_tactics.items()):
        summary_lines.append(f"  {sender}:")
        for tactic, count in tactics.most_common():
            summary_lines.append(f"    {tactic:20s}: {count}")
        # Compute negotiation style
        offers = tactics.get("offer", 0) + tactics.get("concession", 0)
        pressures = tactics.get("threat", 0) + tactics.get("deadline", 0) + tactics.get("emotional_pressure", 0)
        rejections = tactics.get("rejection", 0) + tactics.get("walkaway", 0)
        total = offers + pressures + rejections or 1
        summary_lines.append(f"    → Style: cooperative={offers/total:.0%} pressure={pressures/total:.0%} resistant={rejections/total:.0%}")
        summary_lines.append("")

    # LLM deep analysis
    if use_llm:
        try:
            from mistral_client import mistral_chat
            sample = "\n".join(
                f"[{m['timestamp'][:16]}] {m['sender']}: {m['message'][:200]}"
                for m in messages[-100:]
                if m.get("message") and m["message"] != "null"
            )
            llm_result = mistral_chat(
                f"Analyze this negotiation. Identify: BATNA for each party, "
                f"tactics used, power dynamics, bluffs vs genuine positions, "
                f"likely outcomes, and recommended counter-strategies.\n\n{sample[:6000]}",
                system="You are an expert negotiation analyst. Be strategic and actionable."
            )
            summary_lines.append(f"LLM Strategic Analysis:\n{llm_result[:1000]}")
        except Exception:
            pass

    summary = "\n".join(summary_lines)
    print(summary)
    return negotiation_events, summary


# ── Role: Behavioral Predictor ─────────────────────────────────────────────

def predict_behavior(conn, subject_name, scenario, use_llm=True):
    """Predict how a person would react to a scenario based on historical patterns."""
    sub = conn.execute("SELECT * FROM subjects WHERE name LIKE ?",
                       (f'%{subject_name}%',)).fetchone()
    if not sub:
        print(f"  No profile for '{subject_name}'. Run 'profile' first.")
        return

    subject_id = sub["id"]
    profile = json.loads(sub["profile_json"]) if sub["profile_json"] else {}

    # Get recent manipulation patterns
    manips = conn.execute("""
        SELECT technique, count(*) as cnt FROM manipulations
        WHERE subject_id = ? GROUP BY technique ORDER BY cnt DESC
    """, (subject_id,)).fetchall()

    # Get emotional baseline
    emotions = conn.execute("""
        SELECT emotion, AVG(intensity) as avg_i, count(*) as cnt
        FROM emotions WHERE subject_id = ?
        GROUP BY emotion ORDER BY cnt DESC
    """, (subject_id,)).fetchall()

    # Build context for prediction
    context = {
        "profile": profile,
        "top_manipulations": [{"technique": m["technique"], "count": m["cnt"]} for m in manips[:5]],
        "emotional_baseline": [{"emotion": e["emotion"], "avg_intensity": round(e["avg_i"], 2)} for e in emotions[:5]],
    }

    prediction = ""
    if use_llm:
        try:
            from mistral_client import mistral_chat
            messages = get_whatsapp_messages(subject_name, limit=200)
            their_msgs = [m for m in messages if subject_name.lower() in m["sender"].lower()
                          and m.get("message") and m["message"] != "null"]
            sample = "\n".join(
                f"[{m['timestamp'][:16]}] {m['message'][:150]}"
                for m in their_msgs[-50:]
            )

            prediction = mistral_chat(
                f"Based on this person's behavioral profile and communication history, "
                f"predict how they would react to this scenario:\n\n"
                f"SCENARIO: {scenario}\n\n"
                f"PROFILE:\n"
                f"Dominant emotion: {profile.get('dominant_emotion', 'unknown')}\n"
                f"Narcissism indicator: {profile.get('narcissism_indicator', '?')}\n"
                f"Top manipulation: {context['top_manipulations'][:3]}\n"
                f"Emotional baseline: {context['emotional_baseline'][:3]}\n\n"
                f"RECENT MESSAGES:\n{sample[:4000]}\n\n"
                f"Predict: (1) immediate reaction, (2) likely tactics, (3) timeline, "
                f"(4) recommended counter-strategy.",
                system="You are a forensic behavioral analyst. Make specific, actionable predictions. "
                       "Be direct. Base predictions on observable patterns, not speculation."
            )
        except Exception as e:
            prediction = f"[LLM unavailable: {e}]"
    else:
        # Rule-based prediction
        top_manip = manips[0]["technique"] if manips else "unknown"
        dom_emo = profile.get("dominant_emotion", "unknown")
        prediction = (
            f"Based on pattern analysis:\n"
            f"- Dominant response style: {dom_emo}\n"
            f"- Most likely tactic: {MANIPULATION_PATTERNS.get(top_manip, {}).get('label', top_manip)}\n"
            f"- Narcissism indicator: {profile.get('narcissism_indicator', '?')}\n"
            f"- Expected response time: {profile.get('response_time', {}).get('avg_minutes', '?')} min\n"
            f"[Run with --llm for deeper analysis]"
        )

    # Save prediction
    conn.execute("""
        INSERT INTO predictions (subject_id, scenario, predicted_response, confidence, reasoning)
        VALUES (?, ?, ?, 0.5, ?)
    """, (subject_id, scenario, prediction, json.dumps(context)))
    conn.commit()

    print(f"PREDICTION: {subject_name} → {scenario}\n")
    print(prediction)
    return prediction


# ── Role: Compare ──────────────────────────────────────────────────────────

def compare_styles(conn, name1, name2):
    """Compare communication styles of two people."""
    msgs1 = get_whatsapp_messages(name1)
    msgs2 = get_whatsapp_messages(name2)

    def compute_stats(messages, name):
        their = [m for m in messages if name.lower() in m["sender"].lower()
                 and m.get("message") and m["message"] != "null"]
        if not their:
            return {}
        total_style = Counter()
        total_emotions = Counter()
        total_manip = Counter()
        lengths = []
        for msg in their:
            a = analyze_text(msg["message"])
            for k, v in a["style"].items():
                total_style[k] += v
            for k, v in a["emotions"].items():
                total_emotions[k] += v
            for m in a["manipulations"]:
                total_manip[m] += 1
            lengths.append(a["word_count"])
        n = len(their) or 1
        return {
            "msgs": len(their),
            "avg_length": round(sum(lengths) / n, 1),
            "emotions": {k: round(v / n, 3) for k, v in total_emotions.most_common(5)},
            "style": {k: round(v / n, 3) for k, v in total_style.most_common(10)},
            "manipulations": dict(total_manip.most_common(5)),
            "narcissism": round(
                total_style.get("self_reference", 0) /
                (total_style.get("self_reference", 0) + total_style.get("other_reference", 0) + 1), 3
            ),
        }

    s1 = compute_stats(msgs1, name1)
    s2 = compute_stats(msgs2, name2)

    print(f"{'METRIC':<30s} {'< ' + name1[:15]:>20s} {'> ' + name2[:15]:>20s}")
    print("─" * 72)
    print(f"{'Messages analyzed':<30s} {s1.get('msgs', 0):>20,d} {s2.get('msgs', 0):>20,d}")
    print(f"{'Avg message length':<30s} {s1.get('avg_length', 0):>20.1f} {s2.get('avg_length', 0):>20.1f}")
    print(f"{'Narcissism indicator':<30s} {s1.get('narcissism', 0):>20.3f} {s2.get('narcissism', 0):>20.3f}")
    print()
    print("Emotions:")
    all_emos = set(list(s1.get("emotions", {}).keys()) + list(s2.get("emotions", {}).keys()))
    for emo in sorted(all_emos):
        v1 = s1.get("emotions", {}).get(emo, 0)
        v2 = s2.get("emotions", {}).get(emo, 0)
        print(f"  {emo:<28s} {v1:>20.3f} {v2:>20.3f}")
    print()
    print("Manipulation techniques:")
    all_manips = set(list(s1.get("manipulations", {}).keys()) + list(s2.get("manipulations", {}).keys()))
    for m in sorted(all_manips):
        v1 = s1.get("manipulations", {}).get(m, 0)
        v2 = s2.get("manipulations", {}).get(m, 0)
        label = MANIPULATION_PATTERNS.get(m, {}).get("label", m)
        print(f"  {label:<28s} {v1:>20d} {v2:>20d}")


# ── Game Theory Engine ─────────────────────────────────────────────────────

# Pre-defined game scenarios relevant to the case
GAME_SCENARIOS = {
    "le_rosey_pension": {
        "title": "Le Rosey + Pension: Constantin's Choice",
        "players": ["Hadrien", "Marina"],
        "description": "Constantin asked: live with father OR Le Rosey. Either outcome reduces Hadrien's burn.",
        "strategies": {
            "Hadrien": ["offer_choice", "insist_live_together", "negotiate_school", "court_order_custody"],
            "Marina": ["block_contact", "accept_rosey", "keep_status_quo", "fight_custody"],
        },
        "payoffs": {
            # offer_choice is dominant: Constantin picks father → no pension; picks Rosey → Marina pays school
            ("offer_choice", "block_contact"): (3, -4),           # MCA forces contact, Marina looks obstructive
            ("offer_choice", "accept_rosey"): (9, 1),             # Best: Marina pays Rosey (120K+), Hadrien saves pension
            ("offer_choice", "keep_status_quo"): (6, 3),          # Status quo but choice offered = leverage for later
            ("offer_choice", "fight_custody"): (5, -3),           # Criminal record + violence → custody fight favors Hadrien
            ("insist_live_together", "block_contact"): (-2, -2),  # Deadlock, both lose
            ("insist_live_together", "accept_rosey"): (4, 4),     # She agrees Rosey, he gets custody path
            ("insist_live_together", "keep_status_quo"): (-3, 5),  # Status quo favors Marina
            ("insist_live_together", "fight_custody"): (-4, -1),  # Ugly fight
            ("negotiate_school", "block_contact"): (1, -3),       # She blocks → court intervention
            ("negotiate_school", "accept_rosey"): (8, 3),         # Both agree on Rosey, costs split or shifted
            ("negotiate_school", "keep_status_quo"): (2, 5),      # She keeps power
            ("negotiate_school", "fight_custody"): (0, -2),       # Negotiation fails
            ("court_order_custody", "block_contact"): (6, -6),    # Court forces, Marina penalized for obstruction
            ("court_order_custody", "accept_rosey"): (7, 0),      # Court + Rosey = structured solution
            ("court_order_custody", "keep_status_quo"): (4, 2),   # Court takes time
            ("court_order_custody", "fight_custody"): (3, -5),    # Criminal charges + Hague = Marina loses badly
        },
        "context": "Le Rosey: EUR 120K+/yr. Pension: EUR 32.5K/mo (EUR 390K/yr). If Constantin lives with Hadrien → pension eliminated. If Constantin at Rosey → school fees become primary expense (Marina's obligation if she has custody). MCA already involved. Criminal charges pending against Marina. Hague hearing 17/03/2026. Malta CA jurisdiction WON. Annulment filed. PROBATION CONSTRAINT: Hadrien has 3yr probation (Oct 2025-2028) — any direct confrontation = catastrophic (return to jail). All strategies must go through institutional channels (MCA, CPM, courts, lawyers). Child Protection Malta informed. Victim Support Malta supports Natalia Zaiets."
    },
    "long_term_profitability": {
        "title": "Long-Term Financial Optimization (5yr horizon)",
        "players": ["Hadrien", "Marina"],
        "description": "Multi-year strategy: annulment → asset recovery → BTC income → RE flipping → pension elimination. PROBATION: all confrontation paths catastrophic.",
        "strategies": {
            "Hadrien": ["aggressive_legal", "selective_settlement", "full_court_press", "parallel_income"],
            "Marina": ["delay_everything", "selective_concession", "asset_hiding", "scorched_earth"],
        },
        "payoffs": {
            # aggressive_legal: pursue all cases simultaneously via lawyers — safe under probation
            ("aggressive_legal", "delay_everything"): (5, -3),     # Costs mount but cases converge
            ("aggressive_legal", "selective_concession"): (8, -1), # She concedes on some, Hadrien gains
            ("aggressive_legal", "asset_hiding"): (6, -7),         # IFW + crypto forensics catch her
            ("aggressive_legal", "scorched_earth"): (1, -8),       # Risk: she provokes confrontation → probation trap
            # selective_settlement: settle weak cases, push strong ones — safest path
            ("selective_settlement", "delay_everything"): (3, 2),   # She delays, he wastes time
            ("selective_settlement", "selective_concession"): (7, 4), # Both rational → efficient resolution
            ("selective_settlement", "asset_hiding"): (4, -2),      # He misses some assets
            ("selective_settlement", "scorched_earth"): (0, -5),    # She escalates, probation risk if proximity
            # full_court_press: criminal + civil + police + asset recovery ALL via institutions — optimal under probation
            ("full_court_press", "delay_everything"): (8, -6),     # Institutional momentum, she can't delay all
            ("full_court_press", "selective_concession"): (9, -2), # She capitulates under institutional weight
            ("full_court_press", "asset_hiding"): (8, -9),         # Police TF + CPM + IFW + Victim Support = overwhelming
            ("full_court_press", "scorched_earth"): (5, -10),      # Institutions shield Hadrien from confrontation
            # parallel_income: focus on BTC staking + RE flipping while legal plays out
            ("parallel_income", "delay_everything"): (6, 3),       # Income grows while she delays
            ("parallel_income", "selective_concession"): (8, 5),   # Best: both stable, income flowing
            ("parallel_income", "asset_hiding"): (5, 0),           # Income offsets legal costs
            ("parallel_income", "scorched_earth"): (2, -4),        # Income survives but probation risk from escalation
        },
        "context": "5-year horizon. Current burn EUR 943K/yr, target EUR 240K/yr. Liquid: EUR 2.2M + 20.5 BTC. Annulment enables asset recovery (Marina 'crypto queen'). Criminal cases (assassination, extortion, violence) = leverage. BTC staking 10 BTC. Malta RE flipping as income source. 14 active legal cases across 4 jurisdictions. PROBATION (Oct 2025-2028): full_court_press now DOMINANT because all action flows through institutions (police TF, CPM, Victim Support, MCA, courts) — Hadrien never in direct confrontation. Scorched_earth payoffs reduced for Hadrien because Marina may provoke proximity violations."
    },
    "institutional_coalition": {
        "title": "Institutional Coalition: Police TF + CPM + Victim Support",
        "players": ["Hadrien", "Marina"],
        "description": "Multi-agency institutional pressure. Police task force (criminal/DV), Child Protection Malta (Constantin welfare), Victim Support Malta (Natalia Zaiets). Hadrien acts ONLY through institutions — probation-safe.",
        "strategies": {
            "Hadrien": ["full_institutional", "selective_agencies", "passive_compliance", "direct_petition"],
            "Marina": ["cooperate_agencies", "obstruct_agencies", "flee_jurisdiction", "counter_narrative"],
        },
        "payoffs": {
            # full_institutional: engage all agencies simultaneously — dominant strategy
            ("full_institutional", "cooperate_agencies"): (8, -1),    # Best outcome: agencies document everything, Marina's cooperation = admission
            ("full_institutional", "obstruct_agencies"): (9, -8),     # Obstruction = contempt + additional charges + proves pattern
            ("full_institutional", "flee_jurisdiction"): (7, -9),     # Flight = guilt + EAW + Hague default + asset freeze
            ("full_institutional", "counter_narrative"): (6, -4),     # Agencies verify facts independently, her narrative crumbles
            # selective_agencies: focus on CPM + police, less on victim support
            ("selective_agencies", "cooperate_agencies"): (6, 1),     # Decent but misses corroboration from Natalia
            ("selective_agencies", "obstruct_agencies"): (7, -5),     # Still strong but less documentation
            ("selective_agencies", "flee_jurisdiction"): (5, -7),     # Loses some tracking capability
            ("selective_agencies", "counter_narrative"): (4, -1),     # She can partially control narrative
            # passive_compliance: let agencies lead, minimal proactive input
            ("passive_compliance", "cooperate_agencies"): (4, 3),     # Too passive, she shapes narrative
            ("passive_compliance", "obstruct_agencies"): (5, -2),     # Agencies still act on obstruction
            ("passive_compliance", "flee_jurisdiction"): (3, -5),     # Slow response to flight
            ("passive_compliance", "counter_narrative"): (2, 2),      # She dominates narrative, agencies lack input
            # direct_petition: bypass agencies, go directly to court — risky under probation
            ("direct_petition", "cooperate_agencies"): (5, 2),        # Court action without agency backing = weaker
            ("direct_petition", "obstruct_agencies"): (4, -3),        # Court sees obstruction but no agency corroboration
            ("direct_petition", "flee_jurisdiction"): (6, -6),        # Court issues orders but enforcement harder
            ("direct_petition", "counter_narrative"): (1, 1),         # He said / she said without institutional weight
        },
        "context": "ACTIVE AGENCIES: 1) Malta Police Task Force — criminal charges (violence 7/POL/536/2026, extortion, DV). 2) Child Protection Malta (CPM) — informed about Constantin, welfare monitoring, mandatory reporting. 3) Victim Support Malta — supporting Natalia Zaiets (witness/victim of Marina's violence). 4) Malta Central Authority — Hague Convention, international child access. PROBATION CONSTRAINT: Hadrien MUST operate exclusively through institutions. Full_institutional is DOMINANT (EV +7.5): every agency cross-corroborates, Marina faces simultaneous pressure from independent bodies. Her obstruction in any one agency strengthens cases in others. Flight = European Arrest Warrant + Hague default judgment."
    },
    "divorce_jurisdiction": {
        "title": "Divorce Jurisdiction: Monaco vs Malta",
        "players": ["Hadrien", "Marina"],
        "description": "Where the divorce proceedings should take place",
        "strategies": {
            "Hadrien": ["move_to_malta", "stay_monaco", "dual_track"],
            "Marina": ["fight_monaco", "accept_malta", "delay"],
        },
        "payoffs": {
            # (Hadrien_strategy, Marina_strategy) -> (Hadrien_payoff, Marina_payoff)
            # Scale: -10 (catastrophic) to +10 (optimal)
            ("move_to_malta", "fight_monaco"): (6, -3),     # H gets lower pension in Malta, M loses Monaco advantage
            ("move_to_malta", "accept_malta"): (8, -1),     # Clean transfer, both move forward
            ("move_to_malta", "delay"): (4, 2),             # M buys time, H still moves but slowly
            ("stay_monaco", "fight_monaco"): (-2, 7),       # M keeps €32.5K pension, H stuck
            ("stay_monaco", "accept_malta"): (3, 3),        # Unlikely but cooperative
            ("stay_monaco", "delay"): (-4, 5),              # Worst for H: stuck AND delayed
            ("dual_track", "fight_monaco"): (5, -1),        # H hedges, M confused
            ("dual_track", "accept_malta"): (7, 0),         # Best hedge pays off
            ("dual_track", "delay"): (2, 3),                # Both treading water
        },
        "context": "Zimeray recommends Malta. €32.5K/month pension at stake. Malta CA ruling on competence expected summer 2026."
    },
    "pension_negotiation": {
        "title": "Pension Negotiation",
        "players": ["Hadrien", "Marina"],
        "description": "Monthly pension amount and conditions",
        "strategies": {
            "Hadrien": ["slash_hard", "moderate_reduction", "maintain_conditional", "total_cutoff"],
            "Marina": ["demand_increase", "accept_reduction", "litigate", "negotiate_lump_sum"],
        },
        "payoffs": {
            ("slash_hard", "demand_increase"): (-2, -5),
            ("slash_hard", "accept_reduction"): (8, -3),
            ("slash_hard", "litigate"): (3, -2),
            ("slash_hard", "negotiate_lump_sum"): (5, 2),
            ("moderate_reduction", "demand_increase"): (-1, -2),
            ("moderate_reduction", "accept_reduction"): (6, 1),
            ("moderate_reduction", "litigate"): (2, 0),
            ("moderate_reduction", "negotiate_lump_sum"): (4, 3),
            ("maintain_conditional", "demand_increase"): (-4, 3),
            ("maintain_conditional", "accept_reduction"): (3, 4),
            ("maintain_conditional", "litigate"): (-3, 2),
            ("maintain_conditional", "negotiate_lump_sum"): (2, 5),
            ("total_cutoff", "demand_increase"): (-6, -8),
            ("total_cutoff", "accept_reduction"): (9, -6),
            ("total_cutoff", "litigate"): (-5, -3),
            ("total_cutoff", "negotiate_lump_sum"): (4, -1),
        },
        "context": "Current: €32.5K/month (was €50K). Marina crypto: ~$18M. Sanctions angle may block payments."
    },
    "custody_constantine": {
        "title": "Constantin Custody",
        "players": ["Hadrien", "Marina"],
        "description": "Custody arrangement for Constantin",
        "strategies": {
            "Hadrien": ["shared_custody", "full_custody", "status_quo", "leverage_abduction"],
            "Marina": ["block_access", "shared_custody", "relocate_child", "negotiate_terms"],
        },
        "payoffs": {
            # PROBATION-ADJUSTED: all must go through institutions (MCA/CPM/courts)
            ("shared_custody", "block_access"): (-2, 2),            # CPM documents obstruction, MCA enforces
            ("shared_custody", "shared_custody"): (7, 5),           # Best cooperative outcome
            ("shared_custody", "relocate_child"): (-5, 3),          # CPM + Hague = strong response
            ("shared_custody", "negotiate_terms"): (6, 6),          # Both rational
            ("full_custody", "block_access"): (-3, -4),             # Conviction weakens full custody bid slightly
            ("full_custody", "shared_custody"): (4, 2),             # Her criminal charges >> his conviction
            ("full_custody", "relocate_child"): (-6, -5),           # Hague + CPM + abduction precedent
            ("full_custody", "negotiate_terms"): (3, 3),            # Conviction = slight discount
            ("status_quo", "block_access"): (-4, 5),                # Worst: she blocks, he can't act directly
            ("status_quo", "shared_custody"): (3, 6),               # She controls narrative
            ("status_quo", "relocate_child"): (-7, 3),              # Catastrophic passivity
            ("status_quo", "negotiate_terms"): (2, 7),              # She sets terms
            ("leverage_abduction", "block_access"): (3, -6),        # Institutional leverage: CPM + MCA + police TF
            ("leverage_abduction", "shared_custody"): (8, 1),       # Strongest: institutions force her hand
            ("leverage_abduction", "relocate_child"): (-2, -7),     # EAW + Hague + CPM mandatory reporting
            ("leverage_abduction", "negotiate_terms"): (7, 2),      # Institutions as backdrop = maximum leverage
        },
        "context": "Constantin at International School of Monaco. Marina previously took child to Malta without consent. Zimeray handles abduction angle. PROBATION: Hadrien convicted Oct 2025 Malta (1mo jail, 3yr probation, restraining order). Direct custody confrontation = catastrophic. Must go through MCA + CPM + courts only. Child Protection Malta now informed about Constantin's welfare. Victim Support Malta engaged for Natalia Zaiets corroboration. Leverage_abduction through institutions = strongest (her criminal charges dwarf his conviction)."
    },
    "crypto_disclosure": {
        "title": "Marina's Crypto Assets Disclosure",
        "players": ["Hadrien", "Marina"],
        "description": "Strategy around Marina's hidden crypto (~$18M)",
        "strategies": {
            "Hadrien": ["reveal_evidence", "hold_leverage", "negotiate_quietly", "court_filing"],
            "Marina": ["deny_everything", "partial_disclosure", "claim_hadrien_gave", "preemptive_liquidate"],
        },
        "payoffs": {
            ("reveal_evidence", "deny_everything"): (7, -7),
            ("reveal_evidence", "partial_disclosure"): (5, -3),
            ("reveal_evidence", "claim_hadrien_gave"): (3, -1),
            ("reveal_evidence", "preemptive_liquidate"): (4, -5),
            ("hold_leverage", "deny_everything"): (6, 2),
            ("hold_leverage", "partial_disclosure"): (4, 3),
            ("hold_leverage", "claim_hadrien_gave"): (2, 4),
            ("hold_leverage", "preemptive_liquidate"): (1, 5),
            ("negotiate_quietly", "deny_everything"): (-2, 5),
            ("negotiate_quietly", "partial_disclosure"): (5, 4),
            ("negotiate_quietly", "claim_hadrien_gave"): (3, 5),
            ("negotiate_quietly", "preemptive_liquidate"): (-1, 3),
            ("court_filing", "deny_everything"): (8, -8),
            ("court_filing", "partial_disclosure"): (6, -4),
            ("court_filing", "claim_hadrien_gave"): (4, -2),
            ("court_filing", "preemptive_liquidate"): (3, -6),
        },
        "context": "163 BTC ($14.3M) + 875K ATOM ($1.5M) + 1,100 ETH ($2.4M). Forensic PDF sealed. Kraken subpoena pending."
    },
    "sanctions_leverage": {
        "title": "Sanctions Intelligence as Leverage",
        "players": ["Hadrien", "Marina"],
        "description": "How to use sanctions information strategically",
        "strategies": {
            "Hadrien": ["reveal_to_court", "private_pressure", "report_authorities", "hold_card"],
            "Marina": ["preempt_narrative", "deny_knowledge", "cooperate_compliance", "counterthreat"],
        },
        "payoffs": {
            ("reveal_to_court", "preempt_narrative"): (3, -2),
            ("reveal_to_court", "deny_knowledge"): (7, -6),
            ("reveal_to_court", "cooperate_compliance"): (5, 1),
            ("reveal_to_court", "counterthreat"): (2, -3),
            ("private_pressure", "preempt_narrative"): (4, 0),
            ("private_pressure", "deny_knowledge"): (6, -2),
            ("private_pressure", "cooperate_compliance"): (8, 3),
            ("private_pressure", "counterthreat"): (1, 1),
            ("report_authorities", "preempt_narrative"): (5, -5),
            ("report_authorities", "deny_knowledge"): (8, -8),
            ("report_authorities", "cooperate_compliance"): (6, -1),
            ("report_authorities", "counterthreat"): (3, -4),
            ("hold_card", "preempt_narrative"): (2, 3),
            ("hold_card", "deny_knowledge"): (5, 4),
            ("hold_card", "cooperate_compliance"): (4, 5),
            ("hold_card", "counterthreat"): (0, 2),
        },
        "context": "Marina referenced 'international sanctions' in WhatsApp Dec 2024. No public listing found. Source claims she is/was sanctioned."
    },
}


def find_nash_equilibria(payoffs, strategies_a, strategies_b):
    """Find Nash equilibria in a 2-player game."""
    equilibria = []

    for sa in strategies_a:
        for sb in strategies_b:
            is_nash = True
            pa, pb = payoffs.get((sa, sb), (0, 0))

            # Check if A can improve by deviating
            for alt_a in strategies_a:
                if alt_a != sa:
                    alt_pa, _ = payoffs.get((alt_a, sb), (0, 0))
                    if alt_pa > pa:
                        is_nash = False
                        break

            if not is_nash:
                continue

            # Check if B can improve by deviating
            for alt_b in strategies_b:
                if alt_b != sb:
                    _, alt_pb = payoffs.get((sa, alt_b), (0, 0))
                    if alt_pb > pb:
                        is_nash = False
                        break

            if is_nash:
                equilibria.append((sa, sb, pa, pb))

    return equilibria


def find_dominant_strategies(payoffs, strategies_a, strategies_b):
    """Find strictly dominant strategies for each player."""
    dominant_a = None
    dominant_b = None

    # Check A's strategies
    for candidate in strategies_a:
        dominates_all = True
        for other in strategies_a:
            if other == candidate:
                continue
            # candidate must beat other for ALL of B's strategies
            for sb in strategies_b:
                pa_cand, _ = payoffs.get((candidate, sb), (0, 0))
                pa_other, _ = payoffs.get((other, sb), (0, 0))
                if pa_cand <= pa_other:
                    dominates_all = False
                    break
            if not dominates_all:
                break
        if dominates_all:
            dominant_a = candidate

    # Check B's strategies
    for candidate in strategies_b:
        dominates_all = True
        for other in strategies_b:
            if other == candidate:
                continue
            for sa in strategies_a:
                _, pb_cand = payoffs.get((sa, candidate), (0, 0))
                _, pb_other = payoffs.get((sa, other), (0, 0))
                if pb_cand <= pb_other:
                    dominates_all = False
                    break
            if not dominates_all:
                break
        if dominates_all:
            dominant_b = candidate

    return dominant_a, dominant_b


def compute_minimax(payoffs, strategies_a, strategies_b):
    """Compute minimax strategies (risk-averse play)."""
    # For A: maximize the minimum payoff
    minimax_a = None
    best_worst_a = -999
    for sa in strategies_a:
        worst = min(payoffs.get((sa, sb), (0, 0))[0] for sb in strategies_b)
        if worst > best_worst_a:
            best_worst_a = worst
            minimax_a = (sa, worst)

    # For B: maximize the minimum payoff
    minimax_b = None
    best_worst_b = -999
    for sb in strategies_b:
        worst = min(payoffs.get((sa, sb), (0, 0))[1] for sa in strategies_a)
        if worst > best_worst_b:
            best_worst_b = worst
            minimax_b = (sb, worst)

    return minimax_a, minimax_b


def compute_expected_value(payoffs, strategies_a, strategies_b, profile_a=None, profile_b=None):
    """Compute expected values using behavioral profiles to estimate opponent's strategy distribution."""
    # Default: uniform distribution
    prob_a = {s: 1.0 / len(strategies_a) for s in strategies_a}
    prob_b = {s: 1.0 / len(strategies_b) for s in strategies_b}

    # Adjust based on psychological profiles
    if profile_b:
        # If opponent is high narcissism, they overweight aggressive strategies
        narcissism = profile_b.get("narcissism_indicator", 0.5)
        aggression_boost = narcissism * 0.3
        for s in strategies_b:
            if any(w in s for w in ["fight", "demand", "block", "deny", "counter", "litigate"]):
                prob_b[s] += aggression_boost
            elif any(w in s for w in ["accept", "cooperate", "negotiate", "shared"]):
                prob_b[s] -= aggression_boost * 0.5
        # Normalize
        total = sum(prob_b.values())
        prob_b = {s: max(0.05, p / total) for s, p in prob_b.items()}

    # Compute expected values for each of A's strategies
    ev_a = {}
    for sa in strategies_a:
        ev = sum(payoffs.get((sa, sb), (0, 0))[0] * prob_b[sb] for sb in strategies_b)
        ev_a[sa] = round(ev, 2)

    ev_b = {}
    for sb in strategies_b:
        ev = sum(payoffs.get((sa, sb), (0, 0))[1] * prob_a[sa] for sa in strategies_a)
        ev_b[sb] = round(ev, 2)

    return ev_a, ev_b, prob_a, prob_b


def classify_game_type(payoffs, strategies_a, strategies_b):
    """Classify the game type based on payoff structure."""
    types = []

    # Check for zero-sum tendency
    total_sum = sum(pa + pb for (pa, pb) in payoffs.values())
    avg_sum = total_sum / len(payoffs) if payoffs else 0
    if abs(avg_sum) < 1:
        types.append("zero-sum")
    elif avg_sum > 2:
        types.append("positive-sum (cooperation possible)")
    else:
        types.append("mixed-motive")

    # Check for prisoner's dilemma structure
    # (mutual cooperation > mutual defection, but defection temptation exists)
    nash = find_nash_equilibria(payoffs, strategies_a, strategies_b)
    pareto = find_pareto_optimal(payoffs, strategies_a, strategies_b)

    if nash and pareto:
        nash_outcomes = set((n[0], n[1]) for n in nash)
        pareto_outcomes = set((p[0], p[1]) for p in pareto)
        if not nash_outcomes.intersection(pareto_outcomes):
            types.append("prisoner's-dilemma-like (Nash ≠ Pareto optimal)")

    # Check for chicken game (two Nash equilibria, each favoring different player)
    if len(nash) == 2:
        if nash[0][2] > nash[1][2] and nash[0][3] < nash[1][3]:
            types.append("chicken-game-like (brinkmanship)")

    return types


def find_pareto_optimal(payoffs, strategies_a, strategies_b):
    """Find Pareto optimal outcomes."""
    outcomes = []
    for sa in strategies_a:
        for sb in strategies_b:
            pa, pb = payoffs.get((sa, sb), (0, 0))
            outcomes.append((sa, sb, pa, pb))

    pareto = []
    for o in outcomes:
        dominated = False
        for other in outcomes:
            if other[2] >= o[2] and other[3] >= o[3] and (other[2] > o[2] or other[3] > o[3]):
                dominated = True
                break
        if not dominated:
            pareto.append(o)

    return pareto


def run_game_analysis(conn, scenario_key, use_llm=False):
    """Run full game theory analysis on a scenario."""
    if scenario_key not in GAME_SCENARIOS:
        print(f"Unknown scenario: {scenario_key}")
        print(f"Available: {', '.join(GAME_SCENARIOS.keys())}")
        return

    game = GAME_SCENARIOS[scenario_key]
    players = game["players"]
    strats_a = game["strategies"][players[0]]
    strats_b = game["strategies"][players[1]]
    payoffs = game["payoffs"]

    # Get profiles if available
    profile_b = None
    sub_b = conn.execute("SELECT profile_json FROM subjects WHERE name LIKE ?",
                         (f'%{players[1]}%',)).fetchone()
    if sub_b and sub_b["profile_json"]:
        profile_b = json.loads(sub_b["profile_json"])

    # Analysis
    nash = find_nash_equilibria(payoffs, strats_a, strats_b)
    dominant_a, dominant_b = find_dominant_strategies(payoffs, strats_a, strats_b)
    minimax_a, minimax_b = compute_minimax(payoffs, strats_a, strats_b)
    pareto = find_pareto_optimal(payoffs, strats_a, strats_b)
    game_types = classify_game_type(payoffs, strats_a, strats_b)
    ev_a, ev_b, prob_a, prob_b = compute_expected_value(
        payoffs, strats_a, strats_b, profile_b=profile_b
    )

    # Display
    print(f"\n{'='*70}")
    print(f"  GAME THEORY ANALYSIS: {game['title']}")
    print(f"  {game['description']}")
    print(f"{'='*70}")
    print(f"\nContext: {game['context']}")
    print(f"Game type: {', '.join(game_types)}")

    # Payoff matrix
    col_width = max(max(len(s) for s in strats_b) + 2, 10)
    row_width = max(len(s) for s in strats_a) + 2
    table_width = row_width + 2 + col_width * len(strats_b) + 4

    print(f"\n  PAYOFF MATRIX  ({players[0]} payoff, {players[1]} payoff)")
    print(f"  {'─' * table_width}")

    # Header
    print(f"  {'':>{row_width}s}", end="")
    for sb in strats_b:
        print(f"  {sb:>{col_width}s}", end="")
    print()
    print(f"  {'─' * table_width}")

    for sa in strats_a:
        print(f"  {sa:>{row_width}s}", end="")
        for sb in strats_b:
            pa, pb = payoffs.get((sa, sb), (0, 0))
            cell = f"({pa:+d},{pb:+d})"
            print(f"  {cell:>{col_width}s}", end="")
        print()

    print(f"  {'─' * table_width}")

    # Nash equilibria
    print(f"\n── Nash Equilibria ──")
    if nash:
        for sa, sb, pa, pb in nash:
            print(f"  ★ {players[0]}={sa}, {players[1]}={sb}  →  ({pa:+d}, {pb:+d})")
    else:
        print(f"  No pure strategy Nash equilibrium (mixed strategy game)")

    # Dominant strategies
    print(f"\n── Dominant Strategies ──")
    print(f"  {players[0]}: {dominant_a or 'None (no dominant strategy)'}")
    print(f"  {players[1]}: {dominant_b or 'None (no dominant strategy)'}")

    # Minimax (safety-first)
    print(f"\n── Minimax (Risk-Averse) ──")
    if minimax_a:
        print(f"  {players[0]}: {minimax_a[0]} (guaranteed ≥ {minimax_a[1]:+d})")
    if minimax_b:
        print(f"  {players[1]}: {minimax_b[0]} (guaranteed ≥ {minimax_b[1]:+d})")

    # Expected values (profile-adjusted)
    print(f"\n── Expected Values (profile-adjusted) ──")
    print(f"  {players[0]}'s strategies:")
    for s in sorted(ev_a, key=ev_a.get, reverse=True):
        bar = "█" * max(0, int((ev_a[s] + 10) * 2))
        print(f"    {s:25s}  EV={ev_a[s]:+5.1f}  {bar}")

    if profile_b:
        print(f"\n  {players[1]}'s estimated strategy distribution (narcissism={profile_b.get('narcissism_indicator', '?')}):")
        for s in sorted(prob_b, key=prob_b.get, reverse=True):
            pct = prob_b[s] * 100
            bar = "▓" * int(pct / 2)
            print(f"    {s:25s}  {pct:4.1f}%  {bar}")

    # Pareto optimal
    print(f"\n── Pareto Optimal Outcomes ──")
    for sa, sb, pa, pb in pareto:
        is_nash = any(n[0] == sa and n[1] == sb for n in nash)
        marker = " ★NASH" if is_nash else ""
        print(f"  {players[0]}={sa}, {players[1]}={sb}  →  ({pa:+d}, {pb:+d}){marker}")

    # Strategic recommendation
    print(f"\n── RECOMMENDATION ──")
    best_ev = max(ev_a, key=ev_a.get)
    safe_play = minimax_a[0] if minimax_a else "unknown"

    if best_ev == safe_play:
        print(f"  ✓ CLEAR: Play '{best_ev}' (best EV AND safest)")
    else:
        print(f"  ⚖ TRADE-OFF:")
        print(f"    Aggressive: '{best_ev}' (EV={ev_a[best_ev]:+.1f}, higher reward)")
        print(f"    Safe:       '{safe_play}' (guaranteed ≥{minimax_a[1]:+d}, lower variance)")

    # Check if there's a commitment advantage
    nash_payoffs_a = [n[2] for n in nash]
    if nash_payoffs_a and max(nash_payoffs_a) > min(nash_payoffs_a):
        print(f"\n  ⚡ FIRST-MOVER ADVANTAGE detected:")
        print(f"    Committing early to a strategy can force opponent's hand")

    # LLM strategic synthesis
    if use_llm:
        try:
            from mistral_client import mistral_chat
            analysis_summary = (
                f"Game: {game['title']}\n"
                f"Nash equilibria: {nash}\n"
                f"Minimax: A={minimax_a}, B={minimax_b}\n"
                f"Expected values: A={ev_a}\n"
                f"Opponent profile narcissism: {profile_b.get('narcissism_indicator', '?') if profile_b else 'unknown'}\n"
                f"Context: {game['context']}\n"
            )
            llm_advice = mistral_chat(
                f"You are a game theory strategist advising {players[0]} in a divorce/custody battle. "
                f"Based on this analysis, provide specific tactical advice:\n\n{analysis_summary}\n\n"
                f"Consider: timing, information asymmetry, commitment devices, "
                f"credible threats, and the opponent's psychological profile.",
                system="Expert game theorist and strategic advisor. Be specific, actionable, "
                       "and consider both rational and emotional dimensions."
            )
            print(f"\n── LLM Strategic Synthesis ──\n{llm_advice[:1000]}")
        except Exception as e:
            print(f"\n  [LLM unavailable: {e}]")

    # Save analysis
    result = {
        "scenario": scenario_key,
        "nash": [(n[0], n[1], n[2], n[3]) for n in nash],
        "dominant": {"a": dominant_a, "b": dominant_b},
        "minimax": {"a": minimax_a, "b": minimax_b},
        "expected_values": {"a": ev_a, "b": ev_b},
        "pareto": [(p[0], p[1], p[2], p[3]) for p in pareto],
        "game_types": game_types,
        "recommendation": best_ev,
    }

    conn.execute("""
        INSERT INTO analyses (subject_id, analysis_type, scope, result_json, summary, confidence)
        VALUES (NULL, 'game_theory', ?, ?, ?, 0.7)
    """, (scenario_key, json.dumps(result),
          f"Game: {game['title']} | Nash: {len(nash)} | Rec: {best_ev}"))
    conn.commit()

    return result


def show_payoff_matrix(scenario_key):
    """Display payoff matrix for a scenario."""
    if scenario_key == "list" or scenario_key not in GAME_SCENARIOS:
        print("Available scenarios:")
        for k, v in GAME_SCENARIOS.items():
            print(f"  {k:25s}  {v['title']}")
        return

    game = GAME_SCENARIOS[scenario_key]
    players = game["players"]
    strats_a = game["strategies"][players[0]]
    strats_b = game["strategies"][players[1]]
    payoffs = game["payoffs"]

    print(f"\n{game['title']}")
    print(f"  {players[0]} (rows) vs {players[1]} (columns)")
    print(f"  Values: ({players[0]} payoff, {players[1]} payoff)\n")

    col_w = 18
    print(f"{'':22s}", end="")
    for sb in strats_b:
        print(f"{sb:>{col_w}s}", end="")
    print()
    print("─" * (22 + col_w * len(strats_b)))

    for sa in strats_a:
        print(f"{sa:20s} │", end="")
        for sb in strats_b:
            pa, pb = payoffs.get((sa, sb), (0, 0))
            print(f"  ({pa:+2d},{pb:+2d}){'':>8s}", end="")
        print()


# ── CLI Commands ───────────────────────────────────────────────────────────

def cmd_profile(args):
    conn = init_db()
    name = " ".join(args) if args else "Marina"
    use_llm = "--llm" in args
    if use_llm:
        args = [a for a in args if a != "--llm"]
        name = " ".join(args) if args else "Marina"
    print(f"Building profile for: {name}")
    result = build_profile(conn, name, use_llm=use_llm)
    if result:
        profile, summary = result
        print(summary)


def cmd_manipulate(args):
    conn = init_db()
    name = " ".join(args) if args else "Marina"
    print(f"Classifying manipulations for: {name}")
    result = classify_manipulations(conn, name)
    if result:
        events, summary = result
        print(summary)


def cmd_emotion(args):
    conn = init_db()
    name = " ".join(args) if args else "Marina"
    print(f"Building emotion timeline for: {name}")
    result = build_emotion_timeline(conn, name)
    if result:
        _, summary = result
        print(summary)


def cmd_relations(args):
    conn = init_db()
    name = " ".join(args) if args else None
    map_relationships(conn, name)


def cmd_deception(args):
    conn = init_db()
    name = " ".join(args) if args else "Marina"
    use_llm = "--llm" in args
    if use_llm:
        args = [a for a in args if a != "--llm"]
        name = " ".join(args) if args else "Marina"
    print(f"Running deception analysis for: {name}")
    result = detect_deception(conn, name, use_llm=use_llm)
    if result:
        _, summary = result
        print(summary)


def cmd_negotiate(args):
    conn = init_db()
    chat = " ".join(args) if args else "Marina"
    use_llm = "--llm" in args
    if use_llm:
        args = [a for a in args if a != "--llm"]
        chat = " ".join(args) if args else "Marina"
    print(f"Analyzing negotiation in: {chat}")
    analyze_negotiation(conn, chat, use_llm=use_llm)


def cmd_predict(args):
    conn = init_db()
    if len(args) < 2:
        print("Usage: psych predict <name> <scenario description>")
        return
    name = args[0]
    scenario = " ".join(args[1:])
    use_llm = "--llm" in args
    predict_behavior(conn, name, scenario, use_llm=use_llm)


def cmd_compare(args):
    conn = init_db()
    if len(args) < 2:
        print("Usage: psych compare <name1> <name2>")
        return
    compare_styles(conn, args[0], args[1])


def cmd_briefing(args):
    """Full multi-role briefing for a person."""
    conn = init_db()
    name = " ".join(args) if args else "Marina"
    use_llm = "--llm" in args
    if use_llm:
        args = [a for a in args if a != "--llm"]
        name = " ".join(args) if args else "Marina"

    print(f"{'='*60}")
    print(f"  PSYCHOLOGICAL BRIEFING: {name.upper()}")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    print("─── 1. PROFILE ───")
    result = build_profile(conn, name, use_llm=use_llm)
    if result:
        _, summary = result
        print(summary)

    print("\n─── 2. MANIPULATION PATTERNS ───")
    result = classify_manipulations(conn, name)
    if result:
        _, summary = result
        print(summary)

    print("\n─── 3. EMOTIONAL TIMELINE ───")
    result = build_emotion_timeline(conn, name)
    if result:
        _, summary = result
        print(summary)

    print("\n─── 4. DECEPTION ANALYSIS ───")
    result = detect_deception(conn, name, use_llm=use_llm)
    if result:
        _, summary = result
        print(summary)

    print("\n─── 5. RELATIONSHIP MAP ───")
    map_relationships(conn, name)

    print(f"\n{'='*60}")
    print(f"  END OF BRIEFING")
    print(f"{'='*60}")


def cmd_search(args):
    conn = init_db()
    query = " ".join(args)
    rows = conn.execute("""
        SELECT a.id, a.analysis_type, a.created_at, a.summary, s.name
        FROM analyses a
        JOIN analyses_fts f ON a.id = f.rowid
        JOIN subjects s ON a.subject_id = s.id
        WHERE analyses_fts MATCH ?
        ORDER BY a.created_at DESC LIMIT 20
    """, (query,)).fetchall()
    for r in rows:
        print(f"  [{r['analysis_type']:10s}] {r['created_at'][:16]} — {r['name']}")
        print(f"    {r['summary'][:150]}")
        print()
    print(f"{len(rows)} results")


def cmd_people(args):
    conn = init_db()
    rows = conn.execute("""
        SELECT s.*, count(a.id) as analysis_count,
               (SELECT count(*) FROM manipulations WHERE subject_id = s.id) as manip_count,
               (SELECT count(*) FROM emotions WHERE subject_id = s.id) as emo_count
        FROM subjects s LEFT JOIN analyses a ON s.id = a.subject_id
        GROUP BY s.id ORDER BY analysis_count DESC
    """).fetchall()
    print(f"{'Name':<30s} {'Role':10s} {'Analyses':>8s} {'Manips':>8s} {'Emotions':>8s} {'Updated':12s}")
    print("─" * 80)
    for r in rows:
        print(f"  {r['name'][:28]:<28s} {r['role']:10s} {r['analysis_count']:>8d} "
              f"{r['manip_count']:>8d} {r['emo_count']:>8d} {(r['updated_at'] or '')[:10]:12s}")


def cmd_stats(args):
    conn = init_db()
    subjects = conn.execute("SELECT count(*) FROM subjects").fetchone()[0]
    analyses = conn.execute("SELECT count(*) FROM analyses").fetchone()[0]
    manips = conn.execute("SELECT count(*) FROM manipulations").fetchone()[0]
    emotions = conn.execute("SELECT count(*) FROM emotions").fetchone()[0]
    predictions = conn.execute("SELECT count(*) FROM predictions").fetchone()[0]
    sz = DB_PATH.stat().st_size / 1048576 if DB_PATH.exists() else 0

    print(f"\nPsychological Engine Stats")
    print(f"  Subjects:      {subjects:>8,d}")
    print(f"  Analyses:      {analyses:>8,d}")
    print(f"  Manipulations: {manips:>8,d}")
    print(f"  Emotions:      {emotions:>8,d}")
    print(f"  Predictions:   {predictions:>8,d}")
    print(f"  DB size:       {sz:>8.1f} MB")

    # Analysis type breakdown
    types = conn.execute("""
        SELECT analysis_type, count(*) as cnt FROM analyses GROUP BY analysis_type ORDER BY cnt DESC
    """).fetchall()
    if types:
        print(f"\n  Analysis breakdown:")
        for t in types:
            print(f"    {t['analysis_type']:15s}: {t['cnt']:>5d}")

    # Top manipulation techniques
    top_manip = conn.execute("""
        SELECT technique, count(*) as cnt FROM manipulations GROUP BY technique ORDER BY cnt DESC LIMIT 10
    """).fetchall()
    if top_manip:
        print(f"\n  Top manipulation techniques:")
        for m in top_manip:
            label = MANIPULATION_PATTERNS.get(m["technique"], {}).get("label", m["technique"])
            print(f"    {label:30s}: {m['cnt']:>5d}")


def cmd_timeline(args):
    conn = init_db()
    name = " ".join(args) if args else "Marina"
    sub = conn.execute("SELECT id FROM subjects WHERE name LIKE ?",
                       (f'%{name}%',)).fetchone()
    if not sub:
        print(f"No profile for '{name}'")
        return

    # Combine manipulations and emotions into one timeline
    events = []
    for m in conn.execute("""
        SELECT 'manip' as type, technique as detail, timestamp, severity as intensity, message_excerpt as excerpt
        FROM manipulations WHERE subject_id = ? ORDER BY timestamp
    """, (sub["id"],)).fetchall():
        events.append(dict(m))
    for e in conn.execute("""
        SELECT 'emotion' as type, emotion as detail, timestamp, intensity, message_excerpt as excerpt
        FROM emotions WHERE subject_id = ? ORDER BY timestamp
    """, (sub["id"],)).fetchall():
        events.append(dict(e))

    events.sort(key=lambda x: x.get("timestamp", ""))

    print(f"PSYCHOLOGICAL TIMELINE: {name}")
    print(f"Events: {len(events)}")
    print()

    prev_month = ""
    for evt in events[-100:]:  # Last 100 events
        month = evt["timestamp"][:7] if evt.get("timestamp") else "?"
        if month != prev_month:
            print(f"\n  ── {month} ──")
            prev_month = month

        icon = "⚡" if evt["type"] == "manip" else "💭"
        detail = evt["detail"]
        if evt["type"] == "manip":
            detail = MANIPULATION_PATTERNS.get(detail, {}).get("label", detail)
        intensity = evt.get("intensity", 0)
        bar = "█" * int(intensity * 10)

        print(f"  {icon} {evt['timestamp'][:16]}  {detail:25s} {bar:10s}  {(evt.get('excerpt') or '')[:60]}")


# ══════════════════════════════════════════════════════════════
# PSYOPS SUBMODULE — Influence Operations Analysis
# ══════════════════════════════════════════════════════════════

INFLUENCE_OPERATIONS = {
    "white_propaganda": {"description": "Truthful info from identified source", "legality": "legal", "ethics": "acceptable"},
    "gray_propaganda": {"description": "Info from unidentified source", "legality": "legal", "ethics": "questionable"},
    "black_propaganda": {"description": "Disinformation from false source", "legality": "varies", "ethics": "unacceptable"},
    "perception_management": {"description": "Shape target's interpretation of events", "legality": "legal", "ethics": "context-dependent"},
    "strategic_communication": {"description": "Coordinated messaging across channels", "legality": "legal", "ethics": "acceptable"},
    "information_denial": {"description": "Prevent target from accessing information", "legality": "varies", "ethics": "context-dependent"},
    "deception_operation": {"description": "Cause target to believe false reality", "legality": "varies", "ethics": "unacceptable"},
    "influence_through_proxy": {"description": "Use third parties to deliver message", "legality": "legal", "ethics": "questionable"},
    "narrative_warfare": {"description": "Competing narratives to control interpretation", "legality": "legal", "ethics": "acceptable"},
    "social_proof_engineering": {"description": "Manufacture consensus or support", "legality": "varies", "ethics": "questionable"},
}

PSYOPS_INDICATORS = {
    # Detect if someone is running influence ops on the subject
    "repetitive_framing": re.compile(r'(?i)(always|never|every\s*time|you\s*always|you\s*never)'),
    "false_consensus": re.compile(r'(?i)(everyone\s*(knows|says|thinks|agrees)|nobody\s*(believes|supports))'),
    "urgency_manufacturing": re.compile(r'(?i)(immediately|right\s*now|last\s*chance|urgent|deadline|running\s*out)'),
    "authority_invocation": re.compile(r'(?i)(the\s*(judge|court|law|police|doctor)\s*(said|says|ordered|confirmed))'),
    "isolation_tactics": re.compile(r'(?i)(no\s*one\s*(will|can|wants)|you.re\s*alone|only\s*I)'),
    "reality_distortion": re.compile(r'(?i)(that\s*never\s*happened|you.re\s*(imagining|crazy|confused)|I\s*never\s*said)'),
    "loyalty_testing": re.compile(r'(?i)(if\s*you\s*(really|truly)\s*(loved|cared)|prove\s*(it|your|that\s*you))'),
    "information_flooding": re.compile(r'(?i)(also|and\s*another\s*thing|plus|not\s*to\s*mention|on\s*top\s*of)'),
    "victim_reversal": re.compile(r'(?i)(you.re\s*the\s*one\s*who|look\s*what\s*you|you\s*made\s*me|this\s*is\s*your\s*fault)'),
    "future_faking": re.compile(r'(?i)(I\s*(will|promise|swear)|things\s*will\s*(change|be\s*different)|next\s*time)'),
}

def analyze_psyops(conn, subject_name: str, target_name: str = None):
    """Analyze potential influence operations between subjects."""
    # Get messages from subject
    wa_conn = sqlite3.connect(str(WA_DB))
    wa_conn.row_factory = sqlite3.Row

    messages = wa_conn.execute("""
        SELECT timestamp, sender, message FROM messages
        WHERE sender LIKE ? AND is_system=0 AND message != '' AND message != 'null'
        ORDER BY timestamp
    """, (f'%{subject_name}%',)).fetchall()

    if not messages:
        print(f"No messages found for {subject_name}")
        wa_conn.close()
        return None

    # Detect PSYOPS indicators
    indicators = {}
    examples = {}
    for indicator_name, pattern in PSYOPS_INDICATORS.items():
        count = 0
        exs = []
        for msg in messages:
            if msg['message'] and pattern.search(msg['message']):
                count += 1
                if len(exs) < 3:
                    exs.append(f"[{msg['timestamp'][:16]}] {msg['message'][:100]}")
        if count > 0:
            indicators[indicator_name] = count
            examples[indicator_name] = exs

    total_msgs = len(messages)

    # Calculate influence operation score
    psyops_score = sum(indicators.values()) / total_msgs if total_msgs > 0 else 0

    # Classify detected operations
    detected_ops = []
    if indicators.get('reality_distortion', 0) > 3 or indicators.get('victim_reversal', 0) > 3:
        detected_ops.append(('gaslighting_campaign', 'black_propaganda'))
    if indicators.get('isolation_tactics', 0) > 2:
        detected_ops.append(('isolation_operation', 'information_denial'))
    if indicators.get('false_consensus', 0) > 3:
        detected_ops.append(('consensus_manufacturing', 'social_proof_engineering'))
    if indicators.get('urgency_manufacturing', 0) > 5:
        detected_ops.append(('pressure_campaign', 'perception_management'))
    if indicators.get('repetitive_framing', 0) > 10:
        detected_ops.append(('narrative_control', 'narrative_warfare'))
    if indicators.get('loyalty_testing', 0) > 2:
        detected_ops.append(('compliance_testing', 'influence_through_proxy'))

    result = {
        'subject': subject_name,
        'total_messages': total_msgs,
        'psyops_score': round(psyops_score, 4),
        'indicators': indicators,
        'examples': examples,
        'detected_operations': detected_ops,
        'threat_level': 'HIGH' if psyops_score > 0.15 else 'MODERATE' if psyops_score > 0.08 else 'LOW',
    }

    # Store analysis
    subject = conn.execute("SELECT id FROM subjects WHERE name LIKE ?", (f'%{subject_name}%',)).fetchone()
    if subject:
        conn.execute("""
            INSERT INTO analyses (subject_id, analysis_type, scope, result_json, summary, confidence)
            VALUES (?, 'psyops', 'whatsapp', ?, ?, ?)
        """, (subject['id'], json.dumps(result, default=str),
              f"PSYOPS analysis: {result['threat_level']} threat, score {result['psyops_score']:.3f}, {len(detected_ops)} operations detected",
              min(0.5 + total_msgs/1000, 0.95)))
        conn.commit()

    wa_conn.close()
    return result

def show_psyops_report(result):
    """Display PSYOPS analysis report."""
    if not result:
        return
    print(f"\n  PSYOPS ANALYSIS: {result['subject']}")
    print(f"  {'='*60}")
    print(f"  Messages analyzed: {result['total_messages']}")
    print(f"  Influence score: {result['psyops_score']:.4f}")
    print(f"  Threat level: {result['threat_level']}")

    if result['indicators']:
        print(f"\n  Indicators detected:")
        for ind, count in sorted(result['indicators'].items(), key=lambda x: -x[1]):
            bar = '\u2588' * min(count, 30)
            print(f"    {ind:25s} {count:>4d}  {bar}")
            if ind in result['examples']:
                for ex in result['examples'][ind][:2]:
                    print(f"      -> {ex}")

    if result['detected_operations']:
        print(f"\n  Detected influence operations:")
        for op_name, op_type in result['detected_operations']:
            info = INFLUENCE_OPERATIONS.get(op_type, {})
            print(f"    * {op_name} ({op_type})")
            if info:
                print(f"      {info.get('description', '')}")
                print(f"      Legality: {info.get('legality', '?')} | Ethics: {info.get('ethics', '?')}")


def cmd_psyops(args):
    """CLI handler for psyops analysis."""
    if not args:
        print("Usage: psych psyops <name>")
        return
    name = " ".join(args)
    conn = init_db()
    result = analyze_psyops(conn, name)
    show_psyops_report(result)


# ── Main CLI ───────────────────────────────────────────────────────────────

def cmd_game(args):
    conn = init_db()
    if not args or args[0] == "list":
        print("Available game scenarios:")
        for k, v in GAME_SCENARIOS.items():
            print(f"  {k:25s}  {v['title']}")
        return
    scenario = args[0]
    use_llm = "--llm" in args
    run_game_analysis(conn, scenario, use_llm=use_llm)


def cmd_payoff(args):
    if not args:
        show_payoff_matrix("list")
    else:
        show_payoff_matrix(args[0])


# ══════════════════════════════════════════════════════════════════════════════
# COGNITIVE BIAS MITIGATION MODULE — Self-analysis for Hadrien
# ══════════════════════════════════════════════════════════════════════════════

# ── Seed data: detected biases from actual financial behavior ─────────────
SEED_BIASES = [
    {
        "bias_name": "Optimism Bias",
        "category": "financial",
        "detected_in": "Probability estimates of 70% escroquerie conviction, 55% annulment. "
                       "Historical base rates for Monaco criminal fraud convictions ~40-50%, "
                       "marriage annulments after 13 years ~25-35%.",
        "severity": "critical",
        "financial_impact": 675000.0,
        "mitigation": "Use reference class forecasting. Always show base rates alongside personal estimates.",
    },
    {
        "bias_name": "Present Bias / Hyperbolic Discounting",
        "category": "financial",
        "detected_in": "EUR 2.85M BTC purchase Dec 2025 while facing liquidity crisis. "
                       "EUR 208K G63. EUR 76K jets. EUR 20K casino. "
                       "All while Frick balance collapsed to EUR 139K.",
        "severity": "critical",
        "financial_impact": 3150000.0,
        "mitigation": "Mandatory 48-hour delay on any expenditure >EUR 5K. "
                      "Show opportunity cost in months of runway.",
    },
    {
        "bias_name": "Sunk Cost Fallacy",
        "category": "financial",
        "detected_in": "EUR 315K to KER-MEUR continuing monthly. EUR 108K 99 Avocats outstanding. "
                       "Continuing to pay because already invested.",
        "severity": "high",
        "financial_impact": 107000.0,
        "mitigation": "For each payment >EUR 10K, answer: "
                      "\"If I hadn't already paid X, would I start paying now?\"",
    },
    {
        "bias_name": "Illusion of Control",
        "category": "emotional",
        "detected_in": "Building surveillance systems, OSINT infrastructure, SCADA databases, "
                       "forensic chains. Creates feeling of control but doesn't move legal outcomes.",
        "severity": "high",
        "financial_impact": 0.0,
        "mitigation": "Ask \"What specific court outcome does this action influence?\"",
    },
    {
        "bias_name": "Anchoring",
        "category": "legal",
        "detected_in": "Anchored to EUR 32,500 pension as the problem. "
                       "Real threat is French fiscal investigation (potential EUR 2M+ and prison).",
        "severity": "medium",
        "financial_impact": 0.0,
        "mitigation": "Weekly priority ranking exercise. "
                      "\"What is the single highest-EV action this week?\"",
    },
    {
        "bias_name": "Complexity Bias",
        "category": "legal",
        "detected_in": "11 cases, 5 jurisdictions, 10+ law firms. "
                       "Complexity as proxy for thoroughness.",
        "severity": "high",
        "financial_impact": 47000.0,
        "mitigation": "Consolidation rule: maximum 3 active law firms at any time.",
    },
    {
        "bias_name": "Dunning-Kruger (Legal)",
        "category": "decision",
        "detected_in": "Self-directing legal strategy across multiple jurisdictions, "
                       "choosing which arguments to file, timing motions. "
                       "This is expert domain work.",
        "severity": "medium",
        "financial_impact": 0.0,
        "mitigation": "For each legal decision, explicitly defer to the specialist "
                      "lawyer's recommendation before overriding.",
    },
    {
        "bias_name": "Status Quo Bias",
        "category": "financial",
        "detected_in": "French addresses remain on 3 accounts despite months of awareness. "
                       "Roquebrune house not sold despite being a fiscal liability.",
        "severity": "medium",
        "financial_impact": 0.0,
        "mitigation": "For each \"I'll do it later\" item, calculate daily cost of inaction.",
    },
]

# ── Debiased probability estimates ────────────────────────────────────────
DEBIASED_ESTIMATES = [
    {"case": "Escroquerie conviction",  "your_estimate": 70, "base_rate": 45, "debiased": 55},
    {"case": "Annulment success",       "your_estimate": 55, "base_rate": 30, "debiased": 40},
    {"case": "Hague return",            "your_estimate": 65, "base_rate": 50, "debiased": 55},
    {"case": "Pension suspension",      "your_estimate": 80, "base_rate": 35, "debiased": 50},
    {"case": "French fiscal favorable", "your_estimate": 30, "base_rate": 20, "debiased": 25},
]

# ── Reframe reference values ─────────────────────────────────────────────
REFRAME_ANCHORS = [
    ("months of pension alimentaire",   32500.0),
    ("months of Malta rent",            6000.0),
    ("months of food budget",           2000.0),
    ("months of legal fees",            20000.0),
    ("days of Frick runway at current burn", 139000.0 / (30.0 * 437.0)),  # ~10.6 per day
    ("BTC at current price",            83000.0),
]

# ── Bias detection patterns for decision checking ─────────────────────────
BIAS_DETECTORS = {
    "Optimism Bias": [
        r"\b(definitely|certainly|sure|guaranteed|will work|no doubt|easy)\b",
        r"\b(best case|optimistic|hoping|should be fine)\b",
        r"\b(\d{2,3})\s*%",  # High percentage claims
    ],
    "Present Bias / Hyperbolic Discounting": [
        r"\b(right now|today|immediately|can't wait|urgent|asap)\b",
        r"\b(deal|opportunity|won't last|limited time|special offer)\b",
        r"\b(buy|purchase|spend|invest)\b.*\b(now|today|immediately)\b",
    ],
    "Sunk Cost Fallacy": [
        r"\b(already (paid|spent|invested)|can't stop now|too far|committed)\b",
        r"\b(wasted|thrown away|for nothing|all that money)\b",
    ],
    "Anchoring": [
        r"\b(compared to|relative to|at least|only|just)\b.*\b(EUR|\u20ac|eur)\b",
        r"\b(cheap|bargain|deal|good price|reasonable)\b",
    ],
    "Illusion of Control": [
        r"\b(i('ll| will) make|i('ll| will) force|i('ll| will) ensure)\b",
        r"\b(my plan|my strategy|i control|i decide)\b",
    ],
    "Status Quo Bias": [
        r"\b(later|eventually|soon|next (week|month)|when i have time)\b",
        r"\b(not now|wait|postpone|delay|defer)\b",
    ],
    "Complexity Bias": [
        r"\b(also|additionally|plus|another|more)\b.*\b(lawyer|firm|case|action)\b",
        r"\b(comprehensive|thorough|cover all|every angle)\b",
    ],
}


def seed_biases(conn):
    """Seed the cognitive_biases table if empty."""
    count = conn.execute("SELECT count(*) FROM cognitive_biases").fetchone()[0]
    if count > 0:
        return  # already seeded
    for b in SEED_BIASES:
        conn.execute("""
            INSERT INTO cognitive_biases
                (bias_name, category, detected_in, severity, financial_impact, mitigation)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (b["bias_name"], b["category"], b["detected_in"],
              b["severity"], b["financial_impact"], b["mitigation"]))
    conn.commit()


def show_biases(conn):
    """Display all detected cognitive biases."""
    seed_biases(conn)
    biases = conn.execute("""
        SELECT * FROM cognitive_biases ORDER BY
            CASE severity
                WHEN 'critical' THEN 0
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
            END,
            financial_impact DESC
    """).fetchall()

    severity_colors = {
        'critical': '\033[91m',  # red
        'high': '\033[93m',      # yellow
        'medium': '\033[96m',    # cyan
        'low': '\033[92m',       # green
    }
    reset = '\033[0m'

    total_impact = 0.0
    print(f"\n  COGNITIVE BIAS SELF-ANALYSIS — Hadrien Majoie")
    print(f"  {'='*70}")
    print()

    for b in biases:
        sev = b['severity']
        color = severity_colors.get(sev, '')
        status_mark = '\u2713' if b['status'] == 'mitigated' else '\u2717' if b['status'] == 'active' else '~'
        impact_str = f"EUR {b['financial_impact']:,.0f}" if b['financial_impact'] else "indirect"

        print(f"  {color}[{sev.upper():>8s}]{reset}  {status_mark} {b['bias_name']}")
        print(f"             Category: {b['category']}")
        print(f"             Impact:   {impact_str}")
        print(f"             Status:   {b['status']}")
        print()
        # Wrap detected_in text
        detected = b['detected_in']
        lines = []
        while len(detected) > 72:
            split_at = detected[:72].rfind(' ')
            if split_at == -1:
                split_at = 72
            lines.append(detected[:split_at])
            detected = detected[split_at:].lstrip()
        lines.append(detected)
        for line in lines:
            print(f"             {line}")
        print()
        print(f"             Mitigation: {b['mitigation']}")
        print()

        if b['financial_impact']:
            total_impact += b['financial_impact']

    print(f"  {'─'*70}")
    print(f"  Total quantified financial impact: EUR {total_impact:,.0f}")
    print(f"  Active biases: {sum(1 for b in biases if b['status'] == 'active')}")
    print(f"  Mitigated: {sum(1 for b in biases if b['status'] == 'mitigated')}")
    print()

    # Interventions count
    interventions = conn.execute("SELECT count(*) FROM bias_interventions").fetchone()[0]
    print(f"  Interventions logged: {interventions}")
    print()


def check_decision_biases(conn, decision_text):
    """Check a decision description against bias patterns and flag potential biases."""
    seed_biases(conn)
    text_lower = decision_text.lower()
    flagged = []

    for bias_name, patterns in BIAS_DETECTORS.items():
        matches = []
        for pattern in patterns:
            found = re.findall(pattern, text_lower, re.IGNORECASE)
            if found:
                matches.extend(found)
        if matches:
            # Get the bias record for context
            row = conn.execute(
                "SELECT * FROM cognitive_biases WHERE bias_name = ?", (bias_name,)
            ).fetchone()
            flagged.append((bias_name, matches, row))

    print(f"\n  BIAS CHECK: \"{decision_text[:80]}{'...' if len(decision_text) > 80 else ''}\"")
    print(f"  {'='*70}")

    if not flagged:
        print(f"\n  No obvious bias patterns detected.")
        print(f"  (This does NOT mean the decision is bias-free. Consider a premortem.)")
    else:
        print(f"\n  {len(flagged)} potential bias(es) detected:\n")
        for bias_name, matches, row in flagged:
            sev = row['severity'] if row else 'unknown'
            print(f"  \u26a0  {bias_name} [{sev.upper()}]")
            print(f"     Trigger words: {', '.join(str(m) for m in matches[:5])}")
            if row:
                print(f"     Mitigation: {row['mitigation']}")
            print()

            # Log the intervention
            bias_id = row['id'] if row else None
            if bias_id:
                conn.execute("""
                    INSERT INTO bias_interventions (bias_id, intervention_type, message, triggered_by)
                    VALUES (?, 'bias_check', ?, ?)
                """, (bias_id, f"Bias check flagged {bias_name}", decision_text[:200]))
        conn.commit()

    # Always show the generic debiasing questions
    print(f"  {'─'*70}")
    print(f"  Debiasing checklist for this decision:")
    print(f"    1. What would I advise a friend in this exact situation?")
    print(f"    2. What is the base rate for this type of outcome?")
    print(f"    3. If this fails, what was the most likely cause? (premortem)")
    print(f"    4. What is the opportunity cost in months of runway?")
    print(f"    5. Am I deciding now because it's optimal, or because it feels urgent?")
    print()


def mitigate_bias(conn, bias_id_str):
    """Mark a bias as mitigated."""
    seed_biases(conn)
    try:
        bias_id = int(bias_id_str)
    except ValueError:
        print(f"Invalid bias ID: {bias_id_str}")
        return
    row = conn.execute("SELECT * FROM cognitive_biases WHERE id = ?", (bias_id,)).fetchone()
    if not row:
        print(f"No bias found with ID {bias_id}")
        return
    conn.execute("""
        UPDATE cognitive_biases SET status = 'mitigated', mitigated_at = datetime('now')
        WHERE id = ?
    """, (bias_id,))
    conn.execute("""
        INSERT INTO bias_interventions (bias_id, intervention_type, message, triggered_by)
        VALUES (?, 'mitigate', ?, 'manual')
    """, (bias_id, f"Bias '{row['bias_name']}' marked as mitigated"))
    conn.commit()
    print(f"\n  Bias #{bias_id} '{row['bias_name']}' marked as MITIGATED.")
    print(f"  (It remains in the record for calibration tracking.)")
    print()


def show_debiased(conn):
    """Show debiased probability estimates using reference class forecasting."""
    seed_biases(conn)
    print(f"\n  DEBIASED PROBABILITY ESTIMATES (reference class forecasting)")
    print(f"  {'─'*65}")
    print(f"  {'Case':<25s} {'Your estimate':>13s} {'Base rate':>10s} {'Debiased':>10s}")
    print(f"  {'─'*65}")

    for e in DEBIASED_ESTIMATES:
        your = f"{e['your_estimate']}%"
        base = f"{e['base_rate']}%"
        debiased = f"{e['debiased']}%"
        print(f"  {e['case']:<25s} {your:>13s} {base:>10s} {debiased:>10s}")

    print(f"  {'─'*65}")
    print()

    # Calculate expected pension under both models
    # Your estimate: weighted by optimistic conviction/suspension probs
    your_suspension_prob = 0.80
    debiased_suspension_prob = 0.50
    pension = 32500.0

    your_expected = pension * (1 - your_suspension_prob) + 0 * your_suspension_prob
    debiased_expected = pension * (1 - debiased_suspension_prob) + 0 * debiased_suspension_prob

    # But the user's estimate is that pension gets suspended (favorable),
    # so flip: your expectation is to pay less
    # Actually: your estimate = 80% pension suspended = you pay EUR 32500 * 0.2 = 6500
    # debiased = 50% = you pay EUR 32500 * 0.5 = 16250
    your_monthly = pension * (1 - your_suspension_prob)
    debiased_monthly = pension * (1 - debiased_suspension_prob)

    print(f"  Expected pension outflow (debiased): EUR {debiased_monthly:,.0f}/mo")
    print(f"  vs your estimate:                    EUR {your_monthly:,.0f}/mo")
    print(f"  Monthly delta:                       EUR {debiased_monthly - your_monthly:,.0f}/mo")
    print(f"  Annual delta:                        EUR {(debiased_monthly - your_monthly) * 12:,.0f}/yr")
    print()

    # Log intervention
    conn.execute("""
        INSERT INTO bias_interventions (bias_id, intervention_type, message, triggered_by)
        VALUES ((SELECT id FROM cognitive_biases WHERE bias_name = 'Optimism Bias'),
                'reference_class', 'Showed debiased probability estimates', 'psych debias')
    """)
    conn.commit()

    print(f"  NOTE: Debiased estimates use reference class forecasting.")
    print(f"  Your personal case specifics may justify deviation, but the burden")
    print(f"  of proof is on the deviation, not the base rate.")
    print()


def run_premortem(conn, scenario):
    """Run a premortem analysis: 'It's 2027 and this failed. Why?'"""
    seed_biases(conn)
    print(f"\n  PREMORTEM ANALYSIS")
    print(f"  {'='*70}")
    print(f"  Scenario: {scenario}")
    print(f"  {'─'*70}")
    print(f"  Frame: It is March 2027. This plan FAILED. Why?\n")

    # Generic premortem failure modes relevant to Hadrien's situation
    failure_modes = [
        ("Financial exhaustion",
         "Frick account depleted before legal resolution. Unable to fund lawyers. "
         "Cases stall or are dropped."),
        ("French fiscal hammer",
         "DGFIP issues EUR 2M+ assessment. Assets frozen across jurisdictions. "
         "Criminal referral initiated."),
        ("Legal complexity collapse",
         "Too many parallel cases. Contradictory filings across jurisdictions. "
         "One lawyer's action undermines another's."),
        ("Optimistic timeline",
         "Monaco courts delayed 12+ months beyond expected. Appeals extend every case. "
         "Pension continues the entire time."),
        ("Key assumption wrong",
         "The conviction/annulment you are counting on does not materialize. "
         "Base rates were right, not your estimate."),
        ("Adversary adaptation",
         "Marina/Giaccardi adapt strategy in response to your filings. "
         "Your telegraphed moves are countered."),
        ("Health/burnout",
         "Stress from managing 11 cases across 5 jurisdictions causes health crisis. "
         "Decision quality degrades. Key deadlines missed."),
        ("Black swan",
         "Crypto market crash, BTC drops 60%. Or: new evidence surfaces that "
         "reframes the entire case."),
    ]

    for i, (mode, desc) in enumerate(failure_modes, 1):
        print(f"  {i}. {mode}")
        # Wrap description
        remaining = desc
        first = True
        while remaining:
            chunk = remaining[:68]
            if len(remaining) > 68:
                split = chunk.rfind(' ')
                if split > 0:
                    chunk = remaining[:split]
                    remaining = remaining[split:].lstrip()
                else:
                    remaining = remaining[68:]
            else:
                remaining = ''
            prefix = '     ' if first else '     '
            print(f"     {chunk}")
            first = False
        print()

    print(f"  {'─'*70}")
    print(f"  ACTIONS to prevent the most likely failure mode:")
    print(f"    1. Calculate exact runway (months) at current burn rate")
    print(f"    2. Identify the single action with highest expected value this week")
    print(f"    3. For each active case, answer: does this move the needle on #1 or #2?")
    print(f"    4. Cancel or pause anything that doesn't")
    print()

    # Also run bias check on the scenario text
    text_lower = scenario.lower()
    triggered = []
    for bias_name, patterns in BIAS_DETECTORS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                triggered.append(bias_name)
                break
    if triggered:
        print(f"  Biases possibly active in this scenario:")
        for b in triggered:
            print(f"    \u26a0  {b}")
        print()

    # Log intervention
    conn.execute("""
        INSERT INTO bias_interventions (bias_id, intervention_type, message, triggered_by)
        VALUES (NULL, 'premortem', ?, ?)
    """, (f"Premortem analysis for: {scenario[:200]}", scenario[:200]))
    conn.commit()


def reframe_amount(conn, amount_str):
    """Reframe a financial amount in terms of meaningful reference points."""
    seed_biases(conn)
    try:
        amount = float(amount_str.replace(',', '').replace('EUR', '').replace('\u20ac', '').strip())
    except ValueError:
        print(f"Cannot parse amount: {amount_str}")
        return

    print(f"\n  EUR {amount:,.0f} =")

    anchors = [
        ("months of pension alimentaire",       32500.0),
        ("months of Malta rent",                6000.0),
        ("months of food budget",               2000.0),
        ("months of legal fees",                20000.0),
        ("days of Frick runway at current burn", 139000.0 / 30.0),  # ~4633/day approx
        ("BTC at current price",                83000.0),
    ]

    for label, ref_value in anchors:
        ratio = amount / ref_value
        print(f"    {ratio:>8.1f} {label}")

    print()

    # If amount > 5K, show the 48-hour rule reminder
    if amount >= 5000:
        print(f"  \u26a0  48-HOUR RULE: This exceeds EUR 5,000.")
        print(f"     Before committing, wait 48 hours and re-evaluate.")
        print(f"     Opportunity cost: {amount / (139000.0 / 30.0):.1f} days of Frick runway.")
        print()

    # Log intervention
    conn.execute("""
        INSERT INTO bias_interventions (bias_id, intervention_type, message, triggered_by)
        VALUES ((SELECT id FROM cognitive_biases WHERE bias_name LIKE '%Present Bias%'),
                'reframe', ?, ?)
    """, (f"Reframed EUR {amount:,.0f}", f"psych reframe {amount_str}"))
    conn.commit()


# ── CLI handlers for cognitive bias module ────────────────────────────────

def cmd_bias(args):
    """CLI handler for bias subcommands."""
    conn = init_db()
    if not args:
        show_biases(conn)
        return
    sub = args[0]
    if sub == "check":
        if len(args) < 2:
            print("Usage: psych bias check <decision description>")
            return
        decision = " ".join(args[1:])
        check_decision_biases(conn, decision)
    elif sub == "mitigate":
        if len(args) < 2:
            print("Usage: psych bias mitigate <bias_id>")
            return
        mitigate_bias(conn, args[1])
    else:
        # Treat the whole thing as a check
        decision = " ".join(args)
        check_decision_biases(conn, decision)


def cmd_debias(args):
    """CLI handler for debiased estimates."""
    conn = init_db()
    show_debiased(conn)


def cmd_premortem(args):
    """CLI handler for premortem analysis."""
    conn = init_db()
    if not args:
        scenario = "Current legal strategy across all active cases"
    else:
        scenario = " ".join(args)
    run_premortem(conn, scenario)


def cmd_reframe(args):
    """CLI handler for financial reframing."""
    conn = init_db()
    if not args:
        print("Usage: psych reframe <amount>")
        print("  Example: psych reframe 20000")
        return
    reframe_amount(conn, " ".join(args))


COMMANDS = {
    "profile": cmd_profile,
    "manipulate": cmd_manipulate,
    "emotion": cmd_emotion,
    "relations": cmd_relations,
    "deception": cmd_deception,
    "negotiate": cmd_negotiate,
    "predict": cmd_predict,
    "compare": cmd_compare,
    "game": cmd_game,
    "payoff": cmd_payoff,
    "briefing": cmd_briefing,
    "search": cmd_search,
    "people": cmd_people,
    "stats": cmd_stats,
    "timeline": cmd_timeline,
    "psyops": cmd_psyops,
    "bias": cmd_bias,
    "debias": cmd_debias,
    "premortem": cmd_premortem,
    "reframe": cmd_reframe,
}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd in COMMANDS:
        COMMANDS[cmd](args)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
