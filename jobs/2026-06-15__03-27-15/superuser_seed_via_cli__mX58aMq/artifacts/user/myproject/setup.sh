#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PB="${SCRIPT_DIR}/pocketbase"
PB_DATA_DIR="${SCRIPT_DIR}/pb_data"
HEALTH_URL="http://127.0.0.1:8090/api/health"
API_BASE="http://127.0.0.1:8090/api"
SUPERUSER_EMAIL="admin@example.com"
SUPERUSER_PASSWORD='Adm1n_passw0rd!'

# -------------------------------------------------------------------
# 1. Create / upsert the superuser (idempotent by design)
# -------------------------------------------------------------------
echo "==> Creating / upserting superuser..."
"$PB" superuser upsert "$SUPERUSER_EMAIL" "$SUPERUSER_PASSWORD" --dir "$PB_DATA_DIR"

# -------------------------------------------------------------------
# 2. Run pending migrations (idempotent – already-applied ones are skipped)
# -------------------------------------------------------------------
echo "==> Running migrations..."
"$PB" migrate up --dir "$PB_DATA_DIR" --migrationsDir "${SCRIPT_DIR}/pb_migrations"

# -------------------------------------------------------------------
# 3. Ensure the PocketBase server is running
# -------------------------------------------------------------------
ensure_server_running() {
  # Check if the server is already healthy
  if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
    echo "==> PocketBase server is already running."
    return 0
  fi

  # Kill any stale process on port 8090
  local pid
  pid="$(lsof -ti :8090 2>/dev/null || true)"
  if [ -n "$pid" ]; then
    echo "==> Killing stale process on port 8090 (pid: $pid)..."
    kill -9 $pid 2>/dev/null || true
    sleep 1
  fi

  echo "==> Starting PocketBase server..."
  "$PB" serve --dir "$PB_DATA_DIR" --http 127.0.0.1:8090 &
  local server_pid=$!

  # Wait for the server to become healthy (up to 30 seconds)
  echo "==> Waiting for server to become healthy..."
  local attempts=0
  while [ $attempts -lt 30 ]; do
    if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
      echo "==> PocketBase server is healthy (pid: $server_pid)."
      return 0
    fi
    attempts=$((attempts + 1))
    sleep 1
  done

  echo "ERROR: PocketBase server did not become healthy within 30 seconds." >&2
  return 1
}

ensure_server_running

# -------------------------------------------------------------------
# 4. Authenticate as superuser to obtain a token
# -------------------------------------------------------------------
echo "==> Authenticating as superuser..."
AUTH_RESPONSE="$(curl -sf -X POST \
  "${API_BASE}/collections/_superusers/auth-with-password" \
  -H 'Content-Type: application/json' \
  -d "{\"identity\":\"${SUPERUSER_EMAIL}\",\"password\":\"${SUPERUSER_PASSWORD}\"}")"

TOKEN="$(echo "$AUTH_RESPONSE" | grep -o '"token":"[^"]*"' | head -1 | cut -d'"' -f4)"

if [ -z "$TOKEN" ]; then
  echo "ERROR: Failed to authenticate as superuser." >&2
  echo "Response: $AUTH_RESPONSE" >&2
  exit 1
fi

AUTH_HEADER="Authorization: Bearer ${TOKEN}"

# -------------------------------------------------------------------
# 5. Seed the tasks collection (idempotent – skip existing titles)
# -------------------------------------------------------------------
SEED_TITLES=("Buy groceries" "Walk the dog" "Read a book" "Write weekly report" "Call mom")

echo "==> Seeding tasks..."

# Fetch existing task titles
EXISTING_RESPONSE="$(curl -sf \
  -H "$AUTH_HEADER" \
  "${API_BASE}/collections/tasks/records?perPage=200")"

# Extract existing titles from the response using a simple approach
# The JSON response has items in an "items" array, each with a "title" field
EXISTING_TITLES=""
if [ -n "$EXISTING_RESPONSE" ]; then
  # Use python or a simple parser to extract titles
  EXISTING_TITLES="$(echo "$EXISTING_RESPONSE" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for item in data.get('items', []):
    print(item.get('title', ''))
" 2>/dev/null || echo "")"
fi

for title in "${SEED_TITLES[@]}"; do
  # Check if this title already exists
  if echo "$EXISTING_TITLES" | grep -qF "$title"; then
    echo "    Task '${title}' already exists, skipping."
    continue
  fi

  echo "    Creating task: ${title}"
  HTTP_CODE="$(curl -s -o /dev/null -w '%{http_code}' -X POST \
    "${API_BASE}/collections/tasks/records" \
    -H 'Content-Type: application/json' \
    -H "$AUTH_HEADER" \
    -d "{\"title\":\"${title}\",\"done\":false}")"

  if [ "$HTTP_CODE" -ne 200 ] && [ "$HTTP_CODE" -ne 204 ]; then
    echo "WARNING: Creating task '${title}' returned HTTP ${HTTP_CODE}"
  fi
done

echo "==> Setup complete!"
exit 0