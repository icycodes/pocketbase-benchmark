FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip jq && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf pytest-xprocess requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

RUN mkdir -p /home/user/pb && \
    cd /home/user/pb && \
    wget https://github.com/pocketbase/pocketbase/releases/download/v0.22.22/pocketbase_0.22.22_linux_amd64.zip && \
    unzip pocketbase_0.22.22_linux_amd64.zip && \
    rm pocketbase_0.22.22_linux_amd64.zip && \
    chmod +x pocketbase

RUN cd /home/user/pb && \
    ./pocketbase serve --http=127.0.0.1:8090 > /dev/null 2>&1 & \
    sleep 3 && \
    curl -s -X POST http://127.0.0.1:8090/api/admins -H "Content-Type: application/json" -d '{"email":"admin@example.com", "password":"password123", "passwordConfirm":"password123"}' && \
    TOKEN=$(curl -s -X POST http://127.0.0.1:8090/api/admins/auth-with-password -H "Content-Type: application/json" -d '{"identity":"admin@example.com", "password":"password123"}' | jq -r '.token') && \
    curl -s -X POST http://127.0.0.1:8090/api/collections -H "Authorization: $TOKEN" -H "Content-Type: application/json" -d '{"name":"posts", "type":"base", "schema":[{"name":"image", "type":"file", "options":{"maxSelect":1, "maxSize":5242880, "mimeTypes":["image/png", "image/jpeg"], "thumbs":["100x100"], "protected":false}}], "listRule":"", "viewRule":"", "createRule":"", "updateRule":"", "deleteRule":""}' && \
    kill -9 $(jobs -p) && \
    sleep 1

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase environment with pre-configured posts collection."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip jq
#   - always required pip3 packages: pytest-json-ctrf
#   - additional pip3 packages: pytest-xprocess requests
#   - PocketBase v0.22.22 downloaded and extracted to /home/user/pb
#   - Pre-initialized PocketBase database with a "posts" collection that has a public "image" file field
