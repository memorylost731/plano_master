#!/usr/bin/env python3
"""Revenue Engine — Self-reinforcing money machine.

Orchestrates all revenue streams, tracks BTC earnings, feeds successful
patterns back into training for continuous improvement.

The loop:
  Scan → Find → Earn (BTC) → Train on success → Better scans → More BTC

Usage:
    revenue_engine.py status       — dashboard of all revenue streams
    revenue_engine.py activate     — activate all dormant streams
    revenue_engine.py cycle        — run one full revenue cycle
    revenue_engine.py earnings     — show BTC earnings
    revenue_engine.py reinforce    — feed successes into training data
"""

import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple

BASE_DIR = Path.home() / "data-gathering-agent"
DB_PATH = BASE_DIR / "revenue_engine.db"
OLLAMA_URL = "http://100.71.235.99:11434"
BTC_WALLET = "cael"
GPU_HOST = "gpu"

# Revenue streams ranked by: speed to first dollar × probability × automation
STREAMS = {
    "bug_bounty": {
        "priority": 1,
        "monthly_potential": "$500-$25,000",
        "activation": "scan_and_submit",
        "tools": ["nuclei", "subfinder", "httpx", "ffuf"],
        "cron": "0 */4 * * *",
        "script": "cael_bounty_monitor.py run-cycle",
    },
    "inference_api": {
        "priority": 2,
        "monthly_potential": "$50-$500",
        "activation": "deploy_endpoint",
        "port": 8888,
        "cron": None,  # persistent service
        "script": "cael_inference_api.py serve",
    },
    "btc_yield": {
        "priority": 3,
        "monthly_potential": "$30-$50",
        "activation": "stake_babylon",
        "allocation_btc": 0.014,  # 10% of treasury
    },
    "compute_provider": {
        "priority": 4,
        "monthly_potential": "$200-$500",
        "activation": "akash_deploy",
        "sellable_vram_gb": 148,
    },
    "osint_service": {
        "priority": 5,
        "monthly_potential": "$500-$5,000",
        "activation": "publish_landing_page",
    },
    "smart_contract_audit": {
        "priority": 6,
        "monthly_potential": "$1,000-$10,000",
        "activation": "first_public_audit",
    },
    "client_billing": {
        "priority": 7,
        "monthly_potential": "$120-$500",
        "activation": "invoice_hadrien",
        "script": "cael_billing.py invoice",
    },
    "plano_saas": {
        "priority": 8,
        "monthly_potential": "$0-$2,000",
        "activation": "stripe_integration",
    },
    "referral_program": {
        "priority": 9,
        "monthly_potential": "$50-$500",
        "activation": "needs_customers_first",
    },
    "lightning_routing": {
        "priority": 10,
        "monthly_potential": "$1-$5",
        "activation": "open_channels",
        "capital_btc": 0.02,
    },
    "ipfs_pinning": {
        "priority": 11,
        "monthly_potential": "$5-$15",
        "activation": "publish_service",
    },
    "consulting": {
        "priority": 12,
        "monthly_potential": "EUR 5,000-$20,000",
        "activation": "find_clients",
        "status": "pro_bono_until_cashflow",
    },
}


def init_db() -> sqlite3.Connection:
    """Initialize revenue tracking database."""
    db = sqlite3.connect(str(DB_PATH))
    db.execute("PRAGMA journal_mode=WAL")
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS earnings (
            id INTEGER PRIMARY KEY,
            timestamp TEXT DEFAULT (datetime('now')),
            stream TEXT NOT NULL,
            amount_btc REAL DEFAULT 0,
            amount_usd REAL DEFAULT 0,
            description TEXT,
            tx_id TEXT
        );
        CREATE TABLE IF NOT EXISTS stream_status (
            stream TEXT PRIMARY KEY,
            status TEXT DEFAULT 'dormant',
            last_cycle TEXT,
            total_earned_btc REAL DEFAULT 0,
            total_cycles INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 0,
            last_error TEXT
        );
        CREATE TABLE IF NOT EXISTS reinforcement_log (
            id INTEGER PRIMARY KEY,
            timestamp TEXT DEFAULT (datetime('now')),
            stream TEXT,
            event_type TEXT,
            data TEXT,
            fed_to_training INTEGER DEFAULT 0
        );
    """)
    # Seed stream status
    for name in STREAMS:
        db.execute(
            "INSERT OR IGNORE INTO stream_status (stream) VALUES (?)",
            (name,),
        )
    db.commit()
    return db


def run_cmd(cmd: str, timeout: int = 60) -> Tuple[bool, str]:
    """Run a shell command and return (success, output)."""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return r.returncode == 0, r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


def get_btc_balance() -> float:
    """Get current BTC wallet balance from GPU bitcoind."""
    ok, out = run_cmd(
        f"ssh {GPU_HOST} 'docker exec bitcoind bitcoin-cli -datadir=/home/bitcoin/.bitcoin -rpcwallet={BTC_WALLET} getbalance' 2>/dev/null"
    )
    if ok:
        try:
            return float(out.strip())
        except ValueError:
            pass
    return 0.0


def get_btc_price() -> float:
    """Get current BTC/USD price."""
    ok, out = run_cmd(
        "curl -s 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd' 2>/dev/null"
    )
    if ok:
        try:
            return json.loads(out)["bitcoin"]["usd"]
        except (json.JSONDecodeError, KeyError):
            pass
    return 69000.0  # fallback


def activate_bug_bounty(db: sqlite3.Connection) -> str:
    """Ensure bounty scanner is running and producing."""
    # Check cron
    ok, out = run_cmd("crontab -l 2>/dev/null | grep -c bounty_monitor")
    if not ok or out.strip() == "0":
        run_cmd(
            '(crontab -l 2>/dev/null; echo "0 */4 * * * cd /home/memorylost/data-gathering-agent '
            '&& python3 cael_bounty_monitor.py run-cycle >> logs/bounty_monitor.log 2>&1") | crontab -'
        )
    # Check tools
    for tool in ["nuclei", "subfinder", "httpx", "ffuf"]:
        ok, _ = run_cmd(f"which {tool}")
        if not ok:
            return f"BLOCKED: {tool} not installed"
    # Trigger a scan cycle
    run_cmd(
        f"cd {BASE_DIR} && nohup python3 cael_bounty_monitor.py run-cycle "
        f">> logs/bounty_monitor.log 2>&1 &"
    )
    db.execute(
        "UPDATE stream_status SET status='active', last_cycle=datetime('now'), "
        "total_cycles=total_cycles+1 WHERE stream='bug_bounty'"
    )
    db.commit()
    return "ACTIVE: scan cycle triggered"


def activate_inference_api(db: sqlite3.Connection) -> str:
    """Deploy inference API as systemd service."""
    # Check if service exists
    ok, out = run_cmd("systemctl --user is-active cael-inference-api 2>/dev/null")
    if ok and out.strip() == "active":
        db.execute(
            "UPDATE stream_status SET status='active' WHERE stream='inference_api'"
        )
        db.commit()
        return "ACTIVE: already running"

    # Create service if missing
    svc_path = Path.home() / ".config/systemd/user/cael-inference-api.service"
    if not svc_path.exists():
        svc_path.write_text(f"""[Unit]
Description=Cael Inference API — OpenAI-compatible endpoint
After=network-online.target

[Service]
Type=simple
WorkingDirectory={BASE_DIR}
ExecStart=/usr/bin/python3 {BASE_DIR}/cael_inference_api.py serve
Restart=always
RestartSec=30
Environment=OLLAMA_URL={OLLAMA_URL}

[Install]
WantedBy=default.target
""")
        run_cmd("systemctl --user daemon-reload")
        run_cmd("systemctl --user enable --now cael-inference-api")

    db.execute(
        "UPDATE stream_status SET status='activating' WHERE stream='inference_api'"
    )
    db.commit()
    return "ACTIVATING: service created and started"


def activate_client_billing(db: sqlite3.Connection) -> str:
    """Generate and record billing for active clients."""
    ok, out = run_cmd(f"cd {BASE_DIR} && python3 cael_billing.py status 2>/dev/null")
    db.execute(
        "UPDATE stream_status SET status='active', last_cycle=datetime('now') "
        "WHERE stream='client_billing'"
    )
    db.commit()
    return f"ACTIVE: {out.strip()[:100]}" if ok else "ACTIVE: billing system ready"


def record_earning(
    db: sqlite3.Connection,
    stream: str,
    amount_btc: float,
    description: str,
    tx_id: str = "",
) -> None:
    """Record a BTC earning."""
    price = get_btc_price()
    db.execute(
        "INSERT INTO earnings (stream, amount_btc, amount_usd, description, tx_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (stream, amount_btc, amount_btc * price, description, tx_id),
    )
    db.execute(
        "UPDATE stream_status SET total_earned_btc=total_earned_btc+? WHERE stream=?",
        (amount_btc, stream),
    )
    db.commit()


def feed_to_training(db: sqlite3.Connection) -> int:
    """Feed successful patterns into GRPO training data."""
    # Get unfed reinforcement events
    events = db.execute(
        "SELECT id, stream, event_type, data FROM reinforcement_log "
        "WHERE fed_to_training=0 ORDER BY id"
    ).fetchall()

    if not events:
        return 0

    pairs = []
    for ev in events:
        data = json.loads(ev["data"]) if ev["data"] else {}
        # Convert success/failure into GRPO reward signal
        reward = 1.0 if ev["event_type"] == "success" else -0.5
        pair = {
            "messages": [
                {
                    "role": "system",
                    "content": f"You are Cael, running the {ev['stream']} revenue stream.",
                },
                {
                    "role": "user",
                    "content": data.get("prompt", f"Execute {ev['stream']} cycle"),
                },
                {
                    "role": "assistant",
                    "content": data.get(
                        "response", f"Cycle completed: {ev['event_type']}"
                    ),
                },
            ],
            "reward": reward,
        }
        pairs.append(pair)

    # Write to training lake
    grpo_path = BASE_DIR / "training_lake" / "revenue_grpo.jsonl"
    with open(grpo_path, "a") as f:
        for p in pairs:
            f.write(json.dumps(p) + "\n")

    # Mark as fed
    ids = [ev["id"] for ev in events]
    db.executemany(
        "UPDATE reinforcement_log SET fed_to_training=1 WHERE id=?",
        [(i,) for i in ids],
    )
    db.commit()

    return len(pairs)


def log_reinforcement(
    db: sqlite3.Connection,
    stream: str,
    event_type: str,
    data: dict,
) -> None:
    """Log an event for reinforcement learning."""
    db.execute(
        "INSERT INTO reinforcement_log (stream, event_type, data) VALUES (?, ?, ?)",
        (stream, event_type, json.dumps(data)),
    )
    db.commit()


def run_full_cycle(db: sqlite3.Connection) -> Dict[str, str]:
    """Run one complete revenue cycle across all streams."""
    results = {}

    # Priority 1: Bug bounty
    results["bug_bounty"] = activate_bug_bounty(db)
    log_reinforcement(db, "bug_bounty", "cycle", {"action": "scan_triggered"})

    # Priority 2: Inference API
    results["inference_api"] = activate_inference_api(db)

    # Priority 7: Client billing
    results["client_billing"] = activate_client_billing(db)

    # Feed successes to training
    fed = feed_to_training(db)
    results["reinforcement"] = f"{fed} events fed to training"

    return results


def show_status() -> None:
    """Print revenue dashboard."""
    db = init_db()
    balance = get_btc_balance()
    price = get_btc_price()

    print("\n" + "=" * 60)
    print("  REVENUE ENGINE — MONEY MACHINE STATUS")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    print(f"\n  BTC Balance:  {balance:.8f} BTC (${balance * price:,.2f})")
    print(f"  BTC Price:    ${price:,.0f}")
    print(f"  Monthly Burn: $452")
    print(f"  Runway:       {int((balance * price * 0.75) / 452)} months")

    print("\n  REVENUE STREAMS:")
    print(f"  {'Stream':<25} {'Status':<12} {'Earned BTC':<15} {'Cycles':<8}")
    print("  " + "─" * 60)

    rows = db.execute(
        "SELECT * FROM stream_status ORDER BY total_earned_btc DESC"
    ).fetchall()
    for r in rows:
        status_icon = (
            "●" if r["status"] == "active" else
            "◐" if r["status"] == "activating" else "○"
        )
        print(
            f"  {status_icon} {r['stream']:<23} {r['status']:<12} "
            f"{r['total_earned_btc']:.8f}    {r['total_cycles']}"
        )

    # Total earnings
    total = db.execute(
        "SELECT COALESCE(SUM(amount_btc), 0) FROM earnings"
    ).fetchone()[0]
    print(f"\n  TOTAL EARNED: {total:.8f} BTC (${total * price:,.2f})")

    # Recent earnings
    recent = db.execute(
        "SELECT timestamp, stream, amount_btc, description "
        "FROM earnings ORDER BY id DESC LIMIT 5"
    ).fetchall()
    if recent:
        print("\n  RECENT EARNINGS:")
        for r in recent:
            print(f"    {r['timestamp']} | {r['stream']} | {r['amount_btc']:.8f} BTC | {r['description']}")

    # Reinforcement stats
    unfed = db.execute(
        "SELECT COUNT(*) FROM reinforcement_log WHERE fed_to_training=0"
    ).fetchone()[0]
    total_fed = db.execute(
        "SELECT COUNT(*) FROM reinforcement_log WHERE fed_to_training=1"
    ).fetchone()[0]
    print(f"\n  REINFORCEMENT: {total_fed} events trained, {unfed} pending")

    db.close()


def show_earnings() -> None:
    """Show all BTC earnings."""
    db = init_db()
    rows = db.execute(
        "SELECT timestamp, stream, amount_btc, amount_usd, description, tx_id "
        "FROM earnings ORDER BY id DESC"
    ).fetchall()
    if not rows:
        print("No earnings yet. Run 'revenue_engine.py cycle' to activate streams.")
        return
    print(f"\n{'Time':<20} {'Stream':<20} {'BTC':<15} {'USD':<10} {'Description'}")
    print("─" * 80)
    for r in rows:
        print(
            f"{r['timestamp']:<20} {r['stream']:<20} {r['amount_btc']:.8f}    "
            f"${r['amount_usd']:.2f}    {r['description']}"
        )
    db.close()


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: revenue_engine.py {status|activate|cycle|earnings|reinforce}")
        sys.exit(1)

    cmd = sys.argv[1]
    db = init_db()

    if cmd == "status":
        show_status()
    elif cmd == "activate":
        results = run_full_cycle(db)
        for stream, result in results.items():
            print(f"  {stream}: {result}")
    elif cmd == "cycle":
        results = run_full_cycle(db)
        for stream, result in results.items():
            print(f"  {stream}: {result}")
    elif cmd == "earnings":
        show_earnings()
    elif cmd == "reinforce":
        fed = feed_to_training(db)
        print(f"Fed {fed} events to GRPO training data")
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

    db.close()


if __name__ == "__main__":
    main()
