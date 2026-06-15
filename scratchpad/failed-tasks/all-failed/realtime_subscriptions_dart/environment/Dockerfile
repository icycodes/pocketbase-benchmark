FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf pytest-xprocess && \
    curl -L -o pocketbase.zip https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip pocketbase.zip -d /usr/local/bin && \
    chmod +x /usr/local/bin/pocketbase && \
    rm pocketbase.zip && \
    curl -fsSL -o dartsdk.zip "https://storage.googleapis.com/dart-archive/channels/stable/release/latest/sdk/dartsdk-linux-x64-release.zip" && \
    unzip dartsdk.zip -d /usr/local && \
    ln -s /usr/local/dart-sdk/bin/dart /usr/local/bin/dart && \
    rm dartsdk.zip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

# Setup PocketBase initial state (admin, users collection, posts collection)
RUN mkdir -p /pb/pb_data && \
    cd /pb && \
    /usr/local/bin/pocketbase serve --http="0.0.0.0:8090" --dir="/pb/pb_data" & \
    sleep 3 && \
    # Create admin
    curl -X POST http://127.0.0.1:8090/api/admins \
        -H "Content-Type: application/json" \
        -d '{"email":"admin@example.com","password":"admin_password","passwordConfirm":"admin_password"}' && \
    # Get admin token
    ADMIN_TOKEN=$(curl -s -X POST http://127.0.0.1:8090/api/admins/auth-with-password \
        -H "Content-Type: application/json" \
        -d '{"identity":"admin@example.com","password":"admin_password"}' | grep -o '"token":"[^"]*' | cut -d'"' -f4) && \
    # Create test user
    curl -X POST http://127.0.0.1:8090/api/collections/users/records \
        -H "Authorization: Bearer $ADMIN_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"email":"test@example.com","password":"secure_password","passwordConfirm":"secure_password","verified":true}' && \
    # Create posts collection
    curl -X POST http://127.0.0.1:8090/api/collections \
        -H "Authorization: Bearer $ADMIN_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"name":"posts","type":"base","listRule":"","viewRule":"","createRule":"","updateRule":"","deleteRule":"","fields":[{"name":"title","type":"text","required":true},{"name":"author","type":"text"},{"name":"content","type":"text"}]}' && \
    # Kill the server gracefully
    pkill pocketbase && sleep 2

# We need to update test_final_state.py and test_initial_state.py to include --dir=/pb/pb_data
LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase environment with Dart SDK installed and a pre-configured 'posts' collection."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip
#   - always required pip3 packages: pytest-json-ctrf pytest-xprocess
#   - PocketBase v0.31.0 binary installed in /usr/local/bin
#   - Dart SDK installed in /usr/local/dart-sdk and linked to /usr/local/bin/dart
#   - /pb/pb_data: Pre-populated PocketBase data with 'posts' collection and test user
#   - /home/user: empty user directory for the Dart project
