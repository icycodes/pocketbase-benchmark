FROM ubuntu:24.04

ENV GO_VERSION=1.23.4
ENV GOPATH=/root/go
ENV PATH=/usr/local/go/bin:/root/go/bin:$PATH

ENV PB_SUPERUSER_EMAIL=harbor-admin@example.com
ENV PB_SUPERUSER_PASSWORD=harbor-admin-pass-1234

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep \
        unzip build-essential && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Go toolchain.
RUN curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -o /tmp/go.tgz && \
    tar -C /usr/local -xzf /tmp/go.tgz && \
    rm /tmp/go.tgz && \
    /usr/local/go/bin/go version

# Pre-fetch github.com/pocketbase/pocketbase@v0.31.0 and its transitive deps
# into the module cache so the executor can build offline-friendly.
RUN mkdir -p /tmp/prefetch && \
    cd /tmp/prefetch && \
    /usr/local/go/bin/go mod init prefetch && \
    /usr/local/go/bin/go get github.com/pocketbase/pocketbase@v0.31.0 && \
    /usr/local/go/bin/go mod download && \
    cd / && \
    rm -rf /tmp/prefetch

RUN mkdir -p /home/user && chmod 0755 /home/user
RUN mkdir -p /home/user/myproject && chmod 0755 /home/user/myproject

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 Go-migration task environment with Go toolchain and pre-cached pocketbase module."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - extra apt packages: unzip build-essential (needed for cgo / go build)
#   - extra pip3 packages: requests (used by tests/test_final_state.py)
#   - Go ${GO_VERSION} toolchain installed under /usr/local/go
#   - github.com/pocketbase/pocketbase@v0.31.0 pre-cached in the Go module cache
#     under /root/go/pkg/mod/github.com/pocketbase
#   - /home/user/myproject: empty project directory for the executor to populate
