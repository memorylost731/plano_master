#!/usr/bin/env bash
# PlanO — Full setup script
# Downloads and installs all dependencies for development and production
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log() { echo -e "${GREEN}[plano]${NC} $1"; }
warn() { echo -e "${YELLOW}[plano]${NC} $1"; }
err() { echo -e "${RED}[plano]${NC} $1"; }

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# ── System dependencies ──────────────────────────────────────────

log "Checking system dependencies..."

install_if_missing() {
    if ! command -v "$1" &>/dev/null; then
        warn "$1 not found — installing..."
        if command -v apt-get &>/dev/null; then
            sudo apt-get update -qq && sudo apt-get install -y -qq "$2"
        elif command -v brew &>/dev/null; then
            brew install "$2"
        else
            err "Cannot install $1 — install manually"
            return 1
        fi
        log "$1 installed"
    else
        log "$1 ✓"
    fi
}

# Node.js (v20+)
if ! command -v node &>/dev/null || [ "$(node -v | cut -d. -f1 | tr -d v)" -lt 20 ]; then
    warn "Node.js 20+ required. Installing via nvm..."
    if ! command -v nvm &>/dev/null; then
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    fi
    nvm install 24 && nvm use 24
else
    log "Node.js $(node -v) ✓"
fi

# Python 3.10+
if ! command -v python3 &>/dev/null; then
    install_if_missing python3 python3
fi
log "Python $(python3 --version | cut -d' ' -f2) ✓"

# Docker
if command -v docker &>/dev/null; then
    log "Docker $(docker --version | grep -oP '\d+\.\d+\.\d+') ✓"
else
    warn "Docker not installed — production deployment requires Docker"
    warn "Install: https://docs.docker.com/engine/install/"
fi

# Redis (optional, for Rasta async mode)
if command -v redis-cli &>/dev/null; then
    log "Redis ✓"
else
    warn "Redis not installed — Rasta will run in sync mode"
    warn "Install: sudo apt install redis-server"
fi

# ── Frontend: plano-ui ───────────────────────────────────────────

log "Installing plano-ui dependencies..."
cd "$REPO_ROOT/00_frontend_skeleton/plano-ui"
npm ci --ignore-scripts
log "plano-ui dependencies installed ($(ls node_modules | wc -l) packages)"

# ── Frontend: react-planner engine ───────────────────────────────

log "Installing react-planner dependencies..."
cd "$REPO_ROOT/02_react_planner/react-planner"
npm ci --ignore-scripts
log "react-planner dependencies installed"

# ── Backend: Rasta (Python) ──────────────────────────────────────

log "Setting up Rasta Python environment..."
cd "$REPO_ROOT/01_raster"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    log "Created Python virtualenv"
fi
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q fastapi uvicorn python-multipart opencv-python-headless Pillow numpy
log "Rasta Python dependencies installed"
deactivate

# ── Verify ───────────────────────────────────────────────────────

log ""
log "Setup complete! Quick start:"
log ""
log "  Development (3 terminals):"
log "    Terminal 1: cd 00_frontend_skeleton/plano-ui && npm run dev"
log "    Terminal 2: cd 02_react_planner/react-planner && npm run start-demo"
log "    Terminal 3: cd 01_raster && source .venv/bin/activate && uvicorn server.app_local:app --port 8011"
log ""
log "  Production (Docker):"
log "    docker compose -f deploy/docker-compose.yml up -d --build"
log ""
log "  URLs:"
log "    plano-ui:   http://localhost:5174"
log "    engine:     http://localhost:5173"
log "    rasta API:  http://localhost:8011"
log "    production: http://localhost:8031"
