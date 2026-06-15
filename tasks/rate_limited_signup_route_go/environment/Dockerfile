FROM ubuntu:24.04

ENV GO_VERSION=1.23.4
ENV PB_VERSION=0.31.0

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep \
        unzip jq build-essential && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests pytest-xprocess && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Go toolchain (required if the executor opts to build a custom PocketBase Go middleware).
RUN curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -o /tmp/go.tgz && \
    tar -C /usr/local -xzf /tmp/go.tgz && \
    rm /tmp/go.tgz && \
    ln -s /usr/local/go/bin/go /usr/local/bin/go && \
    ln -s /usr/local/go/bin/gofmt /usr/local/bin/gofmt

ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH="/root/go"
ENV GOCACHE="/root/.cache/go-build"

RUN mkdir -p /home/user && chmod 0755 /home/user

# Prepare the PocketBase project skeleton at /home/user/myproject with the official
# v0.31.0 prebuilt binary, then run `migrate` once so the default `users` auth
# collection is materialized in `pb_data/` and reachable on first startup.
RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    curl -fsSL "https://github.com/pocketbase/pocketbase/releases/download/v${PB_VERSION}/pocketbase_${PB_VERSION}_linux_amd64.zip" -o /tmp/pocketbase.zip && \
    unzip -o /tmp/pocketbase.zip -d /home/user/myproject && \
    rm /tmp/pocketbase.zip && \
    chmod +x /home/user/myproject/pocketbase && \
    mkdir -p /home/user/myproject/pb_hooks /home/user/myproject/pb_migrations /home/user/myproject/pb_public && \
    /home/user/myproject/pocketbase migrate up && \
    cat > /home/user/myproject/start.sh <<'EOF'
#!/bin/bash
# Default startup script: serves the stock PocketBase v0.31.0 binary on :8090.
# The executor is expected to overwrite this file so that the started server
# enforces the per-IP signup rate limit described in instruction.md.
cd /home/user/myproject
exec /home/user/myproject/pocketbase serve --http=0.0.0.0:8090
EOF
RUN chmod +x /home/user/myproject/start.sh

# Pre-warm Go module cache for a typical PocketBase v0.31.0 embedding so the
# executor does not have to download ~hundreds of MB at evaluation time.
RUN mkdir -p /tmp/pbwarm && cd /tmp/pbwarm && \
    go mod init pbwarm && \
    go get github.com/pocketbase/pocketbase@v${PB_VERSION} && \
    go mod tidy && \
    cd / && rm -rf /tmp/pbwarm

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 environment with Go 1.23 toolchain for building a per-IP signup rate-limit middleware."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip jq build-essential
#   - pip3 packages: pytest-json-ctrf requests pytest-xprocess
#   - Go toolchain: /usr/local/go (go ${GO_VERSION})
#   - /home/user/myproject/pocketbase: PocketBase v${PB_VERSION} prebuilt binary
#   - /home/user/myproject/pb_data: pre-migrated PocketBase data dir with default users collection
#   - /home/user/myproject/pb_hooks, /pb_migrations, /pb_public: empty PocketBase directories
#   - /home/user/myproject/start.sh: default startup script (executor is expected to overwrite)
