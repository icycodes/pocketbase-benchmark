FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep \
        unzip jq procps && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install PocketBase v0.31.0 binary
RUN curl -L -o /tmp/pocketbase.zip \
        https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    mkdir -p /opt/pocketbase && \
    unzip /tmp/pocketbase.zip -d /opt/pocketbase && \
    rm /tmp/pocketbase.zip && \
    chmod +x /opt/pocketbase/pocketbase && \
    ln -s /opt/pocketbase/pocketbase /usr/local/bin/pocketbase

RUN mkdir -p /home/user && chmod 0755 /home/user

# Project workspace pre-populated with the PocketBase JS SDK so the
# executor can `require('pocketbase')` from /home/user/myproject.
RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    printf '%s\n' \
        '{' \
        '  "name": "batch-atomic-records",' \
        '  "version": "1.0.0",' \
        '  "private": true,' \
        '  "dependencies": {' \
        '    "pocketbase": "^0.26.0"' \
        '  }' \
        '}' > package.json && \
    npm install --no-audit --no-fund

# PocketBase data directory and superuser credentials baked into the image
ENV PB_DATA_DIR=/var/pb_data
ENV PB_URL=http://127.0.0.1:8090
ENV PB_ADMIN_EMAIL=admin@example.com
ENV PB_ADMIN_PASSWORD=Adminpass12345!

RUN mkdir -p ${PB_DATA_DIR} && \
    pocketbase --dir=${PB_DATA_DIR} superuser upsert "${PB_ADMIN_EMAIL}" "${PB_ADMIN_PASSWORD}"

# Idempotent helper that starts PocketBase as a detached background service.
RUN printf '%s\n' \
        '#!/bin/bash' \
        'set -u' \
        'if curl -fsS http://127.0.0.1:8090/api/health >/dev/null 2>&1; then' \
        '  exit 0' \
        'fi' \
        'mkdir -p /var/log' \
        'nohup /usr/local/bin/pocketbase --dir=/var/pb_data serve --http=0.0.0.0:8090 \' \
        '  >>/var/log/pocketbase.log 2>&1 &' \
        'disown || true' \
        'for i in $(seq 1 120); do' \
        '  if curl -fsS http://127.0.0.1:8090/api/health >/dev/null 2>&1; then' \
        '    exit 0' \
        '  fi' \
        '  sleep 0.5' \
        'done' \
        'echo "PocketBase failed to start within 60s" >&2' \
        'tail -n 200 /var/log/pocketbase.log >&2 || true' \
        'exit 1' \
        > /usr/local/bin/start-pocketbase.sh && \
    chmod +x /usr/local/bin/start-pocketbase.sh

# Bootstrap script: enable batch API and create the two collections.
RUN printf '%s\n' \
        'import json, os, sys, urllib.error, urllib.request' \
        '' \
        'PB_URL = "http://127.0.0.1:8090"' \
        'EMAIL = os.environ["PB_ADMIN_EMAIL"]' \
        'PASSWORD = os.environ["PB_ADMIN_PASSWORD"]' \
        '' \
        'def req(method, path, body=None, token=None):' \
        '    url = PB_URL + path' \
        '    data = json.dumps(body).encode() if body is not None else None' \
        '    headers = {"Content-Type": "application/json"}' \
        '    if token: headers["Authorization"] = token' \
        '    r = urllib.request.Request(url, data=data, headers=headers, method=method)' \
        '    try:' \
        '        with urllib.request.urlopen(r) as resp:' \
        '            txt = resp.read().decode() or "null"' \
        '            return json.loads(txt)' \
        '    except urllib.error.HTTPError as e:' \
        '        body = e.read().decode()' \
        '        raise SystemExit(f"HTTP {e.code} on {method} {path}: {body}")' \
        '' \
        'auth = req("POST", "/api/collections/_superusers/auth-with-password",' \
        '           {"identity": EMAIL, "password": PASSWORD})' \
        'token = auth["token"]' \
        '' \
        'settings = req("GET", "/api/settings", token=token)' \
        'settings["batch"] = {"enabled": True, "maxRequests": 100, "timeout": 30, "maxBodySize": 0}' \
        'req("PATCH", "/api/settings", settings, token=token)' \
        '' \
        'def ensure_orders():' \
        '    try:' \
        '        return req("GET", "/api/collections/orders", token=token)' \
        '    except SystemExit:' \
        '        pass' \
        '    return req("POST", "/api/collections", {' \
        '        "name": "orders",' \
        '        "type": "base",' \
        '        "listRule": "",' \
        '        "viewRule": "",' \
        '        "createRule": "",' \
        '        "updateRule": "",' \
        '        "deleteRule": None,' \
        '        "fields": [' \
        '            {"name": "customer", "type": "text", "required": False},' \
        '            {"name": "total", "type": "number", "required": False},' \
        '        ],' \
        '    }, token=token)' \
        '' \
        'orders = ensure_orders()' \
        'orders_id = orders["id"]' \
        '' \
        'def ensure_order_items():' \
        '    try:' \
        '        return req("GET", "/api/collections/order_items", token=token)' \
        '    except SystemExit:' \
        '        pass' \
        '    return req("POST", "/api/collections", {' \
        '        "name": "order_items",' \
        '        "type": "base",' \
        '        "listRule": "",' \
        '        "viewRule": "",' \
        '        "createRule": "",' \
        '        "updateRule": "",' \
        '        "deleteRule": None,' \
        '        "fields": [' \
        '            {"name": "order", "type": "relation", "required": True,' \
        '             "collectionId": orders_id, "cascadeDelete": True, "maxSelect": 1, "minSelect": 1},' \
        '            {"name": "product", "type": "text", "required": True},' \
        '            {"name": "quantity", "type": "number", "required": True, "min": 1, "onlyInt": True},' \
        '        ],' \
        '    }, token=token)' \
        '' \
        'ensure_order_items()' \
        'print("PocketBase bootstrap complete: batch enabled, collections ready.")' \
        > /usr/local/bin/bootstrap_pb.py

# Run the server once at build time to apply the bootstrap, then shut it down.
RUN /usr/local/bin/start-pocketbase.sh && \
    python3 /usr/local/bin/bootstrap_pb.py && \
    pkill -f "pocketbase.*serve" || true && \
    sleep 1

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 server (batch API enabled, orders/order_items collections) with Node.js v22 LTS and the pocketbase JS SDK for a transactional batch-create benchmark task."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - PocketBase v0.31.0 binary installed to /usr/local/bin/pocketbase
#   - Pre-provisioned superuser (env: PB_ADMIN_EMAIL / PB_ADMIN_PASSWORD)
#   - Pre-created collections: orders (customer, total) and order_items (order relation, product, quantity>=1)
#   - Batch Web API enabled in settings (maxRequests=100)
#   - Node.js v22 LTS for the executor's `node app.js` script
#   - /home/user/myproject: project workspace with the `pocketbase` JS SDK pre-installed
#   - /usr/local/bin/start-pocketbase.sh: idempotent helper that starts PocketBase in the background
