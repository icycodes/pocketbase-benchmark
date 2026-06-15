FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip jq && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf pytest-xprocess requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Go 1.22.5
RUN curl -fsSL https://go.dev/dl/go1.22.5.linux-amd64.tar.gz | tar -C /usr/local -xz && \
    ln -s /usr/local/go/bin/go /usr/local/bin/go && \
    ln -s /usr/local/go/bin/gofmt /usr/local/bin/gofmt

RUN mkdir -p /home/user && chmod 0755 /home/user

# Setup project directory and initialize PocketBase posts collection
RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    go mod init myproject && \
    go get github.com/pocketbase/pocketbase@v0.23.0 && \
    go mod tidy && \
    curl -L -o pocketbase.zip https://github.com/pocketbase/pocketbase/releases/download/v0.23.0/pocketbase_0.23.0_linux_amd64.zip && \
    unzip pocketbase.zip -d /tmp/pb && \
    /tmp/pb/pocketbase superuser upsert admin@example.com password1234 --dir /home/user/myproject/pb_data && \
    cat > /tmp/payload.json <<'EOF'
{
  "name": "posts",
  "type": "base",
  "schema": [
    { "name": "title", "type": "text" },
    { "name": "slug", "type": "text" }
  ],
  "createRule": ""
}
EOF
RUN cd /home/user/myproject && \
    /tmp/pb/pocketbase serve --dir /home/user/myproject/pb_data --http="127.0.0.1:8090" & \
    PB_PID=$! && \
    sleep 3 && \
    TOKEN=$(curl -s -X POST http://127.0.0.1:8090/api/collections/_superusers/auth-with-password \
      -H "Content-Type: application/json" \
      -d '{"identity": "admin@example.com", "password": "password1234"}' | jq -r .token) && \
    curl -s -X POST http://127.0.0.1:8090/api/collections \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d @/tmp/payload.json && \
    kill $PB_PID && \
    wait $PB_PID || true && \
    rm -rf /tmp/pb /home/user/myproject/pocketbase.zip /tmp/payload.json

LABEL Author="generate-harbor-tasks"
LABEL Description="Go environment with PocketBase embedded and pre-configured 'posts' collection."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip jq
#   - always required pip3 packages: pytest-json-ctrf pytest-xprocess requests
#   - Go 1.22.5 installed
#   - /home/user/myproject: project directory with initialized go.mod
#   - /home/user/myproject/pb_data: pre-populated PocketBase data with 'posts' collection
