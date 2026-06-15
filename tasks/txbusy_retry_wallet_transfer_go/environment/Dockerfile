FROM ubuntu:24.04

# Base toolchain + Python deps for tests + Go toolchain (>=1.22) for embedded PocketBase
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep \
        jq unzip xz-utils build-essential pkg-config && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests pytest-xprocess && \
    curl -fsSL https://go.dev/dl/go1.22.5.linux-amd64.tar.gz | tar -C /usr/local -xz && \
    ln -sf /usr/local/go/bin/go /usr/local/bin/go && \
    ln -sf /usr/local/go/bin/gofmt /usr/local/bin/gofmt && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV GOPATH=/root/go
ENV PATH=/usr/local/go/bin:/root/go/bin:$PATH

RUN mkdir -p /home/user && chmod 0755 /home/user

# Scaffold the embedded PocketBase Go project. The executor only needs to add the
# POST /api/wallets/transfer route inside main.go.
RUN mkdir -p /home/user/myproject && \
    cat > /home/user/myproject/go.mod <<'EOF'
module myapp

go 1.22

require github.com/pocketbase/pocketbase v0.31.0
EOF

RUN cat > /home/user/myproject/main.go <<'EOF'
package main

import (
	"log"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		// TODO: Register POST /api/wallets/transfer here.
		// The handler MUST run inside app.RunInTransaction, lock both wallets
		// in a consistent id-ascending order, retry on SQLITE_BUSY with
		// exponential backoff (up to 5 attempts, 50ms..1.6s), and write an
		// audit row in the `transfers` collection.
		return se.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
EOF

# Download module cache and build the starter binary so the env passes test_initial_state.
RUN cd /home/user/myproject && \
    go mod tidy && \
    go build -o /home/user/myproject/myapp .

# Seed PocketBase data: create a superuser, start the server, create collections,
# seed the tester user and the two wallets (A=100, B=0) via the admin REST API.
RUN cat > /tmp/seed.sh <<'EOF'
#!/usr/bin/env bash
set -eu

PB_DIR=/home/user/myproject
BIN="$PB_DIR/myapp"
DATA="$PB_DIR/pb_data"
HOST="127.0.0.1:8090"

cd "$PB_DIR"

# Create superuser (idempotent: ignore if already exists).
"$BIN" superuser upsert admin@example.com admin12345 --dir="$DATA"

# Boot server.
"$BIN" serve --http="$HOST" --dir="$DATA" >/tmp/pb_seed.log 2>&1 &
PID=$!

trap 'kill $PID 2>/dev/null || true' EXIT

# Wait for /api/health.
for i in $(seq 1 60); do
    if curl -fsS "http://$HOST/api/health" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# Authenticate as superuser.
TOKEN=$(curl -fsS -X POST "http://$HOST/api/collections/_superusers/auth-with-password" \
    -H 'Content-Type: application/json' \
    -d '{"identity":"admin@example.com","password":"admin12345"}' | jq -r .token)

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo "Failed to obtain superuser token" >&2
    cat /tmp/pb_seed.log >&2
    exit 1
fi

AUTH="Authorization: $TOKEN"

# Create the `wallets` collection.
curl -fsS -X POST "http://$HOST/api/collections" \
    -H "$AUTH" -H 'Content-Type: application/json' \
    -d '{
        "name": "wallets",
        "type": "base",
        "listRule": "@request.auth.id != \"\"",
        "viewRule": "@request.auth.id != \"\"",
        "createRule": "@request.auth.id != \"\"",
        "updateRule": "@request.auth.id != \"\"",
        "deleteRule": "@request.auth.id != \"\"",
        "fields": [
            {"name": "owner", "type": "text"},
            {"name": "balance", "type": "number"}
        ]
    }' >/dev/null

# Create the `transfers` audit collection.
curl -fsS -X POST "http://$HOST/api/collections" \
    -H "$AUTH" -H 'Content-Type: application/json' \
    -d '{
        "name": "transfers",
        "type": "base",
        "listRule": "@request.auth.id != \"\"",
        "viewRule": "@request.auth.id != \"\"",
        "createRule": "@request.auth.id != \"\"",
        "updateRule": "@request.auth.id != \"\"",
        "deleteRule": "@request.auth.id != \"\"",
        "fields": [
            {"name": "fromId", "type": "text"},
            {"name": "toId", "type": "text"},
            {"name": "amount", "type": "number"}
        ]
    }' >/dev/null

# Seed the tester user.
USER_ID=$(curl -fsS -X POST "http://$HOST/api/collections/users/records" \
    -H "$AUTH" -H 'Content-Type: application/json' \
    -d '{
        "email": "tester@example.com",
        "password": "password12345",
        "passwordConfirm": "password12345",
        "emailVisibility": true,
        "verified": true
    }' | jq -r .id)

if [ -z "$USER_ID" ] || [ "$USER_ID" = "null" ]; then
    echo "Failed to create tester user" >&2
    cat /tmp/pb_seed.log >&2
    exit 1
fi

# Seed wallet A (balance=100) and wallet B (balance=0).
curl -fsS -X POST "http://$HOST/api/collections/wallets/records" \
    -H "$AUTH" -H 'Content-Type: application/json' \
    -d "{\"owner\":\"$USER_ID\",\"balance\":100}" >/dev/null

curl -fsS -X POST "http://$HOST/api/collections/wallets/records" \
    -H "$AUTH" -H 'Content-Type: application/json' \
    -d "{\"owner\":\"$USER_ID\",\"balance\":0}" >/dev/null

# Graceful shutdown.
kill $PID
wait $PID 2>/dev/null || true
trap - EXIT
EOF

RUN chmod +x /tmp/seed.sh && /tmp/seed.sh && rm /tmp/seed.sh

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 Go-embedded scaffold with seeded wallets A=100 and B=0 for the txbusy_retry_wallet_transfer_go task."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - extra apt: jq, unzip, xz-utils, build-essential, pkg-config
#   - extra pip3: requests, pytest-xprocess (used by test_final_state.py)
#   - Go 1.22.5 toolchain installed under /usr/local/go
#   - /home/user/myproject: starter Go project pinned to github.com/pocketbase/pocketbase v0.31.0
#   - /home/user/myproject/myapp: pre-built starter binary (executor will rebuild it)
#   - /home/user/myproject/pb_data: seeded SQLite DB with superuser admin@example.com,
#     tester user tester@example.com, wallets collection (A=100, B=0) and transfers collection
