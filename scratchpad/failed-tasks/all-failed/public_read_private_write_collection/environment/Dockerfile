FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep golang && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests pytest-xprocess && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

RUN mkdir -p /home/user/pb-app && \
    cd /home/user/pb-app && \
    go mod init pb-app && \
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

RUN cd /home/user/pb-app && \
    go get github.com/pocketbase/pocketbase@v0.31.0 && \
    go mod tidy

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase task environment with Go installed and a basic project initialized in /home/user/pb-app."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - test dependencies: requests, pytest-xprocess
#   - golang installed via apt for Go project compilation
#   - /home/user/pb-app: PocketBase Go project directory with main.go and go.mod initialized
