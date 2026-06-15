FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

# Install PocketBase v0.31.0 into /home/user/myproject. The release archive
# only ships an amd64 linux binary, which matches the runtime architecture
# of the Harbor evaluator base image.
RUN mkdir -p /home/user/myproject/pb_data /home/user/myproject/pb_migrations /home/user/myproject/pb_public && \
    cd /tmp && \
    curl -fsSL -o pocketbase.zip \
        https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip -o pocketbase.zip -d /home/user/myproject && \
    rm -f pocketbase.zip && \
    chmod +x /home/user/myproject/pocketbase

# Bootstrap the initial superuser non-interactively. `superuser upsert` was
# introduced in v0.23+ and is the official non-interactive bootstrap path; it
# creates the `pb_data/data.db` file with an embedded superuser record so the
# REST API can be exercised immediately on first `serve`.
RUN cd /home/user/myproject && \
    ./pocketbase superuser upsert admin@example.com 'Adm1n_Password!'

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 environment with a bootstrapped superuser, prepared for the multi-tenant access-rules task."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - additional apt packages: unzip (for extracting the PocketBase release zip)
#   - always required pip3 packages: pytest-json-ctrf
#   - additional pip3 packages: requests (used by the verification tests via urllib only, kept for agent convenience)
#   - PocketBase v0.31.0 binary at /home/user/myproject/pocketbase
#   - /home/user/myproject/pb_data: PocketBase data directory with bootstrapped superuser (admin@example.com / Adm1n_Password!)
#   - /home/user/myproject/pb_migrations: empty migrations directory ready for agent-authored migrations
#   - /home/user/myproject/pb_public: empty public assets directory
#   - The PocketBase server is NOT started in the image; it is launched by tests/initial-state setup with: ./pocketbase serve --http=0.0.0.0:8090 --dir=./pb_data --migrationsDir=./pb_migrations
