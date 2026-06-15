FROM ubuntu:24.04

ENV GO_VERSION=1.22.7
ENV GOROOT=/usr/local/go
ENV GOPATH=/root/go
ENV PATH=/usr/local/go/bin:/root/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV PB_VERSION=0.31.0
# Pre-seeded superuser credentials baked into /opt/pb_seed/pb_data.
ENV PB_SUPERUSER_EMAIL=harbor-admin@example.com
ENV PB_SUPERUSER_PASSWORD=harbor-admin-pass-1234

# Base OS packages + Python tooling + Go toolchain (downloaded from go.dev) +
# pre-warmed PocketBase v0.31.0 Go module cache + a seeded pb_data directory
# created with the official PocketBase v0.31.0 binary containing a superuser.
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash \
        ripgrep unzip build-essential && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages \
        pytest-json-ctrf requests pytest-xprocess && \
    ARCH="$(dpkg --print-architecture)" && \
    curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-${ARCH}.tar.gz" \
        -o /tmp/go.tar.gz && \
    tar -C /usr/local -xzf /tmp/go.tar.gz && \
    rm /tmp/go.tar.gz && \
    mkdir -p /opt/pb_warm && cd /opt/pb_warm && \
    /usr/local/go/bin/go mod init pbwarm && \
    /usr/local/go/bin/go get github.com/pocketbase/pocketbase@v${PB_VERSION} && \
    cd / && \
    mkdir -p /opt/pb_seed && cd /opt/pb_seed && \
    if [ "${ARCH}" = "amd64" ]; then PB_ARCH=amd64; \
       elif [ "${ARCH}" = "arm64" ]; then PB_ARCH=arm64; \
       else PB_ARCH="${ARCH}"; fi && \
    curl -fsSL -o /tmp/pocketbase.zip \
        "https://github.com/pocketbase/pocketbase/releases/download/v${PB_VERSION}/pocketbase_${PB_VERSION}_linux_${PB_ARCH}.zip" && \
    unzip -q /tmp/pocketbase.zip -d /opt/pb_seed && \
    rm /tmp/pocketbase.zip && \
    chmod +x /opt/pb_seed/pocketbase && \
    /opt/pb_seed/pocketbase superuser create \
        "${PB_SUPERUSER_EMAIL}" "${PB_SUPERUSER_PASSWORD}" \
        --dir /opt/pb_seed/pb_data && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /opt/pb_warm

RUN mkdir -p /home/user && chmod 0755 /home/user
RUN mkdir -p /home/user/myproject && chmod 0755 /home/user/myproject

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 Go-embedded task environment with Go 1.22 toolchain, pre-warmed module cache, and a seeded pb_data directory containing a superuser."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - additional pip3 packages: requests, pytest-xprocess (for spawning the PocketBase server during verification)
#   - Go 1.22 toolchain installed under /usr/local/go (in PATH)
#   - github.com/pocketbase/pocketbase@v0.31.0 pre-downloaded into the Go module cache
#   - /opt/pb_seed: official PocketBase v0.31.0 binary + seeded pb_data containing the superuser
#   - /home/user/myproject: empty project directory for the executor to populate
#   - ENV PB_SUPERUSER_EMAIL / PB_SUPERUSER_PASSWORD: credentials matching the seeded superuser
