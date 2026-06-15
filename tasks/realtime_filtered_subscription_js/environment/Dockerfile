FROM ubuntu:24.04

ENV PB_ADMIN_EMAIL=harbor-admin@example.com \
    PB_ADMIN_PASSWORD=harbor-admin-pass-1234

# Install required apt packages, Node.js LTS (v22), PocketBase v0.31.0 binary,
# and the required pip3 packages for the initial-state and final-state pytest scripts.
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip procps && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    pip3 install --break-system-packages pytest-json-ctrf && \
    curl -fsSL -o /tmp/pocketbase.zip https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip /tmp/pocketbase.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/pocketbase && \
    rm -f /tmp/pocketbase.zip /usr/local/bin/CHANGELOG.md /usr/local/bin/LICENSE.md && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set up the per-task home directory and the empty project directory the agent will fill in.
RUN mkdir -p /home/user && chmod 0755 /home/user && \
    mkdir -p /home/user/myproject && \
    mkdir -p /home/user/pb_data

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 server + Node.js 22 LTS environment for the realtime_filtered_subscription_js task."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip procps
#   - always required pip3 packages: pytest-json-ctrf
#   - PocketBase v0.31.0 server binary at /usr/local/bin/pocketbase
#   - Node.js 22 LTS for the agent's `pocketbase` npm SDK script
#   - /home/user/myproject: empty project directory the agent must fill in
#   - /home/user/pb_data: persistent PocketBase data dir (created/seeded by test_initial_state.py)
