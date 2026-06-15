FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests pytest-xprocess && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

RUN mkdir -p /home/user/pocketbase_app && \
    cd /home/user/pocketbase_app && \
    curl -L -o pocketbase.zip https://github.com/pocketbase/pocketbase/releases/download/v0.31.0/pocketbase_0.31.0_linux_amd64.zip && \
    unzip pocketbase.zip && \
    rm pocketbase.zip && \
    mkdir -p pb_hooks pb_migrations pb_public

LABEL Author="generate-harbor-tasks"
LABEL Description="PocketBase v0.31.0 standalone environment with default directories created."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep unzip
#   - always required pip3 packages: pytest-json-ctrf
#   - additional pip3 packages: requests pytest-xprocess
#   - PocketBase v0.31.0 binary installed in /home/user/pocketbase_app/pocketbase
#   - /home/user/pocketbase_app: PocketBase project directory with pb_hooks, pb_migrations, pb_public
