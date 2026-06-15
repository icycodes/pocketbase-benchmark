FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep golang-go && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests pytest-xprocess && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

RUN mkdir -p /home/user/app && \
    cd /home/user/app && \
    go mod init app && \
    go get github.com/pocketbase/pocketbase@v0.31.0 && \
    go mod tidy && \
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

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase task environment with Go 1.22 installed and a basic PocketBase app."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - golang-go for compiling PocketBase Go hooks
#   - requests and pytest-xprocess for verification tests
#   - /home/user/app: initialized PocketBase project directory with go.mod and main.go
