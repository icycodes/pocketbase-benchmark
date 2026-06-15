FROM ubuntu:24.04

# -----------------------------------------------------------------------------
# Base packages, Python tooling, and Python dependencies for the verifier.
# -----------------------------------------------------------------------------
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep \
        unzip jq procps && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages \
        pytest-json-ctrf \
        requests \
        pytest-xprocess && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# Install PocketBase v0.31.0 binary into the project directory.
# -----------------------------------------------------------------------------
RUN mkdir -p /home/user && chmod 0755 /home/user && \
    mkdir -p /home/user/myproject && \
    cd /tmp && \
    curl -fsSL -o pocketbase.zip \
        https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip -o pocketbase.zip -d /home/user/myproject && \
    chmod +x /home/user/myproject/pocketbase && \
    rm -f pocketbase.zip

# -----------------------------------------------------------------------------
# Pre-seed the PocketBase instance:
#   - superuser:  admin@example.com / SuperAdmin1234
#   - users.A:    alice@example.com / AlicePass1234
#   - users.B:    bob@example.com   / BobPass1234
#
# The `notifications` collection is intentionally NOT created here; the
# executor is expected to add it (via REST API, JSVM migration, or hook).
# -----------------------------------------------------------------------------
RUN mkdir -p /home/user/myproject/pb_migrations && \
    mkdir -p /home/user/myproject/pb_hooks && \
    mkdir -p /home/user/myproject/pb_public && \
    cat > /home/user/myproject/pb_migrations/1700000000_seed_users.js <<'EOF'
/// <reference path="../pb_data/types.d.ts" />

migrate((app) => {
    const users = app.findCollectionByNameOrId("users");

    const alice = new Record(users);
    alice.set("email", "alice@example.com");
    alice.set("emailVisibility", true);
    alice.set("verified", true);
    alice.set("name", "Alice");
    alice.setPassword("AlicePass1234");
    app.save(alice);

    const bob = new Record(users);
    bob.set("email", "bob@example.com");
    bob.set("emailVisibility", true);
    bob.set("verified", true);
    bob.set("name", "Bob");
    bob.setPassword("BobPass1234");
    app.save(bob);
}, (app) => {
    try {
        const alice = app.findAuthRecordByEmail("users", "alice@example.com");
        app.delete(alice);
    } catch (e) { /* ignore */ }
    try {
        const bob = app.findAuthRecordByEmail("users", "bob@example.com");
        app.delete(bob);
    } catch (e) { /* ignore */ }
})
EOF

# Initialize the data directory: create the superuser and apply the seed
# migration so the test users exist before the executor starts.
RUN cd /home/user/myproject && \
    ./pocketbase superuser upsert admin@example.com SuperAdmin1234 && \
    ./pocketbase migrate up

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 self-hosted instance pre-seeded with a superuser plus users alice and bob; the notifications collection is the executor's task to configure."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip jq procps
#   - pip3 packages: pytest-json-ctrf requests pytest-xprocess
#   - PocketBase v0.31.0 binary at /home/user/myproject/pocketbase
#   - /home/user/myproject/pb_data: SQLite database initialised with one
#     superuser and the auth records for alice@example.com and bob@example.com
#   - /home/user/myproject/pb_migrations: seed migration that created the users
#   - /home/user/myproject/pb_hooks: empty hooks directory ready for the
#     executor to drop JSVM scripts into (optional, not required by the task)
