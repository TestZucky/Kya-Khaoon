#!/usr/bin/env bash
#
# Boots the Kya Khaoon backend + frontend together for local dev.
#
#   ./run.sh
#
# Backend runs on :8000 (SQLite + fake Swiggy + console OTP — no real accounts
# touched). Frontend runs on :5173. Ctrl+C stops both.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

# Config lives in the single root .env — the backend and Vite both read it.
if [[ ! -f "$ROOT/.env" ]]; then
  echo "!  No .env at repo root. Copy it: cp .env.example .env  (then add keys)"
  exit 1
fi

PIDS=()
cleanup() {
  echo ""
  echo "→ stopping…"
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

# Free a TCP port, killing whatever holds it (uvicorn --reload has a parent +
# worker, so kill by name too), then wait until it's actually released.
free_port() {
  local port="$1"
  lsof -ti tcp:"$port" | xargs kill -9 2>/dev/null || true
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    lsof -ti tcp:"$port" >/dev/null 2>&1 || return 0
    sleep 0.3
    lsof -ti tcp:"$port" | xargs kill -9 2>/dev/null || true
  done
}

# ── Backend ─────────────────────────────────────────────────────────────────
if [[ ! -d "$BACKEND/.venv" ]]; then
  echo "!  backend/.venv not found. Create it first:"
  echo "     cd backend && python -m venv .venv && ./.venv/bin/pip install -r requirements.txt"
  exit 1
fi

cd "$BACKEND"

# Bring the schema up to date (creates the database on first run). No seeding:
# the dish catalogue starts empty and fills with whatever the LLM generates, so
# nothing hand-written ever shows up in a deck. `make seed` still exists if you
# want the offline rules fallback to have something to work with.
echo "→ migrating database…"
if ! ./.venv/bin/alembic upgrade head >/dev/null 2>&1; then
  echo "  ! migration failed — run 'make migrate' to see why"
fi

# Free the port if a previous run (or a stray uvicorn --reload) left something.
pkill -f "uvicorn app.main:app" 2>/dev/null || true
free_port 8000

echo "→ backend  → http://localhost:8000  (docs: /docs)"
./.venv/bin/uvicorn app.main:app --reload --port 8000 &
PIDS+=($!)

# ── Frontend ────────────────────────────────────────────────────────────────
if [[ ! -d "$FRONTEND/node_modules" ]]; then
  echo "→ installing frontend deps (first run)…"
  (cd "$FRONTEND" && npm install)
fi

free_port 5173

echo "→ frontend → http://localhost:5173"
(cd "$FRONTEND" && npm run dev) &
PIDS+=($!)

# ── ngrok tunnel (optional) ──────────────────────────────────────────────────
# For testing on a phone: Google Sign-In needs an HTTPS origin, which a LAN IP
# can't be. If NGROK_DOMAIN is set in .env and ngrok is installed, expose :5173
# on that stable domain too. Skipped silently otherwise (localhost-only dev).
NGROK_DOMAIN="$(grep -E '^NGROK_DOMAIN=' "$ROOT/.env" | head -1 | cut -d= -f2- | tr -d '[:space:]')"
NGROK_URL=""
if [[ -n "$NGROK_DOMAIN" ]] && command -v ngrok >/dev/null 2>&1; then
  NGROK_URL="https://$NGROK_DOMAIN"
  echo "→ tunnel   → $NGROK_URL  (phone / Google Sign-In)"
  ngrok http 5173 --url="$NGROK_URL" --log=stdout >/tmp/kya-ngrok.log 2>&1 &
  PIDS+=($!)
elif [[ -n "$NGROK_DOMAIN" ]]; then
  echo "!  NGROK_DOMAIN set but ngrok not installed — skipping tunnel."
fi

echo ""
echo "Running. Open http://localhost:5173${NGROK_URL:+  ·  $NGROK_URL}  ·  Ctrl+C to stop."
echo "(OTP codes print here — SMS_PROVIDER=console — and auto-fill in the app.)"
wait
