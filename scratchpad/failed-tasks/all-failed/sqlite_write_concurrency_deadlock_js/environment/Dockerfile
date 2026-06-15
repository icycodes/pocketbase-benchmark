FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests pytest-xprocess && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

RUN mkdir -p /home/user/pocketbase_app && \
    cd /home/user/pocketbase_app && \
    curl -L -o pocketbase.zip https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip pocketbase.zip && \
    rm pocketbase.zip && \
    mkdir -p pb_hooks pb_migrations pb_public

RUN cd /home/user/pocketbase_app && \
    cat > init_db.py <<'EOF'
import time
import requests
import subprocess

p = subprocess.Popen(["./pocketbase", "serve", "--http=127.0.0.1:8090"])
time.sleep(3)

requests.post("http://127.0.0.1:8090/api/admins", json={
    "email": "admin@example.com",
    "password": "adminpassword123",
    "passwordConfirm": "adminpassword123"
})

resp = requests.post("http://127.0.0.1:8090/api/admins/auth-with-password", json={
    "identity": "admin@example.com",
    "password": "adminpassword123"
}).json()
token = resp["token"]
headers = {"Authorization": token}

users = requests.get("http://127.0.0.1:8090/api/collections/users", headers=headers).json()
users["fields"].append({"name": "wallet", "type": "number", "required": True})
requests.patch("http://127.0.0.1:8090/api/collections/users", headers=headers, json=users)

requests.post("http://127.0.0.1:8090/api/collections", headers=headers, json={
    "name": "orders",
    "type": "base",
    "fields": [
        {"name": "user", "type": "relation", "relationOptions": {"collectionId": users["id"], "maxSelect": 1}},
        {"name": "amount", "type": "number"}
    ]
})

requests.post("http://127.0.0.1:8090/api/collections", headers=headers, json={
    "name": "audit_logs",
    "type": "base",
    "fields": [
        {"name": "user", "type": "relation", "relationOptions": {"collectionId": users["id"], "maxSelect": 1}},
        {"name": "order_amount", "type": "number"},
        {"name": "action", "type": "text"}
    ]
})

p.terminate()
p.wait()
EOF

RUN cd /home/user/pocketbase_app && \
    python3 init_db.py && \
    rm init_db.py

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase task environment with pre-configured users, orders, and audit_logs collections for concurrency testing."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip
#   - always required pip3 packages: pytest-json-ctrf requests pytest-xprocess
#   - PocketBase v0.31.0 installed in /home/user/pocketbase_app
#   - Pre-initialized pb_data with users (with wallet), orders, and audit_logs collections
