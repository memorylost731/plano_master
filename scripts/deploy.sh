#!/usr/bin/env bash
# PlanO — Deploy to production (Docker on GPU server)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log() { echo -e "${GREEN}[deploy]${NC} $1"; }
warn() { echo -e "${YELLOW}[deploy]${NC} $1"; }

GPU_HOST="${PLANO_GPU_HOST:-gpu}"

log "Deploying PlanO to production ($GPU_HOST)..."

# 1. TypeScript check
log "Running TypeScript check..."
cd "$REPO_ROOT/00_frontend_skeleton/plano-ui"
npx tsc --noEmit || { warn "TypeScript errors — fix before deploying"; exit 1; }
log "TypeScript ✓"

# 2. Sync to GPU
log "Syncing to $GPU_HOST..."
rsync -az \
    --exclude node_modules \
    --exclude .git \
    --exclude dist \
    --exclude '01_raster/models' \
    --exclude '*.db' \
    "$REPO_ROOT/" "$GPU_HOST:~/plano_master/"
log "Sync complete"

# 3. Docker build & deploy
log "Building Docker image on $GPU_HOST..."
ssh "$GPU_HOST" "cd ~/plano_master && docker compose -f deploy/docker-compose.yml up -d --build"
log "Docker deployed"

# 4. Health check
log "Checking health..."
sleep 3
STATUS=$(ssh "$GPU_HOST" "curl -s -o /dev/null -w '%{http_code}' http://localhost:8031/plano/")
if [ "$STATUS" = "200" ]; then
    log "Health check passed (HTTP $STATUS)"
else
    warn "Health check returned HTTP $STATUS"
fi

log ""
log "Deployment complete!"
log "  Production: https://hacking.eu/plano/"
log "  Docker:     ssh $GPU_HOST 'docker logs plano-app --tail 20'"
