#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# setup.sh - Idempotent PocketBase v0.31.0 setup
# ============================================================
# Creates a superuser, applies migrations, starts the server,
# and seeds 5 task records via the REST API.
# Running multiple times is safe: no duplicates, no errors.
# ============================================================

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PB_BIN="${PROJECT_DIR}/pocketbase"
PB_DATA_DIR="${PROJECT_DIR}/pb_data"
PB_MIGRATIONS_DIR="${PROJECT_DIR}/pb_migrations"
PB_URL="http://127.0.0.1:8090"
SUPERUSER_EMAIL="admin@example.com"
SUPERUSER_PASS="Adm1n_passw0rd!"

# Task records to seed (one per line, exact title)
TASKS=(
    "Buy groceries"
    "Walk the dog"
    "Read a book"
    "Write weekly report"
    "Call mom"
)

# -----------------------------------------------------------
# Step 1: Clean up any existing server on port 8090
# -----------------------------------------------------------
echo "[setup] Stopping any existing PocketBase server on port 8090..."
EXISTING_PID=$(lsof -ti :8090 2>/dev/null || true)
if [ -n "${EXISTING_PID}" ]; then
    kill "${EXISTING_PID}" 2>/dev/null || true
    sleep 1
    # Force kill if still running
    kill -9 "${EXISTING_PID}" 2>/dev/null || true
    sleep 1
fi

# -----------------------------------------------------------
# Step 2: Create superuser (idempotent via upsert)
# -----------------------------------------------------------
echo "[setup] Creating/updating superuser..."
"${PB_BIN}" superuser upsert "${SUPERUSER_EMAIL}" "${SUPERUSER_PASS}" \
    --dir "${PB_DATA_DIR}" \
    --migrationsDir "${PB_MIGRATIONS_DIR}"

# -----------------------------------------------------------
# Step 3: Apply migrations (creates tasks collection)
# -----------------------------------------------------------
echo "[setup] Applying migrations..."
"${PB_BIN}" migrate up \
    --dir "${PB_DATA_DIR}" \
    --migrationsDir "${PB_MIGRATIONS_DIR}"

# -----------------------------------------------------------
# Step 4: Start PocketBase server in the background
# -----------------------------------------------------------
echo "[setup] Starting PocketBase server..."
"${PB_BIN}" serve \
    --dir "${PB_DATA_DIR}" \
    --migrationsDir "${PB_MIGRATIONS_DIR}" \
    --http "127.0.0.1:8090" \
    > "${PROJECT_DIR}/pb_server.log" 2>&1 &

PB_PID=$!
echo "[setup] PocketBase server PID: ${PB_PID}"

# -----------------------------------------------------------
# Step 5: Wait for server to be ready
# -----------------------------------------------------------
echo "[setup] Waiting for server to be ready..."
MAX_WAIT=30
WAITED=0
while [ "${WAITED}" -lt "${MAX_WAIT}" ]; do
    if curl -sf -o /dev/null "${PB_URL}/api/health" 2>/dev/null; then
        echo "[setup] Server is ready (after ${WAITED}s)."
        break
    fi
    sleep 1
    WAITED=$((WAITED + 1))
done

if [ "${WAITED}" -ge "${MAX_WAIT}" ]; then
    echo "[setup] ERROR: Server did not become ready within ${MAX_WAIT}s."
    exit 1
fi

# -----------------------------------------------------------
# Step 6: Authenticate as superuser to get auth token
# -----------------------------------------------------------
echo "[setup] Authenticating as superuser..."
AUTH_RESPONSE=$(curl -sf -X POST "${PB_URL}/api/collections/_superusers/auth-with-password" \
    -H "Content-Type: application/json" \
    -d "{\"identity\":\"${SUPERUSER_EMAIL}\",\"password\":\"${SUPERUSER_PASS}\"}")

AUTH_TOKEN=$(echo "${AUTH_RESPONSE}" | grep -o '"token":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "${AUTH_TOKEN}" ]; then
    echo "[setup] ERROR: Failed to authenticate as superuser."
    echo "[setup] Response: ${AUTH_RESPONSE}"
    exit 1
fi
echo "[setup] Authenticated successfully."

# -----------------------------------------------------------
# Step 7: Seed task records (idempotent - skip if title exists)
# -----------------------------------------------------------
echo "[setup] Seeding task records..."

for TASK_TITLE in "${TASKS[@]}"; do
    # URL-encode the title for the filter query
    ENCODED_TITLE=$(printf '%s' "${TASK_TITLE}" | jq -sRr @uri)

    # Check if a record with this title already exists
    EXISTING=$(curl -sf --get "${PB_URL}/api/collections/tasks/records" \
        --data-urlencode "filter=(title='${TASK_TITLE}')" \
        -H "Authorization: ${AUTH_TOKEN}" 2>/dev/null || true)

    if echo "${EXISTING}" | grep -q '"totalItems":0'; then
        echo "[setup]   Creating task: '${TASK_TITLE}'"
        curl -sf -X POST "${PB_URL}/api/collections/tasks/records" \
            -H "Content-Type: application/json" \
            -H "Authorization: ${AUTH_TOKEN}" \
            -d "{\"title\":\"${TASK_TITLE}\",\"done\":false}" \
            > /dev/null
    else
        echo "[setup]   Task already exists, skipping: '${TASK_TITLE}'"
    fi
done

echo "[setup] Setup complete."
echo "[setup] Server is running at ${PB_URL}"
echo "[setup] Superuser: ${SUPERUSER_EMAIL}"
echo "[setup] Tasks seeded: ${#TASKS[@]}"
