FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    GO_VERSION=1.23.4 \
    GOPATH=/root/go \
    GOMODCACHE=/root/go/pkg/mod \
    GOCACHE=/root/.cache/go-build \
    PATH=/usr/local/go/bin:/root/go/bin:/usr/local/bin:/usr/bin:/bin \
    PB_VERSION=0.31.0 \
    MINIO_ROOT_USER=minioadmin \
    MINIO_ROOT_PASSWORD=minioadmin

# --- base apt + pip deps ---
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep \
        unzip jq psmisc lsof xz-utils && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages \
        pytest-json-ctrf pytest-xprocess requests boto3 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# --- install Go toolchain (PocketBase v0.31 requires Go 1.23+) ---
RUN curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -o /tmp/go.tar.gz && \
    tar -C /usr/local -xzf /tmp/go.tar.gz && \
    rm /tmp/go.tar.gz && \
    /usr/local/go/bin/go version

# --- install MinIO server binary ---
RUN curl -fsSL https://dl.min.io/server/minio/release/linux-amd64/minio -o /usr/local/bin/minio && \
    chmod +x /usr/local/bin/minio && \
    mkdir -p /var/lib/minio/data && \
    /usr/local/bin/minio --version

# --- install PocketBase v0.31.0 standalone binary (used only for bootstrapping pb_data) ---
RUN curl -fsSL "https://github.com/pocketbase/pocketbase/releases/download/v${PB_VERSION}/pocketbase_${PB_VERSION}_linux_amd64.zip" -o /tmp/pb.zip && \
    mkdir -p /tmp/pb && \
    unzip -q /tmp/pb.zip -d /tmp/pb && \
    install -m 0755 /tmp/pb/pocketbase /usr/local/bin/pocketbase-bootstrap && \
    rm -rf /tmp/pb /tmp/pb.zip

# --- pre-warm Go module cache so the agent does not need network for the heavy deps ---
RUN mkdir -p /tmp/warm && cd /tmp/warm && \
    /usr/local/go/bin/go mod init warm && \
    /usr/local/go/bin/go get github.com/pocketbase/pocketbase@v${PB_VERSION} && \
    /usr/local/go/bin/go get github.com/aws/aws-sdk-go-v2 && \
    /usr/local/go/bin/go get github.com/aws/aws-sdk-go-v2/config && \
    /usr/local/go/bin/go get github.com/aws/aws-sdk-go-v2/credentials && \
    /usr/local/go/bin/go get github.com/aws/aws-sdk-go-v2/service/s3 && \
    /usr/local/go/bin/go get github.com/google/uuid && \
    cd / && rm -rf /tmp/warm

# --- user dir + project dir ---
RUN mkdir -p /home/user && chmod 0755 /home/user && \
    mkdir -p /home/user/myapp

# --- bootstrap pb_data with the superuser and two regular users that the verifier expects ---
# We start MinIO briefly here too so the bootstrap PocketBase can boot without errors,
# but the real MinIO server for the task is started by test_initial_state.py.
RUN bash -lc '\
    set -eu; \
    mkdir -p /tmp/bootstrap-pb; \
    cd /tmp/bootstrap-pb; \
    cp /usr/local/bin/pocketbase-bootstrap ./pocketbase; \
    ./pocketbase superuser upsert admin@example.com 1234567890; \
    ./pocketbase serve --http=127.0.0.1:18090 >/tmp/pb-bootstrap.log 2>&1 & \
    PB_PID=$!; \
    READY=0; \
    for i in $(seq 1 120); do \
        if curl -fsS http://127.0.0.1:18090/api/health >/dev/null 2>&1; then READY=1; break; fi; \
        sleep 0.5; \
    done; \
    if [ "$READY" != "1" ]; then echo "bootstrap PB failed to become ready"; cat /tmp/pb-bootstrap.log; kill $PB_PID 2>/dev/null || true; exit 1; fi; \
    SU_TOKEN=$(curl -fsS -X POST http://127.0.0.1:18090/api/collections/_superusers/auth-with-password \
        -H "Content-Type: application/json" \
        -d "{\"identity\":\"admin@example.com\",\"password\":\"1234567890\"}" | jq -r .token); \
    if [ -z "$SU_TOKEN" ] || [ "$SU_TOKEN" = "null" ]; then echo "failed to obtain superuser token"; cat /tmp/pb-bootstrap.log; kill $PB_PID 2>/dev/null || true; exit 1; fi; \
    curl -fsS -X POST http://127.0.0.1:18090/api/collections/users/records \
        -H "Authorization: $SU_TOKEN" -H "Content-Type: application/json" \
        -d "{\"email\":\"user@example.com\",\"password\":\"password1234\",\"passwordConfirm\":\"password1234\",\"verified\":true}"; \
    echo; \
    curl -fsS -X POST http://127.0.0.1:18090/api/collections/users/records \
        -H "Authorization: $SU_TOKEN" -H "Content-Type: application/json" \
        -d "{\"email\":\"other@example.com\",\"password\":\"password1234\",\"passwordConfirm\":\"password1234\",\"verified\":true}"; \
    echo; \
    kill $PB_PID; \
    wait $PB_PID 2>/dev/null || true; \
    cp -r pb_data /home/user/myapp/pb_data; \
    chmod -R a+rwX /home/user/myapp; \
    cd /; \
    rm -rf /tmp/bootstrap-pb /tmp/pb-bootstrap.log; \
'

LABEL Author="generate-harbor-tasks"
LABEL Description="Ubuntu 24.04 with Go 1.23, MinIO server, PocketBase v0.31.0 module cache pre-warmed, and a pb_data seeded with one superuser plus two regular users for the S3 presigned-upload task."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - apt: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip jq psmisc lsof xz-utils
#   - pip3: pytest-json-ctrf pytest-xprocess requests boto3
#   - /usr/local/go: Go 1.23.4 toolchain
#   - /usr/local/bin/minio: MinIO server binary (started by test_initial_state.py on :9000)
#   - /usr/local/bin/pocketbase-bootstrap: standalone PocketBase v0.31.0 used only at build time to seed pb_data
#   - Go module cache pre-warmed for github.com/pocketbase/pocketbase@v0.31.0 and aws-sdk-go-v2
#   - /home/user/myapp: project directory (agent writes Go sources here and runs `go build -o myapp`)
#   - /home/user/myapp/pb_data: seeded SQLite database with superuser admin@example.com / 1234567890 and users user@example.com / password1234 and other@example.com / password1234
