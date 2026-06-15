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
    go mod init myproject && \
    go get github.com/pocketbase/pocketbase@v0.31.0

# Initialize pb_data using the official binary
RUN cd /home/user/myproject && \
    curl -L -o pocketbase.zip https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip pocketbase.zip && \
    ./pocketbase superuser upsert "admin@example.com" "password123456" && \
    ./pocketbase serve --http="0.0.0.0:8090" > pb.log 2>&1 & \
    sleep 3 && \
    TOKEN=$(curl -s -X POST http://127.0.0.1:8090/api/collections/_superusers/auth-with-password -H "Content-Type: application/json" -d '{"identity":"admin@example.com","password":"password123456"}' | grep -o '"token":"[^"]*' | cut -d'"' -f4) && \
    curl -s -X POST http://127.0.0.1:8090/api/collections -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"name":"posts","type":"base","createRule":"","fields":[{"name":"title","type":"text"},{"name":"slug","type":"text"}]}' && \
    kill %1 && \
    sleep 1 && \
    rm pocketbase* CHANGELOG.md LICENSE.md pb.log || true

RUN cd /home/user/myproject && \
    cat > main.go <<'EOF'
package main

import (
	"fmt"
	"log"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	app.OnRecordBeforeCreateRequest("posts").Add(func(e *core.RecordCreateEvent) error {
		title := e.Record.GetString("title")
		if title == "" {
			return fmt.Errorf("Title cannot be empty")
		}

		e.Record.Set("slug", title + "-slug")

		return nil
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
EOF

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase task environment for fixing breaking hook API signature."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]
