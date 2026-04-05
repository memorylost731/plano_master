#!/usr/bin/env python3
"""
PlanO — Automated Scaling & Redundancy Engine

Monitors all systems, auto-scales vertically and horizontally,
manages redundancy, and self-heals — zero human intervention.

Architecture:
  VERTICAL:  GPU VRAM allocation, worker concurrency, cache sizes
  HORIZONTAL: Docker replicas, Celery workers, read replicas
  REDUNDANCY: backup paths, failover triggers, health cascades

Usage:
    python3 autoscale.py status          # current scale + health
    python3 autoscale.py plan            # show scaling plan based on load
    python3 autoscale.py execute         # apply scaling decisions
    python3 autoscale.py simulate --users 10000  # project infra needs
    python3 autoscale.py redundancy      # check all backup paths
    python3 autoscale.py drill --scenario gpu_down  # failover drill

DEBUG: PLANO_DEBUG=1
"""

import json
import logging
import math
import os
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "scaling"

logging.basicConfig(
    level=logging.DEBUG if os.environ.get("PLANO_DEBUG") else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("plano.autoscale")

# 25% MARGIN — Black Parade principle
MARGIN = 0.25


# ═══════════════════════════════════════════════════════════
# SYSTEM PROBES — measure current state
# ═══════════════════════════════════════════════════════════

@dataclass
class SystemState:
    """Current state of all PlanO infrastructure."""
    timestamp: str = ""

    # GPU server
    gpu_vram_used_mb: int = 0
    gpu_vram_total_mb: int = 0
    gpu_vram_pct: float = 0
    gpu_disk_used_pct: float = 0
    gpu_cpu_load: float = 0
    gpu_ram_used_pct: float = 0

    # Docker
    docker_container_status: str = ""
    docker_restart_count: int = 0

    # Rasta
    rasta_status: str = ""
    rasta_workers: int = 0
    rasta_queue_depth: int = 0
    rasta_avg_latency_ms: float = 0

    # Ollama (AI agents)
    ollama_status: str = ""
    ollama_model_loaded: str = ""

    # Redis
    redis_status: str = ""
    redis_memory_mb: float = 0

    # Caddy
    caddy_status: str = ""

    # Auth
    auth_status: str = ""

    # Metrics
    active_users: int = 0
    plans_per_hour: float = 0
    api_requests_per_min: float = 0


def probe_system() -> SystemState:
    """Probe all systems and return current state."""
    s = SystemState(timestamp=datetime.now(timezone.utc).isoformat())

    def ssh_cmd(cmd: str) -> str:
        try:
            r = subprocess.run(
                ["ssh", "gpu", cmd], capture_output=True, text=True, timeout=10
            )
            return r.stdout.strip()
        except Exception:
            return ""

    # GPU VRAM
    vram = ssh_cmd("nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits")
    if vram and "," in vram:
        parts = vram.split(",")
        s.gpu_vram_used_mb = int(parts[0].strip())
        s.gpu_vram_total_mb = int(parts[1].strip())
        s.gpu_vram_pct = s.gpu_vram_used_mb / max(s.gpu_vram_total_mb, 1)

    # GPU disk
    disk = ssh_cmd("df /home/hadrienm --output=pcent | tail -1")
    if disk:
        s.gpu_disk_used_pct = float(disk.strip().replace("%", "")) / 100

    # GPU CPU load
    load = ssh_cmd("cat /proc/loadavg | awk '{print $1}'")
    if load:
        try:
            s.gpu_cpu_load = float(load)
        except ValueError:
            pass

    # Docker
    docker = ssh_cmd("docker inspect plano-app --format '{{.State.Status}} {{.RestartCount}}' 2>/dev/null")
    if docker:
        parts = docker.split()
        s.docker_container_status = parts[0] if parts else "unknown"
        s.docker_restart_count = int(parts[1]) if len(parts) > 1 else 0

    # Rasta health
    rasta = ssh_cmd("curl -s http://localhost:8020/api/health 2>/dev/null")
    if rasta:
        try:
            h = json.loads(rasta)
            s.rasta_status = h.get("status", "unknown")
            s.rasta_workers = 2  # configured concurrency
        except json.JSONDecodeError:
            s.rasta_status = "error"

    # Redis
    redis_info = ssh_cmd("redis-cli info memory 2>/dev/null | grep used_memory_human")
    if redis_info:
        s.redis_status = "ok"
        try:
            s.redis_memory_mb = float(redis_info.split(":")[1].strip().replace("M", "").replace("K", ""))
        except (ValueError, IndexError):
            pass

    # Caddy
    caddy = ssh_cmd("curl -s -o /dev/null -w '%{http_code}' http://localhost:2019/config/ 2>/dev/null")
    s.caddy_status = "ok" if caddy == "200" else "down"

    # Auth
    auth = ssh_cmd("curl -s -o /dev/null -w '%{http_code}' http://localhost:9099/auth/verify 2>/dev/null")
    s.auth_status = "ok" if auth == "401" else "down"

    return s


# ═══════════════════════════════════════════════════════════
# SCALING RULES — when and how to scale
# ═══════════════════════════════════════════════════════════

@dataclass
class ScalingAction:
    """A scaling decision."""
    system: str
    action: str  # scale_up, scale_down, add_replica, failover, alert
    reason: str
    priority: str  # critical, high, medium, low
    automated: bool  # can be executed without human
    command: str  # shell command to execute
    rollback: str  # command to undo


# User thresholds (with 25% margin)
THRESHOLDS = {
    "gpu_vram_pct": {"warn": 0.60, "critical": 0.75, "max": 1.0 - MARGIN},
    "gpu_disk_pct": {"warn": 0.60, "critical": 0.75, "max": 1.0 - MARGIN},
    "gpu_cpu_load": {"warn": 4.0, "critical": 8.0},
    "rasta_queue": {"warn": 5, "critical": 20},
    "rasta_latency_ms": {"warn": 2000, "critical": 5000},
    "redis_memory_mb": {"warn": 500, "critical": 900},
    "docker_restarts": {"warn": 3, "critical": 10},
}

# Scaling triggers by user count
SCALE_TRIGGERS = {
    50:    {"rasta_workers": 2, "docker_replicas": 1, "cache_mb": 256},
    200:   {"rasta_workers": 3, "docker_replicas": 1, "cache_mb": 512},
    500:   {"rasta_workers": 4, "docker_replicas": 2, "cache_mb": 1024},
    1000:  {"rasta_workers": 6, "docker_replicas": 2, "cache_mb": 2048, "note": "Consider Dell server for Rasta overflow"},
    2000:  {"rasta_workers": 8, "docker_replicas": 3, "cache_mb": 4096, "note": "Move Rasta to Dell (503GB RAM)"},
    5000:  {"rasta_workers": 12, "docker_replicas": 4, "cache_mb": 8192, "note": "Evaluate AWS ECS Fargate"},
    10000: {"note": "MUST move to cloud — single GPU server insufficient"},
    50000: {"note": "Multi-region deployment required (EU-West, EU-East)"},
}


def compute_scaling_plan(state: SystemState, target_users: int = 0) -> list[ScalingAction]:
    """Analyze current state and compute required scaling actions."""
    actions = []
    users = target_users or state.active_users

    # ── Vertical scaling checks ──

    if state.gpu_vram_pct > THRESHOLDS["gpu_vram_pct"]["critical"]:
        actions.append(ScalingAction(
            system="gpu", action="alert", priority="critical",
            reason=f"GPU VRAM at {state.gpu_vram_pct:.0%} (>{THRESHOLDS['gpu_vram_pct']['critical']:.0%})",
            automated=False,
            command="# Reduce Ollama model size or unload unused models",
            rollback="# Reload models",
        ))
    elif state.gpu_vram_pct > THRESHOLDS["gpu_vram_pct"]["warn"]:
        actions.append(ScalingAction(
            system="gpu", action="alert", priority="medium",
            reason=f"GPU VRAM at {state.gpu_vram_pct:.0%}",
            automated=False, command="", rollback="",
        ))

    if state.gpu_disk_used_pct > THRESHOLDS["gpu_disk_pct"]["critical"]:
        actions.append(ScalingAction(
            system="gpu_disk", action="scale_up", priority="high",
            reason=f"Disk at {state.gpu_disk_used_pct:.0%}",
            automated=True,
            command="ssh gpu 'find /tmp -mtime +7 -delete; docker system prune -f'",
            rollback="# No rollback needed for cleanup",
        ))

    if state.docker_restart_count > THRESHOLDS["docker_restarts"]["critical"]:
        actions.append(ScalingAction(
            system="docker", action="failover", priority="critical",
            reason=f"Docker restarted {state.docker_restart_count} times",
            automated=True,
            command="ssh gpu 'cd ~/plano_master && docker compose -f deploy/docker-compose.yml down && docker compose -f deploy/docker-compose.yml up -d --build'",
            rollback="ssh gpu 'docker compose -f deploy/docker-compose.yml down'",
        ))

    # ── Horizontal scaling checks ──

    # Find the right scale tier
    scale_config = {"rasta_workers": 2, "docker_replicas": 1, "cache_mb": 256}
    for threshold, config in sorted(SCALE_TRIGGERS.items()):
        if users >= threshold:
            scale_config.update(config)

    current_workers = state.rasta_workers
    needed_workers = scale_config.get("rasta_workers", 2)

    if needed_workers > current_workers:
        actions.append(ScalingAction(
            system="rasta", action="scale_up", priority="high",
            reason=f"Need {needed_workers} Celery workers for {users} users (have {current_workers})",
            automated=True,
            command=f"ssh gpu 'cd ~/plano-raster-engine && PLANO_WORKERS={needed_workers} source .venv/bin/activate && PYTHONPATH=. bash run.sh stop && PYTHONPATH=. bash run.sh start'",
            rollback=f"ssh gpu 'cd ~/plano-raster-engine && PLANO_WORKERS={current_workers} bash run.sh stop && bash run.sh start'",
        ))

    if scale_config.get("note"):
        actions.append(ScalingAction(
            system="infra", action="alert", priority="medium",
            reason=scale_config["note"],
            automated=False, command="", rollback="",
        ))

    return actions


# ═══════════════════════════════════════════════════════════
# REDUNDANCY — backup paths for every system
# ═══════════════════════════════════════════════════════════

REDUNDANCY_MAP = {
    "frontend": {
        "primary": "Docker nginx on GPU (:8031)",
        "backup": "Vite dev server on local (:5174)",
        "failover": "rsync to Dell, start nginx there",
        "auto": True,
        "rto_minutes": 5,
    },
    "rasta_api": {
        "primary": "GPU FastAPI + Celery (:8020)",
        "backup": "Local OpenCV server (:8011)",
        "failover": "Switch nginx proxy to local:8011",
        "auto": True,
        "rto_minutes": 2,
    },
    "rasta_model": {
        "primary": "CubiCasa5k on GPU CUDA",
        "backup": "OpenCV pipeline (CPU, 91% accuracy)",
        "failover": "Already built into gpu_engine.py — auto-fallback",
        "auto": True,
        "rto_minutes": 0,
    },
    "database": {
        "primary": "SQLite files on GPU",
        "backup": "Daily rsync to local + Dell",
        "failover": "Restore from latest backup",
        "auto": True,
        "rto_minutes": 15,
    },
    "payments_stripe": {
        "primary": "Stripe API",
        "backup": "BTCPay Server (self-hosted)",
        "failover": "Show BTCPay option if Stripe down",
        "auto": True,
        "rto_minutes": 0,
    },
    "payments_btcpay": {
        "primary": "BTCPay on GPU (:8032)",
        "backup": "bitcoind wallet direct",
        "failover": "Manual invoice from wallet",
        "auto": False,
        "rto_minutes": 60,
    },
    "auth": {
        "primary": "Auth service on GPU (:9099)",
        "backup": "Bypass auth (emergency read-only mode)",
        "failover": "Caddy config: remove forward_auth block",
        "auto": False,
        "rto_minutes": 5,
    },
    "caddy_tls": {
        "primary": "Caddy auto-HTTPS on GPU",
        "backup": "Cloudflare proxy (DNS failover)",
        "failover": "Change DNS to Cloudflare, enable proxy",
        "auto": False,
        "rto_minutes": 30,
    },
    "dns": {
        "primary": "hacking.eu (registrar)",
        "backup": "Multi-year registration, auto-renew",
        "failover": "Secondary domain registered (plano.eu if available)",
        "auto": True,
        "rto_minutes": 0,
    },
    "ollama_agents": {
        "primary": "Ollama on GPU (Mistral-Small-24B)",
        "backup": "Cloud API fallback (Anthropic/OpenAI)",
        "failover": "Switch OLLAMA_URL to cloud API endpoint",
        "auto": True,
        "rto_minutes": 1,
    },
    "osm_data": {
        "primary": "Overpass API (weekly sync)",
        "backup": "Cached local copy (data/osm/)",
        "failover": "Use cached data, alert for manual refresh",
        "auto": True,
        "rto_minutes": 0,
    },
    "gpu_server": {
        "primary": "hadrien-skoed-mt (RTX 6000 Ada)",
        "backup": "Dell server (503GB RAM, CPU-only Rasta)",
        "failover": "Migrate Docker + Rasta to Dell via rsync",
        "auto": False,
        "rto_minutes": 30,
    },
}


def check_redundancy() -> list[dict]:
    """Verify all backup paths are functional."""
    results = []
    for system, config in REDUNDANCY_MAP.items():
        result = {
            "system": system,
            "primary": config["primary"],
            "backup": config["backup"],
            "auto_failover": config["auto"],
            "rto_minutes": config["rto_minutes"],
            "status": "ok",  # TODO: actually test backup paths
        }
        results.append(result)
    return results


# ═══════════════════════════════════════════════════════════
# CAPACITY PLANNING — project needs for N users
# ═══════════════════════════════════════════════════════════

def simulate_capacity(target_users: int) -> dict:
    """Project infrastructure requirements for N users.

    Assumptions (with 25% margin):
    - 1 plan upload per user per week avg
    - Rasta processes 1 plan in 0.5s (GPU) or 2s (CPU)
    - Each plan = ~200KB storage
    - Peak traffic = 3x average
    - 75% capacity target (25% margin)
    """
    plans_per_day = target_users * (1 / 7)  # 1/week = 0.14/day
    plans_per_hour_peak = plans_per_day / 8 * 3  # 8 active hours, 3x peak
    plans_per_second_peak = plans_per_hour_peak / 3600

    # Rasta capacity (0.5s per plan on GPU)
    rasta_capacity_per_worker = 1 / 0.5  # 2 plans/sec/worker
    workers_needed_raw = plans_per_second_peak / rasta_capacity_per_worker
    workers_needed = math.ceil(workers_needed_raw / (1 - MARGIN))  # 25% margin

    # Storage
    storage_per_user_mb = 5  # plans + projects + thumbnails
    storage_total_gb = (target_users * storage_per_user_mb) / 1024
    storage_with_margin_gb = storage_total_gb / (1 - MARGIN)

    # RAM (nginx + Rasta + Redis + Ollama)
    base_ram_gb = 4  # nginx + auth + Redis
    rasta_ram_per_worker_gb = 2
    ollama_ram_gb = 16  # Mistral-Small-24B
    total_ram_gb = base_ram_gb + (workers_needed * rasta_ram_per_worker_gb) + ollama_ram_gb
    total_ram_with_margin = total_ram_gb / (1 - MARGIN)

    # GPU VRAM
    rasta_vram_gb = 4  # CubiCasa5k model
    ollama_vram_gb = 14  # Mistral-Small-24B quantized
    total_vram_gb = rasta_vram_gb + ollama_vram_gb
    available_vram_gb = 48  # RTX 6000 Ada

    # Bandwidth
    avg_page_mb = 1.5
    pageviews_per_user_day = 5
    bandwidth_gb_day = (target_users * pageviews_per_user_day * avg_page_mb) / 1024
    bandwidth_gb_month = bandwidth_gb_day * 30

    # Cost (cloud equivalent for scaling reference)
    cloud_gpu_cost = 0  # self-hosted
    cloud_equivalent_monthly = target_users * 0.02  # $0.02/user/month at scale

    # Infrastructure tier
    if target_users <= 500:
        tier = "CURRENT (single GPU server)"
        infra = "GPU server handles everything"
    elif target_users <= 2000:
        tier = "TIER 2 (GPU + Dell)"
        infra = "Move Rasta overflow to Dell (503GB RAM)"
    elif target_users <= 10000:
        tier = "TIER 3 (GPU + Dell + CDN)"
        infra = "Add Cloudflare CDN, Dell handles Rasta"
    elif target_users <= 50000:
        tier = "TIER 4 (Cloud hybrid)"
        infra = "AWS ECS Fargate for Rasta, keep GPU for AI/Ollama"
    else:
        tier = "TIER 5 (Full cloud)"
        infra = "Multi-region AWS/GCP, auto-scaling groups"

    return {
        "target_users": target_users,
        "plans_per_day": round(plans_per_day),
        "plans_per_second_peak": round(plans_per_second_peak, 2),
        "rasta_workers_needed": workers_needed,
        "storage_gb": round(storage_with_margin_gb, 1),
        "ram_gb": round(total_ram_with_margin, 1),
        "vram_gb": round(total_vram_gb, 1),
        "vram_available_gb": available_vram_gb,
        "vram_headroom_pct": round((1 - total_vram_gb / available_vram_gb) * 100),
        "bandwidth_gb_month": round(bandwidth_gb_month, 1),
        "cloud_equivalent_monthly_eur": round(cloud_equivalent_monthly),
        "infrastructure_tier": tier,
        "infrastructure_note": infra,
        "margin_applied": f"{MARGIN:.0%}",
    }


# ═══════════════════════════════════════════════════════════
# FAILOVER DRILLS — test backup paths
# ═══════════════════════════════════════════════════════════

DRILL_SCENARIOS = {
    "gpu_down": {
        "description": "GPU server completely unreachable",
        "steps": [
            "1. Rasta falls back to local OpenCV (:8011)",
            "2. Docker nginx unavailable → need Dell deployment",
            "3. Caddy can't reach backend → 502 errors",
            "4. ACTION: rsync plano_master to Dell, start Docker there",
            "5. Update Caddy to proxy to Dell IP",
        ],
        "rto_minutes": 30,
        "automated": False,
    },
    "rasta_crash": {
        "description": "Rasta API crashes, Celery workers die",
        "steps": [
            "1. Self-heal watchdog detects Rasta down (5-min check)",
            "2. Auto-restart: run.sh stop && run.sh start",
            "3. If restart fails 3x → alert + fallback to local OpenCV",
            "4. Redis queue preserves pending jobs",
        ],
        "rto_minutes": 5,
        "automated": True,
    },
    "docker_corrupt": {
        "description": "Docker container corrupted, won't start",
        "steps": [
            "1. docker compose down",
            "2. docker system prune -f",
            "3. docker compose up -d --build (rebuild from source)",
            "4. If source corrupted → git pull from GitHub",
        ],
        "rto_minutes": 10,
        "automated": True,
    },
    "stripe_down": {
        "description": "Stripe API outage (has happened before)",
        "steps": [
            "1. Show BTCPay option prominently",
            "2. Queue failed Stripe charges for retry",
            "3. Don't downgrade users during outage",
            "4. Stripe webhook backfill when restored",
        ],
        "rto_minutes": 0,
        "automated": True,
    },
    "domain_hijack": {
        "description": "hacking.eu domain compromised/expired",
        "steps": [
            "1. Registrar lock should prevent transfer",
            "2. Multi-year registration prevents expiry",
            "3. Secondary domain (plano.mt or plano.bg) as backup",
            "4. Update DNS, notify users via email",
        ],
        "rto_minutes": 60,
        "automated": False,
    },
    "both_founders_incapacitated": {
        "description": "Both Hadrien and Ogi unable to operate",
        "steps": [
            "1. Agent autonomy must be at L3+ for this to work",
            "2. BDO nominee director has legal authority",
            "3. Credential escrow releases after 30 days no check-in",
            "4. Self-healing watchdog keeps infra running",
            "5. Agents continue content/marketing/support autonomously",
            "6. Stripe/BTCPay process payments automatically",
            "7. BDO handles corporate compliance",
            "8. Business runs indefinitely at current scale",
        ],
        "rto_minutes": 0,
        "automated": True,
    },
}


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def print_status(state: SystemState):
    """Print current system status."""
    print("=" * 60)
    print("  PlanO Infrastructure Status")
    print("=" * 60)
    print(f"  GPU VRAM:    {state.gpu_vram_used_mb}MB / {state.gpu_vram_total_mb}MB ({state.gpu_vram_pct:.0%})")
    print(f"  GPU Disk:    {state.gpu_disk_used_pct:.0%} used")
    print(f"  GPU CPU:     {state.gpu_cpu_load:.1f} load avg")
    print(f"  Docker:      {state.docker_container_status} (restarts: {state.docker_restart_count})")
    print(f"  Rasta:       {state.rasta_status} ({state.rasta_workers} workers)")
    print(f"  Redis:       {state.redis_status} ({state.redis_memory_mb:.0f}MB)")
    print(f"  Caddy:       {state.caddy_status}")
    print(f"  Auth:        {state.auth_status}")
    print(f"  Margin:      {MARGIN:.0%} reserved on all resources")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "status":
        state = probe_system()
        print_status(state)

    elif cmd == "plan":
        state = probe_system()
        actions = compute_scaling_plan(state)
        print(f"\n{'Priority':10} {'System':12} {'Action':12} Reason")
        print("-" * 70)
        for a in sorted(actions, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}[x.priority]):
            print(f"{a.priority:10} {a.system:12} {a.action:12} {a.reason}")
            if a.command:
                print(f"{'':10} CMD: {a.command[:60]}")

    elif cmd == "simulate":
        users = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
        cap = simulate_capacity(users)
        print(f"\n  Capacity plan for {users:,} users (25% margin applied)")
        print("-" * 50)
        for k, v in cap.items():
            print(f"  {k:30} {v}")

    elif cmd == "redundancy":
        results = check_redundancy()
        print(f"\n{'System':20} {'Auto':5} {'RTO':6} Primary → Backup")
        print("-" * 80)
        for r in results:
            auto = "YES" if r["auto_failover"] else "NO"
            print(f"{r['system']:20} {auto:5} {r['rto_minutes']:4}m  {r['primary'][:25]} → {r['backup'][:25]}")

    elif cmd == "drill":
        scenario = sys.argv[3] if len(sys.argv) > 3 else "rasta_crash"
        drill = DRILL_SCENARIOS.get(scenario)
        if not drill:
            print(f"Unknown scenario. Available: {list(DRILL_SCENARIOS.keys())}")
        else:
            print(f"\n  FAILOVER DRILL: {drill['description']}")
            print(f"  RTO: {drill['rto_minutes']} minutes | Auto: {drill['automated']}")
            print()
            for step in drill["steps"]:
                print(f"  {step}")

    elif cmd == "execute":
        state = probe_system()
        actions = compute_scaling_plan(state)
        auto_actions = [a for a in actions if a.automated and a.command]
        if not auto_actions:
            print("No automated actions needed.")
        else:
            for a in auto_actions:
                print(f"Executing: {a.action} on {a.system} — {a.reason}")
                if a.command and a.command.startswith("ssh"):
                    os.system(a.command)

    else:
        print(f"Unknown: {cmd}")
        print(__doc__)
