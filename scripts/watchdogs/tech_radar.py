#!/usr/bin/env python3
"""PlanO Technology Radar — Watchdog swarm system.

Monitors 16 technology domains relevant to PlanO's future,
scoring readiness levels, projecting timelines, and feeding
predictions to the business simulator and agents.

Usage:
    tech_radar.py scan              Run all watchdogs, update readiness
    tech_radar.py radar             Print full technology radar
    tech_radar.py predict --tech X  Detailed prediction for one tech
    tech_radar.py signals           Show recent signals
    tech_radar.py opportunities     What to build now vs plan for
    tech_radar.py train-export      SFT pairs for agents
    tech_radar.py timeline          Visual timeline of mainstream dates
"""

import argparse
import json
import os
import sqlite3
import sys
import textwrap
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_DIR = PROJECT_ROOT / "data" / "watchdogs"
DB_PATH = DB_DIR / "tech_radar.db"
EXPORT_DIR = DB_DIR / "exports"

NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")
CURRENT_YEAR = 2026


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class TechSignal:
    """A single market / research / funding signal."""
    tech_id: str
    signal_type: str          # funding, patent, product_launch, standard_adopted, research_paper
    title: str
    url: str = ""
    significance: float = 0.5
    timestamp: str = field(default_factory=lambda: NOW)


@dataclass
class TechEntry:
    """One technology on the radar."""
    id: str
    domain: str
    name: str
    description: str
    current_readiness: float          # 0-1 (NASA TRL normalised)
    predicted_mainstream_year: int
    confidence: float                 # 0-1
    impact_on_plano: str              # low / medium / high / critical
    action_required: str
    yearly_probabilities: dict = field(default_factory=dict)   # year -> probability
    signals: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Database layer
# ---------------------------------------------------------------------------
def _connect() -> sqlite3.Connection:
    """Open (and optionally initialise) the SQLite database."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS technologies (
            id TEXT PRIMARY KEY,
            domain TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            current_readiness REAL,
            predicted_mainstream_year INTEGER,
            confidence REAL,
            impact_on_plano TEXT,
            action_required TEXT,
            last_updated TEXT
        );
        CREATE TABLE IF NOT EXISTS readiness_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tech_id TEXT REFERENCES technologies(id),
            readiness REAL,
            data_source TEXT,
            timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tech_id TEXT,
            year INTEGER,
            probability REAL,
            reasoning TEXT,
            timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tech_id TEXT,
            signal_type TEXT,
            title TEXT,
            url TEXT,
            significance REAL,
            timestamp TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_rh_tech ON readiness_history(tech_id);
        CREATE INDEX IF NOT EXISTS idx_pred_tech ON predictions(tech_id);
        CREATE INDEX IF NOT EXISTS idx_sig_tech ON signals(tech_id);
    """)


def _upsert_technology(conn: sqlite3.Connection, tech: TechEntry) -> None:
    """Insert or update a technology row."""
    conn.execute("""
        INSERT INTO technologies (id, domain, name, description,
            current_readiness, predicted_mainstream_year, confidence,
            impact_on_plano, action_required, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            current_readiness=excluded.current_readiness,
            predicted_mainstream_year=excluded.predicted_mainstream_year,
            confidence=excluded.confidence,
            impact_on_plano=excluded.impact_on_plano,
            action_required=excluded.action_required,
            last_updated=excluded.last_updated
    """, (
        tech.id, tech.domain, tech.name, tech.description,
        tech.current_readiness, tech.predicted_mainstream_year,
        tech.confidence, tech.impact_on_plano, tech.action_required, NOW,
    ))


def _record_readiness(conn: sqlite3.Connection, tech: TechEntry, source: str) -> None:
    """Append a readiness-history row."""
    conn.execute(
        "INSERT INTO readiness_history (tech_id, readiness, data_source, timestamp) VALUES (?,?,?,?)",
        (tech.id, tech.current_readiness, source, NOW),
    )


def _record_predictions(conn: sqlite3.Connection, tech: TechEntry) -> None:
    """Write yearly probability predictions."""
    for year, prob in tech.yearly_probabilities.items():
        conn.execute(
            "INSERT INTO predictions (tech_id, year, probability, reasoning, timestamp) VALUES (?,?,?,?,?)",
            (tech.id, int(year), prob,
             f"Auto-computed from TRL={tech.current_readiness:.2f}, "
             f"confidence={tech.confidence:.2f}", NOW),
        )


def _record_signals(conn: sqlite3.Connection, tech: TechEntry) -> None:
    """Write signals for this scan."""
    for sig in tech.signals:
        conn.execute(
            "INSERT INTO signals (tech_id, signal_type, title, url, significance, timestamp) VALUES (?,?,?,?,?,?)",
            (sig.tech_id, sig.signal_type, sig.title, sig.url, sig.significance, sig.timestamp),
        )


# ---------------------------------------------------------------------------
# Prediction engine
# ---------------------------------------------------------------------------
def _compute_yearly_probabilities(
    trl: float,
    mainstream_year: int,
    confidence: float,
) -> dict[int, float]:
    """Compute probability of mainstream adoption for each year 2026-2031.

    Uses a logistic growth curve anchored at the predicted mainstream year,
    stretched by confidence level and current TRL.
    """
    probs = {}
    for year in range(CURRENT_YEAR, CURRENT_YEAR + 6):
        if year >= mainstream_year:
            # past predicted date: high probability, adjusted by confidence
            base = 0.85 + 0.15 * confidence
            years_past = year - mainstream_year
            prob = min(1.0, base + years_past * 0.05)
        else:
            # before predicted date: logistic ramp-up
            years_left = mainstream_year - year
            total_span = max(1, mainstream_year - CURRENT_YEAR)
            progress = 1.0 - (years_left / total_span)
            # trl gives a head start
            prob = trl * 0.4 + progress * 0.5 * confidence + 0.05
            prob = min(0.85, max(0.05, prob))
        probs[year] = round(prob, 3)
    return probs


def _trl_label(trl: float) -> str:
    """Human-readable TRL label."""
    if trl < 0.2:
        return "Research"
    if trl < 0.4:
        return "Demo"
    if trl < 0.6:
        return "Early Adopter"
    if trl < 0.8:
        return "Growing"
    return "Mainstream"


def _impact_color(impact: str) -> str:
    """ANSI color for impact level."""
    colors = {
        "critical": "\033[91m",  # red
        "high": "\033[93m",      # yellow
        "medium": "\033[96m",    # cyan
        "low": "\033[90m",       # grey
    }
    return colors.get(impact, "")

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


# ---------------------------------------------------------------------------
# Watchdog definitions — 16 technology domains
# ---------------------------------------------------------------------------
def _build_all_technologies() -> list[TechEntry]:
    """Define and score all 16 monitored technologies.

    Each watchdog function returns a TechEntry with realistic
    readiness scores and predictions as of early 2026.
    """
    techs = []

    # 1. WebGPU / WebGL adoption
    techs.append(TechEntry(
        id="webgpu",
        domain="Web Platform",
        name="WebGPU / WebGL Adoption",
        description=(
            "GPU-accelerated rendering in browsers via WebGPU API. "
            "Chrome shipped WebGPU in 2023, Firefox Nightly has it, Safari partial. "
            "Full cross-browser support enables real-time 3D floor plan rendering."
        ),
        current_readiness=0.55,
        predicted_mainstream_year=2027,
        confidence=0.80,
        impact_on_plano="critical",
        action_required=(
            "Build WebGPU renderer with WebGL fallback. Start now — Chrome+Edge "
            "already cover 70% of users. Prepare progressive enhancement path."
        ),
        signals=[
            TechSignal("webgpu", "standard_adopted", "WebGPU W3C Candidate Recommendation", "https://www.w3.org/TR/webgpu/", 0.9),
            TechSignal("webgpu", "product_launch", "Chrome 113+ ships WebGPU by default", "https://chromestatus.com", 0.85),
            TechSignal("webgpu", "product_launch", "Firefox WebGPU enabled in Nightly 2025", "https://bugzilla.mozilla.org", 0.6),
        ],
        dependencies=["browser_ai"],
    ))

    # 2. Browser-based AI inference
    techs.append(TechEntry(
        id="browser_ai",
        domain="AI/ML",
        name="Browser-based AI Inference",
        description=(
            "Running ML models directly in the browser via ONNX Runtime Web, "
            "TensorFlow.js, and the emerging WebNN API. Goal: run Rasta floor plan "
            "detection without server GPU. Currently limited to small models (<100M params)."
        ),
        current_readiness=0.35,
        predicted_mainstream_year=2029,
        confidence=0.55,
        impact_on_plano="critical",
        action_required=(
            "Export Rasta to ONNX, test TF.js inference for lightweight detection. "
            "Full browser inference for complex models is 3+ years out. Maintain "
            "server-side pipeline as primary, browser as progressive enhancement."
        ),
        signals=[
            TechSignal("browser_ai", "standard_adopted", "WebNN API in Chrome Origin Trial", "https://chromestatus.com", 0.7),
            TechSignal("browser_ai", "research_paper", "ONNX Runtime Web 1.17 — 2x perf on WebGPU backend", "", 0.6),
            TechSignal("browser_ai", "product_launch", "MediaPipe supports WebGPU acceleration 2025", "", 0.65),
        ],
        dependencies=["webgpu", "edge_ai_chips"],
    ))

    # 3. LiDAR on phones
    techs.append(TechEntry(
        id="phone_lidar",
        domain="Hardware",
        name="LiDAR on Phones",
        description=(
            "Depth-sensing LiDAR on consumer phones. iPhone Pro (2020+) and iPad Pro "
            "have it. Samsung flagship ToF sensors. Question: when will mid-range "
            "phones (~$300) include LiDAR for instant 3D room scanning?"
        ),
        current_readiness=0.45,
        predicted_mainstream_year=2029,
        confidence=0.50,
        impact_on_plano="high",
        action_required=(
            "Build LiDAR scan pipeline for iPhone Pro NOW (20% of users). "
            "Use photogrammetry fallback for non-LiDAR phones. Plan for "
            "universal LiDAR by 2029 — affects 3D room scanning feature."
        ),
        signals=[
            TechSignal("phone_lidar", "product_launch", "iPhone 16 Pro retains LiDAR, improved range", "", 0.5),
            TechSignal("phone_lidar", "research_paper", "Qualcomm dToF sensor roadmap for mid-range 2027", "", 0.7),
            TechSignal("phone_lidar", "patent", "Samsung LiDAR miniaturization patent 2025", "", 0.4),
        ],
    ))

    # 4. AR/VR headset adoption
    techs.append(TechEntry(
        id="ar_vr_headsets",
        domain="Hardware",
        name="AR/VR Headset Adoption",
        description=(
            "Consumer AR/VR headsets: Apple Vision Pro ($3499), Meta Quest 3 ($499), "
            "Meta Quest 3S ($299). Current install base ~30M (mostly Meta Quest). "
            "Target: 10% of renovation contractors own one for AR visualization."
        ),
        current_readiness=0.30,
        predicted_mainstream_year=2030,
        confidence=0.40,
        impact_on_plano="medium",
        action_required=(
            "Build WebXR viewer for Quest 3 (cheapest path). Do NOT invest "
            "in Vision Pro native app yet — too expensive, too niche. "
            "AR overlay on phone camera is better ROI for 2026-2028."
        ),
        signals=[
            TechSignal("ar_vr_headsets", "product_launch", "Meta Quest 3S at $299 — lowest price point", "", 0.7),
            TechSignal("ar_vr_headsets", "funding", "Apple Vision Pro 2 rumored at lower price point 2026", "", 0.5),
            TechSignal("ar_vr_headsets", "product_launch", "Samsung XR headset with Qualcomm XR2 Gen 3", "", 0.4),
        ],
        dependencies=["webgpu"],
    ))

    # 5. AI code generation
    techs.append(TechEntry(
        id="ai_codegen",
        domain="AI/ML",
        name="AI Code Generation",
        description=(
            "AI-assisted and autonomous code generation. GitHub Copilot, Cursor, "
            "Claude Code, Devin. Current state: AI writes 30-50% of boilerplate, "
            "still needs human architecture decisions and debugging."
        ),
        current_readiness=0.60,
        predicted_mainstream_year=2027,
        confidence=0.75,
        impact_on_plano="high",
        action_required=(
            "Already using Claude Code. Invest in good specs, test suites, "
            "and CI/CD — AI writes code faster when guardrails are strong. "
            "Plan for 80% AI-written code by 2028. Focus humans on architecture."
        ),
        signals=[
            TechSignal("ai_codegen", "product_launch", "Claude Code, Cursor, Windsurf shipping agent-mode", "", 0.85),
            TechSignal("ai_codegen", "funding", "Cognition (Devin) raised $175M Series A", "", 0.6),
            TechSignal("ai_codegen", "research_paper", "SWE-bench scores crossing 50% for top models", "", 0.7),
        ],
    ))

    # 6. Autonomous AI agents
    techs.append(TechEntry(
        id="autonomous_agents",
        domain="AI/ML",
        name="Autonomous AI Agents",
        description=(
            "AI agents that handle full workflows: customer support, marketing, "
            "sales, scheduling. OpenAI Operator, Anthropic tool-use agents, "
            "AutoGPT descendants. Currently good for narrow tasks, fragile on open-ended ones."
        ),
        current_readiness=0.40,
        predicted_mainstream_year=2028,
        confidence=0.60,
        impact_on_plano="critical",
        action_required=(
            "Build agent framework NOW for PlanO support bot. Start with "
            "constrained flows (quote requests, scheduling). Plan for full "
            "autonomous sales agent by 2028. Keep human-in-loop for edge cases."
        ),
        signals=[
            TechSignal("autonomous_agents", "product_launch", "OpenAI Operator launched for web tasks", "", 0.7),
            TechSignal("autonomous_agents", "product_launch", "Anthropic Claude tool-use and computer-use", "", 0.8),
            TechSignal("autonomous_agents", "research_paper", "Agent benchmarks (GAIA, WebArena) improving rapidly", "", 0.65),
        ],
    ))

    # 7. BIM mandate adoption
    techs.append(TechEntry(
        id="bim_mandate",
        domain="Regulation",
        name="BIM Mandate Adoption (EU Residential)",
        description=(
            "EU BIM mandates for public buildings exist (UK, Germany, France, Nordics). "
            "Residential BIM mandates are rare. Malta has no BIM mandate yet. "
            "EPBD recast may push residential BIM requirements by 2028-2030."
        ),
        current_readiness=0.25,
        predicted_mainstream_year=2030,
        confidence=0.45,
        impact_on_plano="high",
        action_required=(
            "Build IFC export from PlanO floor plans — positions us ahead of mandate. "
            "Monitor Malta Building Regulation Office announcements. First-mover "
            "advantage if we're BIM-ready when mandate drops."
        ),
        signals=[
            TechSignal("bim_mandate", "standard_adopted", "EPBD recast 2024 — digital building logbooks required", "", 0.8),
            TechSignal("bim_mandate", "standard_adopted", "Germany BIM mandate for public buildings >5M EUR", "", 0.6),
            TechSignal("bim_mandate", "research_paper", "EU BIM Task Group recommends residential extension", "", 0.5),
        ],
    ))

    # 8. 3D printing in construction
    techs.append(TechEntry(
        id="construction_3dprint",
        domain="Construction Tech",
        name="3D Printing in Construction",
        description=(
            "Companies like ICON, Apis Cor, COBOD printing houses. ~200 3D-printed "
            "buildings worldwide as of 2025. Still mostly walls/structure, not full "
            "buildings. Each needs a digital floor plan as input — new market segment."
        ),
        current_readiness=0.20,
        predicted_mainstream_year=2031,
        confidence=0.35,
        impact_on_plano="medium",
        action_required=(
            "Low priority now. Monitor ICON and COBOD progress. When 3D-printed "
            "buildings reach 1000+/year, offer PlanO-to-Gcode export pipeline. "
            "Partnership opportunity with print companies who need floor plan input."
        ),
        signals=[
            TechSignal("construction_3dprint", "funding", "ICON raised $451M, building in Texas", "", 0.7),
            TechSignal("construction_3dprint", "product_launch", "COBOD BOD2 printer — 3 stories capability", "", 0.5),
            TechSignal("construction_3dprint", "patent", "Multi-material print head patents increasing", "", 0.4),
        ],
    ))

    # 9. EU Renovation Wave funding
    techs.append(TechEntry(
        id="eu_renovation_wave",
        domain="Regulation",
        name="EU Renovation Wave / EPBD Enforcement",
        description=(
            "EU Energy Performance of Buildings Directive (EPBD) recast 2024: "
            "worst-performing buildings must be renovated by 2030 (non-residential) "
            "and 2033 (residential). Massive demand trigger for renovation planning tools."
        ),
        current_readiness=0.50,
        predicted_mainstream_year=2028,
        confidence=0.75,
        impact_on_plano="critical",
        action_required=(
            "THIS IS THE BIGGEST DEMAND DRIVER. Build energy audit integration "
            "into PlanO. Target F/G-rated buildings in Malta and Bulgaria first. "
            "Partner with EPC assessors. Deadline-driven demand starts 2027."
        ),
        signals=[
            TechSignal("eu_renovation_wave", "standard_adopted", "EPBD recast published in Official Journal 2024", "", 0.95),
            TechSignal("eu_renovation_wave", "funding", "EU allocates 150B EUR for renovation wave", "", 0.9),
            TechSignal("eu_renovation_wave", "standard_adopted", "Malta MEPS transposition deadline 2026", "", 0.7),
        ],
    ))

    # 10. Payment tech / embedded finance
    techs.append(TechEntry(
        id="payment_tech",
        domain="FinTech",
        name="Embedded Finance / BNPL for Renovation",
        description=(
            "Stripe embedded finance, BNPL (Klarna, Affirm) for high-ticket items. "
            "Renovation financing through the platform: homeowner gets quote in PlanO, "
            "finances it in-app. Stripe Connect for contractor payouts."
        ),
        current_readiness=0.55,
        predicted_mainstream_year=2027,
        confidence=0.70,
        impact_on_plano="high",
        action_required=(
            "Integrate Stripe Connect for contractor payments in 2026. "
            "Add BNPL partner (Klarna/Alma) for renovation financing by 2027. "
            "This is a revenue multiplier — PlanO takes cut of financing."
        ),
        signals=[
            TechSignal("payment_tech", "product_launch", "Stripe embedded lending API in beta", "", 0.7),
            TechSignal("payment_tech", "product_launch", "Alma (EU BNPL) supports renovation verticals", "", 0.6),
            TechSignal("payment_tech", "funding", "Embedded finance market projected $7T by 2030", "", 0.5),
        ],
    ))

    # 11. Edge AI chips
    techs.append(TechEntry(
        id="edge_ai_chips",
        domain="Hardware",
        name="Edge AI Chips (Phone NPUs)",
        description=(
            "Dedicated neural processing units in phones: Apple Neural Engine (16-core), "
            "Qualcomm Hexagon, Samsung Exynos NPU, Google Tensor. Question: when can "
            "a $300 phone run CubiCasa5k-level floor plan detection locally?"
        ),
        current_readiness=0.50,
        predicted_mainstream_year=2028,
        confidence=0.65,
        impact_on_plano="high",
        action_required=(
            "Optimize Rasta model for INT8 quantization targeting phone NPUs. "
            "Test CoreML export for iPhone, NNAPI for Android. Local inference "
            "eliminates server costs and latency — critical for scaling."
        ),
        signals=[
            TechSignal("edge_ai_chips", "product_launch", "Apple A18 Neural Engine — 35 TOPS", "", 0.7),
            TechSignal("edge_ai_chips", "product_launch", "Qualcomm Snapdragon 8 Gen 4 — 45 TOPS NPU", "", 0.75),
            TechSignal("edge_ai_chips", "product_launch", "MediaTek Dimensity 9400 — NPU in mid-range 2026", "", 0.65),
        ],
        dependencies=["browser_ai"],
    ))

    # 12. Computer vision accuracy (floor plan recognition)
    techs.append(TechEntry(
        id="cv_accuracy",
        domain="AI/ML",
        name="Floor Plan Recognition Accuracy",
        description=(
            "SOTA on floor plan recognition benchmarks: CubiCasa5k mIoU ~72% (2019), "
            "recent transformer models hitting 82-85%. Target: 99% accuracy on clean "
            "architectural drawings. Currently 90%+ only on ideal inputs."
        ),
        current_readiness=0.55,
        predicted_mainstream_year=2028,
        confidence=0.65,
        impact_on_plano="critical",
        action_required=(
            "This IS our core tech. Keep training Rasta on expanded datasets. "
            "Synthetic data generation to cover edge cases. Monitor arXiv weekly "
            "for new architectures. Target 95% by end 2026, 99% by 2028."
        ),
        signals=[
            TechSignal("cv_accuracy", "research_paper", "SAM-2 + GroundingDINO for zero-shot floor plan parsing", "", 0.7),
            TechSignal("cv_accuracy", "research_paper", "DINOv2 features improve plan recognition 5%", "", 0.6),
            TechSignal("cv_accuracy", "product_launch", "CubiCasa commercial API claims 95% accuracy", "", 0.65),
        ],
    ))

    # 13. Voice / multimodal AI
    techs.append(TechEntry(
        id="voice_multimodal",
        domain="AI/ML",
        name="Voice + Multimodal AI for Floor Plans",
        description=(
            "Contractor describes a room verbally, AI generates floor plan. "
            "Requires: speech-to-text (Whisper) + LLM reasoning + structured "
            "output (walls, dimensions). Currently possible for simple rooms, "
            "unreliable for complex layouts."
        ),
        current_readiness=0.25,
        predicted_mainstream_year=2029,
        confidence=0.45,
        impact_on_plano="high",
        action_required=(
            "Prototype voice-to-floorplan with GPT-4o/Claude multimodal + "
            "constrained output. Start with 'describe room, get rough layout' "
            "feature. Full voice-driven editing is 3+ years out."
        ),
        signals=[
            TechSignal("voice_multimodal", "product_launch", "GPT-4o native voice mode with vision", "", 0.7),
            TechSignal("voice_multimodal", "product_launch", "Claude multimodal with structured output", "", 0.65),
            TechSignal("voice_multimodal", "research_paper", "Text-to-floorplan papers at CVPR 2025", "", 0.5),
        ],
    ))

    # 14. Satellite / aerial imagery
    techs.append(TechEntry(
        id="satellite_imagery",
        domain="Geospatial",
        name="Satellite Imagery for Building Detection",
        description=(
            "Maxar WorldView at 30cm resolution, Planet Labs daily 3m coverage. "
            "Current: can detect building footprints from satellite (Microsoft "
            "Building Footprints, Google Open Buildings). Room-level detection "
            "from above is still impossible — need <5cm resolution."
        ),
        current_readiness=0.20,
        predicted_mainstream_year=2031,
        confidence=0.30,
        impact_on_plano="medium",
        action_required=(
            "Use existing building footprint datasets (OSM, MS Footprints) for "
            "lead generation. Room-level satellite detection is 5+ years out. "
            "Drone-based scanning is a better near-term path for exterior plans."
        ),
        signals=[
            TechSignal("satellite_imagery", "product_launch", "Maxar Legion constellation — 15cm resolution", "", 0.5),
            TechSignal("satellite_imagery", "funding", "Planet Labs AI-ready imagery API", "", 0.4),
            TechSignal("satellite_imagery", "research_paper", "Neural radiance fields from satellite imagery", "", 0.3),
        ],
    ))

    # 15. Blockchain / smart contracts for construction
    techs.append(TechEntry(
        id="blockchain_construction",
        domain="FinTech",
        name="Blockchain for Construction Contracts",
        description=(
            "Smart contracts for construction milestones, payment escrow, "
            "material provenance. Some pilots exist (Briq, Brickschain). "
            "Adoption very low — construction industry is conservative. "
            "Regulatory clarity needed for legal enforceability."
        ),
        current_readiness=0.10,
        predicted_mainstream_year=2032,
        confidence=0.25,
        impact_on_plano="low",
        action_required=(
            "Do NOT invest now. Monitor only. If EU passes construction "
            "digital identity requirements, reconsider. Stripe escrow is "
            "simpler and legally established for milestone payments."
        ),
        signals=[
            TechSignal("blockchain_construction", "funding", "Briq raised $30M for construction blockchain", "", 0.4),
            TechSignal("blockchain_construction", "research_paper", "EU exploring digital construction logs on DLT", "", 0.3),
            TechSignal("blockchain_construction", "patent", "Oracle construction blockchain patent 2024", "", 0.2),
        ],
    ))

    # 16. Robotics in construction
    techs.append(TechEntry(
        id="construction_robotics",
        domain="Construction Tech",
        name="Robotics in Construction / Renovation",
        description=(
            "Boston Dynamics Spot for site inspection, Built Robotics autonomous "
            "equipment, Dusty Robotics for layout marking. Renovation robots that "
            "need digital floor plans as input. Still very early and expensive."
        ),
        current_readiness=0.15,
        predicted_mainstream_year=2031,
        confidence=0.30,
        impact_on_plano="medium",
        action_required=(
            "Monitor Dusty Robotics (they need floor plan input). When "
            "renovation robots hit commercial availability, offer PlanO "
            "export format as robot-readable floor plan. 5+ year horizon."
        ),
        signals=[
            TechSignal("construction_robotics", "product_launch", "Dusty Robotics FieldPrinter — prints layouts on floors", "", 0.6),
            TechSignal("construction_robotics", "funding", "Built Robotics raised $100M Series D", "", 0.5),
            TechSignal("construction_robotics", "product_launch", "Spot robot used for construction site surveys", "", 0.4),
        ],
    ))

    # Compute yearly probabilities for all
    for tech in techs:
        tech.yearly_probabilities = _compute_yearly_probabilities(
            tech.current_readiness,
            tech.predicted_mainstream_year,
            tech.confidence,
        )

    return techs


# ---------------------------------------------------------------------------
# Scan command — run all watchdogs
# ---------------------------------------------------------------------------
def cmd_scan() -> None:
    """Run all watchdog functions, score readiness, persist to DB."""
    techs = _build_all_technologies()
    conn = _connect()

    print(f"{BOLD}PlanO Technology Radar — Scanning 16 domains...{RESET}\n")

    for tech in techs:
        _upsert_technology(conn, tech)
        _record_readiness(conn, tech, "watchdog_scan")
        _record_predictions(conn, tech)
        _record_signals(conn, tech)
        trl = _trl_label(tech.current_readiness)
        color = _impact_color(tech.impact_on_plano)
        print(f"  {color}[{tech.impact_on_plano.upper():>8}]{RESET}  "
              f"TRL {tech.current_readiness:.2f} ({trl:>14})  "
              f"{tech.name}")

    conn.commit()
    conn.close()

    total = len(techs)
    critical = sum(1 for t in techs if t.impact_on_plano == "critical")
    high = sum(1 for t in techs if t.impact_on_plano == "high")
    print(f"\n{BOLD}Scan complete:{RESET} {total} technologies tracked, "
          f"{critical} critical, {high} high impact")
    print(f"Database: {DB_PATH}")


# ---------------------------------------------------------------------------
# Radar command — quadrant display
# ---------------------------------------------------------------------------
def cmd_radar() -> None:
    """Print the full technology radar in 4 time-horizon columns."""
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM technologies ORDER BY current_readiness DESC"
    ).fetchall()
    conn.close()

    if not rows:
        print("No data. Run 'tech_radar.py scan' first.")
        return

    # Bucket by time horizon
    now_bucket: list[str] = []       # TRL >= 0.6 (build today)
    one_year: list[str] = []         # mainstream 2027
    three_year: list[str] = []       # mainstream 2028-2029
    five_year: list[str] = []        # mainstream 2030+

    for r in rows:
        label = f"{r['name'][:26]}"
        trl = r['current_readiness']
        yr = r['predicted_mainstream_year']
        color = _impact_color(r['impact_on_plano'])

        entry = f"{color}{label}{RESET}"

        if trl >= 0.6 or yr <= CURRENT_YEAR:
            now_bucket.append(entry)
        elif yr <= CURRENT_YEAR + 1:
            one_year.append(entry)
        elif yr <= CURRENT_YEAR + 3:
            three_year.append(entry)
        else:
            five_year.append(entry)

    # Pad columns to same length
    max_len = max(len(now_bucket), len(one_year), len(three_year), len(five_year), 1)
    for lst in (now_bucket, one_year, three_year, five_year):
        while len(lst) < max_len:
            lst.append("")

    print(f"\n{BOLD}PlanO Technology Radar — {datetime.now().strftime('%B %Y')}{RESET}")
    print("=" * 110)
    header = (
        f"  {'NOW (build today)':<30} {'1-YEAR':<28} "
        f"{'3-YEAR':<28} {'5-YEAR':<28}"
    )
    print(header)
    print(f"  {'~' * 26}     {'~' * 24}     {'~' * 24}     {'~' * 24}")

    for i in range(max_len):
        n = now_bucket[i] if i < len(now_bucket) else ""
        o = one_year[i] if i < len(one_year) else ""
        t = three_year[i] if i < len(three_year) else ""
        f_ = five_year[i] if i < len(five_year) else ""
        # Use raw lengths for padding since ANSI codes add invisible chars
        print(f"  {n:<39} {o:<37} {t:<37} {f_:<37}")

    print()
    print(f"{DIM}Impact: {RESET}"
          f"\033[91mCRITICAL{RESET}  "
          f"\033[93mHIGH{RESET}  "
          f"\033[96mMEDIUM{RESET}  "
          f"\033[90mLOW{RESET}")
    print()


# ---------------------------------------------------------------------------
# Predict command — detailed prediction for one tech
# ---------------------------------------------------------------------------
def cmd_predict(tech_id: str) -> None:
    """Show detailed prediction for a single technology."""
    conn = _connect()
    row = conn.execute("SELECT * FROM technologies WHERE id = ?", (tech_id,)).fetchone()
    if not row:
        # Try fuzzy match
        rows = conn.execute(
            "SELECT * FROM technologies WHERE id LIKE ? OR name LIKE ?",
            (f"%{tech_id}%", f"%{tech_id}%"),
        ).fetchall()
        if not rows:
            print(f"Technology '{tech_id}' not found. Run 'scan' first or check the ID.")
            conn.close()
            return
        row = rows[0]

    # Get history
    history = conn.execute(
        "SELECT readiness, data_source, timestamp FROM readiness_history "
        "WHERE tech_id = ? ORDER BY timestamp DESC LIMIT 10",
        (row['id'],),
    ).fetchall()

    # Get predictions
    preds = conn.execute(
        "SELECT year, probability FROM predictions "
        "WHERE tech_id = ? ORDER BY year, timestamp DESC",
        (row['id'],),
    ).fetchall()

    # Get signals
    sigs = conn.execute(
        "SELECT signal_type, title, significance FROM signals "
        "WHERE tech_id = ? ORDER BY significance DESC LIMIT 5",
        (row['id'],),
    ).fetchall()

    conn.close()

    color = _impact_color(row['impact_on_plano'])
    trl = _trl_label(row['current_readiness'])

    print(f"\n{BOLD}Technology Prediction: {row['name']}{RESET}")
    print("=" * 70)
    print(f"  Domain:          {row['domain']}")
    print(f"  ID:              {row['id']}")
    print(f"  Impact on PlanO: {color}{row['impact_on_plano'].upper()}{RESET}")
    print(f"  Current TRL:     {row['current_readiness']:.2f} ({trl})")
    print(f"  Mainstream by:   {row['predicted_mainstream_year']}")
    print(f"  Confidence:      {row['confidence']:.0%}")
    print()
    print(f"  {BOLD}Description:{RESET}")
    for line in textwrap.wrap(row['description'], 65):
        print(f"    {line}")
    print()
    print(f"  {BOLD}Action Required:{RESET}")
    for line in textwrap.wrap(row['action_required'], 65):
        print(f"    {line}")

    if preds:
        print(f"\n  {BOLD}Yearly Adoption Probability:{RESET}")
        # Deduplicate by year (take latest)
        year_map: dict[int, float] = {}
        for p in preds:
            year_map[p['year']] = p['probability']
        for year in sorted(year_map.keys()):
            prob = year_map[year]
            bar_len = int(prob * 40)
            bar = "#" * bar_len + "." * (40 - bar_len)
            marker = " <-- mainstream" if year == row['predicted_mainstream_year'] else ""
            print(f"    {year}: [{bar}] {prob:.0%}{marker}")

    if sigs:
        print(f"\n  {BOLD}Key Signals:{RESET}")
        for s in sigs:
            icon = {"funding": "$", "patent": "P", "product_launch": "*",
                    "standard_adopted": "S", "research_paper": "R"}.get(s['signal_type'], "?")
            print(f"    [{icon}] {s['title']} (significance: {s['significance']:.0%})")

    print()


# ---------------------------------------------------------------------------
# Signals command
# ---------------------------------------------------------------------------
def cmd_signals() -> None:
    """Show recent signals across all domains."""
    conn = _connect()
    rows = conn.execute("""
        SELECT s.*, t.name as tech_name, t.impact_on_plano
        FROM signals s JOIN technologies t ON s.tech_id = t.id
        ORDER BY s.significance DESC, s.timestamp DESC
        LIMIT 30
    """).fetchall()
    conn.close()

    if not rows:
        print("No signals. Run 'tech_radar.py scan' first.")
        return

    print(f"\n{BOLD}Technology Signals — Top 30 by Significance{RESET}")
    print("=" * 90)

    type_icons = {
        "funding": " $ FUNDING",
        "patent": " P PATENT ",
        "product_launch": " * LAUNCH ",
        "standard_adopted": " S STANDARD",
        "research_paper": " R RESEARCH",
    }

    for r in rows:
        color = _impact_color(r['impact_on_plano'])
        icon = type_icons.get(r['signal_type'], "   ???    ")
        sig_bar = "*" * int(r['significance'] * 5)
        print(f"  {color}[{icon}]{RESET} {sig_bar:<5} "
              f"{r['tech_name'][:20]:<20}  {r['title']}")

    print()


# ---------------------------------------------------------------------------
# Opportunities command
# ---------------------------------------------------------------------------
def cmd_opportunities() -> None:
    """What can PlanO build NOW vs plan for later."""
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM technologies ORDER BY current_readiness DESC"
    ).fetchall()
    conn.close()

    if not rows:
        print("No data. Run 'tech_radar.py scan' first.")
        return

    build_now = [r for r in rows if r['current_readiness'] >= 0.5]
    prepare = [r for r in rows if 0.3 <= r['current_readiness'] < 0.5]
    watch = [r for r in rows if r['current_readiness'] < 0.3]

    print(f"\n{BOLD}PlanO Opportunity Matrix{RESET}")
    print("=" * 80)

    print(f"\n  {BOLD}\033[92mBUILD NOW{RESET} (TRL >= 0.5 — technology ready for production)")
    print(f"  {'~' * 70}")
    for r in build_now:
        color = _impact_color(r['impact_on_plano'])
        print(f"    {color}[{r['impact_on_plano'].upper():>8}]{RESET} {r['name']}")
        for line in textwrap.wrap(r['action_required'], 60):
            print(f"             {DIM}{line}{RESET}")

    print(f"\n  {BOLD}\033[93mPREPARE{RESET} (TRL 0.3-0.5 — prototype and plan)")
    print(f"  {'~' * 70}")
    for r in prepare:
        color = _impact_color(r['impact_on_plano'])
        yr = r['predicted_mainstream_year']
        print(f"    {color}[{r['impact_on_plano'].upper():>8}]{RESET} {r['name']} (mainstream ~{yr})")
        for line in textwrap.wrap(r['action_required'], 60):
            print(f"             {DIM}{line}{RESET}")

    print(f"\n  {BOLD}\033[90mWATCH{RESET} (TRL < 0.3 — monitor only)")
    print(f"  {'~' * 70}")
    for r in watch:
        yr = r['predicted_mainstream_year']
        print(f"    [{r['impact_on_plano'].upper():>8}] {r['name']} (mainstream ~{yr})")

    print()


# ---------------------------------------------------------------------------
# Timeline command
# ---------------------------------------------------------------------------
def cmd_timeline() -> None:
    """Visual timeline of when each tech hits mainstream."""
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM technologies ORDER BY predicted_mainstream_year, current_readiness DESC"
    ).fetchall()
    conn.close()

    if not rows:
        print("No data. Run 'tech_radar.py scan' first.")
        return

    print(f"\n{BOLD}PlanO Technology Timeline{RESET}")
    print("=" * 90)

    years = range(CURRENT_YEAR, CURRENT_YEAR + 8)
    header = "  " + "".join(f"{y:<11}" for y in years)
    print(header)
    print("  " + "".join(f"{'|':<11}" for _ in years))

    for r in rows:
        yr = r['predicted_mainstream_year']
        color = _impact_color(r['impact_on_plano'])
        name = r['name'][:28]

        # Build timeline bar
        bar = "  "
        for y in years:
            if y == yr:
                bar += f"{color}>>>{RESET}        "
            elif y < yr and y >= CURRENT_YEAR:
                bar += f"{DIM}---{RESET}        "
            elif y > yr:
                bar += f"{DIM}   {RESET}        "
            else:
                bar += "           "

        print(f"{bar} {color}{name}{RESET}")

    print()
    print(f"  {DIM}>>> = predicted mainstream adoption year{RESET}")
    print(f"  {DIM}--- = development/adoption phase{RESET}")
    print()


# ---------------------------------------------------------------------------
# Train-export command — SFT pairs for agents
# ---------------------------------------------------------------------------
def cmd_train_export() -> None:
    """Generate SFT training pairs from tech radar data."""
    conn = _connect()
    rows = conn.execute("SELECT * FROM technologies").fetchall()
    sigs = conn.execute("""
        SELECT s.*, t.name as tech_name FROM signals s
        JOIN technologies t ON s.tech_id = t.id
    """).fetchall()
    conn.close()

    if not rows:
        print("No data. Run 'tech_radar.py scan' first.")
        return

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    pairs = []

    # Pair type 1: "What is the status of X technology?"
    for r in rows:
        trl = _trl_label(r['current_readiness'])
        pairs.append({
            "messages": [
                {"role": "user", "content": f"What is the current status of {r['name']} for PlanO?"},
                {"role": "assistant", "content": (
                    f"{r['name']} is currently at TRL {r['current_readiness']:.2f} ({trl}). "
                    f"{r['description']} "
                    f"It is predicted to reach mainstream adoption by {r['predicted_mainstream_year']} "
                    f"with {r['confidence']:.0%} confidence. "
                    f"Impact on PlanO: {r['impact_on_plano']}. "
                    f"Action: {r['action_required']}"
                )},
            ]
        })

    # Pair type 2: "When should PlanO invest in X?"
    for r in rows:
        yr = r['predicted_mainstream_year']
        if r['current_readiness'] >= 0.5:
            timing = "now — the technology is ready for production use"
        elif r['current_readiness'] >= 0.3:
            timing = f"start prototyping now, plan for production by {yr - 1}"
        else:
            timing = f"monitor only for now, revisit in {yr - CURRENT_YEAR - 2} years"

        pairs.append({
            "messages": [
                {"role": "user", "content": f"When should PlanO invest in {r['name']}?"},
                {"role": "assistant", "content": (
                    f"PlanO should {timing}. {r['action_required']}"
                )},
            ]
        })

    # Pair type 3: "What technologies should PlanO build on today?"
    build_now = [r for r in rows if r['current_readiness'] >= 0.5]
    tech_list = ", ".join(r['name'] for r in build_now)
    pairs.append({
        "messages": [
            {"role": "user", "content": "What technologies are ready for PlanO to build on today?"},
            {"role": "assistant", "content": (
                f"Technologies ready for production use (TRL >= 0.5): {tech_list}. "
                f"These have sufficient maturity, tooling, and adoption to build "
                f"reliable features on. Focus development resources here."
            )},
        ]
    })

    # Pair type 4: "What is the biggest opportunity for PlanO?"
    critical = [r for r in rows if r['impact_on_plano'] == 'critical']
    pairs.append({
        "messages": [
            {"role": "user", "content": "What are the biggest technology opportunities for PlanO?"},
            {"role": "assistant", "content": (
                "Critical impact technologies: " +
                "; ".join(
                    f"{r['name']} (TRL {r['current_readiness']:.2f}, "
                    f"mainstream by {r['predicted_mainstream_year']})"
                    for r in critical
                ) +
                ". The EU Renovation Wave (EPBD enforcement) is the single "
                "biggest demand driver — deadline-driven renovation requirements "
                "starting 2027-2028 will create massive demand for digital "
                "floor plan and renovation planning tools."
            )},
        ]
    })

    # Pair type 5: Signal-based pairs
    for s in sigs:
        pairs.append({
            "messages": [
                {"role": "user", "content": f"What does the signal '{s['title']}' mean for PlanO?"},
                {"role": "assistant", "content": (
                    f"This is a {s['signal_type'].replace('_', ' ')} signal for "
                    f"{s['tech_name']} with significance {s['significance']:.0%}. "
                    f"It indicates progress in the technology's maturity and "
                    f"should be tracked as part of PlanO's technology radar."
                )},
            ]
        })

    export_path = EXPORT_DIR / "tech_radar_sft.jsonl"
    with open(export_path, "w") as f:
        for pair in pairs:
            f.write(json.dumps(pair) + "\n")

    print(f"{BOLD}Exported {len(pairs)} SFT training pairs{RESET}")
    print(f"Output: {export_path}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Parse arguments and dispatch to the appropriate command."""
    parser = argparse.ArgumentParser(
        description="PlanO Technology Radar — Watchdog Swarm System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Commands:
              scan          Run all 16 watchdogs, update readiness scores
              radar         Print the full technology radar (now/1yr/3yr/5yr)
              predict       Detailed prediction for one technology
              signals       Show recent signals across all domains
              opportunities What PlanO can build NOW vs plan for
              train-export  Export SFT training pairs for agents
              timeline      Visual timeline of mainstream adoption dates
        """),
    )
    parser.add_argument("command", choices=[
        "scan", "radar", "predict", "signals",
        "opportunities", "train-export", "timeline",
    ])
    parser.add_argument("--tech", "-t", help="Technology ID for predict command")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan()
    elif args.command == "radar":
        cmd_radar()
    elif args.command == "predict":
        if not args.tech:
            print("Usage: tech_radar.py predict --tech <tech_id>")
            print("Tech IDs: webgpu, browser_ai, phone_lidar, ar_vr_headsets,")
            print("  ai_codegen, autonomous_agents, bim_mandate, construction_3dprint,")
            print("  eu_renovation_wave, payment_tech, edge_ai_chips, cv_accuracy,")
            print("  voice_multimodal, satellite_imagery, blockchain_construction,")
            print("  construction_robotics")
            sys.exit(1)
        cmd_predict(args.tech)
    elif args.command == "signals":
        cmd_signals()
    elif args.command == "opportunities":
        cmd_opportunities()
    elif args.command == "train-export":
        cmd_train_export()
    elif args.command == "timeline":
        cmd_timeline()


if __name__ == "__main__":
    main()
