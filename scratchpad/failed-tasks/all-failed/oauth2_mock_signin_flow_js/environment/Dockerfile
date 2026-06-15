FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PB_URL=http://127.0.0.1:8090 \
    PB_SUPERUSER_EMAIL=admin@example.com \
    PB_SUPERUSER_PASSWORD=AdminPass123! \
    MOCK_OAUTH_URL=http://127.0.0.1:9000

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip jq procps && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    pip3 install --break-system-packages pytest-json-ctrf requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install PocketBase v0.31.0
RUN curl -fsSL -o /tmp/pb.zip https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip /tmp/pb.zip -d /opt/pocketbase && \
    chmod +x /opt/pocketbase/pocketbase && \
    ln -s /opt/pocketbase/pocketbase /usr/local/bin/pocketbase && \
    rm /tmp/pb.zip

RUN mkdir -p /home/user && chmod 0755 /home/user

# PocketBase data / hooks / migrations layout
RUN mkdir -p /home/user/pb/pb_data /home/user/pb/pb_hooks /home/user/pb/pb_migrations

# JSVM migration that wires the users collection to the mock OAuth2 provider
RUN cat > /home/user/pb/pb_migrations/1700000000_setup_mockoauth.js <<'JSVM'
/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
    const collection = app.findCollectionByNameOrId("users");
    collection.oauth2.enabled = true;
    collection.oauth2.providers = [
        {
            name: "oidc",
            displayName: "mockoauth",
            clientId: "mock-client-id",
            clientSecret: "mock-client-secret",
            authURL: "http://127.0.0.1:9000/authorize",
            tokenURL: "http://127.0.0.1:9000/token",
            userInfoURL: "http://127.0.0.1:9000/userinfo"
        }
    ];
    app.save(collection);
}, (app) => {
    const collection = app.findCollectionByNameOrId("users");
    collection.oauth2.providers = (collection.oauth2.providers || []).filter(
        (p) => p.displayName !== "mockoauth"
    );
    app.save(collection);
});
JSVM

# Mock OAuth2 server (Express). Speaks the bare minimum of the
# authorization-code + OIDC userinfo flow needed by PocketBase's
# generic OIDC provider.
RUN mkdir -p /opt/mock-oauth && \
    cd /opt/mock-oauth && \
    npm init -y >/dev/null && \
    npm install --silent express@4
RUN cat > /opt/mock-oauth/server.js <<'JSAPP'
const express = require("express");

const app = express();
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

const PORT = parseInt(process.env.MOCK_OAUTH_PORT || "9000", 10);
const PROVIDER_USER_ID = "mock-user-id-001";
const USER_EMAIL = "oauth-user@example.com";

function b64url(obj) {
    return Buffer.from(JSON.stringify(obj)).toString("base64url");
}

function buildIdToken() {
    const header = b64url({ alg: "none", typ: "JWT" });
    const now = Math.floor(Date.now() / 1000);
    const payload = b64url({
        sub: PROVIDER_USER_ID,
        email: USER_EMAIL,
        email_verified: true,
        name: "OAuth User",
        iss: `http://127.0.0.1:${PORT}`,
        aud: "mock-client-id",
        iat: now,
        exp: now + 3600,
    });
    return `${header}.${payload}.`;
}

app.get("/health", (_req, res) => res.json({ ok: true }));

app.get("/authorize", (req, res) => {
    const redirectUri = req.query.redirect_uri;
    if (!redirectUri || typeof redirectUri !== "string") {
        return res.status(400).send("missing redirect_uri");
    }
    const code = "mockcode_" + Math.random().toString(36).slice(2, 12);
    let target;
    try {
        target = new URL(redirectUri);
    } catch (_e) {
        return res.status(400).send("invalid redirect_uri");
    }
    target.searchParams.set("code", code);
    if (typeof req.query.state === "string") {
        target.searchParams.set("state", req.query.state);
    }
    res.redirect(302, target.toString());
});

app.post("/token", (_req, res) => {
    res.json({
        access_token: "mock-access-token",
        token_type: "Bearer",
        expires_in: 3600,
        id_token: buildIdToken(),
        scope: "openid email profile",
    });
});

app.get("/userinfo", (_req, res) => {
    res.json({
        sub: PROVIDER_USER_ID,
        email: USER_EMAIL,
        email_verified: true,
        name: "OAuth User",
        preferred_username: "oauth-user",
    });
});

app.listen(PORT, "0.0.0.0", () => {
    console.log(`Mock OAuth2 server listening on http://127.0.0.1:${PORT}`);
});
JSAPP

# Project directory with the JS SDK pre-installed.
RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    npm init -y >/dev/null && \
    npm install --silent pocketbase@0.26.2

# Bootstrap PocketBase: create the superuser and run JSVM migrations
# by starting the server briefly so default collections + the mock
# provider config are persisted in pb_data.
RUN pocketbase superuser upsert admin@example.com 'AdminPass123!' \
        --dir /home/user/pb/pb_data && \
    ( pocketbase serve --http=127.0.0.1:8090 \
        --dir /home/user/pb/pb_data \
        --hooksDir /home/user/pb/pb_hooks \
        --migrationsDir /home/user/pb/pb_migrations >/tmp/pb_bootstrap.log 2>&1 & \
      PB_PID=$! ; \
      for i in $(seq 1 30); do \
          if curl -fsS http://127.0.0.1:8090/api/health >/dev/null 2>&1; then break; fi; \
          sleep 0.5; \
      done; \
      sleep 2; \
      kill $PB_PID 2>/dev/null; \
      wait $PB_PID 2>/dev/null || true )

# Helper script that idempotently launches PocketBase + the mock
# OAuth2 server. The initial-state test invokes this before checks.
RUN cat > /usr/local/bin/start_services.sh <<'SH' && \
    chmod +x /usr/local/bin/start_services.sh
#!/bin/bash
LOG_DIR=/var/log/services
mkdir -p "$LOG_DIR"

if ! curl -fsS http://127.0.0.1:8090/api/health >/dev/null 2>&1; then
    setsid nohup pocketbase serve \
        --http 0.0.0.0:8090 \
        --dir /home/user/pb/pb_data \
        --hooksDir /home/user/pb/pb_hooks \
        --migrationsDir /home/user/pb/pb_migrations \
        >"$LOG_DIR/pocketbase.log" 2>&1 < /dev/null &
fi

if ! curl -fsS http://127.0.0.1:9000/health >/dev/null 2>&1; then
    cd /opt/mock-oauth && \
        MOCK_OAUTH_PORT=9000 setsid nohup node server.js \
            >"$LOG_DIR/mock-oauth.log" 2>&1 < /dev/null &
fi

for i in $(seq 1 60); do
    if curl -fsS http://127.0.0.1:8090/api/health >/dev/null 2>&1 \
        && curl -fsS http://127.0.0.1:9000/health >/dev/null 2>&1; then
        exit 0
    fi
    sleep 0.5
done
echo "services failed to come up" >&2
exit 1
SH

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 + JS SDK + local mock OAuth2 server for server-side OAuth2 code flow tasks."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf, requests
#   - Node.js v24 + npm (for the JS SDK CLI and the mock OAuth2 server)
#   - PocketBase v0.31.0 binary at /usr/local/bin/pocketbase, data at /home/user/pb
#   - /home/user/pb/pb_migrations/1700000000_setup_mockoauth.js wires the users
#     collection to the mock OAuth2 provider (displayName "mockoauth", provider name "oidc")
#   - /opt/mock-oauth: Express-based mock OAuth2 / OIDC server (port 9000)
#   - /home/user/myproject: working directory with the `pocketbase` JS SDK installed
#   - PocketBase superuser pre-seeded: admin@example.com / AdminPass123!
#   - /usr/local/bin/start_services.sh idempotently boots both servers
