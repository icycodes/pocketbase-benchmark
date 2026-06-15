FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep golang-go && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests pytest-xprocess && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

RUN cat >/home/user/mock_server.py <<'EOF'
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/subscription":
            qs = parse_qs(parsed.query)
            user_id = qs.get("userId", [""])[0]
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            if user_id == "active_user":
                self.wfile.write(json.dumps({"status": "active"}).encode())
            elif user_id == "inactive_user":
                self.wfile.write(json.dumps({"status": "inactive"}).encode())
            else:
                self.wfile.write(json.dumps({"status": "error"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8080), Handler)
    server.serve_forever()
EOF

RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    go mod init myproject && \
    go get github.com/pocketbase/pocketbase@v0.31.0 && \
    go mod tidy

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase Go framework task environment with a pre-configured mock API server."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - golang-go for building the PocketBase Go framework app
#   - requests and pytest-xprocess for verification scripts
#   - /home/user/mock_server.py: simple Python HTTP server to mock the external subscription API
#   - /home/user/myproject: initialized Go module with PocketBase dependency
