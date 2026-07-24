#!/usr/bin/env bash
#
# Boots Kya Khaoon for local dev — everything in containers.
#
#   ./run.sh
#
# Starts Postgres, the backend on :8000 and the frontend on :5173 via docker
# compose (fake Swiggy + console OTP by default — no real accounts touched).
# Source is bind-mounted, so edits reload in place. Ctrl+C stops everything.
#
# The only thing that stays on the host is the optional ngrok tunnel: testing
# Google Sign-In on a phone needs an HTTPS origin, which a LAN IP can't be.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if ! docker info >/dev/null 2>&1; then
  echo "!  Docker isn't running. Start Docker Desktop and try again."
  exit 1
fi

# Config lives in the single root .env — the backend and Vite both read it.
if [[ ! -f "$ROOT/.env" ]]; then
  echo "!  No .env at repo root. Copy it: cp .env.example .env  (then add keys)"
  exit 1
fi

NGROK_PID=""
cleanup() {
  echo ""
  echo "→ stopping…"
  [[ -n "$NGROK_PID" ]] && kill "$NGROK_PID" 2>/dev/null || true
  docker compose down
}
trap cleanup INT TERM EXIT

# ── ngrok tunnel (optional) ──────────────────────────────────────────────────
# If NGROK_DOMAIN is set in .env and ngrok is installed, expose :5173 on that
# stable domain. Skipped silently otherwise (localhost-only dev).
NGROK_DOMAIN="$(grep -E '^NGROK_DOMAIN=' "$ROOT/.env" | head -1 | cut -d= -f2- | tr -d '[:space:]')"
NGROK_URL=""
if [[ -n "$NGROK_DOMAIN" ]] && command -v ngrok >/dev/null 2>&1; then
  NGROK_URL="https://$NGROK_DOMAIN"
  echo "→ tunnel   → $NGROK_URL  (phone / Google Sign-In)"
  ngrok http 5173 --url="$NGROK_URL" --log=stdout >/tmp/kya-ngrok.log 2>&1 &
  NGROK_PID=$!
elif [[ -n "$NGROK_DOMAIN" ]]; then
  echo "!  NGROK_DOMAIN set but ngrok not installed — skipping tunnel."
fi

echo "→ backend  → http://localhost:8000  (docs: /docs)"
echo "→ frontend → http://localhost:5173"
echo "   (first run builds the images — that takes a minute)"
echo ""
echo "Open http://localhost:5173${NGROK_URL:+  ·  $NGROK_URL}  ·  Ctrl+C to stop."
echo "(OTP codes print in the backend logs — SMS_PROVIDER=console.)"
echo ""

# Migrations run in the backend container's entrypoint, once Postgres is healthy.
docker compose up --build
