#!/usr/bin/env bash
# PlanO — Start all development services
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GREEN='\033[0;32m'; NC='\033[0m'
log() { echo -e "${GREEN}[plano]${NC} $1"; }

cleanup() {
    log "Stopping all services..."
    kill $UI_PID $ENGINE_PID $RASTA_PID 2>/dev/null || true
    wait 2>/dev/null
    log "All stopped."
}
trap cleanup EXIT

# Start Rasta backend
log "Starting Rasta API on :8011..."
cd "$REPO_ROOT/01_raster"
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi
PYTHONPATH="$REPO_ROOT/01_raster" uvicorn server.app_local:app --host 0.0.0.0 --port 8011 &
RASTA_PID=$!

# Start react-planner engine
log "Starting React Planner engine on :5173..."
cd "$REPO_ROOT/02_react_planner/react-planner"
npx webpack-dev-server --config demo/webpack.config.js --port 5173 --host 0.0.0.0 &
ENGINE_PID=$!

# Start plano-ui
log "Starting PlanO UI on :5174..."
cd "$REPO_ROOT/00_frontend_skeleton/plano-ui"
npx vite --host --port 5174 &
UI_PID=$!

log ""
log "All services started:"
log "  PlanO UI:      http://localhost:5174"
log "  Planner Engine: http://localhost:5173"
log "  Rasta API:     http://localhost:8011/health"
log ""
log "Press Ctrl+C to stop all services"

wait
