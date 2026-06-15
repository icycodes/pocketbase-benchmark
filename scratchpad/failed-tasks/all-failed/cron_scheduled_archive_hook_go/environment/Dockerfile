FROM ubuntu:24.04

ENV GO_VERSION=1.23.4
ENV PATH=/usr/local/go/bin:/root/go/bin:${PATH}
ENV GOPATH=/root/go
ENV GOTOOLCHAIN=local

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep \
        build-essential unzip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -o /tmp/go.tar.gz && \
    tar -C /usr/local -xzf /tmp/go.tar.gz && \
    rm /tmp/go.tar.gz && \
    pip3 install --break-system-packages \
        pytest-json-ctrf \
        pytest-xprocess \
        requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

# ----------------------------------------------------------------------------
# Provision the Go project skeleton at /home/user/myproject so the executor
# only has to implement the cron + archive logic. The PocketBase v0.31.0
# module is pre-fetched into the Go module cache so the build can run
# offline.
# ----------------------------------------------------------------------------
RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    cat >go.mod <<'EOF'
module pocketbase-archive-job

go 1.23

require github.com/pocketbase/pocketbase v0.31.0
EOF

RUN cd /home/user/myproject && \
    cat >main.go <<'EOF'
package main

import (
    "log"

    "github.com/pocketbase/pocketbase"
)

// Starter skeleton for the scheduled-archive task.
//
// The executor is expected to:
//   1. Ensure two `base` collections (`posts` and `archive_posts`) exist
//      with public REST access for list/view/create/update/delete.
//   2. Register a cron job (via app.Cron()) that, on every minute boundary,
//      copies every `posts` record older than ARCHIVE_AGE_SECONDS into
//      `archive_posts` (preserving the original id and storing an
//      `archived_at` timestamp) and atomically deletes the source row.
//   3. Use a per-record database transaction so partial state can never be
//      observed.
//
// See instruction.md for the full task brief.
func main() {
    app := pocketbase.New()

    if err := app.Start(); err != nil {
        log.Fatal(err)
    }
}
EOF

RUN cd /home/user/myproject && \
    go mod download github.com/pocketbase/pocketbase && \
    go mod tidy

LABEL Author="generate-harbor-tasks"
LABEL Description="Embedded PocketBase v0.31.0 Go project skeleton for the scheduled-archive cron task."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - extra pip3 packages for the verifier: pytest-xprocess, requests
#   - Go 1.23.4 toolchain installed at /usr/local/go (on PATH)
#   - /home/user/myproject: Go project skeleton with go.mod pinned to
#     github.com/pocketbase/pocketbase v0.31.0 and a stub main.go
#   - PocketBase v0.31.0 module pre-populated in the Go module cache for
#     offline builds
