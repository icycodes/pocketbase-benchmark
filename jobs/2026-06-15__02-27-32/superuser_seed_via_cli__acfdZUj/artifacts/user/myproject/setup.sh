#!/usr/bin/env bash
# setup.sh — Idempotent PocketBase v0.31.0 bootstrap
# Creates superuser, applies migrations, starts server, seeds task records.
# Safe to run multiple times: will not create duplicates and exits with 0.
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PB_BIN="$SCRIPT_DIR/pocketbase"
PB_DATA="$SCRIPT_DIR/pb_data"
PB_MIGRATIONS_DIR="$SCRIPT_DIR/pb_migrations"
PB_HOST="127.0.0.1:8090"
PB_URL="http://$PB_HOST"
PB_PID_FILE="$SCRIPT_DIR/pocketbase.pid"

ADMIN_EMAIL="admin@example.com"
ADMIN_PASS="Adm1n_passw0rd!"

TASKS=(
  "Buy groceries"
  "Walk the dog"
  "Read a book"
  "Write weekly report"
  "Call mom"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log()  { echo "[setup] $*"; }
die()  { echo "[setup] ERROR: $*" >&2; exit 1; }

# URL-encode a string using Python (available in the environment)
urlencode() {
  python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=''))" "$1"
}

# ---------------------------------------------------------------------------
# Step 1 — Stop any pre-existing PocketBase instance on port 8090
# ---------------------------------------------------------------------------
log "Checking for a running PocketBase instance..."

# Kill by saved PID file first (clean shutdown)
if [[ -f "$PB_PID_FILE" ]]; then
  OLD_PID=$(cat "$PB_PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    log "Stopping existing PocketBase process (PID $OLD_PID)..."
    kill "$OLD_PID" || true
    sleep 2
  fi
  rm -f "$PB_PID_FILE"
fi

# Force-kill anything else still holding port 8090
if ss -tlnp 2>/dev/null | grep -q ":8090 "; then
  log "Port 8090 still in use – force-killing occupying process..."
  fuser -k 8090/tcp 2>/dev/null || true
  sleep 1
fi

# ---------------------------------------------------------------------------
# Step 2 — Upsert the superuser (idempotent: create-or-update)
# ---------------------------------------------------------------------------
log "Upserting superuser '$ADMIN_EMAIL'..."
"$PB_BIN" --dir="$PB_DATA" \
           --migrationsDir="$PB_MIGRATIONS_DIR" \
           superuser upsert "$ADMIN_EMAIL" "$ADMIN_PASS"

# ---------------------------------------------------------------------------
# Step 3 — Start PocketBase in the background
#           --automigrate (default true) applies pb_migrations automatically.
# ---------------------------------------------------------------------------
log "Starting PocketBase server in the background..."
"$PB_BIN" serve \
  --http="$PB_HOST" \
  --dir="$PB_DATA" \
  --migrationsDir="$PB_MIGRATIONS_DIR" \
  --automigrate \
  >> "$SCRIPT_DIR/pocketbase.log" 2>&1 &

PB_PID=$!
echo "$PB_PID" > "$PB_PID_FILE"
log "PocketBase started (PID $PB_PID), log: $SCRIPT_DIR/pocketbase.log"

# ---------------------------------------------------------------------------
# Step 4 — Wait until the health endpoint returns HTTP 200
# ---------------------------------------------------------------------------
log "Waiting for PocketBase to become ready..."
for i in $(seq 1 30); do
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$PB_URL/api/health" 2>/dev/null || true)
  if [[ "$HTTP_STATUS" == "200" ]]; then
    log "Server is ready (attempt $i)."
    break
  fi
  if [[ "$i" -eq 30 ]]; then
    die "Server did not become ready within 30 seconds. Check pocketbase.log."
  fi
  sleep 1
done

# ---------------------------------------------------------------------------
# Step 5 — Authenticate as the superuser and obtain a bearer token
# ---------------------------------------------------------------------------
log "Authenticating as superuser..."
AUTH_RESPONSE=$(curl -sf -X POST "$PB_URL/api/collections/_superusers/auth-with-password" \
  -H "Content-Type: application/json" \
  -d "{\"identity\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASS\"}")

TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.token')
if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
  die "Failed to obtain auth token. Response: $AUTH_RESPONSE"
fi
log "Authentication successful."

# ---------------------------------------------------------------------------
# Step 6 — Seed task records (idempotent: skip if title already exists)
# ---------------------------------------------------------------------------
log "Seeding task records..."
for TITLE in "${TASKS[@]}"; do
  ENCODED_TITLE=$(urlencode "$TITLE")
  FILTER="title='$(echo "$TITLE" | sed "s/'/\\\\'/g")'"
  ENCODED_FILTER=$(urlencode "$FILTER")

  EXISTING=$(curl -sf \
    -H "Authorization: $TOKEN" \
    "$PB_URL/api/collections/tasks/records?filter=$ENCODED_FILTER&perPage=1" \
    | jq -r '.totalItems')

  if [[ "$EXISTING" -gt 0 ]]; then
    log "  SKIP  '$TITLE' (already exists)"
  else
    curl -sf -X POST "$PB_URL/api/collections/tasks/records" \
      -H "Content-Type: application/json" \
      -H "Authorization: $TOKEN" \
      -d "$(jq -n --arg t "$TITLE" '{title: $t}')" \
      > /dev/null
    log "  CREATED '$TITLE'"
  fi
done

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
log "Setup complete. PocketBase is running on $PB_URL"
log "  Health : $PB_URL/api/health"
log "  Admin  : $PB_URL/_/"
