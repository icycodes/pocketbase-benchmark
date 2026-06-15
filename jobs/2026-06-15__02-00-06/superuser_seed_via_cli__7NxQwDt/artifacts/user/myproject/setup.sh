#!/usr/bin/env bash
set -euo pipefail

# Define variables
PROJECT_DIR="/home/user/myproject"
POCKETBASE_BIN="${PROJECT_DIR}/pocketbase"
HEALTH_URL="http://127.0.0.1:8090/api/health"
AUTH_URL="http://127.0.0.1:8090/api/collections/_superusers/auth-with-password"
TASKS_URL="http://127.0.0.1:8090/api/collections/tasks/records"
ADMIN_EMAIL="admin@example.com"
ADMIN_PASSWORD="Adm1n_passw0rd!"

echo "Stopping any existing PocketBase server instance..."
pkill -f "pocketbase serve" || true

# Wait up to 5 seconds for the port to be free
for i in {1..10}; do
  if ! curl -s "${HEALTH_URL}" > /dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

echo "Applying migrations..."
"${POCKETBASE_BIN}" migrate up --dir "${PROJECT_DIR}/pb_data"

echo "Ensuring superuser exists..."
"${POCKETBASE_BIN}" superuser upsert "${ADMIN_EMAIL}" "${ADMIN_PASSWORD}" --dir "${PROJECT_DIR}/pb_data"

echo "Starting PocketBase server in the background..."
nohup "${POCKETBASE_BIN}" serve --dir "${PROJECT_DIR}/pb_data" > "${PROJECT_DIR}/pocketbase.log" 2>&1 &

echo "Waiting for PocketBase server to become healthy..."
SERVER_HEALTHY=false
for i in {1..30}; do
  if curl -s -o /dev/null -w "%{http_code}" "${HEALTH_URL}" | grep -q "200"; then
    SERVER_HEALTHY=true
    echo "PocketBase server is healthy!"
    break
  fi
  sleep 0.5
done

if [ "${SERVER_HEALTHY}" = false ]; then
  echo "Error: PocketBase server failed to start or become healthy."
  exit 1
fi

echo "Authenticating as superuser..."
TOKEN=$(curl -s -X POST "${AUTH_URL}" \
  -H 'Content-Type: application/json' \
  -d "{\"identity\":\"${ADMIN_EMAIL}\", \"password\":\"${ADMIN_PASSWORD}\"}" | jq -r '.token')

if [ -z "${TOKEN}" ] || [ "${TOKEN}" = "null" ]; then
  echo "Error: Failed to authenticate superuser and retrieve token."
  exit 1
fi

echo "Seeding tasks..."
TASKS=(
  "Buy groceries"
  "Walk the dog"
  "Read a book"
  "Write weekly report"
  "Call mom"
)

for title in "${TASKS[@]}"; do
  echo "Checking if task '${title}' exists..."
  EXISTING=$(curl -s -G "${TASKS_URL}" \
    -H "Authorization: ${TOKEN}" \
    --data-urlencode "filter=title='${title}'" | jq '.totalItems')

  if [ "${EXISTING}" -eq 0 ]; then
    echo "Task '${title}' not found. Creating..."
    curl -s -X POST "${TASKS_URL}" \
      -H "Authorization: ${TOKEN}" \
      -H 'Content-Type: application/json' \
      -d "{\"title\":\"${title}\"}" > /dev/null
  else
    echo "Task '${title}' already exists. Skipping."
  fi
done

echo "Setup completed successfully!"
