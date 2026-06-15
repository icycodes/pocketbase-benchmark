FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git unzip python3 python3-pip python3-pytest bash ripgrep && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    pip3 install --break-system-packages pytest-json-ctrf pytest-xprocess requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# --- Install PocketBase v0.31.0 -------------------------------------------------
RUN mkdir -p /opt/pocketbase && \
    cd /opt/pocketbase && \
    curl -fsSL -o pocketbase.zip \
        https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip pocketbase.zip && \
    rm pocketbase.zip && \
    chmod +x /opt/pocketbase/pocketbase && \
    ln -s /opt/pocketbase/pocketbase /usr/local/bin/pocketbase

# --- Create base user directory -------------------------------------------------
RUN mkdir -p /home/user && chmod 0755 /home/user

# --- PocketBase data directory --------------------------------------------------
RUN mkdir -p /home/user/pb /home/user/pb/pb_data /home/user/pb/pb_migrations /home/user/pb/pb_hooks /home/user/pb/pb_public

# --- PocketBase startup script (idempotent) ------------------------------------
RUN cat > /usr/local/bin/start-pocketbase.sh <<'EOS'
#!/usr/bin/env bash
# Idempotent startup script for the seeded PocketBase server.
set -u
PB_DIR=/home/user/pb
PB_URL=http://127.0.0.1:8090
SU_EMAIL=harbor-admin@example.com
SU_PASSWORD=harbor-admin-pass-1234
USER_EMAIL=harbor-user@example.com
USER_PASSWORD=harbor-pass-1234

# If already healthy, nothing to do.
if curl -fsS "$PB_URL/api/health" >/dev/null 2>&1; then
    exit 0
fi

cd "$PB_DIR" || exit 1

# Ensure a superuser exists (upsert is idempotent).
/usr/local/bin/pocketbase superuser upsert "$SU_EMAIL" "$SU_PASSWORD" >/tmp/pb_su.log 2>&1 || true

# Start the server in the background.
nohup /usr/local/bin/pocketbase serve --http=0.0.0.0:8090 --dir "$PB_DIR/pb_data" \
    --migrationsDir "$PB_DIR/pb_migrations" --hooksDir "$PB_DIR/pb_hooks" \
    --publicDir "$PB_DIR/pb_public" >/tmp/pocketbase.log 2>&1 &
echo $! > /tmp/pocketbase.pid

# Wait until the API is up.
for _ in $(seq 1 60); do
    if curl -fsS "$PB_URL/api/health" >/dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

# If the seeded user can already authenticate, we are done.
if curl -fsS -X POST "$PB_URL/api/collections/users/auth-with-password" \
        -H "Content-Type: application/json" \
        -d "{\"identity\":\"$USER_EMAIL\",\"password\":\"$USER_PASSWORD\"}" >/dev/null 2>&1; then
    exit 0
fi

# Otherwise, log in as superuser and create the seeded user record.
SU_AUTH=$(curl -fsS -X POST "$PB_URL/api/collections/_superusers/auth-with-password" \
    -H "Content-Type: application/json" \
    -d "{\"identity\":\"$SU_EMAIL\",\"password\":\"$SU_PASSWORD\"}")

SU_TOKEN=$(echo "$SU_AUTH" | python3 -c 'import json,sys;print(json.loads(sys.stdin.read()).get("token",""))')

if [ -n "$SU_TOKEN" ]; then
    curl -fsS -X POST "$PB_URL/api/collections/users/records" \
        -H "Content-Type: application/json" \
        -H "Authorization: $SU_TOKEN" \
        -d "{\"email\":\"$USER_EMAIL\",\"password\":\"$USER_PASSWORD\",\"passwordConfirm\":\"$USER_PASSWORD\",\"emailVisibility\":true,\"verified\":true,\"name\":\"Harbor Test User\"}" >/tmp/pb_seed_user.log 2>&1 || true
fi
EOS
RUN chmod +x /usr/local/bin/start-pocketbase.sh

# --- Seed PocketBase database & user during image build -------------------------
RUN bash /usr/local/bin/start-pocketbase.sh && \
    sleep 2 && \
    # Verify the seeded user can authenticate, then stop the build-time server.
    curl -fsS -X POST http://127.0.0.1:8090/api/collections/users/auth-with-password \
        -H "Content-Type: application/json" \
        -d '{"identity":"harbor-user@example.com","password":"harbor-pass-1234"}' >/tmp/seed_check.json && \
    if [ -f /tmp/pocketbase.pid ]; then kill "$(cat /tmp/pocketbase.pid)" || true; fi && \
    sleep 1

# --- Scaffold a minimal SvelteKit project at /home/user/myproject --------------
RUN mkdir -p /home/user/myproject/src/routes /home/user/myproject/static

RUN cat > /home/user/myproject/package.json <<'EOF'
{
  "name": "harbor-sveltekit-pb",
  "version": "0.0.1",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite dev",
    "build": "vite build",
    "preview": "vite preview"
  },
  "devDependencies": {
    "@sveltejs/adapter-node": "^5.2.0",
    "@sveltejs/kit": "^2.8.0",
    "@sveltejs/vite-plugin-svelte": "^4.0.0",
    "svelte": "^5.0.0",
    "vite": "^5.4.0"
  },
  "dependencies": {
    "pocketbase": "^0.26.0"
  }
}
EOF

RUN cat > /home/user/myproject/svelte.config.js <<'EOF'
import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
    preprocess: vitePreprocess(),
    kit: {
        adapter: adapter()
    }
};

export default config;
EOF

RUN cat > /home/user/myproject/vite.config.js <<'EOF'
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
    plugins: [sveltekit()]
});
EOF

RUN cat > /home/user/myproject/src/app.html <<'EOF'
<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width" />
        %sveltekit.head%
    </head>
    <body data-sveltekit-preload-data="hover">
        <div style="display: contents">%sveltekit.body%</div>
    </body>
</html>
EOF

RUN cat > /home/user/myproject/src/routes/+page.svelte <<'EOF'
<h1>Harbor PocketBase SvelteKit</h1>
EOF

RUN cat > /home/user/myproject/.npmrc <<'EOF'
fund=false
audit=false
EOF

# Install dependencies (this is intentionally part of the image so node_modules is preloaded).
RUN cd /home/user/myproject && npm install --no-audit --no-fund

LABEL Author="generate-harbor-tasks"
LABEL Description="SvelteKit skeleton + PocketBase v0.31.0 server with a seeded user, prepared for the SSR cookie auth sync task."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git unzip python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf, pytest-xprocess, requests
#   - Node.js v24 (nodesource) for building and running the SvelteKit app
#   - PocketBase v0.31.0 binary symlinked at /usr/local/bin/pocketbase
#   - /home/user/pb: PocketBase server data dir with a seeded superuser and `users` record
#       superuser: harbor-admin@example.com / harbor-admin-pass-1234
#       seed user: harbor-user@example.com / harbor-pass-1234
#   - /home/user/myproject: minimal SvelteKit skeleton with pocketbase JS SDK pre-installed
#   - /usr/local/bin/start-pocketbase.sh: idempotent startup script invoked by test_initial_state.py
