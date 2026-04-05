#!/usr/bin/env bash
# PlanO — Run all tests (TypeScript, lint, accessibility, broken links)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
log() { echo -e "${GREEN}[test]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; FAILURES=$((FAILURES + 1)); }
FAILURES=0

log "Running PlanO test suite..."
echo ""

# 1. TypeScript
log "1. TypeScript type check..."
cd "$REPO_ROOT/00_frontend_skeleton/plano-ui"
if npx tsc --noEmit 2>&1; then
    log "   TypeScript ✓"
else
    fail "   TypeScript errors found"
fi

# 2. Vite build test
log "2. Vite production build..."
if npm run build -- --logLevel error 2>&1 | tail -3; then
    log "   Build ✓"
else
    fail "   Build failed"
fi

# 3. Accessibility (if pa11y installed and server running)
if command -v pa11y &>/dev/null; then
    log "3. Accessibility audit (pa11y)..."
    TARGET="${PLANO_TEST_URL:-http://localhost:5174}"
    if curl -s "$TARGET" > /dev/null 2>&1; then
        ISSUES=$(pa11y "$TARGET" 2>&1 | grep -c "Error:" || true)
        if [ "$ISSUES" -eq 0 ]; then
            log "   Accessibility ✓ (0 issues)"
        else
            fail "   Accessibility: $ISSUES issues found"
        fi
    else
        log "   Skipped (server not running at $TARGET)"
    fi
else
    log "3. Accessibility: skipped (install: npm i -g pa11y)"
fi

# 4. Broken links (if blc installed and server running)
if command -v blc &>/dev/null; then
    log "4. Broken link check..."
    TARGET="${PLANO_TEST_URL:-http://localhost:5174}"
    if curl -s "$TARGET" > /dev/null 2>&1; then
        BROKEN=$(blc "$TARGET" --exclude-external -o 2>&1 | grep -c "BROKEN" || true)
        if [ "$BROKEN" -eq 0 ]; then
            log "   Links ✓ (0 broken)"
        else
            fail "   $BROKEN broken links found"
        fi
    else
        log "   Skipped (server not running)"
    fi
else
    log "4. Broken links: skipped (install: npm i -g broken-link-checker)"
fi

echo ""
if [ $FAILURES -eq 0 ]; then
    log "All tests passed!"
else
    fail "$FAILURES test(s) failed"
    exit 1
fi
