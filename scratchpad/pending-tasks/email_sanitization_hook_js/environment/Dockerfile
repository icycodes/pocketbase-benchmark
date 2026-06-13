FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests pytest-xprocess && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

# Download and extract PocketBase v0.31.0
RUN mkdir -p /home/user/myproject && \
    cd /tmp && \
    curl -fsSL -o pocketbase.zip https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip -o pocketbase.zip -d /home/user/myproject && \
    rm -f /tmp/pocketbase.zip && \
    chmod +x /home/user/myproject/pocketbase && \
    mkdir -p /home/user/myproject/pb_hooks /home/user/myproject/pb_migrations /home/user/myproject/pb_public

# Pre-create an initial superuser so that PocketBase is fully bootstrapped.
# These are sandboxed test fixtures, not real credentials.
ENV PB_SUPERUSER_EMAIL="harbor-admin@example.com"
ENV PB_SUPERUSER_PASSWORD="HarborAdminPass!42"

RUN cd /home/user/myproject && \
    ./pocketbase superuser create "${PB_SUPERUSER_EMAIL}" "${PB_SUPERUSER_PASSWORD}"

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 single-file backend with a bootstrapped superuser, ready for the JSVM email sanitization hook task."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep, plus unzip for the PocketBase release archive
#   - always required pip3 packages: pytest-json-ctrf
#   - extra pip3 packages used by tests: requests, pytest-xprocess
#   - /home/user/myproject/pocketbase: PocketBase v0.31.0 linux amd64 binary
#   - /home/user/myproject/pb_data: pre-initialized data dir (auto-created when superuser was registered)
#   - /home/user/myproject/pb_hooks, pb_migrations, pb_public: empty support directories ready for agent hook files
#   - ENV PB_SUPERUSER_EMAIL, PB_SUPERUSER_PASSWORD: sandboxed test credentials for verification
