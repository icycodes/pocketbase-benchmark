FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests pytest-xprocess && \
    wget https://go.dev/dl/go1.23.6.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.23.6.linux-amd64.tar.gz && \
    rm go1.23.6.linux-amd64.tar.gz && \
    ln -s /usr/local/go/bin/go /usr/local/bin/go && \
    ln -s /usr/local/go/bin/gofmt /usr/local/bin/gofmt && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

RUN mkdir -p /home/user/pb-app && \
    cd /home/user/pb-app && \
    cat >main.go <<'EOF'
package main

import (
	"log"

	"github.com/pocketbase/pocketbase"
)

func main() {
	app := pocketbase.New()

	// Add your custom route here

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
EOF

RUN cd /home/user/pb-app && \
    cat >go.mod <<'EOF'
module pb-app

go 1.23.0

require github.com/pocketbase/pocketbase v0.23.0
EOF

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase custom Go route task environment with Go 1.23.6."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - additional pip3 packages: requests pytest-xprocess
#   - Go 1.23.6 installed via tarball
#   - /home/user/pb-app: PocketBase project directory with main.go and go.mod
