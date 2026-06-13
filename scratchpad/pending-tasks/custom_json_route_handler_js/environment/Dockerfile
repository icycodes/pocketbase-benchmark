FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf pytest-xprocess requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

# Install PocketBase v0.31.0 prebuilt binary and prepare an empty project skeleton.
RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    curl -fsSL -o pocketbase.zip \
        https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip -o pocketbase.zip && \
    rm -f pocketbase.zip CHANGELOG.md LICENSE.md && \
    chmod +x ./pocketbase && \
    mkdir -p pb_hooks pb_migrations pb_data

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 project ready for adding a JSVM custom route handler under pb_hooks/."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip
#   - always required pip3 packages: pytest-json-ctrf
#   - additional pip3 packages: pytest-xprocess, requests (for verification of HTTP routes)
#   - PocketBase v0.31.0 binary installed at /home/user/myproject/pocketbase
#   - /home/user/myproject: empty PocketBase project skeleton (pb_hooks/, pb_migrations/, pb_data/)
