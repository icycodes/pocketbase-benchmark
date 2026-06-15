FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip jq build-essential && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests pytest-xprocess && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Go 1.22 (required to build the PocketBase v0.31.0 Go module)
RUN curl -fsSL https://go.dev/dl/go1.22.5.linux-amd64.tar.gz -o /tmp/go.tar.gz && \
    tar -C /usr/local -xzf /tmp/go.tar.gz && \
    rm /tmp/go.tar.gz && \
    ln -s /usr/local/go/bin/go /usr/local/bin/go && \
    ln -s /usr/local/go/bin/gofmt /usr/local/bin/gofmt

ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH="/root/go"
ENV GOCACHE="/root/.cache/go-build"

# Install the prebuilt PocketBase v0.31.0 binary (used only to bootstrap pb_data and apply seed migrations)
RUN curl -fsSL https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip -o /tmp/pb.zip && \
    unzip /tmp/pb.zip -d /tmp/pb && \
    mv /tmp/pb/pocketbase /usr/local/bin/pocketbase && \
    chmod +x /usr/local/bin/pocketbase && \
    rm -rf /tmp/pb /tmp/pb.zip

RUN mkdir -p /home/user && chmod 0755 /home/user

# Initialise the Go module pinned to PocketBase v0.31.0 and pre-download its dependencies.
RUN mkdir -p /home/user/myproject && cd /home/user/myproject && \
    go mod init myproject && \
    go get github.com/pocketbase/pocketbase@v0.31.0 && \
    go mod download

# Write JS migration files that pre-create the `posts` and `audit_log` collections
# and seed a regular user. These run via the prebuilt PocketBase binary at build time only.
RUN mkdir -p /home/user/myproject/pb_migrations && \
    cat >/home/user/myproject/pb_migrations/1700000001_create_posts.js <<'EOF'
migrate((app) => {
  const collection = new Collection({
    type: "base",
    name: "posts",
    listRule: "@request.auth.id != \"\"",
    viewRule: "@request.auth.id != \"\"",
    createRule: "@request.auth.id != \"\"",
    updateRule: "@request.auth.id != \"\"",
    deleteRule: "@request.auth.id != \"\"",
    fields: [
      { name: "title", type: "text", required: true },
      { name: "content", type: "text" }
    ]
  });
  app.save(collection);
}, (app) => {
  try {
    const c = app.findCollectionByNameOrId("posts");
    app.delete(c);
  } catch (_) {}
});
EOF

RUN cat >/home/user/myproject/pb_migrations/1700000002_create_audit_log.js <<'EOF'
migrate((app) => {
  const collection = new Collection({
    type: "base",
    name: "audit_log",
    fields: [
      { name: "actor", type: "text" },
      { name: "action", type: "text" },
      { name: "collection", type: "text" },
      { name: "record", type: "text" },
      { name: "at", type: "date" },
      { name: "diff", type: "json", maxSize: 2000000 }
    ]
  });
  app.save(collection);
}, (app) => {
  try {
    const c = app.findCollectionByNameOrId("audit_log");
    app.delete(c);
  } catch (_) {}
});
EOF

RUN cat >/home/user/myproject/pb_migrations/1700000003_seed_user.js <<'EOF'
migrate((app) => {
  const users = app.findCollectionByNameOrId("users");
  const r = new Record(users);
  r.set("email", "user@example.com");
  r.set("password", "testpass1234");
  r.set("emailVisibility", true);
  r.set("verified", true);
  app.save(r);
}, (app) => {
  try {
    const r = app.findAuthRecordByEmail("users", "user@example.com");
    app.delete(r);
  } catch (_) {}
});
EOF

# Bootstrap pb_data: create the superuser (which initialises the SQLite DB with all
# system collections including the default `users` auth collection) and then apply
# the seed migrations so `posts`, `audit_log`, and the regular user exist before the
# executor starts. Finally remove the JS migrations directory so the executor's Go app
# does not surface them as project artefacts.
RUN cd /home/user/myproject && \
    /usr/local/bin/pocketbase --dir pb_data superuser create admin@example.com adminpass1234 && \
    /usr/local/bin/pocketbase --dir pb_data migrate up && \
    rm -rf /home/user/myproject/pb_migrations

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 Go task environment with pre-seeded posts and audit_log collections and a regular user."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - extra pip3 packages: requests, pytest-xprocess (used by the final-state pytest)
#   - Go 1.22.5 toolchain at /usr/local/go installed for building the PocketBase Go app
#   - Prebuilt PocketBase v0.31.0 binary at /usr/local/bin/pocketbase used only at build time to seed pb_data
#   - /home/user/myproject: Go module pinned to github.com/pocketbase/pocketbase v0.31.0 with a pre-seeded pb_data directory
#   - Pre-seeded collections: posts (base, with text `title`), audit_log (base: actor/action/collection/record/at/diff)
#   - Pre-seeded credentials: superuser admin@example.com / adminpass1234 and regular user user@example.com / testpass1234
