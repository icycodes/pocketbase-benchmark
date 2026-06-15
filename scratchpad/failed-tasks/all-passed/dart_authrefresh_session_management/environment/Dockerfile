# syntax=docker/dockerfile:1
FROM ubuntu:24.04

# Base tools + Python verification stack
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep \
        unzip xz-utils libsqlite3-0 procps && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Dart SDK (stable) for building/running the CLI under /home/user/myproject
ENV DART_SDK_VERSION=3.5.4
RUN curl -fsSL "https://storage.googleapis.com/dart-archive/channels/stable/release/${DART_SDK_VERSION}/sdk/dartsdk-linux-x64-release.zip" -o /tmp/dart-sdk.zip && \
    unzip -q /tmp/dart-sdk.zip -d /opt/ && \
    rm /tmp/dart-sdk.zip && \
    ln -sf /opt/dart-sdk/bin/dart /usr/local/bin/dart && \
    ln -sf /opt/dart-sdk/bin/dartaotruntime /usr/local/bin/dartaotruntime
ENV PATH="/opt/dart-sdk/bin:${PATH}"
ENV PUB_CACHE=/root/.pub-cache

# Install PocketBase v0.31.0 server binary
ENV POCKETBASE_VERSION=0.31.0
RUN mkdir -p /opt/pocketbase && \
    curl -fsSL "https://github.com/pocketbase/pocketbase/releases/download/v${POCKETBASE_VERSION}/pocketbase_${POCKETBASE_VERSION}_linux_amd64.zip" -o /tmp/pb.zip && \
    unzip -q /tmp/pb.zip -d /opt/pocketbase && \
    rm /tmp/pb.zip && \
    chmod +x /opt/pocketbase/pocketbase && \
    ln -sf /opt/pocketbase/pocketbase /usr/local/bin/pocketbase

# Seed script: create superuser, start server briefly, create the regular auth user, then stop server.
RUN cat >/tmp/seed_pocketbase.sh <<'PBSEED'
#!/bin/bash
set -euo pipefail

DATA_DIR=/opt/pb_data
mkdir -p "$DATA_DIR"

/opt/pocketbase/pocketbase --dir="$DATA_DIR" superuser upsert admin@example.com adminpassword12345

/opt/pocketbase/pocketbase --dir="$DATA_DIR" serve --http=127.0.0.1:8090 >/tmp/pb_seed.log 2>&1 &
PB_PID=$!

for _ in $(seq 1 60); do
    if curl -fsS http://127.0.0.1:8090/api/health >/dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

if ! curl -fsS http://127.0.0.1:8090/api/health >/dev/null 2>&1; then
    echo "PocketBase failed to become healthy during seeding" >&2
    cat /tmp/pb_seed.log >&2 || true
    kill "$PB_PID" 2>/dev/null || true
    exit 1
fi

ADMIN_TOKEN=$(curl -fsS -X POST http://127.0.0.1:8090/api/collections/_superusers/auth-with-password \
    -H "Content-Type: application/json" \
    -d '{"identity":"admin@example.com","password":"adminpassword12345"}' \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

curl -fsS -X POST http://127.0.0.1:8090/api/collections/users/records \
    -H "Content-Type: application/json" \
    -H "Authorization: ${ADMIN_TOKEN}" \
    -d '{"email":"user@example.com","password":"password","passwordConfirm":"password","emailVisibility":true,"verified":true}' \
    >/tmp/pb_seed_user.json

kill "$PB_PID"
wait "$PB_PID" 2>/dev/null || true
PBSEED
RUN chmod +x /tmp/seed_pocketbase.sh && /tmp/seed_pocketbase.sh && rm -f /tmp/seed_pocketbase.sh

# Helper script to (re)start the PocketBase server on demand from test_initial_state.py
RUN cat >/usr/local/bin/start_pocketbase.sh <<'PBSTART'
#!/bin/bash
set -e
DATA_DIR="${PB_DATA_DIR:-/opt/pb_data}"
if curl -fsS http://127.0.0.1:8090/api/health >/dev/null 2>&1 ; then
    exit 0
fi
nohup /opt/pocketbase/pocketbase serve --dir="${DATA_DIR}" --http=0.0.0.0:8090 \
    >/var/log/pocketbase.log 2>&1 &
disown || true
for _ in $(seq 1 60); do
    if curl -fsS http://127.0.0.1:8090/api/health >/dev/null 2>&1 ; then
        exit 0
    fi
    sleep 0.5
done
echo "pocketbase did not become healthy in time" >&2
exit 1
PBSTART
RUN chmod +x /usr/local/bin/start_pocketbase.sh

# /home/user and the empty project directory the executor will populate
RUN mkdir -p /home/user && chmod 0755 /home/user && \
    mkdir -p /home/user/myproject

LABEL Author="generate-harbor-tasks"
LABEL Description="Dart SDK + PocketBase v0.31.0 server with a pre-seeded user@example.com auth user for session-management CLI tasks."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip xz-utils libsqlite3-0 procps
#   - pip3 packages: pytest-json-ctrf requests
#   - Dart SDK ${DART_SDK_VERSION} installed under /opt/dart-sdk (dart on PATH)
#   - PocketBase v${POCKETBASE_VERSION} installed under /opt/pocketbase with data dir /opt/pb_data
#       * superuser admin@example.com (adminpassword12345)
#       * users-collection auth user user@example.com / password (verified)
#   - /usr/local/bin/start_pocketbase.sh launches the server detached on 0.0.0.0:8090
#   - /home/user/myproject is an empty project directory the executor populates
