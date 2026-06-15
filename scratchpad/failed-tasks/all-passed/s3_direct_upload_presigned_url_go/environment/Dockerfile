FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep golang && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf pytest-xprocess requests boto3 && \
    curl -fsSL -o /usr/local/bin/minio https://dl.min.io/server/minio/release/linux-amd64/minio && \
    chmod +x /usr/local/bin/minio && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

RUN mkdir -p /home/user/app && \
    cd /home/user/app && \
    go mod init app && \
    go get github.com/pocketbase/pocketbase@v0.31.0 && \
    go get github.com/aws/aws-sdk-go-v2@latest && \
    go get github.com/aws/aws-sdk-go-v2/config@latest && \
    go get github.com/aws/aws-sdk-go-v2/service/s3@latest && \
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
LABEL Description="PocketBase Go framework task environment with MinIO installed."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - additional pip3 packages: pytest-xprocess requests boto3
#   - Go installed via apt-get
#   - MinIO installed via curl
#   - /home/user/app: Go project directory with PocketBase and AWS SDK initialized
