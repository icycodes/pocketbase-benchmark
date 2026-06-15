FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep \
        unzip gnupg && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Dart SDK (stable 3.5.4) at /usr/local/dart-sdk
RUN curl -fsSL -o /tmp/dartsdk.zip \
        https://storage.googleapis.com/dart-archive/channels/stable/release/3.5.4/sdk/dartsdk-linux-x64-release.zip && \
    unzip -q /tmp/dartsdk.zip -d /usr/local && \
    rm /tmp/dartsdk.zip && \
    ln -s /usr/local/dart-sdk/bin/dart /usr/local/bin/dart && \
    ln -s /usr/local/dart-sdk/bin/dartaotruntime /usr/local/bin/dartaotruntime

ENV PUB_CACHE=/home/user/.pub-cache
ENV PATH=/usr/local/dart-sdk/bin:/home/user/.pub-cache/bin:${PATH}

# Install PocketBase v0.31.0
RUN curl -fsSL -o /tmp/pocketbase.zip \
        https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip -q /tmp/pocketbase.zip -d /usr/local/bin && \
    chmod +x /usr/local/bin/pocketbase && \
    rm /tmp/pocketbase.zip

# Bootstrap user directory & project scaffold
RUN mkdir -p /home/user && chmod 0755 /home/user && \
    mkdir -p /home/user/myproject && \
    mkdir -p /home/user/pb/pb_data && \
    mkdir -p /home/user/pb/pb_migrations && \
    mkdir -p "${PUB_CACHE}"

# Preload schema via JS migration (creates users/categories/posts/comments)
RUN cat >/home/user/pb/pb_migrations/1700000000_init.js <<'EOF'
/// <reference path="../pb_data/types.d.ts" />
migrate(
  (app) => {
    const users = new Collection({
      type: "auth",
      name: "users",
      listRule: "",
      viewRule: "",
      createRule: "",
      updateRule: "id = @request.auth.id",
      deleteRule: "id = @request.auth.id",
      fields: [
        { name: "name", type: "text", max: 255 },
      ],
    });
    app.save(users);

    const categories = new Collection({
      type: "base",
      name: "categories",
      listRule: "",
      viewRule: "",
      createRule: "",
      updateRule: "",
      deleteRule: "",
      fields: [
        { name: "name", type: "text", required: true, max: 255 },
      ],
    });
    app.save(categories);

    const posts = new Collection({
      type: "base",
      name: "posts",
      listRule: "",
      viewRule: "",
      createRule: "",
      updateRule: "",
      deleteRule: "",
      fields: [
        { name: "title", type: "text", required: true, max: 255 },
        {
          name: "category",
          type: "relation",
          required: true,
          collectionId: categories.id,
          maxSelect: 1,
          cascadeDelete: false,
        },
        {
          name: "author",
          type: "relation",
          required: false,
          collectionId: users.id,
          maxSelect: 1,
          cascadeDelete: false,
        },
      ],
    });
    app.save(posts);

    const comments = new Collection({
      type: "base",
      name: "comments",
      listRule: "",
      viewRule: "",
      createRule: "",
      updateRule: "",
      deleteRule: "",
      fields: [
        { name: "content", type: "text", required: true, max: 5000 },
        {
          name: "post",
          type: "relation",
          required: true,
          collectionId: posts.id,
          maxSelect: 1,
          cascadeDelete: true,
        },
        {
          name: "author",
          type: "relation",
          required: true,
          collectionId: users.id,
          maxSelect: 1,
          cascadeDelete: false,
        },
      ],
    });
    app.save(comments);
  },
  (app) => {
    for (const name of ["comments", "posts", "categories", "users"]) {
      try {
        const c = app.findCollectionByNameOrId(name);
        app.delete(c);
      } catch (e) {}
    }
  }
);
EOF

# Startup script: idempotent superuser upsert + serve
RUN cat >/usr/local/bin/start-pocketbase.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
PB_DIR=/home/user/pb
DATA_DIR="${PB_DIR}/pb_data"
MIG_DIR="${PB_DIR}/pb_migrations"
SU_EMAIL="${SUPERUSER_EMAIL:-admin@example.com}"
SU_PASS="${SUPERUSER_PASSWORD:-Admin12345!}"

mkdir -p "${DATA_DIR}"

# Apply pending migrations (creates default _superusers + custom collections).
pocketbase migrate up --dir="${DATA_DIR}" --migrationsDir="${MIG_DIR}" >/dev/null 2>&1 || true

# Ensure superuser exists (idempotent).
pocketbase superuser upsert "${SU_EMAIL}" "${SU_PASS}" --dir="${DATA_DIR}" >/dev/null 2>&1 || true

exec pocketbase serve \
    --http=0.0.0.0:8090 \
    --dir="${DATA_DIR}" \
    --migrationsDir="${MIG_DIR}"
EOF
RUN chmod +x /usr/local/bin/start-pocketbase.sh

ENV PB_URL=http://127.0.0.1:8090
ENV SUPERUSER_EMAIL=admin@example.com
ENV SUPERUSER_PASSWORD=Admin12345!

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 + Dart SDK environment for nested-relation expand task."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - apt: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip gnupg
#   - pip3: pytest-json-ctrf, requests
#   - Dart SDK 3.5.4 at /usr/local/dart-sdk (dart in PATH)
#   - PocketBase v0.31.0 binary at /usr/local/bin/pocketbase
#   - /home/user/pb/pb_migrations: JS migration creating users/categories/posts/comments collections
#   - /usr/local/bin/start-pocketbase.sh: idempotent superuser upsert + serve
#   - /home/user/myproject: empty project directory for the agent's Dart CLI
