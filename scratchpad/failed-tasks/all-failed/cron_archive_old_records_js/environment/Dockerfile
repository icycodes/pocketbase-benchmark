FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip sqlite3 && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests pytest-xprocess && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

RUN mkdir -p /workspace && \
    cd /workspace && \
    wget https://github.com/pocketbase/pocketbase/releases/download/v0.22.13/pocketbase_0.22.13_linux_amd64.zip && \
    unzip pocketbase_0.22.13_linux_amd64.zip && \
    rm pocketbase_0.22.13_linux_amd64.zip && \
    chmod +x pocketbase && \
    mkdir -p pb_hooks pb_data && \
    sqlite3 pb_data/data.db "CREATE TABLE _collections (id TEXT PRIMARY KEY, system INTEGER DEFAULT 0, type TEXT DEFAULT 'base', name TEXT UNIQUE NOT NULL, schema TEXT DEFAULT '[]', indexes TEXT DEFAULT '[]', listRule TEXT DEFAULT NULL, viewRule TEXT DEFAULT NULL, createRule TEXT DEFAULT NULL, updateRule TEXT DEFAULT NULL, deleteRule TEXT DEFAULT NULL, options TEXT DEFAULT '{}', created TEXT DEFAULT '', updated TEXT DEFAULT '');" && \
    sqlite3 pb_data/data.db "INSERT INTO _collections (id, name, type, system, schema, listRule, viewRule, createRule, updateRule, deleteRule, options, created, updated) VALUES ('messages1234567', 'messages', 'base', 0, '[{\"system\":false,\"id\":\"archived_field\",\"name\":\"archived\",\"type\":\"bool\",\"required\":false,\"presentable\":false,\"unique\":false,\"options\":{}}]', '', '', '', '', '', '{}', '2023-01-01 00:00:00.000Z', '2023-01-01 00:00:00.000Z');" && \
    sqlite3 pb_data/data.db "CREATE TABLE messages (id TEXT PRIMARY KEY, archived INTEGER DEFAULT 0, created TEXT DEFAULT '', updated TEXT DEFAULT '');"

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase JS cron job task environment with a pre-configured messages collection."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip sqlite3
#   - always required pip3 packages: pytest-json-ctrf requests pytest-xprocess
#   - PocketBase v0.22.13 downloaded to /workspace
#   - /workspace/pb_data/data.db initialized with messages collection
