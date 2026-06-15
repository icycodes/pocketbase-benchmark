FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests pytest-xprocess && \
    curl -fsSL https://go.dev/dl/go1.23.4.linux-amd64.tar.gz -o go.tar.gz && \
    tar -C /usr/local -xzf go.tar.gz && \
    rm go.tar.gz && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV PATH=$PATH:/usr/local/go/bin

RUN mkdir -p /home/user && chmod 0755 /home/user

RUN mkdir -p /home/user/pocketbase-app && \
    cd /home/user/pocketbase-app && \
    go mod init pocketbase-app && \
    go get github.com/pocketbase/pocketbase && \
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
LABEL Description="PocketBase custom CLI command task environment with Go 1.23.4."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - additional pip3 packages for verification: requests, pytest-xprocess
#   - Go 1.23.4 installed via official tarball
#   - /home/user/pocketbase-app: initialized Go module with PocketBase dependency and a basic main.go
