FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    pip3 install --break-system-packages pytest-json-ctrf pytest-xprocess requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install PocketBase
RUN curl -L -o pocketbase.zip https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip pocketbase.zip -d /usr/local/bin && \
    rm pocketbase.zip && \
    chmod +x /usr/local/bin/pocketbase

RUN mkdir -p /home/user && chmod 0755 /home/user

# Setup Express project
RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    npm init -y && \
    npm install express cookie-parser pocketbase

# Initialize PocketBase and create test user
# We start PocketBase in the background, create the user via REST API, then stop it.
RUN mkdir -p /home/user/pb_data && \
    cd /home/user && \
    pocketbase serve --http="127.0.0.1:8090" & \
    PB_PID=$! && \
    sleep 3 && \
    curl -X POST http://127.0.0.1:8090/api/collections/users/records \
         -H "Content-Type: application/json" \
         -d '{"email":"test@example.com", "password":"secure_password", "passwordConfirm":"secure_password"}' && \
    kill $PB_PID && \
    wait $PB_PID || true

# Update test_initial_state.py to start PocketBase if it's not already running?
# Actually, test_initial_state.py expects PocketBase to be running. We need to modify it or start it in test_initial_state.py.
# Wait, the instruction says: "If there is any background service that needs to run, start the service during the initial state test, because the initial state test is always run before evaluation."
# I'll update test_initial_state.py to start PocketBase.

LABEL Author="generate-harbor-tasks"
LABEL Description="Express SSR Authentication Sync task with PocketBase and Node.js v24."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip
#   - always required pip3 packages: pytest-json-ctrf pytest-xprocess requests
#   - Node.js v24 for the Express task environment
#   - PocketBase v0.31.0 installed globally
#   - /home/user/myproject: initialized Express project with express, cookie-parser, pocketbase
#   - /home/user/pb_data: Initialized PocketBase data with test user test@example.com
