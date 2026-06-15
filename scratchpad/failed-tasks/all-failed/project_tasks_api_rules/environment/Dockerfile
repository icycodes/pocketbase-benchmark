FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf pytest-xprocess requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

RUN mkdir -p /home/user/app && \
    cd /home/user/app && \
    curl -L -o pocketbase.zip https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip pocketbase.zip && \
    rm pocketbase.zip && \
    mkdir -p pb_hooks pb_migrations pb_public

# Initialize the schema
RUN cd /home/user/app && \
    cat > init_schema.py <<'EOF'
import time
import subprocess
import requests

process = subprocess.Popen(["./pocketbase", "serve", "--http=127.0.0.1:8090"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)

try:
    # Create superuser
    subprocess.run(["./pocketbase", "superuser", "upsert", "admin@example.com", "Admin123456!"], check=True)
    
    # Login
    resp = requests.post("http://127.0.0.1:8090/api/collections/_superusers/auth-with-password", json={"identity": "admin@example.com", "password": "Admin123456!"})
    token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create projects collection
    projects_schema = {
        "name": "projects",
        "type": "base",
        "fields": [
            {"name": "name", "type": "text"},
            {"name": "members", "type": "relation", "collectionId": "_pb_users_auth_", "maxSelect": 999}
        ]
    }
    resp = requests.post("http://127.0.0.1:8090/api/collections", json=projects_schema, headers=headers)
    resp.raise_for_status()
    projects_id = resp.json()["id"]
    
    # Create tasks collection
    tasks_schema = {
        "name": "tasks",
        "type": "base",
        "fields": [
            {"name": "title", "type": "text"},
            {"name": "project", "type": "relation", "collectionId": projects_id, "maxSelect": 1}
        ]
    }
    resp = requests.post("http://127.0.0.1:8090/api/collections", json=tasks_schema, headers=headers)
    resp.raise_for_status()
    
finally:
    process.terminate()
    process.wait()
EOF

RUN cd /home/user/app && python3 init_schema.py && rm init_schema.py

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase environment with pre-configured projects and tasks schema for API rules task."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip
#   - always required pip3 packages: pytest-json-ctrf pytest-xprocess requests
#   - PocketBase v0.31.0 binary at /home/user/app/pocketbase
#   - Initialized database schema with projects and tasks collections
