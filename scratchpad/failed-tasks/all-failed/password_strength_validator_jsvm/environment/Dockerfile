FROM ubuntu:24.04

ARG POCKETBASE_VERSION=0.31.0

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install PocketBase v0.31.0 binary.
RUN ARCH="$(dpkg --print-architecture)" && \
    case "$ARCH" in \
        amd64) PB_ARCH="amd64" ;; \
        arm64) PB_ARCH="arm64" ;; \
        *) echo "Unsupported arch: $ARCH" >&2; exit 1 ;; \
    esac && \
    curl -fsSL -o /tmp/pocketbase.zip \
        "https://github.com/pocketbase/pocketbase/releases/download/v${POCKETBASE_VERSION}/pocketbase_${POCKETBASE_VERSION}_linux_${PB_ARCH}.zip" && \
    unzip -o /tmp/pocketbase.zip -d /usr/local/bin && \
    chmod +x /usr/local/bin/pocketbase && \
    rm -f /tmp/pocketbase.zip && \
    /usr/local/bin/pocketbase --version

RUN mkdir -p /home/user && chmod 0755 /home/user

# Prepare the PocketBase project layout.
RUN mkdir -p /home/user/pb-app/pb_hooks /home/user/pb-app/pb_migrations /home/user/pb-app/pb_public /home/user/pb-app/pb_data

# Add a JSVM migration that ensures the users collection allows public signup.
# This file is mounted as a migration; it is not the file the agent must write.
RUN cat > /home/user/pb-app/pb_migrations/1700000000_allow_public_users_signup.js <<'EOF'
/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
    const collection = app.findCollectionByNameOrId("users")
    collection.createRule = ""
    app.save(collection)
}, (app) => {
    const collection = app.findCollectionByNameOrId("users")
    collection.createRule = null
    app.save(collection)
})
EOF

# Bootstrap pb_data: this auto-creates system collections (including the `users`
# auth collection with email and password fields) and a superuser account.
RUN cd /home/user/pb-app && \
    /usr/local/bin/pocketbase superuser upsert admin@example.com 'Admin1234!Pass' && \
    ls -la pb_data

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 task environment for the password_strength_validator_jsvm task. PocketBase is installed at /usr/local/bin/pocketbase and the project lives under /home/user/pb-app. The server is started in test_initial_state.py (not in CMD)."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip
#   - always required pip3 packages: pytest-json-ctrf
#   - pip3 packages required by tests: requests
#   - PocketBase v0.31.0 binary installed at /usr/local/bin/pocketbase
#   - /home/user/pb-app: project directory with pb_hooks, pb_migrations, pb_public, pb_data subdirectories
#   - /home/user/pb-app/pb_migrations/1700000000_allow_public_users_signup.js: JSVM migration ensuring users.createRule = ""
#   - pb_data bootstrapped via `pocketbase superuser upsert` with default system collections (incl. `users`) and a superuser
#   - PocketBase is NOT started in CMD; it is started during test_initial_state.py via a background subprocess
