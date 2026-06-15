FROM ubuntu:24.04

ARG POCKETBASE_VERSION=0.31.0

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install PocketBase v0.31.0 binary.
RUN ARCH="$(dpkg --print-architecture)" && \
    case "$ARCH" in \
        amd64) PB_ARCH="amd64" ;; \
        arm64) PB_ARCH="arm64" ;; \
        *) echo "Unsupported arch: $ARCH" >&2; exit 1 ;; \
    esac && \
    curl -fsSL -o /tmp/pocketbase.zip \
        "https://github.com/pocketbase/pocketbase/releases/download/v${POCKETBASE_VERSION}/pocketbase_${POCKETBASE_VERSION}_linux_${PB_ARCH}.zip" && \
    unzip -o /tmp/pocketbase.zip -d /usr/local/bin && \
    chmod +x /usr/local/bin/pocketbase && \
    rm -f /tmp/pocketbase.zip && \
    /usr/local/bin/pocketbase --version

RUN mkdir -p /home/user && chmod 0755 /home/user

# Prepare the PocketBase project layout.
RUN mkdir -p /home/user/myproject/pb_hooks \
             /home/user/myproject/pb_migrations \
             /home/user/myproject/pb_public \
             /home/user/myproject/pb_data

# Pre-create the `photos` collection so the agent only needs to wire up file
# access rules and the JSVM thumb-whitelist hook. The migration is mounted
# automatically the first time PocketBase starts.
RUN cat > /home/user/myproject/pb_migrations/1700000000_create_photos_collection.js <<'EOF'
/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
    const users = app.findCollectionByNameOrId("users")

    const collection = new Collection({
        type: "base",
        name: "photos",
        listRule: "owner = @request.auth.id || is_public = true",
        viewRule: "owner = @request.auth.id || is_public = true",
        createRule: "@request.auth.id != \"\"",
        updateRule: "owner = @request.auth.id",
        deleteRule: "owner = @request.auth.id",
        fields: [
            {
                name: "owner",
                type: "relation",
                required: true,
                collectionId: users.id,
                cascadeDelete: true,
                maxSelect: 1,
            },
            {
                name: "image",
                type: "file",
                required: true,
                maxSelect: 1,
                maxSize: 5242880,
                mimeTypes: ["image/png", "image/jpeg", "image/gif", "image/webp"],
                thumbs: ["100x100", "400x300t"],
                protected: true,
            },
            {
                name: "is_public",
                type: "bool",
                required: false,
            },
        ],
    })

    app.save(collection)
}, (app) => {
    const collection = app.findCollectionByNameOrId("photos")
    app.delete(collection)
})
EOF

# Provide a placeholder JSVM hook file so that pb_hooks is non-empty. The agent
# is expected to replace or augment this file with the unsupported-thumb
# enforcement logic required by the task.
RUN cat > /home/user/myproject/pb_hooks/main.pb.js <<'EOF'
/// <reference path="../pb_data/types.d.ts" />
// Placeholder hook file. The task executor must implement the unsupported-thumb
// guard on top of (or replacing) this file.
EOF

# Bootstrap pb_data: this auto-creates system collections (including the `users`
# auth collection with email + password fields), runs the migration above, and
# creates a superuser account.
RUN cd /home/user/myproject && \
    /usr/local/bin/pocketbase migrate up --migrationsDir /home/user/myproject/pb_migrations --dir /home/user/myproject/pb_data && \
    /usr/local/bin/pocketbase superuser upsert admin@example.com 'Admin12345!' --dir /home/user/myproject/pb_data && \
    ls -la pb_data

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 task environment for the file_thumbnail_view_rule_jsvm task. PocketBase is installed at /usr/local/bin/pocketbase and the project lives under /home/user/myproject. The server is started in test_initial_state.py (not in CMD)."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip
#   - always required pip3 packages: pytest-json-ctrf
#   - pip3 packages required by tests: requests
#   - PocketBase v0.31.0 binary installed at /usr/local/bin/pocketbase
#   - /home/user/myproject: project directory with pb_hooks, pb_migrations, pb_public, pb_data subdirectories
#   - /home/user/myproject/pb_migrations/1700000000_create_photos_collection.js: bootstrap migration that creates the `photos` base collection with predeclared thumbs 100x100 / 400x300t and the required ViewRule
#   - /home/user/myproject/pb_hooks/main.pb.js: placeholder hook file (must be extended by the task executor)
#   - pb_data bootstrapped via `pocketbase migrate up` and `pocketbase superuser upsert` with default system collections (incl. `users`) and a superuser
#   - PocketBase is NOT started in CMD; it is started during test_initial_state.py via a background subprocess
