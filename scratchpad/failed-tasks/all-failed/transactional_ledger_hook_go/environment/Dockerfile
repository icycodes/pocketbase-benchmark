FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep golang-go unzip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests pytest-xprocess && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    cat >main.go <<'EOF'
package main

import (
    "log"
    "github.com/pocketbase/pocketbase"
)

func main() {
    app := pocketbase.New()
    if err := app.Start(); err != nil {
        log.Fatal(err)
    }
}
EOF

RUN cd /home/user/myproject && \
    go mod init myproject && \
    go get github.com/pocketbase/pocketbase@v0.31.0 && \
    go mod tidy

# Initialize PocketBase collections and records
RUN curl -L -o pocketbase.zip https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip pocketbase.zip && \
    ./pocketbase admin create test@example.com password12345 && \
    ./pocketbase serve & \
    sleep 3 && \
    TOKEN=$(curl -s -X POST http://127.0.0.1:8090/api/admins/auth-with-password -H "Content-Type: application/json" -d '{"identity":"test@example.com","password":"password12345"}' | grep -o '"token":"[^"]*' | cut -d'"' -f4) && \
    curl -s -X POST http://127.0.0.1:8090/api/collections -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"name":"wallets","type":"base","fields":[{"name":"balance","type":"number"}]}' && \
    curl -s -X POST http://127.0.0.1:8090/api/collections -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"name":"ledger","type":"base","fields":[{"name":"wallet_id","type":"relation","relationOptions":{"collectionId":"wallets","cascadeDelete":false}},{"name":"amount","type":"number"}]}' && \
    curl -s -X POST http://127.0.0.1:8090/api/collections/wallets/records -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"id":"walletrich00000","balance":100}' && \
    curl -s -X POST http://127.0.0.1:8090/api/collections/wallets/records -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"id":"walletpoor00000","balance":10}' && \
    kill %1 && sleep 2 && \
    mv pb_data /home/user/myproject/ && \
    rm pocketbase pocketbase.zip

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase Go project initialized with wallets and ledger collections and some test data."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep golang-go unzip
#   - always required pip3 packages: pytest-json-ctrf requests pytest-xprocess
#   - /home/user/myproject: PocketBase Go project directory
#   - /home/user/myproject/pb_data: SQLite database with wallets and ledger collections
