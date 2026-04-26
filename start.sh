#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# ── Colours ───────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; NC='\033[0m'

log() { echo -e "${CYAN}[filmnerd]${NC} $1"; }
ok()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn(){ echo -e "${YELLOW}[!]${NC} $1"; }
die() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# ── Cleanup on exit ───────────────────────────────────────────────
cleanup() {
  log "Shutting down..."
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
  wait 2>/dev/null
  log "Done."
}
trap cleanup EXIT INT TERM

# ── 1. Qdrant ─────────────────────────────────────────────────────
log "Checking Qdrant..."
if ! curl -sf http://localhost:6333/health &>/dev/null; then
  if command -v docker &>/dev/null; then
    log "Starting Qdrant via Docker..."
    docker run -d -p 6333:6333 -p 6334:6334 \
      -v qdrant_filmnerd_storage:/qdrant/storage \
      --name qdrant-filmnerd \
      qdrant/qdrant:latest 2>/dev/null || \
      docker start qdrant-filmnerd 2>/dev/null || \
      warn "Could not start Qdrant container — chat will not work"
    for i in $(seq 1 20); do
      curl -sf http://localhost:6333/health &>/dev/null && break
      sleep 0.5
    done
    ok "Qdrant ready"
  else
    warn "Docker not found and Qdrant not running — chat will not work"
  fi
else
  ok "Qdrant already running"
fi

# ── 2. Python deps ───────────────────────────────────────────────
log "Checking Python dependencies..."
if ! command -v uv &>/dev/null; then
  warn "uv not found — falling back to pip"
  pip install fastapi "uvicorn[standard]" httpx -q
else
  uv sync --quiet 2>/dev/null || uv pip install -e . -q
fi
ok "Python deps ready"

# ── 3. Node deps ──────────────────────────────────────────────────
log "Checking Node dependencies..."
UI_DIR="$ROOT/filmnerd-ui"
if [ ! -d "$UI_DIR/node_modules" ]; then
  log "Installing node_modules (first run)..."
  cd "$UI_DIR"
  if command -v pnpm &>/dev/null; then
    pnpm install --silent
  elif command -v npm &>/dev/null; then
    npm install --silent
  else
    die "Neither pnpm nor npm found. Install one and retry."
  fi
  cd "$ROOT"
fi
ok "Node deps ready"

# ── 4. Start FastAPI backend ──────────────────────────────────────
log "Starting FastAPI backend on :8000..."
source .venv/bin/activate 2>/dev/null || true
uvicorn src.api.main:app --port 8000 --reload &
BACKEND_PID=$!
ok "Backend started (PID $BACKEND_PID)"

# Wait for backend to be ready
log "Waiting for backend..."
for i in $(seq 1 20); do
  if curl -sf http://localhost:8000/health &>/dev/null; then
    ok "Backend is up"
    break
  fi
  sleep 0.5
done

# ── 5. Start Next.js frontend ─────────────────────────────────────
log "Starting Next.js frontend on :3000..."
cd "$UI_DIR"
if command -v pnpm &>/dev/null; then
  pnpm dev &
else
  npm run dev &
fi
FRONTEND_PID=$!
cd "$ROOT"
ok "Frontend started (PID $FRONTEND_PID)"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  filmnerd is running${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  UI:      ${CYAN}http://localhost:3000${NC}"
echo -e "  API:     ${CYAN}http://localhost:8000${NC}"
echo -e "  Health:  ${CYAN}http://localhost:8000/health${NC}"
echo ""
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop both servers."
echo ""

# Wait for either process to exit
wait
