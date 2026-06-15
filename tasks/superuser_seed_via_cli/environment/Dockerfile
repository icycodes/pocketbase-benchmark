FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep \
        unzip jq iproute2 procps && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

# Install PocketBase v0.31.0 binary into the project directory.
# The agent is expected to create a setup.sh under this directory.
RUN mkdir -p /home/user/myproject && \
    cd /tmp && \
    curl -fsSL -o pocketbase.zip \
        https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip pocketbase.zip -d /home/user/myproject && \
    rm -f pocketbase.zip && \
    chmod +x /home/user/myproject/pocketbase

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 single-binary backend, project directory at /home/user/myproject."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - extra apt packages: unzip (extract PocketBase release), jq (script tooling), iproute2 (ss for port check), procps (pkill)
#   - always required pip3 packages: pytest-json-ctrf
#   - extra pip3 packages: requests (used by test_final_state.py for REST verification)
#   - PocketBase v0.31.0 binary installed at /home/user/myproject/pocketbase
#   - /home/user/myproject: empty project directory where the agent must create setup.sh
