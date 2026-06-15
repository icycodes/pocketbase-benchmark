FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests pytest-xprocess && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

RUN cd /home/user && \
    curl -L -o pocketbase.zip https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip pocketbase.zip -d pocketbase_app && \
    rm pocketbase.zip && \
    cd pocketbase_app && \
    mkdir pb_hooks pb_migrations pb_public

RUN cat > /home/user/pocketbase_app/mock_webhook.py <<'EOF'
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        try:
            data = json.loads(body)
            email = data.get('email', '')
        except json.JSONDecodeError:
            email = ''
        
        if email == 'fail@example.com':
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'Internal Server Error')
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')

    def log_message(self, format, *args):
        pass # Suppress logging

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', 8081), WebhookHandler)
    server.serve_forever()
EOF

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 environment with a mock Python webhook server for JSVM concurrency error handling task."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip
#   - always required pip3 packages: pytest-json-ctrf
#   - task-specific pip3 packages: requests pytest-xprocess
#   - /home/user/pocketbase_app: PocketBase installation directory
#   - /home/user/pocketbase_app/pocketbase: PocketBase binary
#   - /home/user/pocketbase_app/mock_webhook.py: Mock webhook server script
