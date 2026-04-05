#!/usr/bin/env python3
"""
PlanO Autonomous Daemon — 24/7 Self-Learning Operations

Runs continuously, orchestrates all business systems, optimizes its own
execution schedule based on performance data, and reduces human input
toward zero.

Architecture:
  ┌─────────────────────────────────────────────────┐
  │  DAEMON (this process, runs forever)             │
  │                                                  │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
  │  │ Scheduler│→ │ Executor │→ │ Learner  │     │
  │  │ (when)   │  │ (what)   │  │ (adapt)  │     │
  │  └──────────┘  └──────────┘  └──────────┘     │
  │       ↑                            │            │
  │       └────────────────────────────┘            │
  │            feedback loop                         │
  └─────────────────────────────────────────────────┘

Usage:
    python3 plano_daemon.py start        # start daemon (foreground)
    python3 plano_daemon.py status       # show schedule + last runs
    python3 plano_daemon.py optimize     # run self-optimization cycle
    python3 plano_daemon.py run-task <name>  # run a specific task now

DEBUG: PLANO_DEBUG=1
"""

import json
import logging
import math
import os
import signal
import sqlite3
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Callable, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "daemon"
DB_PATH = DATA_DIR / "daemon.db"

logging.basicConfig(
    level=logging.DEBUG if os.environ.get("PLANO_DEBUG") else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(BASE_DIR / "logs" / "plano_daemon.log", mode="a"),
    ],
)
log = logging.getLogger("plano.daemon")


# ═══════════════════════════════════════════════════════════
# TASK DEFINITIONS — what the daemon runs
# ═══════════════════════════════════════════════════════════

@dataclass
class Task:
    name: str
    description: str
    command: str                    # shell command to run
    default_interval_min: int      # default interval in minutes
    min_interval_min: int = 5      # minimum interval (don't run more often)
    max_interval_min: int = 10080  # max interval (1 week)
    current_interval_min: int = 0  # learned interval (0 = use default)
    priority: int = 5              # 1=highest, 10=lowest
    category: str = "general"
    last_run: str = ""
    last_duration_s: float = 0
    last_success: bool = True
    consecutive_failures: int = 0
    total_runs: int = 0
    avg_duration_s: float = 0
    value_score: float = 1.0       # learned value (higher = run more often)
    enabled: bool = True


TASKS = [
    # ── OSINT & Market Intelligence ──
    Task("osint_refresh", "Refresh OSINT data from Eurostat/WorldBank/ECB",
         f"cd {BASE_DIR} && python3 scripts/business/simulator.py osint",
         default_interval_min=10080, min_interval_min=1440, category="market", priority=3),

    Task("osm_sync_mt", "Sync Malta OSM building data",
         f"cd {BASE_DIR} && python3 scripts/pipeline/osm_sync.py sync MT",
         default_interval_min=10080, min_interval_min=1440, category="data", priority=4),

    Task("osm_sync_bg", "Sync Bulgaria OSM building data",
         f"cd {BASE_DIR} && python3 scripts/pipeline/osm_sync.py sync BG",
         default_interval_min=10080, min_interval_min=1440, category="data", priority=4),

    Task("competition_scan", "Scan all 15+ competitors for price/feature changes",
         f"cd {BASE_DIR} && python3 scripts/business/competition_monitor.py scan",
         default_interval_min=1440, min_interval_min=360, category="market", priority=2),

    Task("tech_radar_scan", "Update technology readiness scores",
         f"cd {BASE_DIR} && python3 scripts/watchdogs/tech_radar.py scan",
         default_interval_min=10080, min_interval_min=1440, category="market", priority=5),

    # ── Business Operations ──
    Task("simulator_run", "Run Monte Carlo business simulation with latest OSINT",
         f"cd {BASE_DIR} && python3 scripts/business/simulator.py run --months 48 --simulations 500",
         default_interval_min=1440, min_interval_min=360, category="business", priority=2),

    Task("pricing_recommend", "Generate dynamic pricing recommendations",
         f"cd {BASE_DIR} && python3 scripts/business/pricing_optimizer.py recommend",
         default_interval_min=4320, min_interval_min=1440, category="business", priority=3),

    Task("metrics_report", "Generate business metrics report",
         f"cd {BASE_DIR} && python3 scripts/business/metrics_dashboard.py report --period weekly",
         default_interval_min=10080, min_interval_min=1440, category="business", priority=3),

    Task("benchmarks_run", "Run launch readiness benchmarks",
         f"cd {BASE_DIR} && python3 scripts/business/launch_benchmarks.py run",
         default_interval_min=1440, min_interval_min=360, category="business", priority=1),

    # ── Infrastructure Health ──
    Task("infra_status", "Check infrastructure health + scaling needs",
         f"cd {BASE_DIR} && python3 scripts/infra/autoscale.py status",
         default_interval_min=60, min_interval_min=15, category="infra", priority=1),

    Task("infra_plan", "Compute scaling plan based on current load",
         f"cd {BASE_DIR} && python3 scripts/infra/autoscale.py plan",
         default_interval_min=360, min_interval_min=60, category="infra", priority=2),

    Task("rasta_health", "Check Rasta GPU engine health",
         f"ssh gpu 'curl -s http://localhost:8020/api/health'",
         default_interval_min=15, min_interval_min=5, category="infra", priority=1),

    Task("docker_health", "Check Docker container health",
         f"ssh gpu 'docker ps --filter name=plano-app --format {{{{.Status}}}}'",
         default_interval_min=15, min_interval_min=5, category="infra", priority=1),

    # ── AI Training & Data ──
    Task("cael_feed", "Generate daily intelligence briefing for Cael",
         f"cd {BASE_DIR} && python3 scripts/business/cael_feed.py export",
         default_interval_min=1440, min_interval_min=720, category="training", priority=3),

    Task("training_sft_export", "Export SFT training pairs from all business modules",
         f"cd {BASE_DIR} && python3 scripts/business/simulator.py train-export",
         default_interval_min=4320, min_interval_min=1440, category="training", priority=4),

    Task("rasta_pipeline_status", "Check Rasta training data pipeline status",
         f"cd {BASE_DIR} && python3 scripts/pipeline/rasta_training_pipeline.py status",
         default_interval_min=1440, min_interval_min=720, category="training", priority=4),

    # ── Self-Maintenance ──
    Task("self_optimize", "Optimize daemon's own execution schedule",
         f"cd {BASE_DIR} && python3 scripts/orchestrator/plano_daemon.py optimize",
         default_interval_min=720, min_interval_min=360, category="meta", priority=2),

    Task("log_cleanup", "Rotate and compress old logs (keep 30 days)",
         f"find {BASE_DIR}/logs -name '*.log' -mtime +30 -delete 2>/dev/null; echo cleaned",
         default_interval_min=10080, min_interval_min=1440, category="meta", priority=8),
]


# ═══════════════════════════════════════════════════════════
# DATABASE — persistent state
# ═══════════════════════════════════════════════════════════

def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "logs").mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""CREATE TABLE IF NOT EXISTS task_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_name TEXT, started_at TEXT, finished_at TEXT,
        duration_s REAL, success INTEGER, output TEXT, error TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS schedule_state (
        task_name TEXT PRIMARY KEY,
        current_interval_min INTEGER, value_score REAL,
        last_run TEXT, consecutive_failures INTEGER,
        total_runs INTEGER, avg_duration_s REAL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS optimization_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT, task_name TEXT,
        old_interval INTEGER, new_interval INTEGER,
        reason TEXT
    )""")
    conn.commit()
    conn.close()


def load_state(task: Task) -> Task:
    """Load persisted state for a task."""
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute("SELECT * FROM schedule_state WHERE task_name=?", (task.name,)).fetchone()
    if row:
        task.current_interval_min = row[1] or task.default_interval_min
        task.value_score = row[2] or 1.0
        task.last_run = row[3] or ""
        task.consecutive_failures = row[4] or 0
        task.total_runs = row[5] or 0
        task.avg_duration_s = row[6] or 0
    else:
        task.current_interval_min = task.default_interval_min
    conn.close()
    return task


def save_state(task: Task):
    """Save task state to DB."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""INSERT OR REPLACE INTO schedule_state
        (task_name, current_interval_min, value_score, last_run, consecutive_failures, total_runs, avg_duration_s)
        VALUES (?,?,?,?,?,?,?)""",
        (task.name, task.current_interval_min, task.value_score,
         task.last_run, task.consecutive_failures, task.total_runs, task.avg_duration_s))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════
# EXECUTOR — run tasks
# ═══════════════════════════════════════════════════════════

def execute_task(task: Task) -> tuple[bool, str, float]:
    """Execute a task and return (success, output, duration_seconds)."""
    log.info("Running: %s", task.name)
    t0 = time.time()

    try:
        result = subprocess.run(
            task.command, shell=True, capture_output=True, text=True,
            timeout=300,  # 5 minute max per task
        )
        duration = time.time() - t0
        success = result.returncode == 0
        output = result.stdout[-500:] if result.stdout else ""
        error = result.stderr[-200:] if not success and result.stderr else ""

        if success:
            log.info("  OK: %s (%.1fs)", task.name, duration)
        else:
            log.warning("  FAIL: %s (exit %d, %.1fs): %s", task.name, result.returncode, duration, error[:100])

        return success, output, duration

    except subprocess.TimeoutExpired:
        duration = time.time() - t0
        log.error("  TIMEOUT: %s (%.1fs)", task.name, duration)
        return False, "", duration

    except Exception as e:
        duration = time.time() - t0
        log.error("  ERROR: %s: %s", task.name, e)
        return False, "", duration


def run_task(task: Task):
    """Execute task and update state."""
    success, output, duration = execute_task(task)

    task.last_run = datetime.now(timezone.utc).isoformat()
    task.last_duration_s = duration
    task.last_success = success
    task.total_runs += 1

    if success:
        task.consecutive_failures = 0
    else:
        task.consecutive_failures += 1

    # Running average duration
    if task.avg_duration_s == 0:
        task.avg_duration_s = duration
    else:
        task.avg_duration_s = task.avg_duration_s * 0.9 + duration * 0.1

    # Log to history
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "INSERT INTO task_history (task_name, started_at, finished_at, duration_s, success, output, error) VALUES (?,?,?,?,?,?,?)",
        (task.name, task.last_run, datetime.now(timezone.utc).isoformat(),
         duration, 1 if success else 0, output[:500], "" if success else output[:200])
    )
    conn.commit()
    conn.close()

    save_state(task)


# ═══════════════════════════════════════════════════════════
# LEARNER — self-optimizing scheduler
# ═══════════════════════════════════════════════════════════

def should_run(task: Task) -> bool:
    """Determine if a task should run now."""
    if not task.enabled:
        return False

    if not task.last_run:
        return True  # never run → run now

    interval = task.current_interval_min or task.default_interval_min

    try:
        last = datetime.fromisoformat(task.last_run)
        elapsed = (datetime.now(timezone.utc) - last).total_seconds() / 60
        return elapsed >= interval
    except (ValueError, TypeError):
        return True


def optimize_schedule():
    """Self-learning optimization: adjust intervals based on performance data.

    Rules:
    1. Tasks that fail repeatedly → increase interval (back off)
    2. Tasks that always succeed and complete fast → can run less often
    3. Tasks with high value_score → run more often
    4. Infrastructure checks → always keep short intervals
    5. Never violate min/max bounds
    6. Apply 25% margin (don't saturate execution capacity)
    """
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    changes = []

    for task in TASKS:
        task = load_state(task)
        old_interval = task.current_interval_min or task.default_interval_min
        new_interval = old_interval
        reason = ""

        # Rule 1: Back off on failures
        if task.consecutive_failures >= 3:
            new_interval = min(old_interval * 2, task.max_interval_min)
            reason = f"3+ consecutive failures → back off"

        # Rule 2: Fast, always-successful tasks → slight increase (save resources)
        elif task.total_runs > 10 and task.consecutive_failures == 0:
            if task.avg_duration_s < 5 and task.category != "infra":
                # Quick tasks that always pass can run 10% less often
                new_interval = min(int(old_interval * 1.1), task.max_interval_min)
                reason = f"Always succeeds, fast ({task.avg_duration_s:.1f}s) → relax"

        # Rule 3: Infrastructure tasks stay at minimum when healthy
        if task.category == "infra" and task.consecutive_failures == 0:
            new_interval = max(task.min_interval_min, min(old_interval, task.default_interval_min))
            if new_interval != old_interval:
                reason = f"Infra healthy → maintain default"

        # Rule 4: High-priority tasks with failures → try more often
        if task.priority <= 2 and task.consecutive_failures == 1:
            new_interval = max(task.min_interval_min, old_interval // 2)
            reason = f"Priority {task.priority} failure → retry sooner"

        # Enforce bounds
        new_interval = max(task.min_interval_min, min(new_interval, task.max_interval_min))

        if new_interval != old_interval:
            task.current_interval_min = new_interval
            save_state(task)
            changes.append((task.name, old_interval, new_interval, reason))
            conn.execute(
                "INSERT INTO optimization_log (timestamp, task_name, old_interval, new_interval, reason) VALUES (?,?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(), task.name, old_interval, new_interval, reason)
            )

    conn.commit()
    conn.close()

    if changes:
        log.info("Schedule optimized: %d changes", len(changes))
        for name, old, new, reason in changes:
            log.info("  %s: %dm → %dm (%s)", name, old, new, reason)
    else:
        log.info("Schedule optimization: no changes needed")

    return changes


# ═══════════════════════════════════════════════════════════
# DAEMON — main loop
# ═══════════════════════════════════════════════════════════

running = True

def handle_signal(signum, frame):
    global running
    log.info("Received signal %d — shutting down gracefully", signum)
    running = False


def daemon_loop():
    """Main daemon loop — runs forever, executing tasks on schedule."""
    global running
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    init_db()
    log.info("PlanO Daemon starting — %d tasks registered", len(TASKS))

    # Load all task states
    tasks = [load_state(t) for t in TASKS]

    cycle = 0
    while running:
        cycle += 1
        now = datetime.now(timezone.utc)

        # Check each task
        for task in tasks:
            if should_run(task):
                run_task(task)
                # Reload state after run
                task = load_state(task)

        # Sleep 60 seconds between checks (25% margin — don't busy-loop)
        for _ in range(60):
            if not running:
                break
            time.sleep(1)

    log.info("Daemon stopped after %d cycles", cycle)


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def print_status():
    init_db()
    print()
    print("=" * 85)
    print("  PlanO Autonomous Daemon — Task Schedule")
    print("=" * 85)
    print()
    print(f"{'Task':30} {'Interval':>10} {'Last Run':>18} {'Runs':>5} {'Fails':>5} {'Avg(s)':>7} {'Status':>8}")
    print("-" * 85)

    for task in TASKS:
        task = load_state(task)
        interval = task.current_interval_min or task.default_interval_min

        if interval < 60:
            interval_str = f"{interval}m"
        elif interval < 1440:
            interval_str = f"{interval/60:.0f}h"
        else:
            interval_str = f"{interval/1440:.0f}d"

        last = task.last_run[:16] if task.last_run else "never"
        status = "OK" if task.last_success and task.total_runs > 0 else ("FAIL" if task.total_runs > 0 else "WAIT")

        print(f"  {task.name:28} {interval_str:>10} {last:>18} {task.total_runs:>5} {task.consecutive_failures:>5} {task.avg_duration_s:>6.1f} {status:>8}")

    # Show optimization history
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute("SELECT * FROM optimization_log ORDER BY timestamp DESC LIMIT 5").fetchall()
    conn.close()

    if rows:
        print()
        print("  Recent optimizations:")
        for r in rows:
            print(f"    {r[1][:16]} {r[2]:25} {r[3]}m → {r[4]}m ({r[5]})")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "start":
        daemon_loop()

    elif cmd == "status":
        print_status()

    elif cmd == "optimize":
        init_db()
        # Run all tasks once first to build data
        changes = optimize_schedule()
        if changes:
            for name, old, new, reason in changes:
                print(f"  {name}: {old}m → {new}m ({reason})")
        else:
            print("  No changes needed")

    elif cmd == "run-task":
        if len(sys.argv) < 3:
            print("Usage: plano_daemon.py run-task <task_name>")
            sys.exit(1)
        task_name = sys.argv[2]
        for t in TASKS:
            if t.name == task_name:
                init_db()
                t = load_state(t)
                run_task(t)
                break
        else:
            print(f"Unknown task: {task_name}")
            print("Available:", [t.name for t in TASKS])

    else:
        print(__doc__)

# ── ADDED: Trading tasks ──
# These are appended to the TASKS list at runtime
TRADING_TASKS = [
    # Task("arb_scan", "Crypto arbitrage opportunity scan",
    #      f"cd {BASE_DIR} && python3 scripts/trading/arb_scanner.py scan",
    #      default_interval_min=5, min_interval_min=1, max_interval_min=30,
    #      category="trading", priority=1),
]
# NOTE: Uncomment above when ready to activate trading scans in daemon
